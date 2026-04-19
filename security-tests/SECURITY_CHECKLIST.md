# Security Implementation Checklist

Quick reference for implementing security fixes in dev-kid installation flow.

## Pre-Implementation

- [ ] Read SECURITY_AUDIT_REPORT.md (main findings)
- [ ] Read SECURITY_EXECUTIVE_SUMMARY.md (quick overview)
- [ ] Understand current vulnerabilities and exploit scenarios
- [ ] Review secure-install.sh for implementation patterns

## Phase 1 - CRITICAL Fixes (Day 1)

### Vulnerability #1: Command Injection via INSTALL_DIR

- [ ] **Add sanitization function**:
  ```bash
  sanitize_path() {
    # Check for shell metacharacters
    if [[ "$path" =~ [;\`\$\(\)\{\}\|\&\<\>] ]]; then
      echo "Invalid path" >&2
      exit 1
    fi

    # Canonicalize path
    path=$(realpath -m "$path")

    # Block system directories
    restricted_paths=("/bin" "/sbin" "/etc" "/usr")
    for restricted in "${restricted_paths[@]}"; do
      if [[ "$path" == "$restricted"* ]]; then
        echo "Cannot install to system directory" >&2
        exit 1
      fi
    done

    echo "$path"
  }
  ```

- [ ] **Replace all user input usage**:
  ```bash
  # BEFORE:
  INSTALL_DIR="${1:-$HOME/.dev-kid}"

  # AFTER:
  INSTALL_DIR=$(sanitize_path "${1:-$HOME/.dev-kid}")
  ```

- [ ] **Test command injection attempts**:
  ```bash
  ./install '$(malicious_command)'  # Should reject
  ./install '; touch /tmp/pwned'     # Should reject
  ./install 'valid | cat /etc/passwd' # Should reject
  ```

- [ ] **Verify test passes**:
  ```bash
  cd security-tests
  ./run-security-tests.sh | grep "Command injection"
  # Expected: [PASS] for all command injection tests
  ```

---

### Vulnerability #2: Git Hook Code Injection

- [ ] **Create git hook templates directory**:
  ```bash
  mkdir -p templates/git-hooks
  ```

- [ ] **Move hook code to template files**:
  ```bash
  # Create templates/git-hooks/post-commit
  # Create templates/git-hooks/post-checkout
  # Remove heredoc creation from init.sh
  ```

- [ ] **Add hook validation function**:
  ```bash
  install_git_hook() {
    local hook_name="$1"
    local template="$TEMPLATES/git-hooks/$hook_name"
    local target=".git/hooks/$hook_name"

    # Verify template exists and is regular file
    if [ ! -f "$template" ] || [ -L "$template" ]; then
      echo "Invalid hook template" >&2
      return 1
    fi

    # Copy and set permissions
    cp "$template" "$target"
    chmod +x "$target"

    # Create checksum
    sha256sum "$target" >> .git/hooks/.checksums
  }
  ```

- [ ] **Update init.sh to use templates**:
  ```bash
  # BEFORE:
  cat > .git/hooks/post-commit << 'EOF'
  # ... hook code ...
  EOF

  # AFTER:
  install_git_hook "post-commit"
  ```

- [ ] **Test hook integrity**:
  ```bash
  cd test-project
  dev-kid init
  sha256sum -c .git/hooks/.checksums  # Should pass
  ```

---

### Vulnerability #3: Symlink TOCTOU Race

- [ ] **Implement atomic symlink creation**:
  ```bash
  create_safe_symlink() {
    local target="$1"
    local link_path="$2"

    # Verify target is regular file
    if [ ! -f "$target" ] || [ -L "$target" ]; then
      echo "Invalid target" >&2
      return 1
    fi

    # Create temp symlink
    local temp_link="${link_path}.tmp.$$"
    ln -sf "$target" "$temp_link"

    # Atomic move
    mv -f "$temp_link" "$link_path"

    # Verify result
    actual_target=$(readlink "$link_path")
    if [ "$actual_target" != "$target" ]; then
      rm -f "$link_path"
      return 1
    fi
  }
  ```

- [ ] **Replace all ln -sf commands**:
  ```bash
  # BEFORE:
  ln -sf "$INSTALL_DIR/cli/dev-kid" /usr/local/bin/dev-kid

  # AFTER:
  create_safe_symlink "$INSTALL_DIR/cli/dev-kid" /usr/local/bin/dev-kid
  ```

