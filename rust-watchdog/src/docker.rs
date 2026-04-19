use anyhow::{Context, Result};
use bollard::Docker;
use bollard::container::{Config, CreateContainerOptions, StopContainerOptions};
use bollard::models::HostConfig;
use futures_util::stream::StreamExt;
use std::collections::HashMap;

/// Docker container manager
pub struct DockerManager {
    client: Docker,
}

impl DockerManager {
    /// Create new Docker manager
    /// Returns None if Docker is not available
    pub fn new() -> Option<Self> {
        match Docker::connect_with_local_defaults() {
            Ok(client) => Some(Self { client }),
            Err(_) => None,
        }
    }

    /// Check if Docker daemon is available
    pub fn is_available() -> bool {
        Docker::connect_with_local_defaults().is_ok()
    }

    /// Run a task in a Docker container
    pub async fn run_container(
        &self,
        task_id: &str,
        command: Vec<String>,
        work_dir: &str,
        memory_limit: &str,
        cpu_limit: &str,
        image: Option<&str>,
    ) -> Result<String> {
        let container_name = format!("dev-task-{}", task_id);
        let image = image.unwrap_or("python:3.11-slim");

        println!("🐳 Starting container: {}", container_name);
        println!("   Image: {}", image);
        println!("   Memory: {}, CPU: {}", memory_limit, cpu_limit);

        // Create container configuration
        // SECURITY FIX: Pass commands directly without shell to prevent injection
        let config = Config {
            image: Some(image.to_string()),
            cmd: Some(command),
            working_dir: Some("/workspace".to_string()),
            host_config: Some(HostConfig {
                binds: Some(vec![format!("{}:/workspace", work_dir)]),
                memory: Some(Self::parse_memory(memory_limit)?),
                nano_cpus: Some((cpu_limit.parse::<f64>()? * 1_000_000_000.0) as i64),
                auto_remove: Some(true),
                ..Default::default()
            }),
            ..Default::default()
        };

        // Create container
        let options = CreateContainerOptions {
            name: container_name.as_str(),
            platform: None,
        };

        let container = self
            .client
            .create_container(Some(options), config)
            .await
            .context("Failed to create container")?;

        // Start container
        self.client
            .start_container::<String>(&container.id, None)
            .await
            .context("Failed to start container")?;

        println!("   ✅ Container started: {}", &container.id[..12]);

        Ok(container.id)
    }

    /// Stop a running container
    pub async fn stop_container(&self, container_id: &str) -> Result<()> {
        println!("🛑 Stopping container: {}", &container_id[..12]);

        let options = StopContainerOptions { t: 2 }; // 2 second timeout

        self.client
            .stop_container(container_id, Some(options))
            .await
            .context("Failed to stop container")?;

        println!("   ✅ Container stopped");

        Ok(())
    }

    /// Check if container is running
    pub async fn is_running(&self, container_id: &str) -> bool {
        if let Ok(inspect) = self.client.inspect_container(container_id, None).await {
            if let Some(state) = inspect.state {
                return state.running.unwrap_or(false);
            }
        }
        false
    }

    /// Get container resource usage
    pub async fn get_stats(&self, container_id: &str) -> Result<ContainerStats> {
        use bollard::container::StatsOptions;
        use futures_util::stream::StreamExt;

        let options = StatsOptions {
            stream: false,
            one_shot: true,
        };

        let mut stream = self.client.stats(container_id, Some(options));

        if let Some(Ok(stats)) = stream.next().await {
            let memory_mb = stats.memory_stats.usage.unwrap_or(0) / 1024 / 1024;

            // Calculate CPU percentage
            let cpu_delta = stats.cpu_stats.cpu_usage.total_usage as f64
                - stats.precpu_stats.cpu_usage.total_usage as f64;
            let system_delta = stats.cpu_stats.system_cpu_usage.unwrap_or(0) as f64
                - stats.precpu_stats.system_cpu_usage.unwrap_or(0) as f64;
            let num_cpus = stats.cpu_stats.online_cpus.unwrap_or(1) as f64;

            let cpu_percent = if system_delta > 0.0 {
                (cpu_delta / system_delta) * num_cpus * 100.0
            } else {
                0.0
            };

            return Ok(ContainerStats {
                cpu_percent: cpu_percent as f32,
                memory_mb,
            });
        }

        anyhow::bail!("Failed to get container stats")
    }

    /// List all dev task containers
    pub async fn list_task_containers(&self) -> Result<Vec<String>> {
        use bollard::container::ListContainersOptions;

        let mut filters = HashMap::new();
        filters.insert("name".to_string(), vec!["dev-task-".to_string()]);

        let options = Some(ListContainersOptions {
            all: true,
            filters,
            ..Default::default()
        });

        let containers = self.client.list_containers(options).await?;

        Ok(containers
            .iter()
            .filter_map(|c| c.id.clone())
            .collect())
    }

    /// Parse memory string (e.g., "512m", "1g") to bytes
    fn parse_memory(mem: &str) -> Result<i64> {
        let mem = mem.trim().to_lowercase();

        if mem.is_empty() {
            anyhow::bail!("Empty memory limit");
        }

        let (num_str, unit) = mem.split_at(mem.len() - 1);
        let num: i64 = num_str
            .parse()
            .context("Invalid memory limit number")?;

        let bytes = match unit {
            "k" => num * 1024,
            "m" => num * 1024 * 1024,
            "g" => num * 1024 * 1024 * 1024,
            _ => anyhow::bail!("Invalid memory unit: {}", unit),
        };

        Ok(bytes)
    }
}

/// Container resource usage
#[derive(Debug, Clone)]
pub struct ContainerStats {
    pub cpu_percent: f32,
    pub memory_mb: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_memory() {
        assert_eq!(DockerManager::parse_memory("512m").unwrap(), 512 * 1024 * 1024);
        assert_eq!(DockerManager::parse_memory("1g").unwrap(), 1024 * 1024 * 1024);
        assert_eq!(DockerManager::parse_memory("2048k").unwrap(), 2048 * 1024);
    }
}
