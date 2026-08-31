# audit-quilt-ai

Repo: https://github.com/SuperInstance/quilt-ai
Commit: shallow clone of `main` at audit time.
Audited by: foreman subagent, byte-level.

## Overview

| Field | Value |
|---|---|
| Language | TypeScript (compiled to JS for Node ≥ 18) |
| Main purpose | `@quilt/ai` — single `AIEngine` that wraps 4 LLM providers (z.ai, Kimi, DeepSeek, Cloudflare Workers AI) behind one `engine.call(config)` interface, with an in-memory response cache, per-model cost tracking, and 8 cell-kind shapes (`ai.llm`, `ai.embed`, `ai.image`, `ai.translate`, `ai.sentiment`, `ai.summarize`, `ai.code`, `ai.vision`) intended to plug into a Quilt reactive sheet. |
| Source size | 1,304 lines of TS in `src/` + 82 lines of JS test + 85 lines of evolve example. 271-line README, 311 lines of YAML examples, 48-line SECURITY.md. Excluding `node_modules`, `.git`, and the spurious `src/providers-build/` directory, total is ~1,800 lines. |
| Real TS files | 5 (`src/index.ts`, `src/engine.ts`, `src/types.ts`, `src/providers/{zai,kimi,deepseek,cloudflare}.ts`) |
| Pinned deps | `@quilt/core` and `@quilt/evolve` as `workspace:*` (i.e. this repo is meant to live inside a Quilt monorepo). `typescript ^7.0.2` and `@types/node ^26.2.0` in devDeps. **No runtime dependencies on the npm side** — providers use global `fetch`. |
| Test runner | `npm test` → `node test/*.test.js`. Single file, 5 hand-rolled `try/catch` blocks, no test framework. |

## What's real

