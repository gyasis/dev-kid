use anyhow::{Result, bail};
use clap::{Parser, Subcommand};
use tokio::time::{sleep, Duration};
use chrono::Local;
use std::path::PathBuf;

mod types;
mod process;
mod docker;
mod registry;

use types::*;
use process::ProcessManager;
use docker::DockerManager;
use registry::RegistryManager;

#[derive(Parser)]
#[command(name = "task-watchdog")]
#[command(version = env!("CARGO_PKG_VERSION"))]
#[command(about = "High-performance process monitoring daemon for AI coding tools", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Start watchdog daemon (runs continuously)
    Run {
        /// Check interval in seconds
        #[arg(long, default_value = "300")]
        interval: u64,

        /// Registry file path
        #[arg(long, default_value = ".claude/process_registry.json")]
        registry: String,
    },

    /// Check status of a specific task
    Check {
        /// Task ID to check
        task_id: String,

        /// Registry file path
        #[arg(long, default_value = ".claude/process_registry.json")]
        registry: String,
    },

    /// Kill a running task
    Kill {
        /// Task ID to kill
        task_id: String,

        /// Registry file path
        #[arg(long, default_value = ".claude/process_registry.json")]
        registry: String,
    },

    /// Rehydrate context after compression (show what's running)
    Rehydrate {
        /// Registry file path
        #[arg(long, default_value = ".claude/process_registry.json")]
        registry: String,
    },

    /// Show resource usage report
    Report {
        /// Registry file path
        #[arg(long, default_value = ".claude/process_registry.json")]
        registry: String,
    },

    /// Show registry statistics
    Stats {
        /// Registry file path
        #[arg(long, default_value = ".claude/process_registry.json")]
        registry: String,
    },

    /// Cleanup old completed tasks
    Cleanup {
        /// Days to keep (older tasks will be removed)
        #[arg(long, default_value = "7")]
        days: u64,

        /// Registry file path
        #[arg(long, default_value = ".claude/process_registry.json")]
        registry: String,
    },

    /// Register a new task with constitution rules
    Register {
        /// Task ID
        task_id: String,

        /// Command to execute
        #[arg(short, long)]
        command: String,

        /// Constitution rules (comma-separated)
        #[arg(long)]
        rules: Option<String>,

        /// Registry file path
        #[arg(short, long, default_value = ".claude/process_registry.json")]
        registry: String,
    },
}

/// Validate registry path to prevent path traversal attacks
///
/// Security checks:
/// 1. Path must not contain parent directory references (..)
/// 2. Canonicalized path must be within current working directory
/// 3. Path must not point to sensitive system directories
///
/// Returns validated canonical path or error
fn validate_registry_path(path: &str) -> Result<PathBuf> {
    let path_buf = PathBuf::from(path);

    // SECURITY: Prevent path traversal with .. components
    if path.contains("..") {
        bail!("Registry path cannot contain parent directory references (..)");
    }

    // Convert to absolute path (handles relative paths safely)
    let absolute_path = if path_buf.is_absolute() {
        path_buf.clone()
    } else {
        std::env::current_dir()?.join(&path_buf)
    };

    // Canonicalize to resolve symlinks and normalize path
    let canonical = match absolute_path.canonicalize() {
        Ok(p) => p,
        Err(_) => {
            // If file doesn't exist yet, validate parent directory
            let parent = absolute_path.parent()
                .ok_or_else(|| anyhow::anyhow!("Invalid registry path: no parent directory"))?;

            if !parent.exists() {
                bail!("Registry path parent directory does not exist: {}", parent.display());
            }

            // Return the non-canonical path for new files (will be created)
            absolute_path
        }
    };

    // SECURITY: Prevent access to sensitive system directories
    let canonical_str = canonical.to_string_lossy();
    let forbidden_prefixes = [
        "/etc",
        "/root",
        "/sys",
        "/proc",
        "/boot",
        "/dev",
    ];

    for prefix in &forbidden_prefixes {
        if canonical_str.starts_with(prefix) {
            bail!("Registry path cannot be in system directory: {}", prefix);
        }
    }

    // SECURITY: Ensure path is within current working directory (or .claude subdir)
    let cwd = std::env::current_dir()?;
    if !canonical.starts_with(&cwd) {
        bail!("Registry path must be within current working directory: {}", cwd.display());
    }

    Ok(canonical)
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Run { interval, registry } => {
            let validated_path = validate_registry_path(&registry)?;
            run_watchdog(interval, &validated_path.to_string_lossy()).await?
        },
        Commands::Check { task_id, registry } => {
            let validated_path = validate_registry_path(&registry)?;
            check_task(&task_id, &validated_path.to_string_lossy()).await?
        },
        Commands::Kill { task_id, registry } => {
            let validated_path = validate_registry_path(&registry)?;
            kill_task(&task_id, &validated_path.to_string_lossy()).await?
        },
        Commands::Rehydrate { registry } => {
            let validated_path = validate_registry_path(&registry)?;
            rehydrate(&validated_path.to_string_lossy()).await?
        },
        Commands::Report { registry } => {
            let validated_path = validate_registry_path(&registry)?;
            show_report(&validated_path.to_string_lossy()).await?
        },
        Commands::Stats { registry } => {
            let validated_path = validate_registry_path(&registry)?;
            show_stats(&validated_path.to_string_lossy()).await?
        },
        Commands::Cleanup { days, registry } => {
            let validated_path = validate_registry_path(&registry)?;
            cleanup_tasks(days, &validated_path.to_string_lossy()).await?
        },
        Commands::Register { task_id, command, rules, registry } => {
            let validated_path = validate_registry_path(&registry)?;
            register_task(&task_id, &command, rules, &validated_path.to_string_lossy()).await?
        },
    }

    Ok(())
}

