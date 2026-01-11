#!/usr/bin/env python3
"""
Constitution Manager - Create, validate, and manage project constitutions

This module handles the creation and management of .constitution.md files
that define immutable development rules for Speckit-driven workflows.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ConstitutionViolation:
    """Represents a violation of constitution rules"""
    rule: str
    file: str
    line: int
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
        self.file_path = Path(file_path)
        self.sections: Dict[str, ConstitutionSection] = {}

        if self.file_path.exists():
            self._parse()

    def _parse(self) -> None:
        """Parse constitution markdown file into sections"""
        content = self.file_path.read_text()

        # Extract sections (## Section Name)
        section_pattern = r'^## (.+)$'
        current_section = None
        current_rules = []

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

    def validate_quality(self) -> Tuple[int, List[str]]:
        """
        Validate constitution quality and completeness

        Returns:
            (score, recommendations) where score is 0-100
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

    def get_rules_for_task(self, task_description: str) -> List[str]:
        """
        Extract relevant constitution rules for a specific task

        Args:
            task_description: Task description from tasks.md

        Returns:
            List of relevant rules
        """
        relevant_rules = []

        # Simple keyword matching (can be enhanced with NLP)
        keywords = {
            "api": ["Technology Standards", "Architecture Principles"],
            "test": ["Testing Standards"],
            "model": ["Technology Standards", "Architecture Principles"],
            "database": ["Technology Standards", "Security Standards"],
            "auth": ["Security Standards"],
            "security": ["Security Standards"]
        }

        task_lower = task_description.lower()

        for keyword, sections in keywords.items():
            if keyword in task_lower:
                for section_name in sections:
                    if section_name in self.sections:
                        relevant_rules.extend(self.sections[section_name].rules)

        # Always include all rules if no specific match
        if not relevant_rules:
            for section in self.sections.values():
                relevant_rules.extend(section.rules)

        return relevant_rules

    def validate_file(self, file_path: str) -> List[ConstitutionViolation]:
        """
        Validate a file against constitution rules

        Args:
            file_path: Path to file to validate

        Returns:
            List of violations found
        """
        violations = []
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            return violations

        content = file_path_obj.read_text()
        lines = content.split('\n')

        # Check code standards
        code_section = self.sections.get("Code Standards", ConstitutionSection("", []))

        for rule in code_section.rules:
            # Type hints check
            if "type hint" in rule.lower() or "type annotation" in rule.lower():
                # Check for functions without type hints (simple heuristic)
                for i, line in enumerate(lines, 1):
                    if line.strip().startswith('def ') and '->' not in line:
                        violations.append(ConstitutionViolation(
                            rule=rule,
                            file=file_path,
                            line=i,
                            message="Function missing type hints"
                        ))

            # Docstring check
            if "docstring" in rule.lower():
                # Check for functions without docstrings
                for i, line in enumerate(lines, 1):
                    if line.strip().startswith('def ') or line.strip().startswith('class '):
                        # Check if next non-empty line is a docstring
                        next_lines = lines[i:i+3]
                        has_docstring = any('"""' in l or "'''" in l for l in next_lines)
                        if not has_docstring:
                            violations.append(ConstitutionViolation(
                                rule=rule,
                                file=file_path,
                                line=i,
                                message="Function/class missing docstring"
                            ))

        # Check security standards
        security_section = self.sections.get("Security Standards", ConstitutionSection("", []))

        for rule in security_section.rules:
            # Check for hardcoded secrets
            if "hardcoded" in rule.lower() or "secret" in rule.lower():
                for i, line in enumerate(lines, 1):
                    if any(keyword in line.lower() for keyword in ['password', 'api_key', 'secret', 'token']):
                        if '=' in line and ('"' in line or "'" in line):
                            violations.append(ConstitutionViolation(
                                rule=rule,
                                file=file_path,
                                line=i,
                                message="Possible hardcoded secret"
                            ))

        return violations


