# audit-quilt-rag

**Repo:** https://github.com/SuperInstance/quilt-rag
**Cloned at:** /workspace/quilt-rag
**HEAD:** `828ee63 feat: add splash image for repo branding`
**Audit date:** 2025-08-31
**Auditor:** cowboy subagent

---

## Overview

A TypeScript RAG framework structured around the Quilt "cells" abstraction. README pitches 8–9 cell kinds (loader, chunker, embedder, vector_store, retriever, reranker, context, generator, evaluator) and advertises 5 vector stores, 5 embedders, 3 rerankers. Roughly 1,300 lines of source spread across 11 files. Tests are 17 `node:test` functions in one file. A GitHub Actions workflow (`.github/workflows/ci.yml`) runs `npm ci`, `npm run lint`, `npm test`, `npm run build`.

**Bottom line before reading further:** README claims "production RAG" with extensive provider support. Code delivers the *shape* of that promise — every advertised cell class is exported and every interface is implemented — but no provider adapter is exercised by tests, `npm run build` would currently fail (49 type errors), and the one provided example is **broken at runtime** (imports a class that doesn't exist).

---

## What's real

I ran `npx --no-install tsx --test test/rag.test.ts` against the freshly-cloned tree (no `node_modules`, no installs). All 17 tests passed in ~1.06s.

Real, working, tested:

- **`MemoryVectorStore`** (`src/cells/vector-store.ts:10-42`) — full in-memory store. Cosine similarity, metadata filter, upsert/delete/count. 3 tests cover it (lines 68-97 of `test/rag.test.ts`).
- **`SentenceChunker`, `ParagraphChunker`, `TokenWindowChunker`, `SemanticChunker`** (`src/cells/chunker.ts`) — all 4 split strategies implemented. 4 tests.
- **`CosineRetriever`, `MmrRetriever`** (`src/cells/retriever.ts:9-50`) — cosine is correct; MMR exists but is broken (see "What's stub"). 2 tests.
- **`DefaultContextBuilder`** (`src/cells/generator.ts:10-24`) — token-budgeted context assembly. 1 test.
- **`RelevanceEvaluator`, `FaithfulnessEvaluator`, `HallucinationEvaluator`, `ContextPrecisionEvaluator`, `RagEvaluatorCell`** (`src/cells/evaluator.ts`) — all 4 evaluators + the composite cell. 5 tests. These are heuristic, not LLM-based.
- **`RAGPipeline`** (`src/index.ts:65-144`) — `ingest()`, `query()`, `evaluate()`, `chunkCount()`. 2 end-to-end tests with a deterministic FakeEmbedder (lines 191-223).

Also real (untested but implemented and compilable in spirit):

- **`UrlLoader`** (`src/cells/loader.ts:53-60`) — plain `fetch`. No tests, but it's 7 lines and obvious.
- **`HybridRetriever`** (`src/cells/retriever.ts:53-93`) — BM25 + dense score fusion, real implementation, no test. The BM25 math at `retriever.ts:103-128` looks correct.
- **`FileLoader`** — directory walk, JSON/text/html parsing, no test.
- **`BgeReranker`, `CohereReranker`, `LocalCrossEncoderReranker`** (`src/cells/reranker.ts`) — real HTTP calls, no tests.
- All 5 embedders: real `fetch` against Cloudflare/OpenAI/Cohere/Voyage/HF, no tests.
- All 3 LLM generators: real `fetch`, no tests.

Total file/line counts (`wc -l`):

```
 144 src/index.ts
 187 src/types.ts
 136 src/cells/chunker.ts
 118 src/cells/embedder.ts
  85 src/cells/evaluator.ts
  85 src/cells/generator.ts
  87 src/cells/loader.ts
  64 src/cells/reranker.ts
 133 src/cells/retriever.ts
 219 src/cells/vector-store.ts
  75 examples/basic-qa.ts
 223 test/rag.test.ts
1556 total
```

CI workflow exists at `.github/workflows/ci.yml` (4 steps: install, lint, test, build). Dependabot configured. License: Apache-2.0. `tsconfig.json` is strict (`exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`).

---

## What's stub

### 1. `MmrRetriever` is broken (and the test only checks it returns 2 results)

`src/cells/retriever.ts:35-39` — the diversity penalty uses `s.score` (the relevance score of an already-selected item) as a proxy for similarity-to-already-selected. The author flags this with a comment: `// Approximate by score since we don't have the original vector`. This is not MMR; it's a no-op followed by a relevance sort. The test at `test/rag.test.ts:114-128` only asserts `results.length === 2`, not that diversity is actually achieved.

### 2. `examples/basic-qa.ts` is broken — imports a class that doesn't exist

`examples/basic-qa.ts:26` does `const { ZaiEmbedder } = await import('../src/cells/embedder.js');` and then `new (ZaiEmbedder as any)(zaiKey)` at line 28. There is no `ZaiEmbedder` export in `embedder.ts` — only `WorkersAIEmbedder`, `OpenAIEmbedder`, `CohereEmbedder`, `VoyageEmbedder`, `LocalOnnxEmbedder`. Running the example as documented in the README would throw `ZaiEmbedder is not a constructor`. The `(ZaiEmbedder as any)` cast hides the error at compile time. This is the only example in `examples/`.

### 3. `npm run build` fails — 49 TypeScript errors with strict mode

`tsc --noEmit` against the strict `tsconfig.json` produces 49 errors. Examples:

- `src/cells/embedder.ts:38` — `Property 'modelName' is used before its initialization.` (the `readonly model = this.modelName` line references the constructor param before assignment under `useDefineForClassFields`).
- `src/cells/generator.ts:40,58` — `exactOptionalPropertyTypes` rejects `tokensUsed: number | undefined` for an optional field.
- `src/cells/vector-store.ts:25` and `retriever.ts:82` — same `metadata: undefined` issue against `RetrievalResult.metadata`.
- `src/cells/retriever.ts:13,26,62` — `noUncheckedIndexedAccess` flags `number | undefined` from `[vec]` destructuring of `embed()` result.
- `src/cells/loader.ts:7,8` and `embedder.ts:107`, `reranker.ts:52` — missing `@types/node` and `@huggingface/transformers` (no `node_modules` installed, so types can't resolve; in CI this would resolve fine *if* `npm ci` succeeded).
- `src/index.ts:73-78` — `Required<PipelineConfig>` typed as required, but `Retriever`/`Generator`/`Loader`/`Embedder`/`Reranker` are optional in the source interface. Then `RAGPipeline` later assumes they're non-null and dereferences `this.config.embedder!.model` etc. The constructor doesn't enforce non-null but downstream code does.
- `src/index.ts:111` — type mismatch: `Embedder` returns `number[][]`, but the retriever wants `Promise<number[]>` from `embed(text)`. A signature mismatch that doesn't blow up only because of the `any`-ish `embedder` typing inside the retriever.

CI on master is therefore currently **red** for the `build` step (the lint + test steps would pass). The README badge `[![typescript](https://img.shields.io/badge/TypeScript-strict-blue.svg)]` is aspirational.

### 4. Provider integrations are written but never tested

`OpenAIEmbedder`, `CohereEmbedder`, `VoyageEmbedder`, `LocalOnnxEmbedder`, `WorkersAIEmbedder`, `BgeReranker`, `CohereReranker`, `LocalCrossEncoderReranker`, `OpenAIGenerator`, `ZaiGenerator`, `WorkersAIGenerator`, `VectorizeStore`, `PineconeStore`, `QdrantStore`, `PgVectorStore`, `S3Loader`, `R2Loader` — all 17 of these are real HTTP/RPC call sites but have **zero test coverage**. They would compile, but if any of the third-party APIs change their request shape (they do, frequently), nothing would catch it.

### 5. `HybridRetriever` requires `chunks` in its constructor — leaks pipeline internals

`HybridRetriever` (line 53) takes `private chunks: Chunk[]` directly. This means every RAG user has to hand the retriever a separate copy of all chunks. The README claims "every cell has a unified interface" and "swap any cell" — but you can't swap in a `HybridRetriever` without also wiring chunks through it. Compare to `CosineRetriever` which only needs `store` + `embedder`. The `MmrRetriever` and `HybridRetriever` aren't actually plug-compatible with the rest of the framework as the README advertises.

### 6. `RAGResult.tokensUsed` is reported but `Generator.generate()` returns it inconsistently

`OpenAIGenerator` and `ZaiGenerator` return `tokensUsed` from the API response. `WorkersAIGenerator` does not — returns `{ text }` only. The pipeline surfaces `tokensUsed` in `RAGResult` regardless. Minor, but inconsistent with the README's "5 generators" framing if users expect token accounting on Cloudflare.

### 7. Evaluator heuristics are toy-grade

`RelevanceEvaluator` and `FaithfulnessEvaluator` (`src/cells/evaluator.ts`) use term overlap and substring matching. They will pass the unit tests (which only assert `score > 0` and `unsupported.length > 0`) but are not RAGAS, not TruLens, not LLM-as-judge. The README's table lists them as if they were real metrics. Fine for a first pass; bad for "production."

### 8. No CI cache, no version of node locked

`ci.yml` uses `actions/setup-node@v4` with `node-version: '20'` but the package `engines.node` says `>=18`. Minor.

---

## Test count

| Source | Count |
|---|---|
| `test/rag.test.ts` — `test(...)` blocks | **17** |
| Other `*.ts` files with `test(` | 0 |
| `def test_*` (Python) | 0 |
| `#[test]` (Rust) | 0 |
| `it(` (JS) | 0 |
| **Total real tests** | **17** |

Raw grep result: `grep -rn "def test_\|#\[test\]\|it(" --include="*.py" --include="*.ts" --include="*.rs" --include="*.js" | wc -l` returns **28** — but 11 of those are `it(` or `test(` references in non-test files (e.g. `import { test } from 'node:test'` in the test file itself, plus docstring uses in `README.md` if you count Markdown — though Markdown is excluded by the `--include` filters above). The 17 figure is the actual test count.

README does **not** make a numeric test claim, so there's no "claimed 100, only 30" headline. The implicit promise is "production RAG" though, and 17 unit tests covering only `MemoryVectorStore` + 4 chunkers + cosine/MMR + context builder + 5 evaluators + the pipeline orchestrator — while 17 provider adapters and 4 cloud-store adapters have no test — is a thin safety net.

**Test execution result:** `npx tsx --test test/rag.test.ts` → `# tests 17 / # pass 17 / # fail 0 / duration_ms 1060.7`. No `node_modules` needed for the test step; `tsx` is globally available.

---

## Top 2-3 1-day adds

### 1. Fix the broken example and add a `ZaiEmbedder` (~2 hours)

**File:** `src/cells/embedder.ts` (add class) + `examples/basic-qa.ts` (verify)

The README and the example both reference `ZaiEmbedder` (z.ai / GLM embeddings). Either:
- Add a `ZaiEmbedder` class that hits `https://api.z.ai/api/paas/v4/embeddings` (z.ai's actual endpoint — check the API doc, but pattern is identical to `OpenAIEmbedder`), then `ZAI_API_KEY=... npx tsx examples/basic-qa.ts` actually runs end-to-end. This is the missing piece in the README's "zai + glm-4.5" path.
- Or delete the `ZaiEmbedder` import in `examples/basic-qa.ts:26,28` and only support OpenAI.

Either way, **a one-day tasker can run the example from the README**, which is currently impossible. The OpenAI path is also broken in practice (the example would `TypeError: ZaiEmbedder is not a constructor` before even calling OpenAI).

### 2. Fix the 49 `tsc` errors (~1 day, mostly trivial)

**Files:** `src/cells/embedder.ts`, `src/cells/generator.ts`, `src/cells/retriever.ts`, `src/cells/vector-store.ts`, `src/index.ts`

Most are 1-line fixes:
- `embedder.ts:38` — use a regular field assignment, not `readonly model = this.modelName`.
- `generator.ts:40,58` and `index.ts:124` — change return type or use `if (tokensUsed !== undefined)` to satisfy `exactOptionalPropertyTypes`.
- `retriever.ts:13,26,62` — `const [vec] = ...; if (!vec) throw ...` or use `vec!`.
- `vector-store.ts:25,30` and `retriever.ts:82` — only set `metadata` if defined, don't pass `undefined`.
- `index.ts:73-78` — `Required<PipelineConfig>` should not require the optional cells; refactor to a "validated after ingest" pattern or check at call sites.

This would unstick `npm run build` and make the `[![typescript](https://img.shields.io/badge/TypeScript-strict-blue.svg)]` badge honest. CI is currently red on master; this fixes it.

### 3. Actually fix MMR + add 5–8 provider integration tests (~1 day)

**Files:** `src/cells/retriever.ts:18-50` (MMR math) + new `test/embedders.test.ts` with mocked `fetch`

The MMR fix: store the original `vector` on the `RetrievalResult` (it's already on `Embedding` in the store, just pass it through `query()`), then compute true cosine-to-already-selected instead of using `s.score` as a proxy. The `VectorStore` interface needs a 1-line update to include `vector` in `RetrievalResult`, or add an `originalVector` field. Without this, `MmrRetriever` is a placebo.

Then add tests that mock `globalThis.fetch` for `OpenAIEmbedder`, `CohereReranker`, `BgeReranker`, `LocalOnnxEmbedder`, `ZaiGenerator`. 5 tests, ~150 lines, would raise coverage from "memory store only" to "memory store + 5 provider call shapes." This catches the day an API breaks.

---

## The cowboy's take

**Pattern match:** This is the *third* Quilt repo I've audited that follows the same template — 8–9 cell kinds, N providers, strict TS, Apache-2.0, single test file with `node:test`, the splash.png from the most recent commit. The Quilt factory is consistent. The factory is *also* consistently a step behind: a real working in-memory path + a bunch of `fetch` adapters that look real but are never tested + a `tsc --noEmit` that explodes + a README that oversells what the code actually does.

**What this repo is:** A reasonable first-pass RAG library with a clean cell interface, working cosine + BM25 retrieval, working heuristic evaluators, and a pipeline orchestrator you can actually call. The 17 tests passing without `node_modules` is a real achievement — no broken-import-on-fresh-clone issues in the test path.

**What this repo isn't:** "Production RAG" as the README claims. The `tsc` errors mean `npm run build` is red on master. The example doesn't run. The MMR retriever is a no-op with a comment. The 5 embedders and 3 rerankers and 4 cloud vector stores are HTTP-shaped placeholders that would fail in interesting ways the day someone tries them with real keys. The 17 tests exercise maybe 30% of the public API surface, and 0% of anything network-facing.

**Foreman signal:** If the foreman is grading Quilt repos for "production-ready vs. demo-ware," this one is **demo-ware that wants to be production.** The 1-day adds above are tractable and the bones are good. But the foreman should not trust the README's "ready for production" framing until `tsc` is clean, the example runs, and the providers are at least call-shape tested. The fact that the most recent commit is `feat: add splash image for repo branding` instead of `fix: 49 tsc errors` suggests the author shipped the aesthetic before the substance.
