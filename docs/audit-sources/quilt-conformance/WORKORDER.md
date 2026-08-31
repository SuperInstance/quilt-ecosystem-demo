# WORKORDER — quilt-conformance (lane resumed 2026-08-25)

Mission: shared conformance corpus (~30 programs) run against ALL FIVE quilt VMs
(rust, c, haskell, wasm, typescript). Diff outputs, report divergences, benchmark
the C gold demo honestly. Commit early and often. Push to SuperInstance/quilt-conformance (private) at the end.

## Verified build status (foreman-checked 2026-08-25, do NOT redo)

| VM | Build | Tests | Notes |
|----|-------|-------|-------|
| C | `make` OK | 6/6 PASS | gold runs, prints ~0.04ms internal (README claims 0.11ms; external 20x: min 0.70ms — see results/BENCH.md). BUG-5: `qvm_bind` appends duplicates instead of replacing (T02/T25). |
| Rust | `cargo build --release` OK | **cargo test FAILS TO COMPILE** (BUG-1: E0308/E0277 at lib.rs:282-283) | adapter drives the API directly (per-op catch_unwind); semantic divergences BUG-9/10/11. Repo ships no gold demo — `adapters/rust/src/bin/gold.rs` mirrors it. |
| TypeScript | `npm run build` OK | 6/6 PASS but **only via workaround** `node dist/tests/test_quilt_vm.js` (BUG-2: scripts point at wrong dist paths) | Gold: `node dist/src/gold.js`. Only VM with 0 corpus self-failures. |
| Haskell | builds via patched copy (BUG-4: 6 upstream errors, patch at `adapters/haskell/QuiltVM.hs.fixup.patch`) | runs | GHC 9.10.3 @ ~/.ghcup, static gmp in ~/.local/lib. Divergences BUG-7 (`""` auto-create) + BUG-8 (effect events stamped with dt). |
| WASM | upstream **unbuildable** (BUG-3: invalid Cargo.toml feature) | n/a | prebuilt pkg from patched copy committed at `adapters/wasm/pkg` (BUILD.md). VM is a different, shallower model (BUG-6): effects never applied, no scheduler/subscribers/dispose/log. |

## Phase 2 status (2026-08-25): COMPLETE

All five adapters live under `adapters/` and run the 36-program corpus via
`./run_all.sh` → `results/raw/<vm>/T*.txt`; `python3 scripts/diff.py`
regenerates `results/RESULTS.md` (7/36 MATCH, 29 DIVERGE — wasm stub
dominates; per-step detail + per-VM self-failure lists). `results/BUGS.md`
holds the 11 filed bugs. `results/BENCH.md` holds the honest gold benchmark
(20x each, WSL2 note). Remaining: upstream fixes live in the VM repos (not
this repo); push when asked.

## Corpus design (author in corpus/ as numbered .json files + corpus/README.md)

Corpus format: JSON per program: `{ "id": "T01", "desc": "...", "ops": [...] }`
where ops is a flat sequence like:
`["bind","a","4.2"]`, `["link","a","b","depends_on"]`,
`["effect","a","inc","dec","1"]`, `["view","a","anyone"]`, `["tick","1.0"]`
plus `["expect","<expected output line>"]` / final output lines are the diff surface.
Every program prints deterministic lines; adapters map JSON → VM calls and print
lines in a canonical format: `T01|step|result` (id, step index, string result).

Required coverage (~30 programs):
- Per-opcode basics: BIND value echo; BIND overwrite semantics; LINK basic;
  LINK missing target; EFFECT fwd; EFFECT inverse (undo); VIEW by owner vs
  stranger (projection); VIEW missing; TICK advances time; TICK fires scheduled.
- Composition: spreadsheet chain A1+A2→B1; effect+tick ordering; subscribe
  fires on tick; dispose runs inverses.
- Edge cases: empty cell view; self-LINK (a→a); TICK with dt=0; double EFFECT
  then undo once; LINK duplicate; BIND after LINK; VIEW after dispose;
  TICK ordering with multiple scheduled events at same time.
- Canonical semantics: value formatting — decide canonical (numbers printed
  as-is, e.g. `4.2`, `30`) and note per-VM deviations in results, don't
  force-convert away real divergence.

## Adapters (adapters/)

- adapters/rust.rs — bin in quilt-conformance that reads corpus JSON, drives
  quilt-vm-rust API (see its src/lib.rs; values are String-based JSON-ish).
- adapters/c/main.c — drives quilt_vm.h API.
- adapters/typescript/adapter.ts — imports ../../quilt-vm-typescript/src/quilt_vm.ts (or dist), runs corpus.
- adapters/haskell/Main.hs — drives QuiltVM.hs API (once build unblocked).
- adapters/wasm/ — node driver if wasm-pack succeeds.
- runner: run_all.sh writes raw outputs to results/raw/<vm>/<testid>.txt,
  then scripts/diff.py produces results/RESULTS.md diff table.

## Honesty rules
- Never claim a VM passes anything that wasn't executed here. UNTESTED is a
  valid, honest cell in the table.
- Benchmarks: run C gold 20x, report min/median; same for rust/ts gold.
  Machine: WSL2, single host — say so.
- Disagreements between VMs on the same corpus program = first-class bug
  reports with minimal repro in results/BUGS.md.

## Git
- Commit after every meaningful unit (corpus, each adapter, results).
- Repo: github SuperInstance/quilt-conformance, PRIVATE. gh CLI is authed.