/// Main watchdog loop
async fn run_watchdog(interval_secs: u64, registry_path: &str) -> Result<()> {
    println!("🐕 Task Watchdog v{}", env!("CARGO_PKG_VERSION"));
    println!("   Built with Rust for AI coding tools (Claude-tested)");
    println!("   Check interval: {}s", interval_secs);
    println!("   Registry: {}", registry_path);
    println!("   Memory usage: {}KB", get_self_memory_kb());
    println!();

    // Initialize Docker if available
    let docker = DockerManager::new();
    if docker.is_some() {
        println!("✅ Docker available");
    } else {
        println!("⚠️  Docker not available (native processes only)");
    }
    println!();

    let mut registry = RegistryManager::new(registry_path);

    loop {
        let check_time = Local::now().format("%H:%M:%S");
        println!("🔍 Watchdog check - {}", check_time);

        // Load latest registry state
        registry.load()?;

        // Find orphans in native processes
        let orphan_report = registry.find_orphans();

        // Check Docker containers if available
        if let Some(ref docker_client) = docker {
            check_docker_tasks(&mut registry, docker_client).await?;
        }

        // Report findings
        if orphan_report.has_issues() {
            println!("\n⚠️  Found {} issues:", orphan_report.total_issues());

            if !orphan_report.dead_processes.is_empty() {
                println!("\n💀 Dead Processes ({}):", orphan_report.dead_processes.len());
                for task_id in &orphan_report.dead_processes {
                    if let Some(task) = registry.get_task(task_id) {
                        println!("  {} - {}", task_id, task.command);
                    }
                    // Mark as failed
                    registry.mark_failed(task_id)?;
                }
            }

            if !orphan_report.zombie_processes.is_empty() {
                println!("\n🧟 Zombie Processes ({}):", orphan_report.zombie_processes.len());
                for task_id in &orphan_report.zombie_processes {
                    if let Some(task) = registry.get_task(task_id) {
                        println!("  {} - {}", task_id, task.command);

                        // Kill zombie
                        match &task.mode {
                            ExecutionMode::Native => {
                                if let Some(native) = &task.native {
                                    let _ = ProcessManager::kill_process_group(native.pgid);
                                }
                            }
                            ExecutionMode::Docker => {
                                if let (Some(docker_client), Some(docker_info)) = (&docker, &task.docker) {
                                    let _ = docker_client.stop_container(&docker_info.container_id).await;
                                }
                            }
                        }
                    }
                }
            }
        }

        // Show stats
        let stats = registry.stats();
        println!("\n📊 Status:");
        println!("   Running: {}", stats.running);
        println!("   Completed: {}", stats.completed);
        println!("   Failed: {}", stats.failed);
        println!("   Total: {}", stats.total);
        println!("   Memory: {}KB", get_self_memory_kb());

        println!("\n💤 Next check in {}s...\n", interval_secs);
        sleep(Duration::from_secs(interval_secs)).await;
    }
}

