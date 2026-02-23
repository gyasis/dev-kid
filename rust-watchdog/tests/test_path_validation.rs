use std::env;
use std::fs;
use std::path::PathBuf;

/// Mock the validate_registry_path function for testing
/// (In real implementation, this would be extracted to a module)
fn validate_registry_path(path: &str) -> anyhow::Result<PathBuf> {
    use anyhow::bail;
    use std::path::Path;

    let path_buf = PathBuf::from(path);

    // SECURITY: Prevent path traversal with .. components
    if path.contains("..") {
        bail!("Registry path cannot contain parent directory references (..)");
    }

    // Convert to absolute path (handles relative paths safely)
    let absolute_path = if path_buf.is_absolute() {
        path_buf.clone()
    } else {
        env::current_dir()?.join(&path_buf)
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

    // SECURITY: Ensure path is within current working directory
    let cwd = env::current_dir()?;
    if !canonical.starts_with(&cwd) {
        bail!("Registry path must be within current working directory: {}", cwd.display());
    }

    Ok(canonical)
}

#[test]
fn test_valid_relative_path() {
    // Create temporary directory structure
    let temp_dir = env::temp_dir().join("test_path_validation");
    fs::create_dir_all(&temp_dir).unwrap();

    let original_dir = env::current_dir().unwrap();
    env::set_current_dir(&temp_dir).unwrap();

    // Create .claude directory
    fs::create_dir_all(".claude").unwrap();
    fs::write(".claude/test_registry.json", "{}").unwrap();

    // Test valid relative path
    let result = validate_registry_path(".claude/test_registry.json");
    assert!(result.is_ok(), "Valid relative path should be accepted");

    // Cleanup
    env::set_current_dir(&original_dir).unwrap();
    fs::remove_dir_all(&temp_dir).unwrap();
}

#[test]
fn test_parent_directory_traversal_blocked() {
    // Test path traversal with ..
    let result = validate_registry_path("../../etc/passwd");
    assert!(result.is_err(), "Path traversal with .. should be blocked");

    if let Err(e) = result {
        assert!(e.to_string().contains("parent directory references"));
    }
}

#[test]
fn test_system_directory_blocked() {
    // These tests will fail on the forbidden check (before attempting to access)
    let system_paths = vec![
        "/etc/watchdog.json",
        "/root/.claude/registry.json",
        "/sys/kernel/watchdog",
        "/proc/watchdog",
        "/boot/watchdog.json",
        "/dev/watchdog",
    ];

    for path in system_paths {
        let result = validate_registry_path(path);
        assert!(result.is_err(), "System path {} should be blocked", path);

        if let Err(e) = result {
            let error_msg = e.to_string();
            // Accept multiple valid error messages:
            // - "system directory" (direct forbidden path check)
            // - "current working directory" (CWD restriction)
            // - "does not exist" (parent directory doesn't exist, e.g., /root when user isn't root)
            assert!(
                error_msg.contains("system directory") ||
                error_msg.contains("current working directory") ||
                error_msg.contains("does not exist"),
                "Error should mention security restriction for path {}, got: {}",
                path, error_msg
            );
        }
    }
}

#[test]
fn test_path_outside_cwd_blocked() {
    // Create two separate temp directories
    let temp_dir1 = env::temp_dir().join("test_cwd_1");
    let temp_dir2 = env::temp_dir().join("test_cwd_2");

    fs::create_dir_all(&temp_dir1).unwrap();
    fs::create_dir_all(&temp_dir2).unwrap();
    fs::write(temp_dir2.join("registry.json"), "{}").unwrap();

    let original_dir = env::current_dir().unwrap();
    env::set_current_dir(&temp_dir1).unwrap();

    // Try to access file in temp_dir2 (outside CWD)
    let outside_path = temp_dir2.join("registry.json");
    let result = validate_registry_path(&outside_path.to_string_lossy());

    assert!(result.is_err(), "Path outside CWD should be blocked");

    if let Err(e) = result {
        assert!(e.to_string().contains("current working directory"));
    }

    // Cleanup
    env::set_current_dir(&original_dir).unwrap();
    fs::remove_dir_all(&temp_dir1).unwrap();
    fs::remove_dir_all(&temp_dir2).unwrap();
}

#[test]
fn test_nonexistent_file_with_valid_parent() {
    // Create temporary directory
    let temp_dir = env::temp_dir().join("test_new_file");
    fs::create_dir_all(&temp_dir).unwrap();

    let original_dir = env::current_dir().unwrap();
    env::set_current_dir(&temp_dir).unwrap();

    // Create parent directory
    fs::create_dir_all(".claude").unwrap();

    // Test path to non-existent file with valid parent
    let result = validate_registry_path(".claude/new_registry.json");
    assert!(result.is_ok(), "Non-existent file with valid parent should be accepted");

    // Cleanup
    env::set_current_dir(&original_dir).unwrap();
    fs::remove_dir_all(&temp_dir).unwrap();
}

#[test]
fn test_nonexistent_parent_directory_blocked() {
    let result = validate_registry_path("nonexistent_dir/registry.json");
    assert!(result.is_err(), "Path with non-existent parent should be blocked");

    if let Err(e) = result {
        assert!(e.to_string().contains("does not exist"));
    }
}

#[test]
fn test_absolute_path_within_cwd() {
    // Create temporary directory
    let temp_dir = env::temp_dir().join("test_absolute_path");
    fs::create_dir_all(&temp_dir).unwrap();

    let original_dir = env::current_dir().unwrap();
    env::set_current_dir(&temp_dir).unwrap();

    // Create test file
    fs::create_dir_all(".claude").unwrap();
    let test_file = temp_dir.join(".claude/registry.json");
    fs::write(&test_file, "{}").unwrap();

    // Test absolute path within CWD
    let result = validate_registry_path(&test_file.to_string_lossy());
    assert!(result.is_ok(), "Absolute path within CWD should be accepted");

    // Cleanup
    env::set_current_dir(&original_dir).unwrap();
    fs::remove_dir_all(&temp_dir).unwrap();
}

#[test]
fn test_hidden_parent_traversal_blocked() {
    // Test various obfuscated path traversal attempts
    let malicious_paths = vec![
        "./../../../etc/passwd",
        "./.../../etc/passwd",
        "subdir/../../etc/passwd",
    ];

    for path in malicious_paths {
        let result = validate_registry_path(path);
        assert!(result.is_err(), "Malicious path {} should be blocked", path);

        if let Err(e) = result {
            assert!(e.to_string().contains("parent directory references"));
        }
    }
}

#[test]
fn test_default_path_accepted() {
    // Create temporary directory
    let temp_dir = env::temp_dir().join("test_default_path");
    fs::create_dir_all(&temp_dir).unwrap();

    let original_dir = env::current_dir().unwrap();
    env::set_current_dir(&temp_dir).unwrap();

    // Create default path
    fs::create_dir_all(".claude").unwrap();
    fs::write(".claude/process_registry.json", "{}").unwrap();

    // Test default path from CLI
    let result = validate_registry_path(".claude/process_registry.json");
    assert!(result.is_ok(), "Default registry path should be accepted");

    // Cleanup
    env::set_current_dir(&original_dir).unwrap();
    fs::remove_dir_all(&temp_dir).unwrap();
}
