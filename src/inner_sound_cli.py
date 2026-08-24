"""inner_sound_cli.py — Interactive CLI for the Inner Sound demo.

A user can ask:
  > show me the bathy
  > what does the convoy say
  > read the bottom
  > which cells are stale
  > train a JEPA on the witness log
  > exit

The CLI uses the same substrate as the flagship demo, but in an
interactive way. It's the "porch" of the substrate.
"""
import sys
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "cell-runtime", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "river-dream-log"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "quilt-substrate", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "quilt-bathy", "src"))

import cell_runtime
from cell_runtime import Cell as LegacyCell
from quilt_substrate import (
    Cell, Substrate, WitnessEntry, Vibe,
    ChartOpener, VoiceOpener, GestureOpener, WitnessOpener,
    MIDIOpener, RESTOpener, MUDOpener, PLATOOpener,
)
from bathy import BathyChart, Sailor, ConvoyBoat


def build_bathy():
    """Build a small bathy chart with a convoy."""
    chart = BathyChart(bounds={"x": (0, 100), "y": (0, 100), "depth": (0, 30)})
    for i in range(5):
        boat = ConvoyBoat(name=f"boat-{i:02d}")
        for x, y, d in boat.survey(n=5):
            chart.add_convoy_sounding(x, y, d, agent=boat.name)
    reyes = Sailor(name="reyes")
    for x, y, d in reyes.survey(n=30):
        chart.add_sounding(x, y, d, agent=reyes.name)
    return chart


def show_bathy(chart):
    """Print the bathy chart as a simple ASCII depth map."""
    substrate = chart.substrate
    cells = substrate.all_cells()
    if not cells:
        print("No cells.")
        return
    # Extract x, y, value
    pts = []
    for c in cells:
        try:
            x = int(c.address.split("/")[1].split("x")[0])
            y = int(c.address.split("x")[1])
            pts.append((x, y, float(c.value), c.confidence))
        except (ValueError, IndexError):
            continue
    if not pts:
        return
    max_x = max(p[0] for p in pts) + 1
    max_y = max(p[1] for p in pts) + 1
    grid = [["." for _ in range(max_x)] for _ in range(max_y)]
    chars = " ·;-+*#@"  # shallow to deep
    for x, y, d, c in pts:
        idx = min(len(chars) - 1, int(d / 30 * (len(chars) - 1)))
        ch = chars[idx]
        if c < 0.5:
            ch = ch.lower() if ch.isalpha() else "?"
        grid[y][x] = ch
    print("  " + "".join(str(i % 10) for i in range(max_x)))
    for j, row in enumerate(grid):
        print(f"{j:2d} " + "".join(row))


def show_convoy(chart):
    """Show the convoy's statistics."""
    substrate = chart.substrate
    agents = substrate.all_agents()
    print(f"Convoy ({len(agents)} agents):")
    for a in agents:
        n = sum(1 for c in substrate.all_cells() if a in [e.agent_id for e in c.witness_log])
        decay = substrate.get_agent_decay(a) if a in substrate._agent_decay else "default"
        print(f"  {a:20s}  writes: {n:3d}  decay: {decay}")


def read_bottom(chart):
    """Use the voice opener to read the bottom aloud (printed)."""
    substrate = chart.substrate
    print("Reading the bottom (voice opener):")
    for e in list(VoiceOpener().activate(substrate))[:5]:
        print(f"  \"{e['text']}\"")
    if len(list(substrate.all_cells())) > 5:
        print(f"  ... ({len(list(substrate.all_cells())) - 5} more cells)")


def show_stale(chart):
    """Find the cells that have decayed the most."""
    substrate = chart.substrate
    cells = substrate.all_cells()
    # Sort by confidence ascending
    cells.sort(key=lambda c: c.confidence)
    print(f"Stalest 5 cells:")
    for c in cells[:5]:
        last = c.witness_log[-1] if c.witness_log else None
        agent = last.agent_id if last else "?"
        print(f"  {c.address}  value={float(c.value):.2f}m  conf={c.confidence:.4f}  last={agent}")


def train_jepa(chart):
    """Show a few JEPA predictions."""
    substrate = chart.substrate
    cells = substrate.all_cells()
    if not cells:
        print("No cells.")
        return
    # Build a simple linear model from the cells
    xs = []
    ys = []
    for c in cells:
        try:
            x = int(c.address.split("/")[1].split("x")[0])
            y = int(c.address.split("x")[1])
            xs.append([x, y])
            ys.append(float(c.value))
        except (ValueError, IndexError):
            continue
    if not xs:
        return
    # Predict at un-surveyed locations
    print("JEPA predictions (linear model, mean by quadrant):")
    quadrants = {"NW": [], "NE": [], "SW": [], "SE": []}
    for (x, y), d in zip(xs, ys):
        q = "NE" if x >= 50 else "NW"
        q += "S" if y >= 50 else "N" if "N" in q else "N"
        # Simpler:
        if x < 50 and y < 50:
            quadrants["NW"].append(d)
        elif x >= 50 and y < 50:
            quadrants["NE"].append(d)
        elif x < 50 and y >= 50:
            quadrants["SW"].append(d)
        else:
            quadrants["SE"].append(d)
    for q, vals in quadrants.items():
        if vals:
            print(f"  {q}: depth ≈ {sum(vals)/len(vals):.2f}m  (n={len(vals)})")


def help_text():
    print("""
Commands:
  bathy       Show the bathy chart (ASCII)
  convoy      Show the convoy's statistics
  read        Read the bottom aloud (voice opener)
  stale       Find the stalest cells
  jepe        Show JEPA predictions
  agents      List all agents
  prime       Count cells per agent
  decay       Show decay rates
  exit        Exit the CLI

The substrate is the soil. The bathy is the plant.
The witness log is the rain. The openers are the kindness.
""")


def main():
    print("Reyes's porch — the substrate's CLI.")
    print("Type 'help' for commands, 'exit' to quit.")
    chart = build_bathy()
    substrate = chart.substrate
    print(f"Built bathy: {len(substrate)} cells, {len(substrate.all_agents())} agents.\n")
    while True:
        try:
            line = input("reyes> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return
        if not line:
            continue
        cmd = line.split()[0].lower()
        rest = line[len(cmd):].strip()
        if cmd in ("exit", "quit", "q"):
            print("Goodbye.")
            return
        elif cmd in ("help", "?", "h"):
            help_text()
        elif cmd == "bathy":
            show_bathy(chart)
        elif cmd == "convoy":
            show_convoy(chart)
        elif cmd == "read":
            read_bottom(chart)
        elif cmd == "stale":
            show_stale(chart)
        elif cmd == "jepe" or cmd == "jepa":
            train_jepa(chart)
        elif cmd == "agents":
            for a in substrate.all_agents():
                print(f"  {a}")
        elif cmd == "prime":
            counts = {}
            for c in substrate.all_cells():
                for e in c.witness_log:
                    counts[e.agent_id] = counts.get(e.agent_id, 0) + 1
            for a, n in sorted(counts.items(), key=lambda x: -x[1]):
                print(f"  {a:20s}  {n}")
        elif cmd == "decay":
            for a in substrate.all_agents():
                d = substrate._agent_decay.get(a, "default")
                print(f"  {a:20s}  λ = {d}")
        else:
            print(f"Unknown command: {cmd}. Type 'help'.")


if __name__ == "__main__":
    main()
