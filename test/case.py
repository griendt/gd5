import unittest
from typing import Any

from logger import logger


class TestCase(unittest.TestCase):
    def setUp(self) -> None:
        logger.debug(f"Running test: [b][yellow]{self._testMethodName}[/yellow][/b]")
        logger.indents += 1

    def tearDown(self) -> None:
        logger.indents -= 1
        logger.debug(f"Finished test: [b][yellow]{self._testMethodName}[/yellow][/b]")

    def skipTest(self, reason: Any) -> None:
        logger.warning(f"[red]Skipped test[/red] ([i]{reason}[/i])")
        super().skipTest(reason)
