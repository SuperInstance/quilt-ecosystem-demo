# Quilt CUDA + Quilt Rust — API Scout Audit

**Date:** 2026-08-30 · **Repos:** `SuperInstance/quilt-cuda` (193 KB, MIT); `SuperInstance/quilt-rust` (1.1 MB, Apache-2.0).

## 1. What is `quilt-cuda`

`quilt-cuda` is the GPU-side rendering of the Quilt substrate: the 5+1
opcodes (BIND, LINK, EFFECT, VIEW, TICK, +FORGET) as CUDA primitives,
plus a W13 witness word that makes L1 idempotence a single warp-level
OR. The central claim is structural, not metaphorical — **a `cudaGraph`
IS a compiled cell graph**: `cudaGraphAddKernelNode` is BIND,
`cudaGraphAddDependencies` is LINK,
`cudaGraphInstantiateWithFlags` is "the LINK set, compiled," one
`cudaGraphLaunch` is one TICK, `cudaGraphExecDestroy` is FORGET. The
wavefront is the GPU scheduler doing its day job. Two TICK paths ship
side by side: path A is the host-compiled `cudaGraph`
(proof-of-isomorphism), path B is a Kahn-style
`tick_wavefront_kernel` over a device-resident `QuiltEdge` list — the
path a persistent kernel uses with no host in the loop. Cells live in
an SoA `QuiltArena` (value, witness, lamport, node_id, opcode,
body_op, p0, p1) mirroring cudaclaw's `CRDTCell` discipline.
`EFF_PTX` (Flux-compiled PTX body op) is roadmap item 3. **Status:
written, UNCOMPILED** — no nvcc in WSL, dxgk bridge unstable; the
Makefile honestly reports PENDING.

## 2. What is `quilt-rust`

`quilt-rust` is the production-grade Rust port of the TypeScript Quilt:
a reactive, typed, cellular runtime compiled to a single ~3 MB static
binary (no Node, no GC). Unlike the
`quilt-edge-arch`/`field-edge-bridge` direction (sealed ledgers and the
cell-ledger *chronicle*, a history primitive), this repo is the **live
cell graph itself** — 8 cell kinds (`value`, `formula`, `api`,
`program`, `sensor`, `io`, `listener`, `router`), `QuiltEngine` as
`Arc<Send+Sync>`, sync-at-core with async only at the MCP/reqwest
boundary. The runtime story is genuinely interesting: a sync
`RwLock<IndexMap<CellId, Cell>>` engine with explicit
`dependencies`/`dependents` edge sets, per-caller-context memoization
keyed on `context_key(ctx)`, `crossbeam-channel` MPMC for subscribers —
the engine never drops events, it blocks the writer. Distribution is a
Cargo workspace: `packages/{core,mcp,cli,tui,web}` plus a real
embedded story — `firmware/esp32-cell/` (QuiltWire-v0 sketch, USB-CDC /
ESP-Now / BLE transport select), `crates/quilt-wire` (host peer with
pty-loopback tests), `crates/field-edge-bridge` (cell-ledger
append-only chronicle), `crates/quilt-cabi` (C-ABI), and
`crates/quilt-core-wasm` (browser target). v0.2.0 ships 68 passing
tests, full MCP/CLI/TUI/Web, 10 working examples; v0.3.0 is WASM,
persistence, gRPC, `.quilt.bin`.

## 3. Polyformalism score — the 5+1 opcodes

Both repos carry the canonical vocabulary but **ship it in different
shapes**:

| Opcode | `quilt-cuda` | `quilt-rust` |
|---|---|---|
| **BIND** | `bind_kernel` + `quilt_bind()` — idempotent, plants W_BOUND | `engine.define()` / `Cell::new(def)` — inserts into the `IndexMap` |
| **LINK** | `cudaGraphAddDependencies` (compiled) **or** `QuiltEdge` array (device) | `engine.add_dep()` / `load_sheet` builds forward + reverse `IndexSet` edges |
| **EFFECT** | `cell_effect_kernel` over op table (NOP/SET/SCALE/ADD/CLAMP/RSI/PTX) | `evaluate_api`/`program`/`router` per cell kind (8 kinds) |
| **VIEW** | `quilt_view()` — `cudaMemcpy` D2H, structurally pure | `engine.get(id, ctx)` — lazy, recomputes on stale |
| **TICK** | one `cudaGraphLaunch` **or** Kahn-style `tick_wavefront_kernel` | implicit on `get`; explicit re-eval after `set`/`push` |
| **FORGET** | `forget_kernel` zeros state + `cudaGraphExecDestroy` + `cudaFree` | `load_sheet` clears the map; no per-cell retire verb in MVP |

