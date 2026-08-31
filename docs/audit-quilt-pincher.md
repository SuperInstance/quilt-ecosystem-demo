# audit-quilt-pincher

Repo: https://github.com/SuperInstance/quilt-pincher
Commit: `5d13eaa` (shallow clone, 2026-08-20). Single commit on `main` after `--depth 1`.
Audited by: foreman subagent, byte-level.

## Overview

| Field | Value |
|---|---|
| Language | TypeScript (`type: module`, `module: ES2022`, strict + `noUncheckedIndexedAccess`). Targets Node ≥ 18. |
| Main purpose | `@quilt/pincher` — a reflex-matching engine ("pinch in, match a reflex, execute"). Embedder + vector store + LLM compiler + veto, composed as Quilt cells. Three platform tiers: cloud (browser/Node/Worker), workstation (Node+SQLite), ESP32 (advertised as `no_std` Rust port). |
| Source size | 1,005 lines of TS total: 745 lines in `src/` (8 files), 230 lines in `test/reflex.test.ts`, 64 lines in `examples/devops-bot.ts`. +README (138 lines) +ESP32_PORT.md (95 lines) +CI YAML (17 lines). |
| Real TS files | 8 in `src/`: `index.ts`, `core/{engine,types}.ts`, `cells/sheet.ts`, `adapters/{embedding-adapter,memory-store}.ts`, `platforms/{cloud,workstation,esp32}.ts` |
| Pinned deps | `@quilt/core`, `@quilt/sdk`, `@quilt/ai` all as `*` (unresolved). **None of these exist on npm** (`@quilt/ai` 404s the registry; the others are presumably the same). `npm install` fails on a fresh clone. |
| Test runner | `npm test` → `tsx --test test/*.test.ts`. Single test file, 9 `describe` blocks, 12 `test()` cases, uses `node:test` + `node:assert/strict` (no test framework). |
| Test result | **12/12 pass** when run via `tsx --test` against installed TS sources (after working around the missing `@quilt/*` deps with an external `tsx` install). |
| Typecheck | `tsc --noEmit` reports **2 errors** — duplicate `PincherSheet` identifier in `src/index.ts` (see What's stub). |

## What's real

| File | Lines | What it does | Notes |
|---|---|---|---|
| `src/core/types.ts` | 117 | All public types: `Pinch`, `PinchResult` (5-tuple), `Reflex`, `Embedder`, `ReflexStore`, `Compiler`, `Veto`, `SafetyHints`, `PincherConfig`, `NailBundle`. | Real, clean, exported from `index.ts`. |
| `src/core/engine.ts` | 217 | `PincherEngine` class: 3-tier decision tree (hit ≥ 0.80 / confirm 0.55–0.80 / compile below). Veto check on every path. `execute()` does `new Function('pinch', ...)` with a 5s `Promise.race` timeout. Confidence climbs log10 with hits, capped at 0.99. Plus `HashEmbedder` (384d, char-code hash, L2-normalized) and `DefaultVeto` (network/filesystem/sandbox safety checks). | The core works end-to-end. **One bug**: `allReflexes()` (line 155) always returns `[]` — see What's stub. |
| `src/cells/sheet.ts` | 57 | `PincherSheet()` returns `{ name, engine, cells: PincherCell[] }` with 6 static cell descriptors (`pinch`/`formula`, `match`/`program`, `execute`/`program`, `veto`/`listener`, `compile`/`ai`, `store`/`vector_store`). `runPinch()` is a one-line wrapper. | Real, but the `cells` array is decorative metadata — the engine itself is monolithic. The README's "Quilt cell composition" story is aspirational: the engine is one JS class, the cells are a string array. |
| `src/adapters/memory-store.ts` | 68 | `MemoryReflexStore` with `insert/query/get/delete/count/all`. Brute-force cosine similarity (single-loop dot product, no vectorization). Optional `upstream` for federation (insert+delete fan out). | Real. `query` is O(N·d) which is fine to ~10K reflexes as the comment claims. |
| `src/adapters/embedding-adapter.ts` | 37 | Three trivial wrappers: `CloudflareAIEmbedder` (which **falls back to `HashEmbedder`** — comment says "for now"), `OfflineEmbedder` (same), `QuiltAIEmbedder` (delegates to injected function). | All three are pass-throughs to `HashEmbedder` by default. Real code, zero real embeddings. |
| `src/platforms/cloud.ts` | 41 | `cloudSheet({ name, embedderApi?, compilerApi?, federation? })`. Wires `CloudflareAIEmbedder` + `MemoryReflexStore` + `DefaultVeto` + optional compiler. | Real, but `CloudflareAIEmbedder` is just `HashEmbedder` (see above). |
| `src/platforms/workstation.ts` | 54 | `workstationSheet()` + `SqliteReflexStore`. | **The `SqliteReflexStore` is a 100% stub** — see What's stub. |
| `src/platforms/esp32.ts` | 81 | `ESP32Engine` class, `esp32Sheet()`, `buildNail()`, `EmbeddedNail` type. `ESP32Engine.memoryUsage()` returns `n * 4096` ("~4KB per reflex including embedding"). | Real-ish. The class is TS that wraps `PincherEngine`. No Rust port exists despite `docs/ESP32_PORT.md`. |
| `src/index.ts` | 39 | Re-exports types, engine classes, adapters, sheet, all three platform factories. | Real export surface, but has the `PincherSheet` duplicate-identifier error (see below). |
| `test/reflex.test.ts` | 230 | 9 `describe` blocks, 12 `test()` cases covering: direct hit, slight-trigger-variation hit, confirm tier, compile (with/without compiler), veto on safety mismatch, confidence-climbs, sheet cell composition (asserts exactly 6 cells + 5 cell kinds present), `cloudSheet`/`workstationSheet`/`esp32Sheet` factory calls, `.nail` load. | All 12 pass. Uses `HashEmbedder(64)` (smaller for tests). |
| `examples/devops-bot.ts` | 64 | 4-step demo: unknown compile → similar hit → new compile → similar confirm. Prints latency. | Runs end-to-end via tsx. Output observed: `compiled (1ms) → hit (0ms) → confirm (0ms) → confirm (1ms)`. |
| `package.json` | 33 | Build via `tsc`, test via `tsx --test test/*.test.ts`, lint+typecheck scripts. | `npm install` is broken because `@quilt/core`, `@quilt/sdk`, `@quilt/ai` are 404. |
| `tsconfig.json` | 16 | ES2022, strict, `noUncheckedIndexedAccess`, DOM lib included. `include: ["src/**/*"]`, `exclude: ["test"]`. | Sensible. |
| `.github/workflows/ci.yml` | 17 | `npm ci || npm install` → `npm run typecheck` → `npm test` on Node 20. | Real, will fail on a fresh clone due to 404 deps and the typecheck error. |

## What's stub

| Item | Why it's stub |
|---|---|
| `@quilt/core`, `@quilt/sdk`, `@quilt/ai` in `package.json` deps | All three resolve to `*` and **do not exist on the npm registry** (verified `@quilt/ai` → 404). The whole "Quilt cell composition" thesis — `PincherSheet.cells = [{kind: 'formula'...}]` — is a string array. The repo never actually wires into `QuiltEngine` or `parseSheet` (which the README quick-start imports from `@quilt/core`). `npm install` fails. |
| `src/index.ts` duplicate `PincherSheet` (lines 32–33) | Line 32 does `export { PincherSheet, runPinch } from './cells/sheet.js';` and line 33 does `export type { PincherSheetConfig, PincherSheet, PincherCell } from './cells/sheet.js';` — both export the value `PincherSheet`. `tsc --noEmit` errors with `TS2300: Duplicate identifier 'PincherSheet'`. The `type` re-export is meant to be `type-only`, but without `import type` or `export type {...}` (or a separate runtime export name) the value gets duplicated. Two errors total. |
| `src/core/engine.ts` `allReflexes()` (lines 155–160) | Returns `[]` always. The method has a comment "For a real implementation, we'd paginate. For demo, we re-query." but it doesn't even re-query — it just returns `[]`. **This makes `exportNail()` (line 167–182) ship a `NailBundle` with `reflexes: []`** even when the store has reflexes. The only path that actually exports reflexes is `buildNail()` in `esp32.ts`, which bypasses `allReflexes()` with a `(sheet.engine as any).store.all?.()` cast. |
| `src/platforms/workstation.ts` `SqliteReflexStore` (lines 18–34) | Class is just `private memory: MemoryReflexStore = new MemoryReflexStore();` plus five `async` methods that all delegate to `this.memory` with a `// TODO: persist to sqlite` comment. **No `import` of any sqlite or `better-sqlite3` package.** The header docstring claims it uses `sqlite-vec` for vector queries. `workstationSheet()` instantiates this stub as its default store. The TODO is the single real one in the codebase. |
| `src/adapters/embedding-adapter.ts` `CloudflareAIEmbedder` (lines 12–20) | Comment says "In production this would call Cloudflare's REST API. For now, fall back to hash embedder (offline-friendly)". So the "Cloudflare AI" embedder is just `HashEmbedder`. The whole "Three tiers, same engine" story collapses: cloud has the same fake hash embedding as ESP32. |
| `docs/ESP32_PORT.md` | 95-line markdown advertising a `quilt-pincher-no_std` Rust crate, complete with `Cargo.toml`, sample `#[no_std]` `#[no_main]` code, a 128 KB memory budget table, and a `cargo build --target xtensa-esp32-espidf` build command. **There is no `*.rs` file and no `Cargo.toml` in the repo** (`find -name '*.rs'` and `find -name 'Cargo.toml'` both return nothing). The "ESP32 tier" in `src/platforms/esp32.ts` is a 81-line TS wrapper that just instantiates `MemoryReflexStore` + `OfflineEmbedder` + `DefaultVeto` and is itself too heavy to run on real ESP32 (imports the whole engine, uses `Date.now()`, `Math.log10`, async/await — none of which are `no_std`). |
| `PincherSheet.cells` (the Quilt-cell claim) | Six static `{path, kind, description}` objects. The engine does not consume them. `runPinch()` just calls `sheet.engine.run(pinch)`. The cells array is a documentation prop for the README diagram. |
| `CODEOWNERS` (lines 14–22) | References `/packages/core/src/`, `/packages/sdk/src/`, `/packages/cli/src/`, `/packages/mcp/src/` — **none of these paths exist in this repo**. Cargo-culted from a monorepo template; the rules are inert. |
| `package.json` keywords | Lists `esp32` and `edge` as keywords; the actual ESP32 story is a markdown file. |

## Test count

- Test files: **1** (`test/reflex.test.ts`)
- Describe blocks: **9**
- Test cases: **12**
- Result: **12 pass, 0 fail, 0 skip** (run via `tsx --test test/reflex.test.ts`, observed live)
- Test framework: `node:test` (built-in) + `node:assert/strict`. No vitest/jest.
- Coverage: covers hit/confirm/compile tiers, veto, confidence climb, sheet cell count, all 3 platform factory entry points, `.nail` load. **Does not** cover: `exportNail()` (which silently produces empty `reflexes`), `allReflexes()` (the bug), federation upstream fan-out, veto edge cases beyond network/any, execution timeout, and there's no integration test that actually loads a `.nail` from cloud→esp32 (the existing `esp32Sheet` test builds a `PincherEngine` in TS and calls `buildNail` on it, not a real `cloudSheet`).

## Top 1-day adds

1. **Fix `allReflexes()` and the typecheck errors** (~1 hour total).
   - Replace `engine.allReflexes()` body (engine.ts:155–160) with `return this.store.all ? this.store.all() : [];` — `MemoryReflexStore` already has `all()`. Add `all()` to the `ReflexStore` interface in `types.ts` as optional. `exportNail()` then ships real reflexes.
   - Split `src/index.ts` line 32–33: drop the value `PincherSheet` from the `export type` (it's a value, not a type), or rename the runtime export. Two-line fix; removes both `tsc` errors.
   - Add a test that `engine.exportNail(...).reflexes.length > 0` after `addReflex` so the bug can't regress.

2. **Wire one real `SqliteReflexStore` (~4–6 hours, fits a focused day)**.
   - Add `better-sqlite3` (synchronous, no native build hell on most platforms) to devDeps. Skip `sqlite-vec` for v1 — the in-memory store is already brute-force cosine, and a flat BLOB column plus the same JS loop matches that complexity.
   - Replace the 5 delegating methods in `src/platforms/workstation.ts:18–34` with real SQL: `CREATE TABLE reflexes (id TEXT PRIMARY KEY, embedding BLOB, intent TEXT, action TEXT, safety JSON, confidence REAL, hits INTEGER, created_at INTEGER, last_hit_at INTEGER, provenance JSON)`. `insert` = `INSERT OR REPLACE`, `query` = load all rows + JS cosine (mirroring `MemoryReflexStore`).
   - One workstation test that inserts 10 reflexes, kills the engine, rebuilds from the same `dbPath`, and asserts `count() === 10` and the top-K match returns the same reflex id. That single test turns "SQLite-backed persistence" from a comment into a real feature.

3. **One real embedder path (~3–4 hours)**.
   - Either: (a) actually call Cloudflare's REST API in `CloudflareAIEmbedder` when `AI_BINDING` or an env var is set, fall back to `HashEmbedder` otherwise, plus a test that stubs `globalThis.fetch`; or (b) ship a `TransformersEmbedder` that uses `@xenova/transformers` for local `all-MiniLM-L6-v2` embeddings in Node.
   - Either way, the "Three tiers, same engine" promise stops being a fiction for the cloud tier. One tiny `fetch` test in `test/reflex.test.ts` asserting the embedder returns a 384d vector with `Math.abs(norm - 1) < 1e-6` when given a real stub response.

## The cowboy's take

This is a 1,000-line TS repo with a 217-line engine that actually works — 12/12 tests pass, the devops example runs, the three-tier decision tree (hit/confirm/compile) is correctly implemented, the veto is wired into every execution path, and confidence climbs with hits via a sensible log curve. The author can ship a working reflex matcher today.

But the surrounding scaffolding is costume jewelry. The "Quilt cell composition" thesis is a 6-string array that the engine never reads. The "three tiers" claim collapses because `CloudflareAIEmbedder` and `OfflineEmbedder` are both `HashEmbedder`. The "SQLite-backed" workstation store is a TODO. The "ESP32 `no_std` port" is a markdown file with no Rust. `@quilt/core`/`@quilt/sdk`/`@quilt/ai` are phantom deps that 404 the registry. `allReflexes()` is a stub that silently breaks `exportNail()`. The `CODEOWNERS` references directories that don't exist.

The honest framing: this is a single-process in-memory reflex engine with a decorative cell-model wrapper. That's a real thing, and it's useful. The 1-day fixes above turn it from "demo that runs" into "library that ships" — fix the bugs, land one real embedder, persist the SQLite store, and you've got something worth `npm publish`-ing. Until then, treat the README as marketing and the engine as the product.
