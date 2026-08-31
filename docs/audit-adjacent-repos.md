# Audit: 6 Adjacent SuperInstance Repos

> Scouting the cellular-architecture neighbours. Method: GitHub metadata + recursive tree + key source files (`README.md`, primary module, conformance spec). All six live under `SuperInstance/`. Sources cached in `docs/audit-sources/`.

## 1. Per-repo verdict

- **fleet-homunculus** (Py, 7 files). `BodyImage` + `ReflexArc` for fleet self-monitoring; pain levels, GABAergic cooldowns. **Overlap:** mild — reactive state-graph but signal-centric, no BIND/LINK/EFFECT/TICK vocabulary. **Ship:** medium (dataclasses + tests, but fleet-specific). Verdict: **(c) cross-reference substrate**.
- **quilt-scratch** (JS browser, hull-2 floating, 12 files / 178 kB JS). No-code tile game engine; cells-as-tiles; M1–M4/N1–N4 tile contract in `test.html`. **Overlap:** this *is* Quilt in spirit — README cites "design laws inherited from the quilt substrate" verbatim. **Ship:** high (playable, contract tests). Verdict: **(a) polyformalism, downstream-most mature**.
- **quilt-geometry** (Py, 11 files). Penrose P3 rhombus library: de Bruijn pentagrid, golden deflation, 1/d² field diffusion, 8-dim locality embedding, Pythagorean snapping. **Overlap:** the name says it; `snapping.py` mentions "Quilt opcode compatibility" — but it's a **math library**, not a runtime. **Ship:** high (9 pytest tests, verified numbers, SVG/PNG viz). Verdict: **(c) cross-reference canon** — a *coordinate/affinity substrate* Quilt could adopt.
- **quilt-conformance** (JS + 5 adapters, 11 dirs). 36-program corpus + 5 adapters (TS/Rust/C/Haskell/WASM) + `diff.py` + `BENCH.md`; 7 MATCH / 29 DIVERGE; 11 BUGs. **Overlap:** this *defines* whether a quilt VM is faithful. **Ship:** high and honest — every claim "executed on this host (WSL2)". Verdict: **(a) the meta-polyformalism** — it's the judge.
- **tit-quilt** (Py ≥3.11, stdlib-only, 11 src + 6 test files). "Session is a graph, not a process" — `BIND/LINK/TICK/EFFECT/FORGET` *exactly* as Quilt names them; one graph, two front doors (CLI + MCP); hot→cold→tombstone with provenance integrity law; cell_ref chaining. **Overlap:** **maximum** — same 5+1 opcodes, same witness chains, same EFFECT-confined purity, same FORGET-as-tombstone law. README: "quilt-native TIT prototype." **Ship:** high (8 test files, zero deps, MCP runs, honest gaps). Verdict: **(a) closest polyformalism** — arguably the most complete reference runtime outside `quilt-rust`.
- **quilt-engine-ports** (GDScript + DESIGN.md, 7 dirs). 5+1 opcodes → Godot/Unity/Unreal; Godot scaffold has BIND/LINK/VIEW/TICK real, EFFECT/FORGET law-shaped; C1–C7 porting contract; `MhsTransport` mock rejects out-of-envelope (no clamping). **Overlap:** unique — engine-port face of Quilt (cells as Nodes, TICK = `_process`, sheet = JSON). **Ship:** medium — Godot written but *not run in CI* (no Godot binary in lane); Unity/Unreal specified only. Verdict: **(a) substrate-to-industry bridge**.

## 2. Top 3 most-quilt-like (they ARE quilt polyformalisms in spirit)

