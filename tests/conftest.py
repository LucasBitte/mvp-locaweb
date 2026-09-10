"""Isola contratos de produção sem alterar suas asserções."""
import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if item.path.name.startswith("test_api_"):
            item.add_marker(pytest.mark.banco_real)
        elif item.path.name == "test_ref_meta_sla.py":
            item.add_marker(pytest.mark.integration)
