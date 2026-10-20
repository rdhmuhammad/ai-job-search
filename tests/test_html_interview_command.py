"""Tests for the /html-interview command and its dashboard generator.

Verifies command file structure, lint conformity, and that
tools/build_interview_dashboard.py properly compiles interview questions from
documents/applications/ into a self-contained, interactive HTML checklist
that syncs with reports/interview_progress.json.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMAND_FILE = REPO_ROOT / ".claude" / "commands" / "html-interview.md"
BUILD_SCRIPT = REPO_ROOT / "tools" / "build_interview_dashboard.py"
LINT_SCRIPT = REPO_ROOT / "tools" / "lint_skills.py"

try:
    import yaml  # noqa: F401 - probing availability for lint tests
    _HAVE_YAML = True
except ImportError:
    _HAVE_YAML = False


class HtmlInterviewCommandFileTests(unittest.TestCase):
    """Structural checks on the command file itself."""

    def test_command_file_exists(self):
        self.assertTrue(COMMAND_FILE.exists(), f"{COMMAND_FILE} not found")

    def test_command_file_starts_with_correct_header(self):
        """lint_skills.py requires command files to start with '# /<name>'."""
        text = COMMAND_FILE.read_text(encoding="utf-8")
        first_line = text.lstrip().splitlines()[0]
        self.assertTrue(
            first_line.startswith("# /html-interview"),
            f"Command file must start with '# /html-interview', got: {first_line!r}",
        )

    def test_command_file_is_non_empty(self):
        text = COMMAND_FILE.read_text(encoding="utf-8").strip()
        self.assertGreater(len(text), 100, "Command file appears suspiciously short")


class HtmlInterviewDashboardGeneratorTests(unittest.TestCase):
    """Functional tests for tools/build_interview_dashboard.py."""

    def test_build_script_exists(self):
        self.assertTrue(BUILD_SCRIPT.exists(), f"{BUILD_SCRIPT} not found")

    def test_build_interview_dashboard_execution(self):
        """Run build_interview_dashboard.py into a temporary file and verify HTML output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test-dashboard.html"
            json_file = Path(tmpdir) / "test_progress.json"

            # Pre-seed progress data
            seed_data = {
                "updated_at": "2026-10-20T19:00:00Z",
                "checked_questions": ["binance-tech-1"],
                "notes": {"binance-tech-1": "Preloaded test note about worker pool."}
            }
            json_file.write_text(json.dumps(seed_data), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(BUILD_SCRIPT), "--out", str(out_file), "--json", str(json_file)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"build_interview_dashboard.py failed:\n{result.stdout}\n{result.stderr}",
            )
            self.assertTrue(out_file.exists(), "Output HTML file was not generated")

            content = out_file.read_text(encoding="utf-8")

            # Check essential HTML document tags
            self.assertIn("<!DOCTYPE html>", content)
            self.assertIn("<title>Interview Questions & Prep Dashboard</title>", content)

            # Check that companies from documents/applications are rendered
            self.assertIn("Binance", content)
            self.assertIn("Bibit.id", content)
            self.assertIn("Mekari", content)
            self.assertIn("Traveloka", content)

            # Check checklist features
            self.assertIn('class="prep-checkbox"', content)
            self.assertIn('data-qid="', content)
            self.assertIn('STORAGE_KEY_PREFIX', content)

            # Check JSON persistence features
            self.assertIn('Preloaded test note about worker pool.', content)
            self.assertIn('persistToJsonFile', content)
            self.assertIn('/api/progress', content)
            self.assertIn('syncStatusPill', content)

            # Check navigation and filtering
            self.assertIn('class="company-nav-item', content)
            self.assertIn('selectCompany(', content)
            self.assertIn('filterCategory(', content)
            self.assertIn('globalSearchInput', content)

            # Check personal notes area
            self.assertIn('class="notes-textarea"', content)


@unittest.skipUnless(
    _HAVE_YAML,
    "PyYAML not installed",
)
class HtmlInterviewLintIntegrationTests(unittest.TestCase):
    """lint_skills.py must pass with the new command added."""

    def test_lint_passes_on_real_repo(self):
        result = subprocess.run(
            [sys.executable, str(LINT_SCRIPT)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"lint_skills.py failed:\n{result.stdout}{result.stderr}",
        )
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