1. **tit-quilt** — same 5+1 opcode names, same witness-chain semantics, same hot→cold→tombstone retention, same MCP-as-edge philosophy. It's Quilt's terminal polyformalism with one graph + two doors and survives agent death. The BIND/LINK/TICK/EFFECT/FORGET vocabulary is verbatim; the `MCP call IS a link` law is a first-class Quilt law made executable.
2. **quilt-engine-ports** — opcode-set is canonical, the *contract* (C1–C7) is Quilt canon restated as a porting check, and the Godot scaffold proves the cell-graph-as-scene-tree claim. Unique: bridges Quilt to game-engine and (via MHS seam) to physical hardware.
3. **quilt-scratch** — "design laws inherited from the quilt substrate" is right in the README. The tile contract (M1–M4 swap-by-port, N1–N4 history-by-rename) *is* the quilt substrate's terms. A child-friendly executable proof that the substrate works in the wild — without naming opcodes.

## 3. Top 3 most-substrate-pattern-worthy (design should inform Quilt, not be subsumed)

1. **quilt-geometry** — the **Pythagorean-snapped adjacency-diffused field** is a *coordinate + affinity* substrate Quilt currently lacks. If Quilt cells need a *where-am-I in the lattice* notion (for routing, layout, locality, Z-ordering), this is the seed: Penrose deflation (phi^g scaling) gives scale-free coordinate systems; `field.py` proves variance strictly decreases under diffusion; `embed.py` gives 8-dim locality-correlated vectors. Quilt should *import* this as a `quilt-geometry` port, not replicate.
2. **quilt-conformance's "honest divergence" discipline** — `BUGS.md` is a first-class artifact, `BENCH.md` says "WSL2 single host" out loud, the harness *deliberately* doesn't normalize disagreement. Quilt's *canon* should adopt this: every claim of the form "this is the same value" should be backed by an executable 5-way diff in a results/ folder. The wasm stub (which fails 51 of 36 corpus programs) is *kept failing* because a stub-passing cell would be worse. That stance is the right substrate law.
3. **fleet-homunculus's `ReflexArc` cooldown pattern** — `(trigger_level, cooldown_seconds)` is a *rate-limiter* substrate primitive. Pair with Quilt's TICK and you get a native `quilt-throttle` / `quilt-rate-limit` cell type, expressed as: every BIND bumps a version but the EFFECT can declare `cooldown` and the engine drops re-fires inside the window. Currently Quilt has no native rate-limit; homunculus has it as a first-class object.

## 4. The cowboy's 1-day add

**PR into `quilt-engine-ports`**: add a `tests/` directory containing the **`assert_laws()` test from `quilt_engine.gd` ported to run headless via Godot 4.3's `--headless` flag**, plus a `godot/sheets/rate_limit_demo.json` that demonstrates BIND-idempotence and TICK-monotonicity on a 100-cell sheet, plus a `scripts/ci.sh` that downloads `godot-headless` into `.bin/`, runs the scene, and exits 0/1. **Why:** DESIGN.md §2 names C4 ("the 5 laws hold on the port") as a port-rung requirement, the GDScript already has `assert_laws()` and `journal()` wired — but there's no CI lane (README admits it). Adding a headless test runner is ~80 lines of GDScript + 30 lines of bash, makes the scaffold *conformance-eligible* per its own contract, and unlocks the ladder (Unity/Unreal rungs are gated on a working C4 check in the reference port). One PR, one day, the whole porting ladder advances one rung.

## Summary table

| Repo | Lang | Verdict | Category | Ship |
|---|---|---|---|---|
| fleet-homunculus | Py | fleet body image + reflex cooldowns | (c) substrate-pattern | medium |
| quilt-scratch | JS | no-code cellular game engine | (a) polyformalism | high |
| quilt-geometry | Py | Penrose tiles + snapping + embedding | (c) substrate-pattern | high |
| quilt-conformance | JS+5 | 36-program 5-VM diff suite | (a) polyformalism (meta) | high |
| tit-quilt | Py | session-as-graph, MCP-as-edge | (a) polyformalism (closest) | high |
| quilt-engine-ports | GDScript | 5+1 opcodes → Godot/Unity/Unreal | (a) polyformalism (bridge) | medium |
