"""
inner_sound.py — The flagship integration demo.

A single program that exercises every piece of the Quilt ecosystem:
- cell-runtime: the 8-primitive cell as a Python type
- quilt-substrate: the 11-primitive substrate, with openers, JEPAs, advance_time
- substrate-trainer: JEPA-like model trained on the witness log
- quilt-bathy: the bathy cross-section as a working tool
- river-dream-log: agentic journaling (Hold/Wake/Dawn)
- porch: CLI for 3 a.m. thoughts (we don't use this in the demo, but it's imported)

The story: Reyes is sailing the Inner Sound on a 12-inch tablet.
The tablet runs the full Quilt ecosystem. The chart is the substrate.
The convoy is the other boats in her fishing club. The witness log
is every action she's taken. The voice opener reads the bottom aloud.

This is the substrate, the bathy, and the fables, all running together.
"""
import sys
import os
import time
import random
import math
import json
import argparse

# Make the sibling repos importable
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "cell-runtime", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "river-dream-log"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "river-dream-log", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "quilt-substrate", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "substrate-trainer", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "quilt-bathy", "src"))

# Imports — all 6 packages
import cell_runtime
LegacyCell = cell_runtime.Cell
from river_dream_log import River
from quilt_substrate import (
    Cell, Substrate, ConvoyEntry, WitnessEntry, Vibe,
    Opener, ChartOpener, VoiceOpener, GestureOpener, WitnessOpener,
    MIDIOpener, RESTOpener, MUDOpener, PLATOOpener,
    register, get, all_openers,
    LinearJEPA, MLPJEPA, KnnJEPA, auto_train_jepa,
)
import trainer
Trainer = trainer.Trainer
WitnessLogDataset = trainer.WitnessLogDataset
JEPAModel = trainer.JEPAModel
from bathy import BathyChart, Sailor, ConvoyBoat


def section(title):
    """Print a section header."""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def subsection(title):
    """Print a subsection header."""
    print()
    print(f"--- {title} ---")


def build_bathy_with_substrate():
    """The Inner Sound: build a bathy chart with a convoy."""
    section("THE INNER SOUND — Reyes's bathy chart with the convoy")
    chart = BathyChart(bounds={"x": (0, 100), "y": (0, 100), "depth": (0, 30)})
    # 10 boats in the convoy
    for i in range(10):
        boat = ConvoyBoat(name=f"boat-{i:02d}")
        for x, y, d in boat.survey(n=15):
            chart.add_convoy_sounding(x, y, d, agent=boat.name)
    # Reyes's own high-res data
    reyes = Sailor(name="reyes")
    for x, y, d in reyes.survey(n=80):
        chart.add_sounding(x, y, d, agent=reyes.name)
    n_cells = len(chart.substrate)
    n_agents = len(chart.substrate.all_agents())
    print(f"Built bathy chart: {n_cells} cells, {n_agents} agents in the convoy")
    return chart


def setup_per_agent_decay(substrate):
    """Set decay rates per agent type."""
    subsection("Per-agent decay rates (Q8: freshness depends on data type)")
    # Reyes is a human, her data is moderately fresh
    substrate.set_agent_decay("reyes", 0.001)  # minutes
    # Boats are sensors, slower decay
    for i in range(10):
        substrate.set_agent_decay(f"boat-{i:02d}", 1e-3)
    # The substrate's own inferences decay fast (chat-like)
    substrate.set_agent_decay("inference", 0.1)
    print("Set decay rates:")
    print(f"  reyes:     λ = {substrate.get_agent_decay('reyes')} (1/minute half-life)")
    print(f"  boat-00:   λ = {substrate.get_agent_decay('boat-00')} (1/minute half-life)")
    print(f"  inference: λ = {substrate.get_agent_decay('inference')} (1/10s half-life)")


