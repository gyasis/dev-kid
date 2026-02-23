use anyhow::{Context, Result};
use std::process::Command;
use crate::types::ResourceUsage;

#[cfg(unix)]
use nix::sys::signal::{kill, killpg, Signal};
#[cfg(unix)]
use nix::unistd::Pid;

/// Process manager for native OS processes
pub struct ProcessManager;

impl ProcessManager {
    /// Check if process is running (blazing fast!)
    /// Uses signal 0 which doesn't actually send a signal, just checks existence
    #[cfg(unix)]
    pub fn is_alive(pid: i32) -> bool {
        kill(Pid::from_raw(pid), None).is_ok()
    }

    #[cfg(windows)]
    pub fn is_alive(pid: i32) -> bool {
        // Windows implementation using tasklist
        if let Ok(output) = Command::new("tasklist")
            .args(&["/FI", &format!("PID eq {}", pid)])
            .output()
        {
            let stdout = String::from_utf8_lossy(&output.stdout);
            return stdout.contains(&pid.to_string());
        }
        false
    }

    /// Get process start time to prevent PID recycling confusion
    /// This is critical for ensuring we're checking the SAME process
    #[cfg(unix)]
    pub fn get_start_time(pid: i32) -> Result<String> {
        let output = Command::new("ps")
            .args(&["-p", &pid.to_string(), "-o", "lstart="])
            .output()
            .context("Failed to execute ps command")?;

        if !output.status.success() {
            anyhow::bail!("Process {} not found", pid);
        }

        Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
    }

    #[cfg(windows)]
    pub fn get_start_time(pid: i32) -> Result<String> {
        // Windows implementation using wmic
        let output = Command::new("wmic")
            .args(&["process", "where", &format!("ProcessId={}", pid), "get", "CreationDate"])
            .output()
            .context("Failed to execute wmic")?;

        Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
    }

    /// Validate that a PID is the same process we started
    /// Prevents accidentally killing a different process if PID gets recycled
    pub fn validate_process(pid: i32, expected_start: &str) -> bool {
        if let Ok(actual_start) = Self::get_start_time(pid) {
            return actual_start == expected_start;
        }
        false
    }

    /// Kill a single process gracefully (SIGTERM then SIGKILL)
    #[cfg(unix)]
    pub fn kill_process(pid: i32) -> Result<()> {
        // Try SIGTERM first (graceful)
        if let Ok(()) = kill(Pid::from_raw(pid), Signal::SIGTERM) {
            println!("  Sent SIGTERM to PID {}", pid);

            // Wait 2 seconds
            std::thread::sleep(std::time::Duration::from_secs(2));

            // Check if still alive
            if Self::is_alive(pid) {
                // Force kill with SIGKILL
                kill(Pid::from_raw(pid), Signal::SIGKILL)
                    .context("Failed to send SIGKILL")?;
                println!("  Sent SIGKILL to PID {}", pid);
            }
        }

        Ok(())
    }

    #[cfg(windows)]
    pub fn kill_process(pid: i32) -> Result<()> {
        Command::new("taskkill")
            .args(&["/PID", &pid.to_string(), "/F"])
            .output()
            .context("Failed to kill process")?;
        Ok(())
    }

    /// Kill entire process group (handles process trees)
    /// This is the key to cleaning up all child processes
    #[cfg(unix)]
    pub fn kill_process_group(pgid: i32) -> Result<()> {
        println!("🔪 Killing process group {}", pgid);

        // SIGTERM first (graceful shutdown)
        if let Ok(()) = killpg(Pid::from_raw(pgid), Signal::SIGTERM) {
            println!("  Sent SIGTERM to PGID {}", pgid);

            // Wait 2 seconds for graceful shutdown
            std::thread::sleep(std::time::Duration::from_secs(2));

            // Check if any process in group still alive
            if Self::is_alive(pgid) {
                // Force kill entire group
                killpg(Pid::from_raw(pgid), Signal::SIGKILL)
                    .context("Failed to send SIGKILL to process group")?;
                println!("  Sent SIGKILL to PGID {}", pgid);
            } else {
                println!("  ✅ Process group terminated gracefully");
            }
        }

        Ok(())
    }

    #[cfg(windows)]
    pub fn kill_process_group(pgid: i32) -> Result<()> {
        // Windows doesn't have process groups in the same way
        // Fall back to single process kill
        Self::kill_process(pgid)
    }

    /// Get process resource usage (CPU and memory)
    pub fn get_resource_usage(pid: i32) -> Option<ResourceUsage> {
        use sysinfo::{System, Pid as SysPid};

        let mut sys = System::new_all();
        sys.refresh_all();

        let sys_pid = SysPid::from_u32(pid as u32);

        if let Some(process) = sys.process(sys_pid) {
            return Some(ResourceUsage {
                cpu_percent: process.cpu_usage(),
                memory_kb: process.memory(),
            });
        }

        None
    }

    /// Get all PIDs matching an environment variable tag
    /// This allows finding orphaned child processes
    #[cfg(unix)]
    pub fn find_processes_by_env(env_key: &str, env_value: &str) -> Vec<i32> {
        let mut pids = Vec::new();

        let output = Command::new("ps")
            .args(&["axe"])  // 'e' shows environment
            .output();

        if let Ok(output) = output {
            let stdout = String::from_utf8_lossy(&output.stdout);
            let search = format!("{}={}", env_key, env_value);

            for line in stdout.lines() {
                if line.contains(&search) {
                    if let Some(pid_str) = line.split_whitespace().next() {
                        if let Ok(pid) = pid_str.parse::<i32>() {
                            pids.push(pid);
                        }
                    }
                }
            }
        }

        pids
    }

    #[cfg(windows)]
    pub fn find_processes_by_env(_env_key: &str, _env_value: &str) -> Vec<i32> {
        // Windows doesn't easily support env var inspection
        // Would need WMI queries - skip for now
        Vec::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_alive() {
        // Current process should be alive
        let pid = std::process::id() as i32;
        assert!(ProcessManager::is_alive(pid));

        // PID 999999 should not exist
        assert!(!ProcessManager::is_alive(999999));
    }

    #[test]
    fn test_get_start_time() {
        let pid = std::process::id() as i32;
        let start_time = ProcessManager::get_start_time(pid);
        assert!(start_time.is_ok());
    }
}