- [ ] **Test race condition resistance**:
  ```bash
  # Attempt to swap target during creation
  # (See exploit-poc.sh for test scenario)
  ```

---

## Phase 2 - HIGH Severity Fixes (Days 2-3)

### Vulnerability #4: Sudo Privilege Escalation

- [ ] **Add consent mechanism**:
  ```bash
  install_to_path() {
    local source_path="$1"
    local target_path="/usr/local/bin/dev-kid"

    # Check if sudo needed
    if [ -w "/usr/local/bin" ]; then
      create_safe_symlink "$source_path" "$target_path"
      return 0
    fi

    # Request consent
    echo "Installation to $target_path requires elevated privileges"
    echo ""
    echo "Alternative: Add to PATH without sudo:"
    echo "  export PATH=\"$HOME/.dev-kid/cli:\$PATH\""
    echo ""

    read -p "Use sudo to install globally? (y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "Skipping global installation"
      return 0
    fi

    # Verify sudo available
    if ! command -v sudo &> /dev/null; then
      echo "sudo not available" >&2
      return 1
    fi

    # Execute with sudo
    sudo bash -c "$(declare -f create_safe_symlink); \
                   create_safe_symlink '$source_path' '$target_path'"
  }
  ```

- [ ] **Replace automatic sudo usage**:
  ```bash
  # BEFORE:
  if [ -w "/usr/local/bin" ]; then
    ln -sf ...
  else
    sudo ln -sf ...  # Automatic escalation
  fi

  # AFTER:
  install_to_path "$INSTALL_DIR/cli/dev-kid"
  ```

- [ ] **Test consent flow**:
  ```bash
  # Test without write permission
  # Verify prompt appears
  # Test both y/N responses
  ```

---

### Vulnerability #5: Path Traversal in Templates

- [ ] **Add template validation**:
  ```bash
  validate_template_dir() {
    local templates="$1"

    # Must be under $HOME/.dev-kid or project root
    if [[ ! "$templates" =~ ^"$HOME"/.dev-kid ]]; then
      echo "Invalid template directory" >&2
      return 1
    fi

    # Check required files exist
    required_files=(
      "memory-bank/shared/projectbrief.md"
      ".claude/active_stack.md"
    )

    for file in "${required_files[@]}"; do
      if [ ! -f "$templates/$file" ]; then
        echo "Missing template: $file" >&2
        return 1
      fi

      # Reject symlinks
      if [ -L "$templates/$file" ]; then
        echo "Template is symlink: $file" >&2
        return 1
      fi
    done
  }
  ```

- [ ] **Add safe copy function**:
  ```bash
  safe_copy() {
    local src="$1"
    local dst="$2"

    # Verify source is regular file
    if [ ! -f "$src" ] || [ -L "$src" ]; then
      echo "Invalid source: $src" >&2
      return 1
    fi

    mkdir -p "$(dirname "$dst")"
    cp -p "$src" "$dst"
  }
  ```

- [ ] **Update all cp commands in init.sh**:
  ```bash
  # BEFORE:
  cp "$TEMPLATES/file.md" "destination/"

  # AFTER:
  safe_copy "$TEMPLATES/file.md" "destination/file.md"
  ```

- [ ] **Validate templates before use**:
  ```bash
  if ! validate_template_dir "$TEMPLATES"; then
    echo "Template validation failed" >&2
    exit 1
  fi
  ```

---

### Vulnerability #8: Python Execution Validation

- [ ] **Add DEV_KID_ROOT validation**:
  ```bash
  validate_dev_kid_root() {
    local root="$1"

    # Ensure absolute path
    if [[ ! "$root" =~ ^/ ]]; then
      echo "DEV_KID_ROOT must be absolute" >&2
      return 1
    fi

    # Verify expected files exist
    required_files=(
      "cli/config_manager.py"
      "cli/constitution_manager.py"
    )

    for file in "${required_files[@]}"; do
      if [ ! -f "$root/$file" ]; then
        echo "Missing file: $file" >&2
        return 1
      fi
    done

    # Optional: Verify checksums
    if [ -f "$root/.checksums" ]; then
      (cd "$root" && sha256sum -c .checksums --quiet)
    fi
  }
  ```