def showcase_8_openers(chart):
    """Render the chart through all 8 openers."""
    section("THE 8 OPENERS — the same chart, 8 different views (Fable 06, 10, 11, 21)")
    substrate = chart.substrate

    # Chart opener
    subsection("1. Chart (data view)")
    events = list(ChartOpener().activate(substrate))
    print(f"  Yielded {len(events)} value events")
    if events:
        e = events[0]
        print(f"  First event: kind={e['kind']}, address={e['address']}, value={e['value']:.2f}")

    # Voice opener
    subsection("2. Voice (TTS — Fable 06 Grandmother)")
    events = list(VoiceOpener().activate(substrate))
    print(f"  Yielded {len(events)} speech events")
    print(f"  First 3 phrases:")
    for e in events[:3]:
        print(f"    \"{e['text']}\"")

    # Gesture opener
    subsection("3. Gesture (touch — Fable 06 Grandmother)")
    events = list(GestureOpener().activate(substrate))
    print(f"  Yielded {len(events)} tap events")
    if events:
        e = events[0]
        print(f"  First cell: tap={e['tap']['action']}, long_press={e['long_press']['action']}, swipe={e['swipe_right']['action']}")

    # Witness opener
    subsection("4. Witness (audit log)")
    events = list(WitnessOpener().activate(substrate))
    print(f"  Yielded {len(events)} witness events")
    if events:
        e = events[0]
        print(f"  First entry: agent={e['agent']}, action={e['action']}")

    # MIDI opener
    subsection("5. MIDI (Fable 10 Conductor — the orchestra)")
    events = list(MIDIOpener().activate(substrate))
    if events:
        # Find the 4 unique notes that form a chord
        notes = sorted({e['note'] for e in events[:20]})[:4]
        print(f"  Yielded {len(events)} note events")
        print(f"  First 4 notes (a chord): {[notes] if False else notes}")

    # REST opener
    subsection("6. REST (Fable 11 Paper-Tablet — the API)")
    events = list(RESTOpener().activate(substrate))
    methods = [e["method"] for e in events]
    print(f"  Yielded {len(events)} endpoint events ({methods.count('GET')} GET, {methods.count('POST')} POST)")
    if events:
        e = events[0]
        print(f"  First endpoint: {e['method']} {e['path']}")

    # MUD opener
    subsection("7. MUD (Fable 21 Compass — the text adventure)")
    events = list(MUDOpener().activate(substrate))
    if events:
        e = events[0]
        print(f"  Yielded {len(events)} room events")
        print(f"  First room: \"{e['description'][:80]}...\"")
        print(f"  Exits: {len(e['exits'])} directions")

    # PLATO opener
    subsection("8. PLATO (Fable 06 Grandmother — the lesson)")
    events = list(PLATOOpener().activate(substrate))
    if events:
        e = events[0]
        print(f"  Yielded {len(events)} lesson events")
        print(f"  First lesson: {e['title']}")
        print(f"  Content: {e['content']}")


def showcase_jepas(chart):
    """Show all 3 JEPA implementations."""
    section("THE 3 JEPAs — Linear, MLP, KNN (Open Q9: non-linear prediction)")
    substrate = chart.substrate
    cells = substrate.all_cells()
    if not cells:
        print("No cells, skipping")
        return

    # Linear
    subsection("1. LinearJEPA (the default)")
    linear = LinearJEPA()
    inputs = {cells[0].address: 5.0, cells[1].address: 10.0}
    pred = linear(inputs)
    print(f"  Linear prediction: {pred:.3f} (mean of inputs)")

    # MLP
    subsection("2. MLPJEPA (a small neural network)")
    sample_cell = cells[0]
    mlp = auto_train_jepa(sample_cell, epochs=10, jepa_type="mlp")
    print(f"  MLP trained: input_dim={mlp.input_dim}, hidden_dim={mlp.hidden_dim}")
    pred = mlp({"x0": 0.5, "x1": 0.3, "x2": 0.7, "x3": 0.1})
    print(f"  MLP prediction: {pred:.3f}")

    # KNN
    subsection("3. KnnJEPA (k-nearest neighbors)")
    knn = KnnJEPA(k=5)
    for cell in cells[:50]:
        try:
            x_key = float(cell.address.split("/")[1].split("x")[0])
            y_key = float(cell.address.split("x")[1])
            knn.add({"x": x_key, "y": y_key}, float(cell.value))
        except (ValueError, IndexError):
            continue
    print(f"  KNN trained on {len(knn.examples)} examples")
    # Predict at un-surveyed locations
    for x, y in [(25, 30), (60, 75), (90, 90)]:
        pred = knn({"x": x, "y": y})
        print(f"  Predict ({x}, {y}): depth ≈ {pred:.2f}m")


def showcase_witness_with_justifications(chart):
    """Show witness entries with justifications (Fable 11)."""
    section("THE WITNESS — with justifications (Fable 11: the 'why' not just the 'what')")
    substrate = chart.substrate
    cells = substrate.all_cells()
    if len(cells) < 3:
        return
    # Add a fresh write with a justification
    substrate.witness(
        cells[0], "reyes", "write", 99.9,
        justification="Tied the lead line to the bow, dropped it, waited 30 seconds, measured 99.9m at the spot"
    )
    substrate.witness(
        cells[1], "skate", "read", 88.8,
        justification="Verifying Reyes's sounding; the depth here is 88.8m on my chart"
    )
    substrate.witness(
        cells[2], "inference", "inference", 77.7,
        justification="Substrate's JEPA predicts 77.7m here based on nearby soundings"
    )
    print("Three witness entries with justifications:")
    for c in cells[:3]:
        for entry in c.witness_log[-1:]:  # last entry
            print(f"  {entry.agent_id} {entry.action} {c.address}: \"{entry.justification}\"")