| File | Lines | What it does | Notes |
|---|---|---|---|
| `src/types.ts` | 222 | All 8 cell-kind config interfaces, `Provider`, `AIResult` union, `ProviderResponse`, `AIError` class, `AIProvider` interface, `ModelInfo`. | Real, complete, no `any` leakage except the spread in `engine.ts`. |
| `src/engine.ts` | 176 | `AIEngine` class: provider registry, `call()` with cache-by-config-hash, cost accumulator from per-model `cost_per_1k_input/output`, `getCost`/`getTokens`/`getCacheStats`/`clearCache`. | Real, no stubs. The `cacheKey` JSON-spread is a bit loose (uses `(config as any).prompt` etc.) but functional. |
| `src/providers/zai.ts` | 253 | z.ai (Zhipu GLM 4.5 / AirX / Flash / 9B). Real `fetch` to `https://api.z.ai/api/paas/v4/chat/completions`. Handles 6/8 kinds; throws `AIError` for `ai.image` (correctly — z.ai doesn't do images). | Real, includes `embed` and `translate`/`sentiment` paths. |
| `src/providers/kimi.ts` | 160 | Moonshot Kimi v1 + K2. Chat + embed. Bearer token, OpenAI-compatible shape. | Real. |
| `src/providers/deepseek.ts` | 122 | DeepSeek V3 / R1. Chat + embed. | Real, smallest of the four. |
| `src/providers/cloudflare.ts` | 286 | Cloudflare Workers AI (`https://api.cloudflare.com/client/v4/accounts/{id}/ai/run/{model}`). Handles all 8 kinds: LLM, embed, image (SDXL), translate (M2M100), sentiment, summarize, code, vision (LLaVA). | Real and the most complete. The only provider that delivers on all 8 advertised kinds — z.ai/Kimi/DeepSeek explicitly punt on image. |
| `src/index.ts` | 85 | Re-exports + `createEngine()` that reads `process.env.{ZAI,KIMI,DEEPSEEK,CLOUDFLARE}_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. | Real. |
| `evolve/01-prompt-improvement.js` | 85 | Real example wiring `AIEngine` into `@quilt/evolve` (`FunctionSystem` + `HeuristicJudge` + `LLMMutator` + `SeededGenerator` + `FullSheetScope`). Requires a built `dist/index.js` and live `ZAI_TOKEN`. | Real, but only runs end-to-end if you also have `@quilt/evolve` resolved and a real key. |
| `examples/01-06-*.yaml` | 23–83 each | Six real Quilt sheet YAMLs referenced in the README (basic-llm, fanout-3models, rag, agent-loop, cost-control, image-pipeline). | Real YAML, but **no loader in this repo** — sheets only execute inside `@quilt/core`, which lives in a different repo. |
| `test/types.test.js` | 82 | 5 hand-rolled `try { … } catch (e) { process.exit(1) }` blocks asserting engine construction, custom provider registration, initial cache stats, `AIError` export, and that all 4 provider classes are exported. | Runs and passes — **only after `npm run build` and after fixing the broken require paths** (see "What's stub"). |
| `.github/workflows/ci.yml` | — | Runs `npm ci` → `npm run build` → `npm test` on Node 20 and 22. | Real, sensible. |
| `package.json` | 46 | Correct `main`/`types`/`exports` map, `tsc` build, `node test/*.test.js` test script. | Has a **duplicate `dependencies` key** (lines 31–33 and 36–38 both define `dependencies`); JSON parsers take the last one, so `@quilt/evolve` is silently dropped. JSON would fail strict validators. |

## What's stub

| Item | Why it's stub |
|---|---|
| `src/providers-build/` (whole directory, ~29 KB of checked-in `.js`) | A half-built stale `tsc` output — contains `types.js` and all 4 provider `.js` files, but **no `engine.js` and no `index.js`**. The directory name doesn't match the build output (`dist/`), the `.gitignore` excludes `dist/` and `src-build/` but not `providers-build/`, and the file is committed to the repo. Dead weight. |
| `test/types.test.js` requires `../src/engine.js`, `../src/types.js`, `../src/index.js` | None of those `.js` files exist. The repo only ships `.ts` source. `npm test` straight out of the box fails with `Cannot find module '../src/engine.js'`. The test only passes after you `npm run build` **and** patch the require paths to `../dist/`. So the "test suite" is effectively non-runnable from a fresh clone — exactly the failure mode the foreman wants flagged. |
| README test claim | README line 220: *"The test suite runs 6 unit tests."* The file has 5 `Test N:` blocks. **README is wrong by 1.** |
| `package.json` devDep `typescript: ^7.0.2` | TS 7.0.2 is real (it shipped as a preview/RC line), so `tsc` *does* work and the build succeeds on Node 22. The version is unusual but not a blocker. |
| `package.json` `@types/node: ^26.2.0` | Node 26 isn't out as a stable major at audit time. npm won't error on install (caret allows the major) but the resolved type package is whatever floats to the top. Not a runtime problem, just sloppy. |
| `evolve/01-prompt-improvement.js` line 14 | `require('../dist/index.js')` — only works after `npm run build`, which the file does not document or script. |
| All `examples/*.yaml` sheets | They reference `kind: ai.llm`, `kind: vectorize.search`, `kind: router`, `kind: listener`, `kind: value` — only `ai.*` and `value` kinds are honored by *this* repo's `AIEngine`. The `vectorize.search`, `router`, and `listener` kinds live in `@quilt/core` and `@quilt/cloudflare`. The README is honest that sheets need `@quilt/core`, but a casual reader will think this repo can run them. It can't. |
| "8 cell kinds" claim | Only Cloudflare implements all 8. z.ai implements 6 (throws on `ai.image`), Kimi and DeepSeek implement 2 each (chat + embed). The README is accurate at the *interface* level (`AIConfig` union covers all 8) but the marketing "4 providers × 8 kinds = 32" implied by the table is more like 1×8 + 1×6 + 2×2 = 18 working combinations. |

## Test count

Actual runnable tests, byte-level:

- `test/types.test.js` contains **5** `Test N:` blocks, not the 6 claimed in the README.
- No other `*.test.*` files exist anywhere in the repo.
- Zero `def test_*` (Python), zero `#[test]` (Rust), zero `it(`, `test(`, or `describe(` calls — confirmed with `grep -rEn "^\s*it\(|^\s*test\(|^\s*describe\(" --include="*.ts" --include="*.js"`.
- **`npm test` fails as shipped** with `Cannot find module '../src/engine.js'`. The "test suite" only passes after (a) `npm run build` and (b) patching 3 require paths to point at `../dist/`. With those patches all 5 tests pass green.
- No integration tests against real providers. No mocked HTTP. The tests only assert construction, custom-provider registration, empty cache, and the `AIError` export.
- Evolve example (`evolve/01-prompt-improvement.js`) is not a test and is not run by `npm test`.

**Net: 5 unit tests, 0 of which run on a clean clone, 0 integration tests.**

## Top 2-3 1-day adds

### 1. Fix the test runner so `npm test` works on a fresh clone (≤ 2 hours)

`test/types.test.js` requires `../src/engine.js` etc., but only `.ts` files exist. Two minimal options:

- **A (preferred):** change the test file's `require("../src/engine.js")` to `require("../dist/engine.js")` (3-line patch) and add a `pretest` script to `package.json`: `"pretest": "npm run build"`. Now `npm test` works on a clean clone after `npm install`.
- **B:** add a 1-line `prepare` script: `"prepare": "tsc"`. Then the test path can stay as-is **if** you also move the build output to `src/` (e.g. by changing `tsconfig.json` `outDir` to `src`). More invasive, less idiomatic.

Either way, this is the single highest-leverage change in the repo. As shipped, `npm test` is a trap.

**Concrete files to touch:** `test/types.test.js` (line 16, 28, 44, 58, 71), `package.json` (add `pretest`).

### 2. Fix the README's "6 unit tests" lie, and add 2–3 actually-meaningful tests (half a day)

The current 5 tests are construction-only — they never exercise `call()`, the cache hit path, the cost counter, or the error path. Adding these would have caught the broken-require bug at write time:

- `engine.call()` with a mocked provider → assert cache miss, then assert second call hits cache and bumps `getCacheStats().hits`.
- `engine.call()` → assert `getCost()` matches the model's `cost_per_1k_input` × tokens.
- `engine.call()` with no API key → assert it throws `Error("No API key for provider: …")`.
- `getCacheStats()` after a real `call` cycle to confirm `misses` is computed (right now `engine.ts` line 148 returns `misses: this.cache.size`, which is a *lie* — it should count actual misses, not current size).

**Concrete files to touch:** `test/types.test.js` (add 4 more blocks), and `src/engine.ts` line 148 (real `misses` counter).

### 3. Stop committing `src/providers-build/` and delete the duplicate `dependencies` key (10 minutes)

- `src/providers-build/` is 4 stale `tsc` outputs, ~29 KB, and it's in the repo because the `.gitignore` only excludes `dist/` and `src-build/`. Either delete the directory and add `src/providers-build/` to `.gitignore`, or just delete the directory outright — it serves no purpose; `npm run build` regenerates `dist/` on demand.
- `package.json` has `"dependencies"` defined twice (lines 31–33 declare `@quilt/evolve`, lines 36–38 declare `@quilt/core` and silently overwrite the first block). JSON tolerates this; humans and most tools don't. Merge into a single `dependencies` block with both packages.

**Concrete files to touch:** delete `src/providers-build/`; edit `.gitignore`; edit `package.json` to merge deps.

(Optional bonus for the same day: update the "8 cell kinds per provider" claim in the README to "1 provider (Cloudflare) supports all 8; z.ai supports 6; Kimi/DeepSeek support 2 each" — saves the next reader 20 minutes of confusion.)

## The cowboy's take

This is a tidy, well-scoped TypeScript package: ~1,300 lines of real code, no TODOs, real `fetch` calls to real provider endpoints, all 4 advertised providers actually implemented, cost and cache logic that holds together, and an honest docstring at the top of every file. The author knows how to write an `AIProvider` interface and they did. The shame is that the front door is welded shut: `npm test` is broken on a clean clone because the test imports `.js` paths that don't exist, the README lies by one test (claims 6, ships 5), and the repo commits a half-built `tsc` output under a non-standard name (`src/providers-build/`) that has no `engine.js` and no `index.js` — so it's not even useful as a fallback. A one-line `pretest: npm run build` and a 3-line require-path fix would turn this from "looks real, doesn't run" into "looks real, runs". The deeper gaps (zero integration tests, no mocked HTTP, `getCacheStats().misses` is straight-up wrong, Cloudflare is the only provider that actually delivers the "8 cell kinds" promise) are forgivable for a v0.1; the front-door breakage is not. Bottom line: ship-ready code, demo-ready repo almost.