- [ ] **Validate before Python execution**:
  ```bash
  # BEFORE:
  python3 "$DEV_KID_ROOT/cli/config_manager.py" init

  # AFTER:
  if ! validate_dev_kid_root "$DEV_KID_ROOT"; then
    exit 1
  fi
  python3 "$DEV_KID_ROOT/cli/config_manager.py" init
  ```

---

## Phase 3 - MEDIUM Severity Fixes (Days 4-7)

### Vulnerability #6: Sed Command Injection

- [ ] **Replace sed with safe substitution**:
  ```bash
  safe_sed_replace() {
    local template="$1"
    local output="$2"
    shift 2

    local content=$(<"$template")

    # Use awk for safe replacement
    while [ $# -ge 2 ]; do
      local placeholder="$1"
      local value="$2"
      content=$(echo "$content" | awk -v p="$placeholder" -v v="$value" '{gsub(p, v)}1')
      shift 2
    done

    echo "$content" > "$output"
  }
  ```

- [ ] **Update all sed usage in init.sh**:
  ```bash
  # BEFORE:
  sed "s|{{USER}}|$USER|g" template.json > output.json

  # AFTER:
  safe_sed_replace template.json output.json \
    "{{USER}}" "$USER" \
    "{{PATH}}" "$PROJECT_PATH"
  ```

---

### Vulnerability #7: Unsafe chmod Wildcards

- [ ] **Replace wildcard chmod**:
  ```bash
  safe_chmod_exec() {
    local dir="$1"
    local pattern="$2"

    find "$dir" -maxdepth 1 -type f -name "$pattern" -print0 | \
    while IFS= read -r -d '' file; do
      # Verify file is in expected directory
      file_real=$(realpath "$file")
      dir_real=$(realpath "$dir")

      if [[ "$file_real" != "$dir_real"/* ]]; then
        continue
      fi

      chmod +x "$file"
    done
  }
  ```

- [ ] **Update chmod commands**:
  ```bash
  # BEFORE:
  chmod +x "$INSTALL_DIR/cli"/*.py

  # AFTER:
  safe_chmod_exec "$INSTALL_DIR/cli" "*.py"
  ```

---

### Vulnerability #9: Insecure File Permissions

- [ ] **Set restrictive umask**:
  ```bash
  # At start of script
  umask 077  # Files: 600, Dirs: 700
  ```

- [ ] **Create sensitive files securely**:
  ```bash
  create_sensitive_file() {
    local file="$1"
    local content="$2"

    mkdir -p "$(dirname "$file")"
    chmod 700 "$(dirname "$file")"

    (
      umask 077
      echo "$content" > "$file"
    )

    chmod 600 "$file"
  }
  ```

- [ ] **Audit all created files**:
  ```bash
  find "$INSTALL_DIR" -type f -ls
  # Verify: 600 or 755 only

  find "$INSTALL_DIR" -type d -ls
  # Verify: 700 or 755 only
  ```

---

## Phase 4 - Hardening & Testing

### Add Integrity Checking

- [ ] **Generate checksums on install**:
  ```bash
  (
    cd "$INSTALL_DIR"
    find . -type f -exec sha256sum {} \; > .checksums
    chmod 400 .checksums
  )
  ```

- [ ] **Verify checksums on init**:
  ```bash
  verify_installation_integrity() {
    if [ ! -f "$DEV_KID_ROOT/.checksums" ]; then
      echo "Warning: No checksums found" >&2
      return 1
    fi

    (cd "$DEV_KID_ROOT" && sha256sum -c .checksums --quiet)
  }
  ```

---

### Security Testing

- [ ] **Run automated test suite**:
  ```bash
  cd security-tests
  ./run-security-tests.sh
  ```

- [ ] **Verify all tests pass**:
  ```bash
  # Expected output:
  # Passed: X
  # Failed: 0
  # Warnings: Y (acceptable)
  ```

- [ ] **Run exploit demonstrations** (in safe environment):
  ```bash
  ./exploit-poc.sh
  # All exploits should be prevented
  ```

- [ ] **Manual penetration testing**:
  ```bash
  # Test command injection
  ./install '$(malicious)'

  # Test path traversal
  ./install '../../etc'

  # Test symlink attacks
  # (See exploit-poc.sh)
  ```

---

### Documentation Updates

- [ ] **Update README.md**:
  - Add security section
  - Link to security audit report
  - Mention security-hardened installation

