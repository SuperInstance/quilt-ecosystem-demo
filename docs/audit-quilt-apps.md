# Audit: 7 Quilt Apps Added in the Last 2 Weeks

**Date:** 2026-08-28 · **Repos:** github.com/SuperInstance/{quilt-ai, quilt-rag, quilt-fleet, quilt-mesh, quilt-vault, quilt-pincher, quilt-elf} · **All created 2026-08-19 → 2026-08-20**

---

## 1. Per-app verdict

| App | What it does | Uses from Quilt | Lang | LoC* | Tests | License | Prod-ready? |
|---|---|---|---|---|---|---|---|
| **quilt-ai** | 4 LLM providers (z.ai, Kimi, DeepSeek, Cloudflare) × 8 cell kinds (llm/embed/image/translate/sentiment/summarize/code/vision) | `@quilt/core`, `@quilt/evolve` | TS | ~700 | 6 unit | MIT | **Yes** — clean API, cost tracking, secret handling, 6 YAML examples |
| **quilt-rag** | Full RAG pipeline as 8 cells (loader→chunker→embedder→store→retriever→reranker→context→generator) + 4 evaluators | `@quilt/core`, `@quilt/sdk`, `@quilt/ai` | TS | ~500 | 1 file (8.6k) | Apache-2.0 | **Yes** — 5 vector stores, 5 embedders, 3 rerankers, real test file |
| **quilt-fleet** | Multi-tier federation orchestrator: discovery, health, quorum, migration, auto-scaling across 5 tiers (esp32/jetson/codespace/cf/server) | `@quilt/core`, `@quilt/sdk` (peer) | TS | ~1500 | **13 files** | Apache-2.0 | **Yes (most mature)** — 6 doc files, REST/gRPC/GraphQL, vitest, 4 transports |
| **quilt-mesh** | Broker-less CRDT mesh: Lamport clocks, per-peer version vectors, offline-first gossip | standalone (no `@quilt/*` dep) | Rust | 250 | "3/3" (no files) | MIT | **No** — author calls it "a design sketch" + commented-out deps in Cargo.toml |
| **quilt-vault** | E2E encryption primitive: ECDH P-256 + AES-GCM, per-cell ACL, multi-viewer key wrapping | standalone (no `@quilt/*` dep) | JS | 280 | 1 file (5.8k) | MIT | **Partial** — real WebCrypto, no libsodium/X25519 yet (per its own comment) |
| **quilt-pincher** | Reflex engine (pinch→match→veto) on three tiers, LLM as compiler, content-addressed artifact store | `@quilt/core`, `@quilt/sdk`, `@quilt/ai` | TS | ~270 | 1 file (7.7k) | Apache-2.0 | **Yes** — full engine.ts (8.2k), ESP32 port doc, cloud/workstation/esp32 platforms |
| **quilt-elf** | Cloudflare Workers cron-job: daily-limit-aware, throttles when user busy, dispatches across the same 4 LLM providers as quilt-ai | `@quilt/core`, `@quilt/ai` | TS | ~700 | 2 files (14k) | Apache-2.0 | **Yes** — real `wrangler.toml`, cron triggers, KV + Durable Object binding |

\* LoC = source-line estimate from the tree (not vendor code).

---

## 2. The 3 most useful (most overlap with current canon, easiest to build on)

| App | Why it slots in cleanly |
|---|---|
| **quilt-fleet** | The orchestrator all the others will need. Already a `@quilt/core` peer; URIs (`quilt://[instance]/[sheet]#[cell]`) are exactly the right abstraction. 13 test files + 6 docs = lowest risk to adopt. The REST/gRPC/GraphQL triple gives us flexibility. **Use first.** |
| **quilt-ai** | The de-facto LLM adapter. If we're already calling LLMs, we should be calling them through `AIEngine.call()` — we get cost tracking, memoization, 4-provider failover, and a uniform `ai.llm/ai.embed/...` cell vocabulary. The cost-control router pattern is gold for a budget-aware demo. |
| **quilt-rag** | The other half of "LLM + your data". It already imports `@quilt/ai` for its generator, so combining the two is one line. 5 vector stores (incl. Cloudflare Vectorize — matches the edge-first story) means we can demo it on a Worker without spinning up a server. |

---

## 3. The 3 that need more work