/// Check Docker containers for running tasks
async fn check_docker_tasks(registry: &mut RegistryManager, docker: &DockerManager) -> Result<()> {
    // Collect task_ids to mark as failed (separate from iteration)
    let mut failed_tasks = Vec::new();

    for (task_id, task) in registry.running_tasks() {
        if task.mode == ExecutionMode::Docker {
            if let Some(docker_info) = &task.docker {
                let is_running = docker.is_running(&docker_info.container_id).await;

                if !is_running && task.status == TaskStatus::Running {
                    println!("⚠️  Docker task {} stopped unexpectedly", task_id);
                    failed_tasks.push(task_id.clone());
                }
            }
        }
    }

    // Now mark them as failed (no borrow conflict)
    for task_id in failed_tasks {
        registry.mark_failed(&task_id)?;
    }

    Ok(())
}

/// Check status of specific task
async fn check_task(task_id: &str, registry_path: &str) -> Result<()> {
    let mut registry = RegistryManager::new(registry_path);
    registry.load()?;

    match registry.get_task(task_id) {
        Some(task) => {
            println!("📋 Task: {}", task_id);
            println!("   Command: {}", task.command);
            println!("   Mode: {:?}", task.mode);
            println!("   Status: {:?}", task.status);
            println!("   Started: {}", task.started_at.format("%Y-%m-%d %H:%M:%S"));

            match &task.mode {
                ExecutionMode::Native => {
                    if let Some(native) = &task.native {
                        let is_alive = ProcessManager::is_alive(native.pid);
                        println!("   PID: {} ({})", native.pid, if is_alive { "✅ alive" } else { "💀 dead" });
                        println!("   PGID: {}", native.pgid);

                        if is_alive {
                            if let Some(usage) = ProcessManager::get_resource_usage(native.pid) {
                                println!("   CPU: {:.1}%", usage.cpu_percent);
                                println!("   Memory: {}MB", usage.memory_kb / 1024);
                            }
                        }
                    }
                }
                ExecutionMode::Docker => {
                    if let Some(docker_info) = &task.docker {
                        println!("   Container: {}", &docker_info.container_id[..12]);
                        println!("   Limits: {} memory, {} CPU",
                            docker_info.resource_limits.memory,
                            docker_info.resource_limits.cpu
                        );

                        if let Some(docker) = DockerManager::new() {
                            let is_running = docker.is_running(&docker_info.container_id).await;
                            println!("   Status: {}", if is_running { "✅ running" } else { "💀 stopped" });
                        }
                    }
                }
            }
        }
        None => {
            println!("❌ Task {} not found", task_id);
        }
    }

    Ok(())
}

/// Kill a running task
async fn kill_task(task_id: &str, registry_path: &str) -> Result<()> {
    let mut registry = RegistryManager::new(registry_path);
    registry.load()?;

    match registry.get_task(task_id) {
        Some(task) => {
            println!("🔪 Killing task: {}", task_id);

            match &task.mode {
                ExecutionMode::Native => {
                    if let Some(native) = &task.native {
                        ProcessManager::kill_process_group(native.pgid)?;
                        println!("✅ Killed process group {}", native.pgid);
                    }
                }
                ExecutionMode::Docker => {
                    if let Some(docker_info) = &task.docker {
                        if let Some(docker) = DockerManager::new() {
                            docker.stop_container(&docker_info.container_id).await?;
                            println!("✅ Stopped container {}", &docker_info.container_id[..12]);
                        }
                    }
                }
            }

            registry.mark_complete(task_id)?;
        }
        None => {
            println!("❌ Task {} not found", task_id);
        }
    }

    Ok(())
}

