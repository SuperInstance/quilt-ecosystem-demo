"""Tests for the Inner Sound CLI."""
import sys
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.join(HERE, "..", "src", "inner_sound_cli.py")


def run_cli(commands):
    """Run the CLI with a list of commands, return the output."""
    input_str = "\n".join(commands) + "\n"
    result = subprocess.run(
        ["python3", CLI],
        input=input_str,
        capture_output=True, text=True, timeout=60
    )
    return result.stdout + result.stderr


def test_cli_bathy():
    out = run_cli(["bathy", "exit"])
    assert "Reyes's porch" in out
    assert "0 " in out  # grid line 0


def test_cli_agents():
    out = run_cli(["agents", "exit"])
    assert "reyes" in out
    assert "boat-" in out


def test_cli_stale():
    out = run_cli(["stale", "exit"])
    assert "Stalest" in out


def test_cli_convoy():
    out = run_cli(["convoy", "exit"])
    assert "Convoy" in out


def test_cli_help():
    out = run_cli(["help", "exit"])
    assert "Commands" in out


def test_cli_decoy():
    out = run_cli(["decay", "exit"])
    assert "λ" in out


def test_cli_unknown():
    out = run_cli(["foobar", "exit"])
    assert "Unknown" in out or "foobar" in out


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
