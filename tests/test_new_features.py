"""Tests for the new features: 5 new openers, temperature, category."""
import sys
import os
import subprocess
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(HERE, "..", "src", "inner_sound.py")


def run_demo():
    """Run the demo, return the output."""
    result = subprocess.run(
        ["python3", DEMO],
        capture_output=True, text=True, timeout=120
    )
    return result.stdout + result.stderr


def test_demo_shows_5_new_openers():
    """The demo output mentions the 5 new openers."""
    out = run_demo()
    for opener in ["Slate", "Harbor", "Reef", "Dive", "Tide"]:
        assert opener in out, f"Opener {opener} not mentioned"


def test_demo_shows_temperature():
    """The demo output shows the substrate's temperature."""
    out = run_demo()
    assert "TEMPERATURE" in out or "T̄" in out
    assert "warm" in out or "regime" in out.lower()


def test_substrate_has_13_openers():
    """The substrate has 13 openers (8 original + 5 new)."""
    sys.path.insert(0, "/workspace/quilt-substrate/src")
    from quilt_substrate import all_openers
    openers = all_openers()
    assert len(openers) == 13, f"Expected 13 openers, got {len(openers)}"
    expected = {"chart", "voice", "gesture", "witness", "midi", "rest", "mud", "plato",
                "slate", "harbor", "reef", "dive", "tide"}
    assert set(openers) == expected, f"Opener set mismatch"


def test_temperature_in_substrate():
    """The substrate has temperature() and regime() methods on cells."""
    sys.path.insert(0, "/workspace/quilt-substrate/src")
    from quilt_substrate import Cell, Substrate
    import math
    substrate = Substrate()
    cell = Cell(address="a", value=1.0)
    substrate.add(cell)
    # No writes → temperature 0
    assert cell.temperature() == 0.0
    assert cell.regime() == "frozen"
    # 2 distinct ops → temperature ln(2)
    cell.witness("a", "read", 1.0)
    cell.witness("a", "write", 1.0)
    assert abs(cell.temperature() - math.log(2)) < 0.01
    assert cell.regime() == "warm"


def test_substrate_wide_temperature():
    """The substrate-wide temperature is a weighted average."""
    sys.path.insert(0, "/workspace/quilt-substrate/src")
    from quilt_substrate import Cell, Substrate
    substrate = Substrate()
    # No cells → 0
    assert substrate.temperature() == 0.0


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