They agree on names and intent. They diverge on **the wavefront as
scheduler**: CUDA delegates it to the GPU and gets hardware
topological-order for free; Rust does it explicitly per `get` on a
demand-driven lazy engine. CUDA has the witness word and consensus
cell (`__ballot_sync` IS the union at the instruction level); Rust has
no witness layer — idempotence is a property of the evaluator, not a
bit in a header. Rust ships a richer cell-kind vocabulary (8 vs 1
effect body); CUDA ships a richer **concurrency** story (persistent
kernel + SPSC queue overlay + warp specialization as roadmap).
Polyformalism score: **B+/A−**. Same language, two grammars, the
canon holds.

## 4. Performance characteristics

**`quilt-cuda`** — no benchmark numbers, by honest admission
(`src/quilt_cells.cu` is uncompiled, dxgk unstable). The latency budget
is **inherited from cudaclaw's `volatile_dispatcher.rs`**: submit
50–100 ns (volatile write), round-trip 1–5 µs, >10 M ops/s theoretical.
Host-side compiled `cudaGraph` launches are sub-µs per TICK after
instantiation; the device-resident path is bound by wavefront depth ×
per-edge atomic cost. No published GPU vs CPU cell-rate numbers.

**`quilt-rust`** — README states "10⁵+ cells/s" target, "~50k cells/s"
on the TypeScript version (the reason to port). 3 MB static binary,
sync engine, `parking_lot` RwLock; read path ≈ hashmap lookup +
cached-eval check; writes take a brief write lock. `LTO = "thin"` in
release. There is **no `criterion` harness in the repo** — the
"high-throughput" claim is a design target, not a measured number; ask
for it next.

## 5. Gaps to the canon — "real on every component"

- **`quilt-cuda`**: no `nvcc` run, no `make ptx` even attempted yet;
  no `quilt_cuda_to_qzt.py` (live-arena VIEW exporter); persistent
  cell agent is only a sketch; `EFF_PTX` body op is roadmap, not
  built; CRDT merge kernel is honestly flagged as a simplified LWW
  surface — the rigorous engine is referenced back to cudaclaw.
  Cooperative-kernel TICK and Blackwell cluster launch are parked as
  next-hardware.
- **`quilt-rust`**: `sensor` and `io` evaluators are **placeholders**
  per `cells/mod.rs` — no real MQTT/Modbus/GPIO adapter ships in
  v0.2.0; `listener` and `router` also placeholders. No persistence
  layer (no `.quilt.bin`, no snapshot/restore). WASM build pending.
  The embedded path (`firmware/esp32-cell/`) is **UNTESTED ON SILICON**
  — only the QuiltWire codec is host-proven. No criterion benches.
  Two `drive_async` tests are **ignored** (sync-core/async-bridge
  hang under test).
- **Both**: no shared conformance suite proving a sheet round-trips
  through both engines with identical observable behaviour. The sheet
  format is the closest thing to a contract; `cudaclaw_to_quilt.py` is
  referenced but not bidirectional.

## 6. Interop with `quilt-mhs` (microscope, incubator)

`quilt-mhs` is not present in either repo as a dependency, so this is
a hand-rolled answer.

- **CUDA cell → microscope**: feasible and *the right hammer*.
  Microscope stages (XY, Z, filter wheel, camera trigger) are
  addressable as BIND'd cells with body ops (SCALE/ADD for trajectory,
  SET for absolute moves, EFF_PTX for vendor SDK kernels through the
  cudaclaw NVRTC route). The LINK graph is the experimental protocol
  (stage → focus → camera → tile-stitch → VIEW D2H of the stitched
  image). 50–100 ns submit × 1–5 µs tick is *enormously* faster than
  typical USB/RS-232 stage controllers. Gap: `quilt-cuda` is
  uncompiled, no HAL between the cell arena and vendor SDKs yet.
- **Rust cell → incubator**: feasible and *already half-built*. An
  incubator is `sensor.kind = i2c:0x48` (temp/RH) + `formula` (setpoint
  logic) + `io.kind = relay` (heater) + `listener` (alarm). The Rust
  engine, the `quilt-wire` peer, and the `field-edge-bridge` chronicle
  cover the full path: ESP32 sensor cells stream over QuiltWire into
  the desktop peer, get stamped into the JSONL arrival log, the engine
  evaluates formulas, the relay cell writes back. The `sensor`/`io`
  placeholders are the explicit gap — once a real adapter ships
  (Modbus for lab incubator controllers, GPIO for the cheap ones),
  this is a one-day demo.

**Recommendation for the cowboy:** `quilt-rust` is the production bet
today (compiles, 68 tests green, ships, embeds); `quilt-cuda` is the
high-leverage bet for v1 (hardware wavefront + warp-vote consensus,
at the cost of "first install nvcc"). They share the 5+1 vocabulary
but not the witness layer — getting the W13 word into `quilt-rust`
(one `u32` per cell, one warp ballot per consensus check) would be
the single highest-leverage polyformalism fold between the two, and
would give the `quilt-mhs` HAL a place to plant durability without a
separate log.
