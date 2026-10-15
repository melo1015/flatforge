import pytest
from flatforge_worker.handlers import dispatch

def test_ping():
    assert dispatch("system.ping")["ok"] is True

def test_unfold_requires_mesh():
    with pytest.raises(ValueError):
        dispatch("geometry.unfold", {})

def test_unknown_method():
    with pytest.raises(KeyError):
        dispatch("missing.method", {})