/// Rehydrate context after compression
async fn rehydrate(registry_path: &str) -> Result<()> {
    println!("🧠 Context Re-Hydration Report");
    println!("================================\n");

    let mut registry = RegistryManager::new(registry_path);
    registry.load()?;

    let running = registry.running_tasks();

    if running.is_empty() {
        println!("✅ No tasks currently running\n");
    } else {
        println!("📊 ACTIVE TASKS ({})\n", running.len());

        for (task_id, task) in running {
            println!("Task {}", task_id);
            println!("  Command: {}", task.command);
            println!("  Mode: {:?}", task.mode);
            println!("  Started: {}", task.started_at.format("%H:%M:%S"));

            // Check if still alive
            let is_alive = match &task.mode {
                ExecutionMode::Native => {
                    task.native.as_ref().map_or(false, |n| ProcessManager::is_alive(n.pid))
                }
                ExecutionMode::Docker => {
                    if let Some(docker_info) = &task.docker {
                        if let Some(docker) = DockerManager::new() {
                            docker.is_running(&docker_info.container_id).await
                        } else {
                            false
                        }
                    } else {
                        false
                    }
                }
            };

            println!("  Status: {}", if is_alive { "✅ Running" } else { "⚠️  DEAD" });
            println!();
        }
    }

    let stats = registry.stats();
    println!("💡 SUMMARY:");
    println!("   Running: {}", stats.running);
    println!("   Completed: {}", stats.completed);
    println!("   Failed: {}", stats.failed);
    println!("\n📄 Full context: {}", registry_path);

    Ok(())
}

/// Show resource usage report
async fn show_report(registry_path: &str) -> Result<()> {
    println!("📊 Resource Usage Report");
    println!("========================\n");

    let mut registry = RegistryManager::new(registry_path);
    registry.load()?;

    for (task_id, task) in registry.running_tasks() {
        println!("Task {}", task_id);

        match &task.mode {
            ExecutionMode::Native => {
                if let Some(native) = &task.native {
                    if let Some(usage) = ProcessManager::get_resource_usage(native.pid) {
                        println!("  CPU: {:.1}%", usage.cpu_percent);
                        println!("  Memory: {}MB", usage.memory_kb / 1024);
                    } else {
                        println!("  ⚠️  Process not found");
                    }
                }
            }
            ExecutionMode::Docker => {
                if let Some(docker_info) = &task.docker {
                    println!("  Container: {}", &docker_info.container_id[..12]);
                    println!("  Limits: {}, {}",
                        docker_info.resource_limits.memory,
                        docker_info.resource_limits.cpu
                    );
                }
            }
        }
        println!();
    }

    Ok(())
}

/// Show registry statistics
async fn show_stats(registry_path: &str) -> Result<()> {
    let mut registry = RegistryManager::new(registry_path);
    registry.load()?;

    let stats = registry.stats();

    println!("📈 Registry Statistics");
    println!("=====================\n");
    println!("Total tasks: {}", stats.total);
    println!("Running: {}", stats.running);
    println!("Completed: {}", stats.completed);
    println!("Failed: {}", stats.failed);

    Ok(())
}

/// Cleanup old tasks
async fn cleanup_tasks(days: u64, registry_path: &str) -> Result<()> {
    let mut registry = RegistryManager::new(registry_path);
    registry.load()?;

    println!("🧹 Cleaning up tasks older than {} days...", days);

    let removed = registry.cleanup_old_tasks(days)?;

    println!("✅ Removed {} old tasks", removed);

    Ok(())
}

/// Register a new task with constitution rules
async fn register_task(
    task_id: &str,
    command: &str,
    rules: Option<String>,
    registry_path: &str,
) -> Result<()> {
    let mut registry = RegistryManager::new(registry_path);
    registry.load()?;

    // Parse constitution rules from comma-separated string
    let constitution_rules = rules
        .map(|r| r.split(',').map(|s| s.trim().to_string()).collect())
        .unwrap_or_default();

    // Create task info with default Native mode and Running status
    let task = TaskInfo {
        mode: ExecutionMode::Native,
        command: command.to_string(),
        status: TaskStatus::Running,
        started_at: chrono::Utc::now(),
        completed_at: None,
        native: None,
        docker: None,
        constitution_rules,
    };

    registry.upsert_task(task_id.to_string(), task)?;

    println!("✅ Task {} registered with {} constitution rules",
        task_id,
        registry.get_task(task_id)
            .map(|t| t.constitution_rules.len())
            .unwrap_or(0)
    );

    Ok(())
}

/// Get memory usage of current process
fn get_self_memory_kb() -> u64 {
    use sysinfo::{System, Pid};

    let mut sys = System::new_all();
    sys.refresh_all();

    let pid = Pid::from_u32(std::process::id());

    if let Some(process) = sys.process(pid) {
        return process.memory();
    }

    0
}
