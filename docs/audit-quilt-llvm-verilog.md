# Audit: quilt-llvm and quilt-verilog

*Scout pass, 2026-08-30. Sources: GitHub REST API + `raw.githubusercontent.com`. Both at `master` HEAD.*

## 1. What is quilt-llvm

A **keel-stage repo** — zero source code, four design-intent markdown files (`README`, `docs/{DOCTRINE,THEORY,GLOSSARY,TUTORIAL}.md`), 17 KB. Thesis: an LLVM-style compiler IR where the unit of compilation is the **inspectable cell** (≈ `Value` + stable identity + append-only history), edges are **wires** (≈ `Use`, first-class with attach/detach events), containers are **regions** (≈ basic blocks / MLIR regions), and a pass is a pure function `fabric → (fabric, diff)`. The opcode set is **deliberately not enumerated** — `THEORY.md §8`: *"quilt-verilog's opcodes (bind/link/effect/view/tick) are not our IR operations; the transferable part is operations as recorded data."* Only `const`, `mul`, `ret` are sketched. Status: `[x] Keel`, `[ ] Scout report`, `[ ] Architecture doc`, `[ ] Cell IR v0 + verifier`, `[ ] First real pass + red/green tests` — **nothing ships**.

## 2. What is quilt-verilog

A **shipping, measured, verified** cellular fabric in pure Verilog-2005 (17 RTL modules in `rtl/`, 1,423 KB). Target FPGAs: **Lattice iCE40** (HX8K-CT256, UP5K-sg48) and **ECP5** (LFE5U-25F); bitstreams via open tools only (`yosys` → `nextpnr-ice40` → `icepack`); committed `synth/fabric2_k4b4a8e1.bin` is 135,100 B, 2 cells at 98% LC, fmax 44.43 MHz. State lives in **QUF v1** (`docs/QUF-SPEC.md`, ~15 KB spec) — GGUF-shaped flat binary, magic `51 55 46 00`, sections `dials/edges/routing/ticks`, Python reference `tools/quf.py` (stdlib) + streaming RTL consumer `rtl/q_uf_loader.v` (30 KB). **Yes, formal proofs (sby) attached**: 6 in `formal/` and `tb/formal/` (`cell_core.{tick,fair}.sby`, `echo_gate.dyadic.sby`, `flit_pipe.fly.sby`, `fabric.conservation{,.probe,.probe-t1,.prove,.prove-t1}.sby`, `tb/formal/flit_pipe.sby`) — 5 BMC + 1 k-induction, engine `smtbmc boolector`, all PASS. First run found **two real RTL defects** (multi-driven register, ingress-drop under pending tick) — both fixed, both regression-guarded.

## 3. Polyformalism score: is the same 5+1 opcode set present?

**Yes — quilt-verilog owns the canonical 5+1; quilt-llvm explicitly does not adopt it.** From `rtl/q_cell_core.v` line 24:

```
localparam [OPW-1:0] OP_BIND=0, OP_LINK=1, OP_EFF=2, OP_VIEW=3, OP_TICK=4, OP_ACK=5, OP_NAK=6;
```

Five host verbs + ack/nak response channel. 3-bit field, room 0..7; only 0..6 used (code 7 undefined → NAK). `THEORY.md §8` is unambiguous: *"its opcodes (bind/link/effect/view/tick) are not our IR operations; the transferable part is operations as recorded data."* Encodings differ by **domain**, not bit-pattern: verilog is 3-bit because the field rides a 16-bit ring flit; llvm's opcodes aren't fixed (only `const`/`mul`/`ret` sketched, MLIR-shaped; `TUTORIAL.md §6` self-flags *"the dump format is sketched, not implemented"*). **No shared opcode vocabulary exists today** — only a shared discipline (append-only history = N4 = D5, conservation ledger = F3 → D4, inspectable cells).

## 4. Test coverage

- **quilt-llvm: 0 tests.** No `tests/`, no `examples/`, no CI, no Makefile. The "test surface" is eight D-laws (D1–D8) in `DOCTRINE.md` — **unenforceable**, no pass exists to run.
- **quilt-verilog: 18 RTL TBs + 34 Python unit tests + 6 formal proofs + 4 worked examples.** `make test` → **18/18 PASS** (re-run 2026-08-30); `make sim` → **34/34 OK** (0.009 s); `make formal` → **6/6 PASS** (~14 min). TBs cover: tick scheduler, flit pipe, link ringport, dial file, Hebb edge, hyperbola tail, echo gate, RQH bank + saturation, cell core, IO port, fabric smoke v1+v2, judge consistency, hebb pipe, QUF boot, QUF loader (Python), serfabric differential. T1..T4 examples have `.expected` goldens diffed by `examples/verify.sh`. Proofs prove: ideal-2-deep FIFO (k-inductive, unbounded), 2-cell ledger conservation (A1, T1, SER, DROP, FAN), echo-gate dyadic bracket, tick non-starvation under flood, ingress fairness. **Honest limits in `README.md`**: BMC-bounded for 5/6; conservation at EDGES_N=1, K=4, B=4 (not full fabric); Python lane is a model not a miter; bitstream never met a board; no CI.