| App | What's missing |
|---|---|
| **quilt-mesh** | Still a *protocol sketch*. Cargo.toml has the real deps (`serde`, `tokio`) **commented out**; the source file says "a real impl would use a more efficient structure". No actual networking, no `gossip_with` impl beyond a signature, no test files (badge says "3/3" but the tree shows zero `tests/`). The live demo in the README uses browser `BroadcastChannel`, not the Rust crate. **Don't depend on this until the deps are uncommented and a `cargo test` passes.** |
| **quilt-vault** | The README is gorgeous and the WebCrypto code looks correct, but: (a) no `@quilt/*` import — it's a standalone lib that *describes* how it would attach to cells but doesn't; (b) it self-declares that production should use libsodium/X25519/Argon2id instead of `node:crypto.webcrypto`; (c) `main: "src/index.js"` points at raw source, not a build artifact; (d) zero TypeScript. **Good prototype, not yet a cell.** |
| **quilt-elf** | Strongest of the three "need work", but: 31k lines of source crammed into a single `src/index.ts` (no internal modules), 2 test files of unclear scope, hard-codes the same 4 providers as quilt-ai (no shared `AIEngine` import path — it constructs its own minimal provider map), `package.json` has no `build` script, no Wrangler deploy verified. **Split src/index.ts, reuse quilt-ai, ship a deploy.md.** |

---

## 4. Cross-canon opportunities

| Combination | What it becomes | Effort |
|---|---|---|
| **quilt-elf (Cloudflare) ⊗ quilt-ai (4 providers)** | The elf already duplicates the provider map. Refactor: import `AIEngine` from `@quilt/ai`, expose the same 4 keys via Wrangler secrets, and elf becomes a pure *scheduler* sitting on top of the AIEngine. The budget-aware "spend free tokens before reset" logic then *automatically* benefits from cost tracking and memoization — no duplication. | 1 day. **Do this first.** |
| **quilt-pincher ⊗ quilt-fleet** | A federated reflex engine. Pincher has the three-tier runtime (cloud/workstation/esp32) but each instance is a silo. Fleet gives us the discovery + health + quorum layer to *synchronize* reflex databases across the three tiers. The pincher README even calls this out ("the reflex database on your laptop can mirror the one on the cloud") but the glue isn't there. A `FleetReflexStore` cell that publishes `set reflex.*` updates to the fleet would be the missing link. | 1 week. |
| **quilt-rag ⊗ quilt-ai** | Already wired (`@quilt/ai` is a dep of `@quilt/rag`). The unused win: the rag `evaluator` cell kind can score *other* generators, not just rag outputs — turn it into a general-purpose LLM grader. | 2 days. |
| **quilt-vault ⊗ any cell store** | vault has no `@quilt/*` import. Add a `vault.encrypted` cell kind to `@quilt/core` so that `vector_store`, `loader`, and `cache` cells can all be wrapped transparently. | 1 week (but the highest-leverage privacy primitive in the whole stack). |
| **quilt-mesh ⊗ quilt-fleet** | Mesh is the P2P sync layer Fleet lacks. Fleet today uses MQTT/NATS/WS — all brokered. Mesh's broker-less CRDT gossip could be Fleet's *fourth* transport. But mesh needs to be uncommented first. | Blocked on mesh. |

---

## 5. The 2 highest-leverage additions

| # | Addition | Why |
|---|---|---|
| **1** | **`@quilt/ai` as the single LLM boundary.** Refactor quilt-elf, quilt-rag's generator, and the demo to all consume `AIEngine` instead of building their own provider maps. Add a `CellKind: 'ai.budget'` cell that reads `engine.getCost()` and gates downstream cells. This one change converts 3 duplicated provider tables into one. | Highest leverage because it touches every AI-touching app and gives us centralized cost/quota/retry behavior. |
| **2** | **`@quilt/cell-store` interface + `quilt-vault` adapter.** Define a single `CellStore` port (`get/set/watch/subscribe/list`) with three impls: `MemoryCellStore`, `R2CellStore` (for the edge), `VaultCellStore` (E2EE). Today every app rolls its own. The moment a common port exists, *every* app (rag, pincher, elf, fleet's quorum) gets encryption, federation, and observability for free — without touching their code, just swapping the store. | The right abstraction to make 7 apps compose into a real product. Also unlocks point 4 (vault ⊗ cell store) without a Quilt core change. |

**Honourable mention:** add a `quilt-mesh` task to the team plan to uncomment the deps and write a `cargo test` that passes across 2 processes — once that lands it becomes the most interesting differentiator in the whole stack (offline-first, no-broker federation).

---

*Total: 5 sections, 7 apps audited, 4 cross-opportunities surfaced, 2 concrete next actions. Under 1500 words.*
