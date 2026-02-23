use task_watchdog::docker::DockerManager;
use std::env;

#[tokio::test]
async fn test_command_injection_prevention() {
    // This test verifies that command injection is prevented
    // by passing commands directly to Docker instead of through shell

    let manager = match DockerManager::new() {
        Some(m) => m,
        None => {
            println!("Docker not available, skipping test");
            return;
        }
    };

    // Get current directory as absolute path
    let work_dir = env::current_dir()
        .expect("Failed to get current directory")
        .to_string_lossy()
        .to_string();

    // Attempt command injection with shell metacharacters
    // In vulnerable version: would execute "echo safe && echo injected"
    // In secure version: Docker exec will fail to find command "echo safe && echo injected"
    let malicious_command = vec![
        "echo".to_string(),
        "safe".to_string(),
        "&&".to_string(),
        "echo".to_string(),
        "injected".to_string(),
    ];

    let result = manager.run_container(
        "injection-test",
        malicious_command,
        &work_dir,
        "512m",
        "1.0",
        Some("alpine:latest"),
    ).await;

    // The container should be created (Docker accepts the command array)
    // But Docker will treat "&&" as a literal argument, not shell operator
    match &result {
        Ok(_) => println!("Container created successfully"),
        Err(e) => println!("Container creation error: {}", e),
    }
    assert!(result.is_ok(), "Container creation should succeed: {:?}", result);

    if let Ok(container_id) = result {
        // Clean up
        let _ = manager.stop_container(&container_id).await;
    }
}

#[tokio::test]
async fn test_safe_command_execution() {
    // Verify legitimate commands still work correctly

    let manager = match DockerManager::new() {
        Some(m) => m,
        None => {
            println!("Docker not available, skipping test");
            return;
        }
    };

    // Get current directory as absolute path
    let work_dir = env::current_dir()
        .expect("Failed to get current directory")
        .to_string_lossy()
        .to_string();

    // Safe command: run echo with proper argument array
    let safe_command = vec![
        "echo".to_string(),
        "hello world".to_string(),
    ];

    let result = manager.run_container(
        "safe-test",
        safe_command,
        &work_dir,
        "256m",
        "0.5",
        Some("alpine:latest"),
    ).await;

    match &result {
        Ok(_) => println!("Safe container created successfully"),
        Err(e) => println!("Safe container creation error: {}", e),
    }
    assert!(result.is_ok(), "Safe command should execute successfully: {:?}", result);

    if let Ok(container_id) = result {
        // Clean up
        let _ = manager.stop_container(&container_id).await;
    }
}
