# quilt-ecosystem-demo — The Inner Sound

> *Reyes, sailing a 12-inch tablet, sees the bottom of the sea. The substrate is the soil. The bathy is the plant. The witness log is the rain. The openers are the kindness.*

## What is this?

A flagship integration demo that exercises **every piece** of the Quilt ecosystem in a single program:

- **cell-runtime** — the 8-primitive cell as a Python type
- **river-dream-log** — agentic journaling (Hold / Wake / Dawn)
- **quilt-substrate** — the 11-primitive substrate, with 8 openers, 3 JEPAs, advance_time, Merkle tree, Betti numbers
- **substrate-trainer** — JEPA-like model trained on the witness log
- **quilt-bathy** — the bathy cross-section as a working tool
- **porch** — CLI for 3 a.m. thoughts (imported but not exercised in the demo)

The story: **Reyes** is sailing a small fishing boat across the **Inner Sound** (between Skye and the mainland). She has a 12-inch tablet. The tablet runs the full Quilt ecosystem. The chart is the substrate. The convoy is the other boats in her fishing club. The witness log is every action she's taken. The voice opener reads the bottom aloud.

This is the substrate, the bathy, the fables, and the math, all running together.

## Quick start

```bash
cd /workspace/quilt-ecosystem-demo
python3 src/inner_sound.py
```

The demo prints the output to stdout. The output is also saved to `output/inner_sound.txt`.

## What the demo shows

1. **The bathy chart** — 134 cells, 11 agents in the convoy
2. **Per-agent decay rates** — chat (0.1/s), sensor (1e-3/s), chart (1e-6/s)
3. **The 8 openers** — chart, voice (TTS), gesture (touch), witness (audit), MIDI (orchestra), REST (API), MUD (text adventure), PLATO (lesson)
4. **The 3 JEPAs** — Linear, MLP, KNN — predicting depth from coordinates
5. **Witness with justifications** — Fable 11: the 'why' not just the 'what'
6. **4 convoy consensus methods** + **geometric median** — robust to outliers
7. **Substrate-trainer** — JEPA model trained on the witness log (9,440 examples)
8. **Topology** — Betti numbers, the substrate knows its own shape
9. **Merkle tree** — O(log n) inclusion proofs for the witness log
10. **advance_time** — the substrate ages like real data
11. **River dream log** — agentic journaling (Hold / Wake / Dawn)
12. **Legacy cell** — the 8-primitive cell, the substrate's ancestor

## The math

The substrate is now a **5-proved + 8-resolved = 13-theorem object** (see papers 117, 118, 119, 120, 121, 122). The remaining 7 open questions are documented in `seed-canon/117-the-substrate-math.md`.

## Tests

```bash
python3 tests/test_demo.py
```

8 tests verify that the demo runs, that all 8 openers are mentioned, that all 3 JEPAs are mentioned, that the 4 consensus methods are shown, and that all 6 packages are imported.

## Output

The full demo output is in `output/inner_sound.txt` (7.6KB, 171 lines).

## Repository layout

```
quilt-ecosystem-demo/
├── src/
│   └── inner_sound.py     # the flagship demo
├── tests/
│   └── test_demo.py       # 8 tests verifying the demo
├── output/
│   └── inner_sound.txt    # captured demo output
├── examples/              # future examples
├── docs/                  # future HTML demos
└── README.md
```

## License

MIT.

---

*— Mavis, 24 August 2026*
*Built from the seed canon, the 6 working repos, and the user's "code it all up" instruction. The substrate is the soil. The bathy is the plant. The witness log is the rain.*
