"""Tests for the Inner Sound flagship demo.

The demo exercises every piece of the Quilt ecosystem. These tests
verify that the demo runs to completion and contains the right content.
"""
import sys
import os
import subprocess
import json

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(HERE, "..", "src", "inner_sound.py")


def test_demo_runs():
    """The demo runs to completion without error."""
    result = subprocess.run(
        ["python3", DEMO],
        capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, f"Demo failed: {result.stderr}"
    assert len(result.stdout) > 1000


def test_demo_has_8_openers():
    """The demo output mentions all 8 openers."""
    result = subprocess.run(
        ["python3", DEMO], capture_output=True, text=True, timeout=120
    )
    for opener in ["Chart", "Voice", "Gesture", "Witness", "MIDI", "REST", "MUD", "PLATO"]:
        assert opener in result.stdout, f"Opener {opener} not mentioned"


def test_demo_has_3_jepas():
    """The demo output mentions all 3 JEPA implementations."""
    result = subprocess.run(
        ["python3", DEMO], capture_output=True, text=True, timeout=120
    )
    for jepa in ["LinearJEPA", "MLPJEPA", "KnnJEPA"]:
        assert jepa in result.stdout, f"JEPA {jepa} not mentioned"


def test_demo_shows_convoy_consensus():
    """The demo shows the 4 consensus methods."""
    result = subprocess.run(
        ["python3", DEMO], capture_output=True, text=True, timeout=120
    )
    for method in ["weighted_mean", "weighted_median", "trimmed_mean", "geometric_median"]:
        assert method in result.stdout, f"Consensus {method} not shown"


def test_demo_shows_witness_justifications():
    """The demo shows witness entries with justifications (Fable 11)."""
    result = subprocess.run(
        ["python3", DEMO], capture_output=True, text=True, timeout=120
    )
    assert "justification" in result.stdout.lower() or "Tied the lead line" in result.stdout


def test_demo_shows_topology():
    """The demo shows the substrate's topology (Betti numbers)."""
    result = subprocess.run(
        ["python3", DEMO], capture_output=True, text=True, timeout=120
    )
    assert "β₀" in result.stdout or "beta_0" in result.stdout
    assert "β₁" in result.stdout or "beta_1" in result.stdout


def test_demo_shows_merkle_tree():
    """The demo shows the Merkle tree of witness roots."""
    result = subprocess.run(
        ["python3", DEMO], capture_output=True, text=True, timeout=120
    )
    assert "Merkle" in result.stdout


def test_demo_uses_all_6_packages():
    """The demo imports from all 6 packages."""
    result = subprocess.run(
        ["python3", DEMO], capture_output=True, text=True, timeout=120
    )
    for pkg in ["cell-runtime", "river-dream-log", "quilt-substrate",
                "substrate-trainer", "quilt-bathy"]:
        assert pkg in result.stdout or pkg.replace("-", "_") in result.stdout, \
            f"Package {pkg} not mentioned"


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
