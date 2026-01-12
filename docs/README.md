# Dev-Kid Documentation

Organized documentation for the dev-kid project.

## Root Documentation (User-Facing)

Essential files kept in project root:

- **README.md** - Main project overview and quickstart
- **CLAUDE.md** - Claude Code integration instructions
- **INSTALLATION.md** - Installation guide
- **DEV_KID.md** - Complete system reference

## Documentation Structure

### Architecture (`architecture/`)

System design and architecture documentation:

- **ARCHITECTURE.md** - System architecture deep dive
- **ARCHITECTURE_DATA_FLOW.md** - Data flow and state management
- **ARCHITECTURE_REVIEW_SUMMARY.md** - Architecture review findings
- **TASK_WATCHDOG_ARCHITECTURE_GAP_ANALYSIS.md** - Watchdog design analysis

### Reference (`reference/`)

API and command reference documentation:

- **API.md** - Python API reference
- **CLI_REFERENCE.md** - Command-line interface reference
- **SKILLS_REFERENCE.md** - Skills documentation

### Development (`development/`)

Developer guides and contribution docs:

- **CONTRIBUTING.md** - Contribution guidelines
- **DEPENDENCIES.md** - System dependencies
- **DEVELOPER_TRAINING_GUIDE.md** - Developer onboarding guide
- **IMPLEMENTATION_COMPLETE.md** - Implementation completion reports

### Constitution (`constitution/`)

Constitution system design and testing:

- **CONSTITUTION_CONFIG_INTEGRATION_TEST.md** - Integration test results
- **CONSTITUTION_MANAGEMENT_DESIGN.md** - Constitution management design
- **CONSTITUTION_METADATA.md** - Constitution metadata specification

### Speckit Integration (`speckit-integration/`)

Speckit + dev-kid integration documentation:

- **SPECKIT_DEVKID_INTEGRATION_GUARANTEE.md** - Integration contract
- **SPECKIT_INTEGRATION_GAP_ANALYSIS.md** - Gap analysis
- **SPECKIT-004-COMPLETION-REPORT.md** - Feature 004 completion
- **SPECKIT-005-VERIFICATION.md** - Feature 005 verification
- **SPECKIT-008-FLOW.md** - Workflow documentation
- **SPECKIT-008-IMPLEMENTATION.md** - Implementation details
- **SPECKIT-008-SUMMARY.md** - Feature summary
- **SPECKIT-009-COMPLETION.md** - Feature 009 completion
- **SPECKIT-010-COMPLETION.md** - Feature 010 completion

### Testing (`testing/`)

Test results and verification reports:

- **test_verification_report.md** - Test verification results

## Documentation Guidelines

### For Users

Start with:
1. **README.md** - Project overview
2. **INSTALLATION.md** - Get installed
3. **DEV_KID.md** - Learn the system

### For Developers

Onboarding path:
1. **development/DEVELOPER_TRAINING_GUIDE.md** - Start here
2. **architecture/ARCHITECTURE.md** - Understand design
3. **development/CONTRIBUTING.md** - Contribution process
4. **reference/** - API and CLI references

### For Claude Code Integration

Claude-specific docs:
1. **CLAUDE.md** - Project instructions for Claude
2. **speckit-integration/** - Speckit workflow integration
3. **reference/SKILLS_REFERENCE.md** - Skills documentation

## Maintaining Documentation

### When to Update

- **Architecture** changes → Update `architecture/ARCHITECTURE.md`
- New **API/CLI** features → Update `reference/` docs
- **Constitution** changes → Update `constitution/` docs
- **Speckit integration** changes → Update `speckit-integration/` docs

### Documentation Standards

- Use clear headings and structure
- Include code examples
- Keep root docs user-facing and concise
- Deep technical details go in `docs/` subdirectories
- Use relative links between docs
