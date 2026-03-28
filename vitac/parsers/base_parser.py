"""Abstract base class for test result parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from vitac.types import UnitTestStatus


class BaseParser(ABC):
    """Parse test output into per-test pass/fail results."""

    @abstractmethod
    def parse(self, content: str) -> dict[str, UnitTestStatus]:
        """Parse test output content.

        Returns a dict mapping test names to their status.
        """
        ...