- [ ] **Update INSTALLATION.md**:
  - Document secure installation process
  - Add security best practices
  - Link to security checklist

- [ ] **Create SECURITY.md**:
  - Security policy
  - Vulnerability disclosure process
  - Security update process

- [ ] **Update CHANGELOG.md**:
  - Document security fixes
  - Reference CVE/vulnerability IDs if applicable
  - Credit security researchers

---

### CI/CD Integration

- [ ] **Add security testing to CI**:
  ```yaml
  # .github/workflows/security.yml
  name: Security Tests
  on: [push, pull_request]
  jobs:
    security:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v2
        - name: Run Security Tests
          run: |
            cd security-tests
            ./run-security-tests.sh
  ```

- [ ] **Add pre-commit hooks**:
  ```bash
  # .git/hooks/pre-commit
  # Run security tests before commit
  cd security-tests
  ./run-security-tests.sh
  ```

- [ ] **Add dependency scanning**:
  ```yaml
  # Scan for vulnerable dependencies
  - name: Security Scan
    uses: snyk/actions/node@master
  ```

---

## Verification Checklist

### Installation Testing

- [ ] Fresh install in clean environment
- [ ] Verify all files have correct permissions
- [ ] Verify checksums created
- [ ] Verify symlinks created correctly
- [ ] Test without sudo (PATH alternative)
- [ ] Test with sudo (global installation)

### Security Testing

- [ ] All automated tests pass
- [ ] Command injection attempts rejected
- [ ] Path traversal attempts rejected
- [ ] Symlink attacks prevented
- [ ] Sudo requires consent
- [ ] Templates validated
- [ ] File permissions secure (600/700)

### Regression Testing

- [ ] Normal installation still works
- [ ] All features functional
- [ ] No breaking changes for users
- [ ] Documentation accurate

---

## Rollout Plan

### Stage 1: Internal Testing (Day 1-2)
- [ ] Deploy fixes to staging environment
- [ ] Run full test suite
- [ ] Manual security review
- [ ] Fix any issues found

### Stage 2: Beta Testing (Day 3-4)
- [ ] Deploy to beta testers
- [ ] Monitor for issues
- [ ] Gather feedback
- [ ] Iterate if needed

### Stage 3: Production Deployment (Day 5-7)
- [ ] Announce security update
- [ ] Deploy to production
- [ ] Update documentation
- [ ] Monitor installation success rate

### Stage 4: Post-Deployment (Week 2+)
- [ ] Continue monitoring
- [ ] Address user questions
- [ ] Schedule follow-up audit
- [ ] Plan ongoing security program

---

## Success Criteria

### Technical Metrics
- ✅ 0 CRITICAL vulnerabilities remaining
- ✅ 0 HIGH vulnerabilities remaining
- ✅ All automated security tests passing
- ✅ Code review approved
- ✅ Penetration test passed

### Process Metrics
- ✅ Security policy documented
- ✅ Vulnerability disclosure process established
- ✅ Security testing in CI/CD
- ✅ Regular audit schedule defined

### User Metrics
- ✅ No user-reported security issues
- ✅ Positive feedback on security improvements
- ✅ High adoption rate of secure installation
- ✅ Clear security documentation

---

## Quick Reference Commands

### Test Current Installation Security
```bash
cd security-tests
./run-security-tests.sh
```

### Deploy Secure Installation
```bash
cp security-tests/secure-install.sh install
chmod +x install
```

### Verify Installation Integrity
```bash
cd $HOME/.dev-kid
sha256sum -c .checksums
```

### Check File Permissions
```bash
find $HOME/.dev-kid -ls | awk '{print $3, $NF}'
```

### Run Exploit Demonstrations (SAFE ENVIRONMENT ONLY)
```bash
cd security-tests
./exploit-poc.sh
```

---

## Support

### Questions?
- Review: `SECURITY_AUDIT_REPORT.md` (detailed findings)
- Review: `SECURITY_EXECUTIVE_SUMMARY.md` (quick overview)
- Review: `security-tests/README.md` (implementation guide)

### Issues?
- Check test output for specific failures
- Review error messages in audit report
- Consult OWASP resources for best practices

### Help Needed?
- Security questions: Consult security team
- Implementation help: Review secure-install.sh
- Best practices: OWASP guidelines

---

**Last Updated**: 2026-02-12
**Version**: 1.0
**Status**: Ready for Implementation
