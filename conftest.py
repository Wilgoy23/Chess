"""Pytest configuration.

Living at the repo root, this file also puts the root on sys.path, so tests can
`import rules` / `import fen` without any packaging in place.
"""

import os

import pytest


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", default=False,
                     help="run slow cases (deep perft: several minutes)")


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: deep case, skipped unless --runslow")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow") or os.environ.get("PERFT_SLOW"):
        return
    skip_slow = pytest.mark.skip(reason="slow: pass --runslow or set PERFT_SLOW=1")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
