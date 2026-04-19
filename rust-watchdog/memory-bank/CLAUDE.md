# Claude Intelligence: Task Watchdog Project

## Project-Specific Patterns

### Rebranding Workflow

**Pattern Discovered**: When renaming a project systematically, use wave-based execution:
- Wave 1: Documentation updates (parallel, no file conflicts)
- Wave 2: Build artifacts (sequential, depends on docs)
- Wave 3: Source code changes (parallel if no conflicts)

**Critical**: Always verify with grep after each wave to catch missed references

### File Naming Conventions

**Observed Pattern**: Project uses descriptive UPPERCASE files for reports/audits:
- `REBRANDING_AUDIT_REPORT.md` - Initial audit findings
- `REBRANDING_EXECUTION_PLAN.json` - Wave-based execution plan
- `REBRANDING_VERIFICATION_REPORT.md` - Post-wave verification
- `SECURITY_AUDIT_POST_REBRANDING.md` - Security findings
- `SECURITY_FIXES_IMPLEMENTATION.md` - Fix implementation details
- `SECURITY_SUMMARY.md` - Executive summary

**Preference**: User prefers keeping audit history visible in root, not archived

### Build Script Pattern

**build.sh Structure**:
```bash
#!/bin/bash
set -e  # Exit on error

# Determine build type from argument
if [ "$1" = "dev" ]; then
    cargo build
else
    cargo build --release
fi

# Test if requested
if [ "$2" = "test" ]; then
    cargo test
fi

# Show binary location
echo "Binary: target/release/task-watchdog"
```

**User Preference**: Simple wrapper around cargo, not complex build logic

### Documentation Layering

**Discovered Hierarchy**:
1. README.md - User quickstart (how to use)
2. INTEGRATION.md - Dev-Kid integration specifics
3. DEV_PLANE.md - Multi-tool architecture philosophy
4. SUPPORTED_TOOLS.md - Per-tool integration examples

**Pattern**: Each doc builds on previous, increasing technical depth

## Critical Implementation Paths

### Rebranding Execution

**Verified Approach**:
1. Use Edit tool for targeted replacements (not Write entire files)
2. Multiple replacements in single Edit call for efficiency
3. Verify each file individually after editing
4. Run comprehensive grep audit after wave completion
5. Only audit/report files should contain old naming

**Anti-Pattern**: Don't use Write tool for large files with minor changes - wastes tokens and risks data loss

### Security Fix Priority

**Must Address Before Production**:
1. **docker.rs command injection** (CRITICAL)
   - Line 46-52: Shell interpolation with user input
   - Fix: Use Docker exec API with argument array

2. **main.rs path traversal** (HIGH)
   - Registry path parameter needs validation
   - Fix: Canonicalize and check against allowed directories

3. **registry.rs file permissions** (MEDIUM)
   - Currently uses default 0644 permissions
   - Fix: Create files with mode 0600

**Rationale**: Command injection is most critical (remote code execution risk)

### Build Verification Sequence

**Required Steps**:
1. `cargo clean` - Remove ALL old artifacts
2. Verify target/ directory empty/removed
3. `./build.sh` - Fresh build
4. Check binary exists: `test -f target/release/task-watchdog`
5. Test binary: `target/release/task-watchdog --version`
6. Grep verification: No old naming in source
7. Functional test: Run basic commands (stats, check)

**Don't Skip**: cargo clean is essential to avoid confusion with old binaries

## User Preferences

### Communication Style
- Prefers clear status indicators (checkmarks, symbols)
- Appreciates detailed verification reports
- Wants to see both what was done AND what's next
- Values explicit file paths in summaries

### Technical Approach
- Evidence-based (grep verification, not assumptions)
- Wave-based execution for complex changes
- Comprehensive documentation updates
- Security-conscious (wants fixes before production)

### Project Organization
- Keeps audit/report files visible (not archived)
- Uses UPPERCASE for report files
- Descriptive file names over short abbreviations
- Documentation lives in project root, not docs/ folder

## Discovered Quirks

### No Git Repository Yet
**Observation**: Project has no .git/ directory despite being production code

**Implication**:
- No commit history to analyze
- Can't use git for verification checkpoints
- Wave completion checkpoints will need different mechanism
- Should initialize git after rebranding complete