def showcase_convoy_consensus(chart):
    """Show the 4 consensus methods + geometric median."""
    section("THE CONVOY — 4 consensus methods + geometric median (Open Q1, Q5)")
    substrate = chart.substrate
    cells = substrate.all_cells()
    if not cells:
        return
    cell = cells[0]
    # Set up a convoy with 5 honest + 1 outlier
    cell._add_to_convoy("reyes", weight=1.0, value=12.5)
    cell._add_to_convoy("boat-00", weight=1.0, value=12.4)
    cell._add_to_convoy("boat-01", weight=1.0, value=12.6)
    cell._add_to_convoy("boat-02", weight=1.0, value=12.5)
    cell._add_to_convoy("boat-03", weight=1.0, value=12.5)
    cell._add_to_convoy("outlier", weight=1.0, value=999.0)
    print(f"Convoy: 5 honest agents at 12.4-12.6m, 1 outlier at 999m")
    print()
    print(f"  weighted_mean:   {cell.convoy_value(method='weighted_mean'):.2f}m  (pulled by outlier)")
    print(f"  weighted_median: {cell.convoy_value(method='weighted_median'):.2f}m  (robust)")
    print(f"  trimmed_mean:    {cell.convoy_value(method='trimmed_mean'):.2f}m  (drops outlier)")
    print(f"  geometric_median: {cell.geometric_median():.2f}m  (1D = weighted_median)")


def showcase_substrate_trainer(chart):
    """Use the substrate-trainer on the bathy chart."""
    section("THE SUBSTRATE-TRAINER — JEPA model trained on the witness log")
    substrate = chart.substrate
    trainer = Trainer()
    model = trainer.fit(substrate, n_epochs=20)
    print(f"Trained: {model.n_train} examples, {len(model.agent_to_id)} agents")
    print(f"  target_mean: {model.target_mean:.3f}")
    print(f"  target_std:  {model.target_std:.3f}")
    # Predictions
    print()
    print("Predictions:")
    for ctx in [["reyes"], ["reyes", "boat-00"], ["boat-00", "boat-01"]]:
        pred, conf = model.predict(ctx)
        print(f"  {ctx}: depth ≈ {pred:.2f}m (model confidence: {conf:.2f})")


def showcase_topology(chart):
    """Show the substrate's topology."""
    section("THE TOPOLOGY — the substrate knows its own shape (Open Q13)")
    substrate = chart.substrate
    beta_0 = substrate.betti_0()
    beta_1 = substrate.betti_1()
    n_edges = len(substrate.edges())
    n_cells = len(substrate)
    print(f"  V (cells)   = {n_cells}")
    print(f"  E (edges)   = {n_edges}")
    print(f"  β₀ (components) = {beta_0}")
    print(f"  β₁ (cycles)     = {beta_1}")
    print()
    if beta_1 > 0:
        print(f"  The substrate has {beta_1} independent cycle(s).")
        print("  The ideas reinforce each other.")
    else:
        print("  The substrate is a forest. No cycles yet.")


def showcase_merkle_witness(chart):
    """Show the Merkle tree of witness roots."""
    section("THE MERKLE TREE — O(log n) inclusion proofs (Open Q4)")
    substrate = chart.substrate
    root = substrate.merkle_root()
    print(f"  Merkle root of all witness roots: {root}")
    print(f"  Length: {len(root)} hex chars = {len(root) * 4} bits")
    # Generate a proof for the first cell
    cells = substrate.all_cells()
    if cells:
        proof = substrate.merkle_proof(cells[0].address)
        if proof:
            print(f"  Merkle proof for {cells[0].address}: {len(proof)} hashes (O(log {len(cells)}))")
        else:
            print(f"  No proof generated for {cells[0].address}")


def showcase_advance_time(chart):
    """Show the substrate's time-advance feature."""
    section("THE TIME — advance_time(dt) for batch simulation")
    substrate = chart.substrate
    cells = substrate.all_cells()
    if not cells:
        return
    # Measure confidence before and after
    cell = cells[0]
    initial = cell.confidence
    # Advance 1 hour (3600s) of substrate time
    substrate.advance_time(3600)
    after_1h = cell.confidence
    # Advance 1 day (86400s)
    substrate.advance_time(86400 - 3600)
    after_1d = cell.confidence
    # Advance 1 year (86400 * 365)
    substrate.advance_time(86400 * 365 - 86400)
    after_1y = cell.confidence
    print(f"  Confidence of {cell.address} over time:")
    print(f"    now:        {initial:.4f}")
    print(f"    +1 hour:    {after_1h:.4f}")
    print(f"    +1 day:     {after_1d:.4f}")
    print(f"    +1 year:    {after_1y:.6f}")
    print()
    print("  The substrate ages like real data. The convoy's soundings stay fresh longer than chat.")