## 5. Gaps to the canon (vs. Phase 215 quilt-mhs expansion)

**quilt-llvm** — what would make it "real" on every component:

- **Code.** Zero `.cpp`/`.h`/`.py`/`.mlir`/`.ll` files. Need: (a) cell/wire/region data structure, (b) textual IR parser, (c) a `.expected`-diffed parse test, (d) one real pass (`fold`) with a red/green suite per D1, (e) ledger reconciler per D4, (f) replay per D5.
- **A pinned v0 opcode subset.** Tutorial sketches `const`/`mul`/`ret`; must commit to a v0 set (e.g. `{const, binop, icmp, br, ret, call}`) with width/encoding.
- **A `.expected` golden.** `TUTORIAL.md §6` writes: *"the day the experiments lane produces its first real transcript, this tutorial either matches it or gets corrected in a commit that starts with `TUTORIAL:`"* — that *is* the milestone.
- **CI + Makefile.** None. D1/D4/D5/D7 are unenforceable without a runner.
- **Measured numbers.** D3 forbids "fast/small" without a command. None exist.
- **One example.** verilog ships 4; llvm ships 0.

**quilt-verilog** — gaps are scope-of-claim, not code:

- **Conservation at scale.** BMC at EDGES_N=1, K=4, B=4, depth 55. To match the canon's "every claim at full scale," extend to NCELL≥4, EDGES_N=8 (or keep the cap first-class — `FORMAL-PROOFS.md §2` does).
- **On-hardware test.** README: *"the bitstream has never met a board; no PCF exists."* A real PCF + `make flash` on HX8K closes the loop.
- **k-induction for conservation.** Currently BMC; a `prove` attempt failed informatively and is documented. Lemma-strengthening is the next formal milestone.
- **Python↔RTL equivalence.** 34-test Python lane is a *model*, not a miter; no formal equivalence.
- **CI.** `make test/sim/formal` exists but no `.github/workflows/`.

## 6. Cross-canon opportunities (shared IR for quilt-llvm, quilt-cuda, quilt-mhs, quilt-rust)

- **The 5+1 opcode set is verilog-bound, not transportable.** Bind/link/effect/view/tick assume a per-cell state machine with Hebbian edges — `bind` writes a dial, `link` writes an edge slot, `effect` does cofire+weight-readback+activation-integrate, `view` reads act/wsum/dial, `tick` is decay+leak+fire. None mean anything on an LLVM `Value` (no edges, no dial file, no tick scheduler), a CUDA kernel, or a Rust borrow checker. The **discipline** transfers; the **opcodes** don't.
- **The QUF file format is the closest thing to a shared IR today.** Already GGUF-shaped, has a streaming RTL consumer (`q_uf_loader.v`), byte-identical across Python sim and RTL. A cell-state file is the natural artifact an LLVM pass could emit (compiler → QUF of pre-trained cell state, the way ggml emits GGUF). The KV schema extends cleanly under "unknown KV → skip" (§8 of `QUF-SPEC.md`): add `quilt.version=quilt-llvm-v0`, `quilt.fabric_hashes`, `quilt.diff_log` alongside the fabric-specific `cell_count`/`edge_count`/`routing`/`ticks`.
- **The ledger discipline (D4) is the cleanest cross-polyformalism primitive.** verilog's conservation held 2,852,899 cycles including deadlocks; llvm's `THEORY.md §6` explicitly promotes it. Candidate for a shared *conservation verifier*: a small tool that takes a fabric of any flavor + a diff sequence, asserts `admitted = delivered + dropped-with-entry`. v0 = ~200 lines of Python reading QUF + a sidecar `.diff.jsonl`.
- **N4 (append-only history, D5) is the second shared primitive.** Both repos commit; both need diff compaction, history-pruning, `replay k..0`. A common `fabric-history` crate (Rust) or module (C++) re-uses.
- **φ-as-wire-join is the most speculative cross-canon bet.** `GLOSSARY.md` flags it design-intent. If it survives, it's a candidate shared IR node type (one cell, several wires, multi-predecessor join without an opcode). Zero impl today.
- **Honest read on "one shared IR":** there isn't one, and the authors know it — llvm cites verilog as *inspiration*, not a compiler target. A realistic Phase 216 deliverable is a **`quilt-fabric` Python library** that reads QUF + a diff log, asserts D4 + D5, and exposes a provenance-walk query — usable by all five polyformalisms as their *verification backplane*, even before their IRs are unified.
