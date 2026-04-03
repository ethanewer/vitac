"""Parser for pytest output."""

from __future__ import annotations

import re

from vitac.parsers.base_parser import BaseParser
from vitac.types import UnitTestStatus


class PytestParser(BaseParser):
    """Parse pytest short test summary output into per-test results."""

    def parse(self, content: str) -> dict[str, UnitTestStatus]:
        results: dict[str, UnitTestStatus] = {}

        # Look for the short test summary info section
        in_summary = False
        for line in content.splitlines():
            stripped = line.strip()

            if "short test summary info" in stripped:
                in_summary = True
                continue

            if in_summary:
                # Summary ends at a line of '=' characters or empty line after results
                if re.match(r"^=+", stripped) and "passed" not in stripped and "failed" not in stripped:
                    break

                # Parse PASSED/FAILED lines
                match = re.match(r"(PASSED|FAILED)\s+(.+)", stripped)
                if match:
                    status_str, test_name = match.groups()
                    status = (
                        UnitTestStatus.PASSED
                        if status_str == "PASSED"
                        else UnitTestStatus.FAILED
                    )
                    results[test_name.strip()] = status

        # If no summary section found, try parsing the result line
        # e.g., "5 passed, 2 failed" or individual test lines
        if not results:
            results = self._parse_verbose_output(content)

        return results

    def _parse_verbose_output(self, content: str) -> dict[str, UnitTestStatus]:
        """Parse verbose pytest output (PASSED/FAILED after test names)."""
        results: dict[str, UnitTestStatus] = {}
        for line in content.splitlines():
            # Match lines like: "test_foo.py::test_bar PASSED"
            match = re.match(r"(.+::.+)\s+(PASSED|FAILED)", line.strip())
            if match:
                test_name, status_str = match.groups()
                status = (
                    UnitTestStatus.PASSED
                    if status_str == "PASSED"
                    else UnitTestStatus.FAILED
                )
                results[test_name.strip()] = status
        return results