def showcase_river_dream_log():
    """Show the river dream log integration."""
    section("THE RIVER — agentic journaling (Hold / Wake / Dawn)")
    river = River("reyes")
    # Reyes holds a thought
    h1 = river.hold("reyes saw a 99.9m sounding at the spot")
    h2 = river.hold("the convoy disagreed on the depth at the sandbar")
    h3 = river.hold("the substrate's JEPA predicted 77.7m based on the convoy")
    print(f"Reyes held 3 thoughts:")
    print(f"  {h1.text[:60]}...")
    print(f"  {h2.text[:60]}...")
    print(f"  {h3.text[:60]}...")
    # Reyes wakes (the thought returns)
    w = river.wake(h1.text)
    print(f"Reyes woke: {w.state.name} (wakes: {w.wakes})")
    # Reyes dawns (the thought becomes a memory)
    d = river.dawn(h2.address)
    print(f"Reyes dawns: {d.state.name if d else 'None'} (text: {d.text[:60] if d else None}...)")
    # Show the dawn list
    dawns = river.dawn_list()
    print(f"Reyes has {len(dawns)} dawned thoughts (the memories that have crystallized)")


def showcase_legacy_cell():
    """Show the cell-runtime legacy Cell in use."""
    section("THE LEGACY CELL — cell-runtime (8 primitives, the cell as a Python type)")
    cell = LegacyCell(address="legacy/001", value=0.0)
    # Observe a value 3 times: the Vibe converges toward it
    for _ in range(50):
        cell.observe(42.0)
        cell.tick()
    print(f"Cell {cell.address}: value={cell.value}, ticks={cell._ticks}, vibe={cell._vibe.pos[0]:.3f}")
    print(f"  After 50 observations of 42.0, the Vibe has converged toward the target")
    print(f"  This is the 8-primitive cell, the substrate's ancestor.")


def main():
    parser = argparse.ArgumentParser(description="The Quilt ecosystem flagship demo")
    parser.add_argument("--quiet", action="store_true", help="Suppress section output")
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  THE INNER SOUND — A Quilt ecosystem flagship demo                    ║")
    print("║  Reyes, sailing a 12-inch tablet, sees the bottom of the sea        ║")
    print("║  The substrate is the soil. The bathy is the plant.                  ║")
    print("║  The witness log is the rain. The openers are the kindness.          ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print("Imported from 6 packages:")
    print("  • cell-runtime (8-primitive cell)")
    print("  • river-dream-log (Hold/Wake/Dawn)")
    print("  • quilt-substrate (11-primitive substrate + 8 openers + 3 JEPAs)")
    print("  • substrate-trainer (JEPA model on witness log)")
    print("  • quilt-bathy (the bathy cross-section tool)")
    print("  • porch (3 a.m. thoughts CLI — not used in demo)")

    # Build the bathy
    chart = build_bathy_with_substrate()

    # Setup decay rates
    setup_per_agent_decay(chart.substrate)

    # 8 openers
    if not args.quiet:
        showcase_8_openers(chart)

    # 3 JEPAs
    if not args.quiet:
        showcase_jepas(chart)

    # Witness with justifications
    if not args.quiet:
        showcase_witness_with_justifications(chart)

    # Convoy consensus
    if not args.quiet:
        showcase_convoy_consensus(chart)

    # Substrate-trainer
    if not args.quiet:
        showcase_substrate_trainer(chart)

    # Topology
    if not args.quiet:
        showcase_topology(chart)

    # Merkle tree
    if not args.quiet:
        showcase_merkle_witness(chart)

    # Advance time
    if not args.quiet:
        showcase_advance_time(chart)

    # River dream log
    if not args.quiet:
        showcase_river_dream_log()

    # Legacy cell
    if not args.quiet:
        showcase_legacy_cell()

    # Final summary
    section("THE LOOP — it closes")
    print("  Canon (papers 107-122) → Code (quilt-substrate) → Tests (236) →")
    print("  Papers (more fables) → Code (more substrate) → Tests (more) → ...")
    print()
    print("  The fables are the requirements. The substrate is the implementation.")
    print("  The math is the proof. The witness log is the record.")
    print("  The openers are the kindness. The cycles are the mesh.")
    print("  The loop closes.")


if __name__ == "__main__":
    main()
