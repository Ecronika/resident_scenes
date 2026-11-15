"""Run pytest against Home Assistant 2026.11 with the test package built for 2026.10.

shortcut: depends on internals of the test package; delete once a test package for 2026.11 exists.
"""

import sys

import pytest  # plugins load only in pytest.main, after the alias below

import homeassistant  # noqa: F401  aliases httpx before any plugin imports it
import homeassistant.components.logger as logger_component
from homeassistant.components.logger.helpers import _clear_logger_overwrites

logger_component._clear_logger_overwrites = _clear_logger_overwrites  # moved in 2026.11

sys.exit(pytest.main(sys.argv[1:]))
