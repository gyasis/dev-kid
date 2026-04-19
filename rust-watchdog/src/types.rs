use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use std::collections::HashMap;

/// Execution mode for tasks
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum ExecutionMode {
    Native,
    Docker,
}

/// Native process information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NativeTask {
    pub pid: i32,
    pub pgid: i32,
    pub start_time: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub env_tag: Option<String>,
}

/// Docker container information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DockerTask {
    pub container_id: String,
    pub container_name: String,
    pub resource_limits: ResourceLimits,
}

/// Resource limits for Docker containers
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceLimits {
    pub memory: String,
    pub cpu: String,
}

impl Default for ResourceLimits {
    fn default() -> Self {
        Self {
            memory: "512m".to_string(),
            cpu: "1.0".to_string(),
        }
    }
}

/// Task status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum TaskStatus {
    Running,
    Completed,
    Failed,
    Cancelled,
}

impl ToString for TaskStatus {
    fn to_string(&self) -> String {
        match self {
            TaskStatus::Running => "running".to_string(),
            TaskStatus::Completed => "completed".to_string(),
            TaskStatus::Failed => "failed".to_string(),
            TaskStatus::Cancelled => "cancelled".to_string(),
        }
    }
}

/// Complete task information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskInfo {
    pub mode: ExecutionMode,
    pub command: String,
    pub status: TaskStatus,
    pub started_at: DateTime<Utc>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub completed_at: Option<DateTime<Utc>>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub native: Option<NativeTask>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub docker: Option<DockerTask>,

    #[serde(default)]
    pub constitution_rules: Vec<String>,
}

/// Process registry (root structure)
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ProcessRegistry {
    pub tasks: HashMap<String, TaskInfo>,
}

impl ProcessRegistry {
    pub fn new() -> Self {
        Self {
            tasks: HashMap::new(),
        }
    }

    pub fn add_task(&mut self, task_id: String, task: TaskInfo) {
        self.tasks.insert(task_id, task);
    }

    pub fn get_task(&self, task_id: &str) -> Option<&TaskInfo> {
        self.tasks.get(task_id)
    }

    pub fn get_task_mut(&mut self, task_id: &str) -> Option<&mut TaskInfo> {
        self.tasks.get_mut(task_id)
    }

    pub fn remove_task(&mut self, task_id: &str) -> Option<TaskInfo> {
        self.tasks.remove(task_id)
    }

    pub fn running_tasks(&self) -> Vec<(&String, &TaskInfo)> {
        self.tasks
            .iter()
            .filter(|(_, task)| task.status == TaskStatus::Running)
            .collect()
    }

    pub fn completed_tasks(&self) -> Vec<(&String, &TaskInfo)> {
        self.tasks
            .iter()
            .filter(|(_, task)| task.status == TaskStatus::Completed)
            .collect()
    }
}

/// Orphaned task detection results
#[derive(Debug, Default)]
pub struct OrphanReport {
    pub dead_processes: Vec<String>,     // Process died, task not complete
    pub zombie_processes: Vec<String>,    // Task complete, process still running
}

impl OrphanReport {
    pub fn has_issues(&self) -> bool {
        !self.dead_processes.is_empty() || !self.zombie_processes.is_empty()
    }

    pub fn total_issues(&self) -> usize {
        self.dead_processes.len() + self.zombie_processes.len()
    }
}

/// Resource usage snapshot
#[derive(Debug, Clone)]
pub struct ResourceUsage {
    pub cpu_percent: f32,
    pub memory_kb: u64,
}
