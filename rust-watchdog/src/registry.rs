use anyhow::{Context, Result};
use std::path::{Path, PathBuf};
use std::fs::{self, OpenOptions, Permissions};
use std::os::unix::fs::PermissionsExt;
use fs2::FileExt;
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

    /// Path to advisory lock file (lives next to registry)
    fn lock_path(&self) -> PathBuf {
        self.registry_path.with_extension("lock")
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

    /// Save registry to disk using atomic write (temp file → rename).
    ///
    /// Callers that need safe concurrent access should use `locked_mutate`
    /// instead, which wraps this with an exclusive advisory lock + re-read.
    pub fn save(&self) -> Result<()> {
        let json = serde_json::to_string_pretty(&self.registry)
            .context("Failed to serialize registry")?;

        // Write to a sibling temp file, then rename (atomic on Linux/macOS)
        let tmp_path = self.registry_path.with_extension("json.tmp");
        fs::write(&tmp_path, &json)
            .context("Failed to write temp registry file")?;

        fs::rename(&tmp_path, &self.registry_path)
            .context("Failed to atomically rename registry file")?;

        // SECURITY-003: Set permissions to 0600 (owner read/write only)
        fs::set_permissions(&self.registry_path, Permissions::from_mode(0o600))
            .context("Failed to set registry file permissions to 0600")?;

        Ok(())
    }

    /// Acquire exclusive advisory lock, re-read registry from disk, apply
    /// mutation closure, then atomically write the result back.
    ///
    /// This is the correct primitive for all state-mutating operations when
    /// multiple `task-watchdog` processes may run concurrently
    /// (e.g. PARALLEL_SWARM tasks completing simultaneously).
    fn locked_mutate<F>(&mut self, f: F) -> Result<()>
    where
        F: FnOnce(&mut ProcessRegistry),
    {
        // Ensure parent directory exists for both registry and lock file
        if let Some(parent) = self.registry_path.parent() {
            fs::create_dir_all(parent)
                .context("Failed to create registry directory")?;
        }

        // Open/create the lock file and acquire an exclusive advisory lock.
        // The lock is released automatically when `lock_file` is dropped.
        let lock_file = OpenOptions::new()
            .create(true)
            .write(true)
            .open(self.lock_path())
            .context("Failed to open registry lock file")?;
        lock_file
            .lock_exclusive()
            .context("Failed to acquire exclusive registry lock")?;

        // Re-read from disk to pick up any updates written by other processes
        // since our last load.
        if self.registry_path.exists() {
            let content = fs::read_to_string(&self.registry_path)
                .context("Failed to re-read registry under lock")?;
            self.registry = serde_json::from_str(&content)
                .context("Failed to parse registry JSON under lock")?;
        }

        // Apply the mutation
        f(&mut self.registry);

        // Atomically write the updated state
        self.save()?;

        // lock_file drops here → flock released
        Ok(())
    }

    /// Add or update a task (concurrent-safe)
    pub fn upsert_task(&mut self, task_id: String, task: TaskInfo) -> Result<()> {
        self.locked_mutate(|r| {
            r.add_task(task_id, task);
        })
    }

    /// Get task by ID
    pub fn get_task(&self, task_id: &str) -> Option<&TaskInfo> {
        self.registry.get_task(task_id)
    }

    /// Get mutable task reference
    pub fn get_task_mut(&mut self, task_id: &str) -> Option<&mut TaskInfo> {
        self.registry.get_task_mut(task_id)
    }

    /// Remove task (concurrent-safe)
    pub fn remove_task(&mut self, task_id: &str) -> Result<Option<TaskInfo>> {
        let mut removed: Option<TaskInfo> = None;
        self.locked_mutate(|r| {
            removed = r.remove_task(task_id);
        })?;
        Ok(removed)
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

    /// Mark task as completed (concurrent-safe)
    pub fn mark_complete(&mut self, task_id: &str) -> Result<()> {
        let id = task_id.to_string();
        self.locked_mutate(|r| {
            if let Some(task) = r.get_task_mut(&id) {
                task.status = TaskStatus::Completed;
                task.completed_at = Some(chrono::Utc::now());
            }
        })
    }

    /// Mark task as failed (concurrent-safe)
    pub fn mark_failed(&mut self, task_id: &str) -> Result<()> {
        let id = task_id.to_string();
        self.locked_mutate(|r| {
            if let Some(task) = r.get_task_mut(&id) {
                task.status = TaskStatus::Failed;
                task.completed_at = Some(chrono::Utc::now());
            }
        })
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

    /// Cleanup old completed tasks (older than specified days) — concurrent-safe
    pub fn cleanup_old_tasks(&mut self, days: u64) -> Result<usize> {
        let cutoff = chrono::Utc::now() - chrono::Duration::days(days as i64);
        let mut removed = 0usize;

        self.locked_mutate(|r| {
            let to_remove: Vec<String> = r
                .tasks
                .iter()
                .filter(|(_, task)| {
                    matches!(task.status, TaskStatus::Completed | TaskStatus::Failed)
                        && task.completed_at.map_or(false, |c| c < cutoff)
                })
                .map(|(id, _)| id.clone())
                .collect();

            removed = to_remove.len();
            for task_id in to_remove {
                r.remove_task(&task_id);
            }
        })?;

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
        let _ = fs::remove_file("/tmp/test_registry.lock");
    }

    #[test]
    fn test_concurrent_upsert_no_data_loss() {
        use std::thread;
        use std::sync::Arc;

        let temp_path = "/tmp/test_registry_concurrent.json";
        let _ = fs::remove_file(temp_path);
        let _ = fs::remove_file("/tmp/test_registry_concurrent.lock");

        // Initialize registry
        let mut init = RegistryManager::new(temp_path);
        init.load().unwrap();

        let path = Arc::new(temp_path.to_string());

        // Spawn 4 threads each writing a distinct task concurrently
        let handles: Vec<_> = (0..4)
            .map(|i| {
                let p = Arc::clone(&path);
                thread::spawn(move || {
                    let mut mgr = RegistryManager::new(p.as_str());
                    mgr.load().unwrap();
                    let task = TaskInfo {
                        mode: ExecutionMode::Native,
                        command: format!("task {i}"),
                        status: TaskStatus::Running,
                        started_at: Utc::now(),
                        completed_at: None,
                        native: Some(NativeTask {
                            pid: 10000 + i as i32,
                            pgid: 10000 + i as i32,
                            start_time: format!("t{i}"),
                            env_tag: None,
                        }),
                        docker: None,
                        constitution_rules: vec![],
                    };
                    mgr.upsert_task(format!("T{:03}", i), task).unwrap();
                })
            })
            .collect();

        for h in handles {
            h.join().unwrap();
        }

        // All 4 tasks must be present — no last-writer-wins data loss
        let mut verify = RegistryManager::new(temp_path);
        verify.load().unwrap();
        for i in 0..4 {
            assert!(
                verify.get_task(&format!("T{:03}", i)).is_some(),
                "T{:03} was lost due to race condition",
                i
            );
        }

        // Cleanup
        let _ = fs::remove_file(temp_path);
        let _ = fs::remove_file("/tmp/test_registry_concurrent.lock");
    }
}
