# quilt-conformance

A shared, deterministic conformance corpus run against **all five** quilt VM
implementations (TypeScript, Rust, C, Haskell, WASM), plus a 5-way diff, a
bug ledger, and honest gold-demo benchmarks. Purpose: find where the five
repos disagree with each other and with the shared spec, with minimal repros
and zero "trust me it passes" claims — every number below was produced by
executing code on this host (WSL2).

## Status (2026-08-25, honest)

| VM | upstream builds? | upstream tests | corpus self-failures | notes |
|----|------------------|----------------|----------------------|-------|
| TypeScript | yes | 6/6 (wrong dist paths — BUG-2) | **0 / 36** | reference implementation in practice |
| Rust | lib yes | `cargo test` **fails to compile** (BUG-1) | 4 (T24, T27) | panics instead of catchable errors (BUG-11); no gold demo shipped |
| C | yes | 6/6 | 6 (T02, T25, T27) | `qvm_bind` appends instead of replacing (BUG-5) |
| Haskell | **no** — patched copy (BUG-4, patch in-repo) | runs | 3 (T06, T07, T36) | auto-create uses `""` (BUG-7); effect events stamped with dt (BUG-8) |
| WASM | **no** — invalid Cargo.toml (BUG-3); prebuilt pkg in-repo | n/a | 51 across 26 tests | a different, shallower VM: no effect application, scheduler, subscribers, dispose, log, link accessor (BUG-6) |

5-way verdict over the 36-program corpus: **7 MATCH, 29 DIVERGE** — the wasm
stub accounts for most divergences; the rest are real semantic bugs filed in
`results/BUGS.md` (11 total: 1 per-repo build/test breakage ×4, plus wasm
model gap, C bind-append, Haskell `""`-create + dt-stamped events, Rust
effect-record / link-dup / panic-vs-error).

Gold benchmark (20 runs each, external wall-clock, WSL2 single host — see
`results/BENCH.md`): c 0.70 ms min, rust 0.88, haskell 1.49, typescript
20.4 (node startup dominates). Self-reported internal timings are recorded
but not comparable across languages.

## Layout

```
corpus/            36 programs (T01–T36), JSON op sequences + corpus/README.md (spec)
adapters/
  typescript/      adapter.ts — imports quilt-vm-typescript dist
  rust/            cargo bin — drives quilt-vm-rust API (per-op catch_unwind); + gold.rs
  c/               main.c — compiles against quilt-vm-c sources
  haskell/         cabal project over the patched QuiltVM.hs (+ patch file, gold)
  wasm/            node driver over prebuilt wasm-pack pkg (BUILD.md)
run_all.sh         builds + runs all five → results/raw/<vm>/T*.txt
scripts/diff.py    5-way diff → results/RESULTS.md
scripts/bench.py   20x gold benchmark → results/BENCH.md numbers
results/           RESULTS.md (matrix + per-step divergences), BUGS.md, BENCH.md, raw/
WORKORDER.md       mission, verified build status, phase log
```

## How to run

Prerequisites (as used here): sibling VM checkouts at
`~/projects/quilt-vm-{typescript,rust,c,haskell,wasm}`, node ≥ 22 (plain
node runs the .ts/.cjs adapters), cargo, gcc, cabal/GHC 9.10 via ghcup
(`~/.ghcup/bin`, static gmp in `~/.local/lib`).

```sh
./run_all.sh                # runs all 5 adapters → results/raw/<vm>/
python3 scripts/diff.py     # regenerates results/RESULTS.md
python3 scripts/bench.py    # gold benchmark (optional; writes nothing, prints numbers)
```

`run_all.sh` hardcodes the VM checkout paths and the ghcup/library env for
Haskell — edit the variables at the top if your layout differs.

## Corpus in one minute

Each `corpus/Tnn.json` is `{id, desc, ops}`; every op prints exactly one
canonical line `<testid>|<step>|<result>` (including failures), so raw
outputs align across VMs and `diff.py` can compare step-by-step. `expect`
ops self-check a VM against the spec; cross-VM disagreement is caught by
diffing raw files even when every VM self-passes. Canonical printing,
effect families, and the deliberate probes are specified in
`corpus/README.md`. Test ids are frozen; add new tests, never renumber.

## What this repo deliberately does NOT do

- No upstream fixes: patches/workarounds (Haskell fixup, wasm prebuilt pkg)
  live here with provenance; the VM repos are untouched.
- No normalization of real divergence: if two VMs legitimately print
  different values, that's a finding (see BUGS.md), not something the
  harness papers over.
- wasm is included knowing it fails most of the corpus — the honest
  `error:unsupported op …` lines are the point (BUG-6 documents the model
  gap). A stub-passing cell would be worse than a failing one.
