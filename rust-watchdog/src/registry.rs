use anyhow::{Context, Result};
use std::path::{Path, PathBuf};
use std::fs::{self, Permissions};
use std::os::unix::fs::PermissionsExt;
use crate::types::{ProcessRegistry, TaskInfo, OrphanReport, TaskStatus, ExecutionMode};
use crate::process::ProcessManager;

/// Registry manager for persisting task state
pub struct RegistryManager {
    registry_path: PathBuf,
    registry: ProcessRegistry,
}

impl RegistryManager {
    /// Create new registry manager
    pub fn new<P: AsRef<Path>>(path: P) -> Self {
        Self {
            registry_path: PathBuf::from(path.as_ref()),
            registry: ProcessRegistry::new(),
        }
    }

    /// Load registry from disk
    pub fn load(&mut self) -> Result<()> {
        if !self.registry_path.exists() {
            // Create directory if it doesn't exist
            if let Some(parent) = self.registry_path.parent() {
                fs::create_dir_all(parent)
                    .context("Failed to create registry directory")?;
            }

            // Initialize empty registry
            self.registry = ProcessRegistry::new();
            self.save()?;
            return Ok(());
        }

        let content = fs::read_to_string(&self.registry_path)
            .context("Failed to read registry file")?;

        self.registry = serde_json::from_str(&content)
            .context("Failed to parse registry JSON")?;

        Ok(())
    }

    /// Save registry to disk with secure permissions (0600)
    pub fn save(&self) -> Result<()> {
        let json = serde_json::to_string_pretty(&self.registry)
            .context("Failed to serialize registry")?;

        fs::write(&self.registry_path, json)
            .context("Failed to write registry file")?;

        // SECURITY-003: Set permissions to 0600 (owner read/write only)
        // Prevents other users from reading task metadata and command details
        fs::set_permissions(&self.registry_path, Permissions::from_mode(0o600))
            .context("Failed to set registry file permissions to 0600")?;

        Ok(())
    }

    /// Add or update a task
    pub fn upsert_task(&mut self, task_id: String, task: TaskInfo) -> Result<()> {
        self.registry.add_task(task_id, task);
        self.save()
    }

    /// Get task by ID
    pub fn get_task(&self, task_id: &str) -> Option<&TaskInfo> {
        self.registry.get_task(task_id)
    }

    /// Get mutable task reference
    pub fn get_task_mut(&mut self, task_id: &str) -> Option<&mut TaskInfo> {
        self.registry.get_task_mut(task_id)
    }

    /// Remove task
    pub fn remove_task(&mut self, task_id: &str) -> Result<Option<TaskInfo>> {
        let task = self.registry.remove_task(task_id);
        self.save()?;
        Ok(task)
    }

    /// Get all running tasks
    pub fn running_tasks(&self) -> Vec<(&String, &TaskInfo)> {
        self.registry.running_tasks()
    }

    /// Get all completed tasks
    pub fn completed_tasks(&self) -> Vec<(&String, &TaskInfo)> {
        self.registry.completed_tasks()
    }

    /// Find orphaned processes (dead but not marked complete)
    /// and zombie processes (complete but still running)
    pub fn find_orphans(&self) -> OrphanReport {
        let mut report = OrphanReport::default();

        for (task_id, task) in &self.registry.tasks {
            let is_alive = match &task.mode {
                ExecutionMode::Native => {
                    if let Some(native) = &task.native {
                        // Validate it's the same process (not PID recycling)
                        if ProcessManager::validate_process(native.pid, &native.start_time) {
                            ProcessManager::is_alive(native.pid)
                        } else {
                            false // PID was recycled, original process is dead
                        }
                    } else {
                        false
                    }
                }
                ExecutionMode::Docker => {
                    // Docker check requires async, so we'll mark as "unknown" for now
                    // The main watchdog will handle Docker checks
                    true
                }
            };

            // Dead process but task still running
            if !is_alive && task.status == TaskStatus::Running {
                report.dead_processes.push(task_id.clone());
            }

            // Process alive but task marked complete
            if is_alive && task.status == TaskStatus::Completed {
                report.zombie_processes.push(task_id.clone());
            }
        }

        report
    }

    /// Mark task as completed
    pub fn mark_complete(&mut self, task_id: &str) -> Result<()> {
        if let Some(task) = self.registry.get_task_mut(task_id) {
            task.status = TaskStatus::Completed;
            task.completed_at = Some(chrono::Utc::now());
        }
        self.save()
    }

    /// Mark task as failed
    pub fn mark_failed(&mut self, task_id: &str) -> Result<()> {
        if let Some(task) = self.registry.get_task_mut(task_id) {
            task.status = TaskStatus::Failed;
            task.completed_at = Some(chrono::Utc::now());
        }
        self.save()
    }

    /// Get registry statistics
    pub fn stats(&self) -> RegistryStats {
        let total = self.registry.tasks.len();
        let running = self.registry.running_tasks().len();
        let completed = self.registry.completed_tasks().len();
        let failed = self.registry.tasks.values()
            .filter(|t| t.status == TaskStatus::Failed)
            .count();

        RegistryStats {
            total,
            running,
            completed,
            failed,
        }
    }

    /// Cleanup old completed tasks (older than specified days)
    pub fn cleanup_old_tasks(&mut self, days: u64) -> Result<usize> {
        let cutoff = chrono::Utc::now() - chrono::Duration::days(days as i64);
        let mut removed = 0;

        let to_remove: Vec<String> = self
            .registry
            .tasks
            .iter()
            .filter(|(_, task)| {
                matches!(task.status, TaskStatus::Completed | TaskStatus::Failed)
                    && task.completed_at.map_or(false, |c| c < cutoff)
            })
            .map(|(id, _)| id.clone())
            .collect();

        for task_id in to_remove {
            self.registry.remove_task(&task_id);
            removed += 1;
        }

        if removed > 0 {
            self.save()?;
        }

        Ok(removed)
    }

    /// Get reference to inner registry
    pub fn registry(&self) -> &ProcessRegistry {
        &self.registry
    }
}

/// Registry statistics
#[derive(Debug, Clone)]
pub struct RegistryStats {
    pub total: usize,
    pub running: usize,
    pub completed: usize,
    pub failed: usize,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{ExecutionMode, TaskStatus, NativeTask};
    use chrono::Utc;

    #[test]
    fn test_registry_save_load() {
        let temp_path = "/tmp/test_registry.json";
        let mut manager = RegistryManager::new(temp_path);

        // Add a task
        let task = TaskInfo {
            mode: ExecutionMode::Native,
            command: "test command".to_string(),
            status: TaskStatus::Running,
            started_at: Utc::now(),
            completed_at: None,
            native: Some(NativeTask {
                pid: 12345,
                pgid: 12344,
                start_time: "test time".to_string(),
                env_tag: None,
            }),
            docker: None,
            constitution_rules: vec![],
        };

        manager.upsert_task("TEST-001".to_string(), task).unwrap();

        // Load into new manager
        let mut manager2 = RegistryManager::new(temp_path);
        manager2.load().unwrap();

        assert!(manager2.get_task("TEST-001").is_some());

        // Cleanup
        let _ = fs::remove_file(temp_path);
    }
}