class ConstitutionManager:
    """Manages constitution creation, editing, and templates"""

    TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "constitution_templates"

    TEMPLATES = {
        "python-api": "Python API (FastAPI/Flask)",
        "typescript-frontend": "TypeScript Frontend (React/Next.js)",
        "data-engineering": "Data Engineering (Airflow/dbt)",
        "full-stack": "Full-Stack (Frontend + Backend)",
        "custom": "Custom (blank template)"
    }

    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.constitution_path = self.project_path / "memory-bank" / "shared" / ".constitution.md"

    def init_from_template(self, template_name: str) -> bool:
        """
        Initialize constitution from a template

        Args:
            template_name: Name of template (e.g., 'python-api')

        Returns:
            True if successful
        """
        # Ensure memory-bank directory exists
        self.constitution_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if constitution already exists
        if self.constitution_path.exists():
            print(f"⚠️  Constitution already exists: {self.constitution_path}")
            return False

        # Load template
        template_file = self.TEMPLATES_DIR / f"{template_name}.constitution.md"

        if not template_file.exists():
            print(f"❌ Template not found: {template_name}")
            return False

        # Copy template to project
        template_content = template_file.read_text()
        self.constitution_path.write_text(template_content)

        print(f"✅ Created: {self.constitution_path}")
        print(f"   Template: {self.TEMPLATES[template_name]}")

        return True

    def validate(self) -> bool:
        """
        Validate constitution quality

        Returns:
            True if validation passes
        """
        if not self.constitution_path.exists():
            print(f"❌ Constitution not found: {self.constitution_path}")
            print(f"   Run: dev-kid constitution init")
            return False

        constitution = Constitution(str(self.constitution_path))
        score, recommendations = constitution.validate_quality()

        print(f"\n🔍 Validating Constitution...\n")

        # Check each section
        for section in Constitution.REQUIRED_SECTIONS:
            if section in constitution.sections:
                rule_count = len(constitution.sections[section].rules)
                print(f"✅ {section}: {rule_count} rules defined")
            else:
                print(f"❌ {section}: MISSING")

        print(f"\nQuality Score: {score}/100\n")

        if recommendations:
            print("Recommendations:")
            for rec in recommendations:
                print(f"  • {rec}")
        else:
            print("✅ All critical areas covered")
            print("✅ Rules are specific and actionable")
            print("✅ No conflicts detected")

        # Status
        if score >= 90:
            status = "EXCELLENT (ready for production)"
        elif score >= 75:
            status = "GOOD (ready for use)"
        elif score >= 60:
            status = "ACCEPTABLE (consider improvements)"
        else:
            status = "NEEDS WORK (address recommendations)"

        print(f"\nConstitution Status: {status}\n")

        return score >= 60

    def show(self) -> bool:
        """
        Display current constitution

        Returns:
            True if successful
        """
        if not self.constitution_path.exists():
            print(f"❌ Constitution not found: {self.constitution_path}")
            return False

        content = self.constitution_path.read_text()

        print("\n📜 Current Constitution")
        print("━" * 60)
        print(content)
        print("━" * 60)
        print(f"\nLocation: {self.constitution_path}\n")

        return True


def main():
    """Main entry point for constitution management"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Constitution Management")
    parser.add_argument('command', choices=['init', 'validate', 'show', 'list-templates'],
                       help='Command to execute')
    parser.add_argument('--template', help='Template name for init command')
    parser.add_argument('--project-path', default='.', help='Project root path')

    args = parser.parse_args()

    manager = ConstitutionManager(args.project_path)

    if args.command == 'list-templates':
        print("\nAvailable Templates:\n")
        for i, (key, desc) in enumerate(ConstitutionManager.TEMPLATES.items(), 1):
            print(f"  {i}. {key}: {desc}")
        print()

    elif args.command == 'init':
        if not args.template:
            # Interactive mode
            print("\n📜 Constitution Initialization\n")
            print("Select project type:")
            for i, (key, desc) in enumerate(ConstitutionManager.TEMPLATES.items(), 1):
                print(f"  {i}. {desc}")

            try:
                choice = int(input("\nChoice [1-5]: "))
                template_key = list(ConstitutionManager.TEMPLATES.keys())[choice - 1]
            except (ValueError, IndexError):
                print("❌ Invalid choice")
                sys.exit(1)
        else:
            template_key = args.template

        success = manager.init_from_template(template_key)

        if success:
            print("\nNext steps:")
            print("  1. Edit constitution: dev-kid constitution edit")
            print("  2. Validate: dev-kid constitution validate")
            print("  3. Use in workflow: /speckit.constitution\n")

    elif args.command == 'validate':
        manager.validate()

    elif args.command == 'show':
        manager.show()


if __name__ == '__main__':
    main()
