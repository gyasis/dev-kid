#!/usr/bin/env python3
"""
Constitution Parser - Parse and validate project constitutions

This module provides the Constitution class for parsing .constitution.md files
and validating code against constitutional rules.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ConstitutionViolation:
    """Represents a violation of constitution rules"""
    file: str
    line: int
    rule: str
    message: str


@dataclass
class ConstitutionSection:
    """Represents a section of the constitution"""
    name: str
    rules: List[str]


class Constitution:
    """
    Constitution parser and validator

    Parses .constitution.md files and provides validation
    capabilities for dev-kid workflow integration.
    """

    REQUIRED_SECTIONS = [
        "Technology Standards",
        "Architecture Principles",
        "Testing Standards",
        "Code Standards",
        "Security Standards"
    ]

    def __init__(self, file_path: str = "memory-bank/shared/.constitution.md"):
        """
        Load constitution from memory-bank/shared/.constitution.md

        Args:
            file_path: Path to constitution markdown file
        """
        self.file_path = Path(file_path)
        self.sections: Dict[str, ConstitutionSection] = {}
        self.rules: Dict[str, str] = {}

        if self.file_path.exists():
            self.rules = self._parse(str(file_path))

    def _parse(self, file_path: str) -> Dict[str, str]:
        """
        Parse constitution markdown file into rule dictionary

        Args:
            file_path: Path to constitution file

        Returns:
            Dictionary mapping rule names to rule definitions
        """
        content = self.file_path.read_text()

        # Extract sections (## Section Name)
        section_pattern = r'^## (.+)$'
        current_section = None
        current_rules = []
        rule_dict = {}

        for line in content.split('\n'):
            # Check for section header
            section_match = re.match(section_pattern, line.strip())
            if section_match:
                # Save previous section
                if current_section:
                    self.sections[current_section] = ConstitutionSection(
                        name=current_section,
                        rules=current_rules
                    )

                    # Add to rule dictionary with section prefix
                    for i, rule in enumerate(current_rules, 1):
                        rule_key = f"{current_section}.{i}"
                        rule_dict[rule_key] = rule

                # Start new section
                current_section = section_match.group(1)
                current_rules = []

            # Check for rule (- Rule text)
            elif line.strip().startswith('- '):
                rule = line.strip()[2:].strip()
                if rule and current_section:
                    current_rules.append(rule)

        # Save last section
        if current_section:
            self.sections[current_section] = ConstitutionSection(
                name=current_section,
                rules=current_rules
            )

            # Add to rule dictionary
            for i, rule in enumerate(current_rules, 1):
                rule_key = f"{current_section}.{i}"
                rule_dict[rule_key] = rule

        return rule_dict

    def get_rules_for_task(self, task) -> List[str]:
        """
        Extract rules relevant to this specific task

        Args:
            task: Task object with constitution_rules attribute

        Returns:
            List of relevant rules
        """
        # If task has explicit constitution_rules, use those
        if hasattr(task, 'constitution_rules') and task.constitution_rules:
            relevant_rules = []
            for rule_key in task.constitution_rules:
                if rule_key in self.rules:
                    relevant_rules.append(self.rules[rule_key])
                else:
                    # Try to match by section
                    section_name = rule_key.split('.')[0] if '.' in rule_key else rule_key
                    if section_name in self.sections:
                        relevant_rules.extend(self.sections[section_name].rules)
            return relevant_rules

        # Otherwise, extract based on task description
        task_description = task.description if hasattr(task, 'description') else str(task)
        return self._get_rules_by_keywords(task_description)

    def _get_rules_by_keywords(self, task_description: str) -> List[str]:
        """
        Extract relevant constitution rules based on keywords

        Args:
            task_description: Task description string

        Returns:
            List of relevant rules
        """
        relevant_rules = []

        # Keyword to section mapping
        keywords = {
            "api": ["Technology Standards", "Architecture Principles"],
            "test": ["Testing Standards"],
            "model": ["Technology Standards", "Architecture Principles"],
            "database": ["Technology Standards", "Security Standards"],
            "auth": ["Security Standards"],
            "security": ["Security Standards"],
            "function": ["Code Standards"],
            "class": ["Code Standards"],
            "type": ["Code Standards"],
        }

        task_lower = task_description.lower()

        for keyword, sections in keywords.items():
            if keyword in task_lower:
                for section_name in sections:
                    if section_name in self.sections:
                        relevant_rules.extend(self.sections[section_name].rules)

        # Always include Code Standards as baseline
        if not relevant_rules and "Code Standards" in self.sections:
            relevant_rules.extend(self.sections["Code Standards"].rules)

        return relevant_rules

    def validate_output(self, files: List[str]) -> List[ConstitutionViolation]:
        """
        Validate modified files against constitution rules

        Checks for:
        - Type hints on all functions
        - Docstrings on public functions/classes
        - No hardcoded secrets (API keys, passwords)
        - Test coverage for new code
        - Security best practices

        Args:
            files: List of file paths to validate

        Returns:
            List of violations found
        """
        violations = []

        for file_path in files:
            # Convert to string if Path object
            file_str = str(file_path)

            # Check if file exists
            if not Path(file_str).exists():
                continue

            # Skip non-Python files
            if not file_str.endswith('.py'):
                continue

            # Validate this file
            file_violations = self.validate_file(file_str)
            violations.extend(file_violations)

        return violations

    def validate_file(self, file_path: str) -> List[ConstitutionViolation]:
        """
        Validate a single file against constitution rules

        Args:
            file_path: Path to file to validate

        Returns:
            List of violations found
        """
        violations = []
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            return violations

        # Only validate Python files for now
        if not file_path.endswith('.py'):
            return violations

        content = file_path_obj.read_text()
        lines = content.split('\n')

        # Check code standards
        code_section = self.sections.get("Code Standards", ConstitutionSection("", []))

        for rule in code_section.rules:
            # Type hints check
            if "type hint" in rule.lower() or "type annotation" in rule.lower():
                violations.extend(self._check_type_hints(file_path, lines, rule))

            # Docstring check
            if "docstring" in rule.lower():
                violations.extend(self._check_docstrings(file_path, lines, rule))

        # Check testing standards
        testing_section = self.sections.get("Testing Standards", ConstitutionSection("", []))

        for rule in testing_section.rules:
            # Test coverage check (basic heuristic)
            if "coverage" in rule.lower() or "test" in rule.lower():
                violations.extend(self._check_test_coverage(file_path, lines, rule))

        # Check security standards
        security_section = self.sections.get("Security Standards", ConstitutionSection("", []))

        for rule in security_section.rules:
            # Check for hardcoded secrets
            if "hardcoded" in rule.lower() or "secret" in rule.lower():
                violations.extend(self._check_hardcoded_secrets(file_path, lines, rule))

        return violations

    def _check_type_hints(self, file_path: str, lines: List[str], rule: str) -> List[ConstitutionViolation]:
        """
        Check for functions without type hints

        Validates that all public functions have:
        - Return type annotations (->)
        - Parameter type hints (for non-self/cls parameters)
        """
        violations = []

        for i, line in enumerate(lines, 1):
            # Skip private/dunder methods
            if re.match(r'\s*def\s+_[_\w]*\(', line):
                continue

            # Check for function definition
            if line.strip().startswith('def '):
                # Check if it's a simple property or setter
                if '@property' in '\n'.join(lines[max(0, i-3):i]):
                    continue

                # Check for return type hint
                if '->' not in line:
                    violations.append(ConstitutionViolation(
                        file=file_path,
                        line=i,
                        rule="TYPE_HINTS_REQUIRED",
                        message="Function missing return type hint"
                    ))

                # Check for parameter type hints
                # Extract function signature
                func_match = re.search(r'def\s+\w+\s*\((.*?)\)', line)
                if func_match:
                    params = func_match.group(1).strip()
                    # Skip if no parameters or only self/cls
                    if params and params not in ['self', 'cls']:
                        # Check if parameters have type hints
                        param_list = [p.strip() for p in params.split(',')]
                        for param in param_list:
                            # Skip self, cls, *args, **kwargs
                            if param in ['self', 'cls'] or param.startswith('*'):
                                continue
                            # Check if parameter has type hint (:)
                            if ':' not in param:
                                violations.append(ConstitutionViolation(
                                    file=file_path,
                                    line=i,
                                    rule="TYPE_HINTS_REQUIRED",
                                    message=f"Parameter '{param}' missing type hint"
                                ))

        return violations

    def _check_docstrings(self, file_path: str, lines: List[str], rule: str) -> List[ConstitutionViolation]:
        """
        Check for functions/classes without docstrings

        Validates that all public functions and classes have docstrings.
        Skips private methods (starting with _).
        """
        violations = []

        for i, line in enumerate(lines, 1):
            # Skip private methods
            if re.match(r'\s*def\s+_[_\w]*\(', line):
                continue

            # Skip private classes
            if re.match(r'\s*class\s+_[_\w]*', line):
                continue

            if line.strip().startswith('def ') or line.strip().startswith('class '):
                # Check if next non-empty line is a docstring
                next_lines = lines[i:i+3] if i < len(lines) else []
                has_docstring = any('"""' in l or "'''" in l for l in next_lines)

                if not has_docstring:
                    entity_type = "Function" if line.strip().startswith('def ') else "Class"
                    violations.append(ConstitutionViolation(
                        file=file_path,
                        line=i,
                        rule="DOCSTRINGS_REQUIRED",
                        message=f"{entity_type} missing docstring"
                    ))

        return violations

    def _check_test_coverage(self, file_path: str, lines: List[str], rule: str) -> List[ConstitutionViolation]:
        """
        Check for test coverage requirements

        Validates:
        - Test files contain actual test functions
        - New .py files have corresponding test files (heuristic check)
        """
        violations = []
        file_path_obj = Path(file_path)

        # Check if this is a test file
        is_test_file = 'test_' in file_path_obj.name or file_path_obj.name.endswith('_test.py')

        if is_test_file:
            # Count test functions
            test_count = sum(1 for line in lines if line.strip().startswith('def test_'))

            # If this is a test file with no tests, flag it
            if test_count == 0:
                violations.append(ConstitutionViolation(
                    file=file_path,
                    line=1,
                    rule="TEST_COVERAGE_REQUIRED",
                    message="Test file contains no test functions"
                ))
        else:
            # Check if this is a regular Python file that should have tests
            # Skip __init__.py and other special files
            if file_path_obj.name in ['__init__.py', 'setup.py', 'conftest.py']:
                return violations

            # Check if corresponding test file exists
            # Try both test_<name>.py and <name>_test.py patterns
            parent_dir = file_path_obj.parent
            stem = file_path_obj.stem
            test_file_1 = parent_dir / f"test_{stem}.py"
            test_file_2 = parent_dir / f"{stem}_test.py"

            # Also check in tests/ directory if it exists
            tests_dir = parent_dir / "tests"
            test_file_3 = tests_dir / f"test_{stem}.py" if tests_dir.exists() else None

            has_test_file = (test_file_1.exists() or
                           test_file_2.exists() or
                           (test_file_3 and test_file_3.exists()))

            if not has_test_file:
                violations.append(ConstitutionViolation(
                    file=file_path,
                    line=1,
                    rule="TEST_COVERAGE_REQUIRED",
                    message=f"No test file found for {file_path_obj.name} (expected test_{stem}.py or {stem}_test.py)"
                ))

        return violations

    def _check_hardcoded_secrets(self, file_path: str, lines: List[str], rule: str) -> List[ConstitutionViolation]:
        """
        Check for hardcoded secrets in code

        Detects potential hardcoded credentials, API keys, passwords, and tokens.
        Excludes safe patterns like os.getenv, environment variables, and empty values.
        """
        violations = []

        # Common secret keywords to detect
        secret_keywords = [
            'password', 'passwd', 'pwd',
            'api_key', 'apikey', 'api-key',
            'secret', 'secret_key',
            'token', 'auth_token', 'access_token',
            'private_key', 'privatekey',
            'client_secret', 'client-secret'
        ]

        for i, line in enumerate(lines, 1):
            # Skip comments and docstrings
            stripped_line = line.strip()
            if stripped_line.startswith('#'):
                continue
            if stripped_line.startswith('"""') or stripped_line.startswith("'''"):
                continue

            line_lower = line.lower()

            for keyword in secret_keywords:
                if keyword in line_lower:
                    # Check if it's an assignment with a string literal
                    if '=' in line and ('"' in line or "'" in line):
                        # Exclude common safe patterns
                        safe_patterns = [
                            'os.getenv', 'os.environ',
                            'environ.get', 'config.get',
                            'None', '""', "''",
                            'input(', 'getpass(',
                            'default=', 'help=',  # argparse defaults
                        ]

                        is_safe = any(pattern in line for pattern in safe_patterns)

                        if not is_safe:
                            violations.append(ConstitutionViolation(
                                file=file_path,
                                line=i,
                                rule="NO_HARDCODED_SECRETS",
                                message=f"Possible hardcoded secret: '{keyword}' assignment detected"
                            ))
                            break  # Only report once per line

        return violations

    def validate_quality(self) -> Tuple[int, List[str]]:
        """
        Validate constitution quality and completeness

        Returns:
            Tuple of (score, recommendations) where score is 0-100
        """
        score = 100
        recommendations = []

        # Check required sections
        for section in self.REQUIRED_SECTIONS:
            if section not in self.sections:
                score -= 15
                recommendations.append(f"Missing required section: {section}")
            elif len(self.sections[section].rules) == 0:
                score -= 10
                recommendations.append(f"Section '{section}' has no rules")
            elif len(self.sections[section].rules) < 3:
                score -= 5
                recommendations.append(f"Section '{section}' has few rules (consider adding more)")

        # Check for specific critical rules
        tech_rules = self.sections.get("Technology Standards", ConstitutionSection("", [])).rules
        if not any("version" in r.lower() or "3." in r or "4." in r for r in tech_rules):
            score -= 5
            recommendations.append("Technology Standards: Specify language/framework versions")

        test_rules = self.sections.get("Testing Standards", ConstitutionSection("", [])).rules
        if not any("coverage" in r.lower() or "%" in r for r in test_rules):
            score -= 5
            recommendations.append("Testing Standards: Specify coverage threshold (e.g., >80%)")

        code_rules = self.sections.get("Code Standards", ConstitutionSection("", [])).rules
        if not any("type" in r.lower() or "hint" in r.lower() for r in code_rules):
            score -= 3
            recommendations.append("Code Standards: Consider requiring type hints")

        # Ensure score doesn't go below 0
        score = max(0, score)

        return score, recommendations


def main():
    """Test/demo the Constitution parser"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: constitution_parser.py <constitution_file>")
        sys.exit(1)

    constitution = Constitution(sys.argv[1])

    print(f"\n📜 Constitution Loaded: {constitution.file_path}\n")

    # Show sections
    print("Sections:")
    for section_name, section in constitution.sections.items():
        print(f"  • {section_name}: {len(section.rules)} rules")

    print(f"\nTotal rules: {len(constitution.rules)}\n")

    # Validate quality
    score, recommendations = constitution.validate_quality()
    print(f"Quality Score: {score}/100\n")

    if recommendations:
        print("Recommendations:")
        for rec in recommendations:
            print(f"  • {rec}")
    else:
        print("✅ Constitution is well-formed\n")


if __name__ == '__main__':
    main()