### Docker vs Native Strategy

**Pattern**: Project uses hybrid execution model
- Native processes: Trusted code (builds, tests)
- Docker containers: Untrusted/user code (isolation)

**Quirk**: Container naming changed from `claude-task-` to `dev-task-`
- Suggests broader "dev workflow" context beyond just Claude
- Aligns with "dev plane" multi-tool strategy

### Environment Variable Naming

**Original**: `CLAUDE_TASK_ID` (tool-branded)
**New**: `TASK_ID` (generic)

**Insight**: User prioritizes tool-agnostic design while keeping "task-watchdog" name
- Name reflects Claude origin/primary use
- Implementation is intentionally generic
- Classic "built for X, works for everyone" strategy

## Performance Insights

### Token Efficiency Lessons

**Rebranding Wave 1**:
- 5 tasks completed in single session
- Used Edit tool exclusively (not Write)
- Multiple replacements per Edit call
- Minimal token overhead

**Estimated**:
- Read 5 files: ~10K tokens
- Edit 5 files: ~5K tokens
- Verification: ~2K tokens
- Total: ~17K tokens for complete wave

**Lesson**: Wave-based parallel execution is token-efficient for independent changes

### Build Optimization Observations

**Cargo.toml optimizations**:
```toml
opt-level = "z"      # Size optimization (also fast)
lto = true           # Link-time optimization
codegen-units = 1    # Single codegen unit
strip = true         # Remove debug symbols
panic = "abort"      # No unwinding
```

**Results**: 2MB binary, 4ms startup, 2.8MB memory

**Lesson**: Rust can match C-level performance with right optimization flags

## Project Gotchas

### Common Mistakes to Avoid

1. **Don't assume binary name**: Check Cargo.toml `name` field (task-watchdog, not claude-watchdog)

2. **Don't skip cargo clean**: Old binaries persist in target/ with old names

3. **Don't forget container names**: Docker containers use `dev-task-` prefix, not `claude-task-`

4. **Don't overlook env vars**: `TASK_ID` not `CLAUDE_TASK_ID`

5. **Don't trust first grep**: Verify exclusions (--include patterns) to avoid false negatives

### File Structure Assumptions

**Assumption**: All Rust code in src/
**Reality**: True for this project

**Assumption**: Documentation in docs/
**Reality**: Documentation in project root

**Assumption**: Tests in tests/
**Reality**: No tests directory yet (tests in src/ files)

## Next Session Hints

### Quick Context Restoration

**One-liner**: "Wave 1 of rebranding completed successfully. All documentation updated from claude-watchdog to task-watchdog. Ready for Wave 2: clean build artifacts, rebuild binary, verify functionality."

**Key Files to Read**:
1. `/home/gyasis/Documents/code/dev-kid/rust-watchdog/memory-bank/progress.md` - Current status
2. `/home/gyasis/Documents/code/dev-kid/rust-watchdog/REBRANDING_EXECUTION_PLAN.json` - Full plan
3. `/home/gyasis/Documents/code/dev-kid/rust-watchdog/memory-bank/activeContext.md` - Recent changes

### Commands Ready to Execute (Wave 2)

```bash
# REBRAND-006: Clean artifacts
cd /home/gyasis/Documents/code/dev-kid/rust-watchdog
cargo clean

# REBRAND-007: Build new binary
./build.sh

# Verify binary
ls -lh target/release/task-watchdog
target/release/task-watchdog --version

# REBRAND-008: Final verification
grep -r "claude-watchdog" --include="*.md" --include="*.sh" --include="*.rs" . | grep -v "REBRANDING_"
```

### Critical Success Factors

1. Verify binary name is `task-watchdog` (not claude-watchdog)
2. Test binary actually runs (not just compiles)
3. Confirm grep shows zero old branding references
4. Update progress.md after Wave 2 completion
5. Proceed to Wave 3 security fixes only after Wave 2 verified

## Intelligence Synthesis

**Project Maturity**: Production-ready core, mid-rebranding refinement

**Risk Level**: Low - well-architected, systematic execution

**User Sophistication**: High - understands wave-based execution, security implications, documentation layering

**Optimal Approach**: Evidence-based verification at each step, comprehensive documentation, security-first mindset

**Success Pattern**: Small, verified increments rather than large risky changes
