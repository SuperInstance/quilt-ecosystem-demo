# Quilt Canon — Cutting-Edge Audit

**Date:** 2026-08-31 · **Scout:** API scout for the cowboy
**Scope:** last 6 months of arXiv (cs.PL/cs.DC/cs.MA + adjacent), GitHub trending/topics, SuperInstance's 100 most recent pushes, plus venue pages.
**Token budget:** < 1500 words. Tables > prose.

---

## 1. Top 3 arXiv papers (last 6 months)

| # | arXiv ID | Date | Title | Why Quilt cares |
|---|----------|------|-------|-----------------|
| 1 | **2608.14019** | 2026-08-14 | **Emergent Models: Intelligence from Tiny Substrates** (cs.NE) | 2-D continuous-valued **lattice** as latent state; local-recursive computation at hundreds of parameters extrapolates arithmetic and supports online adaptation. Validates Quilt's "the substrate IS the program" thesis — intelligence is a property of a cellular lattice, not of a giant transformer. |
| 2 | **2608.13574** | 2026-08-17 | **Agentao: A Governed Local-First Runtime for Tool-Using LLM Agents** (cs.AI) | Separates model proposals from host-authorized execution via a **permission-mediated tool system**, **memory/replay** subsystem, **protocol boundaries** (MCP, A2A), and a **structured event interface**. This is the academic version of what Quilt's `cudaclaw` + `BIND/EFFECT` were reaching for: capability-mediated effects outside the model. |
| 3 | **2608.23740** | 2026-08-24 | **AgentRoom: Concurrent Multi-Agent Coding in a CRDT-Backed Shared Workspace** (cs.AI) | N agents on one op-based sequence CRDT (Yjs/`pycrdt`) with **file-level claim, status, broadcast as MCP tools**. Proves CRDT-as-cell-substrate works for live multi-agent coordination. Useful as a worked example + as a competitor. |

**Runners-up worth filing:** `2608.11657` Semantic Lenia (cellular automata in LLM logit space — "Autonomous Semantic Solitons"), `2608.13030` InterSAGE (capability-aware trust substrate for the Internet of Agents, DIDs + capability attenuation), `2608.15888` Bounded Agents / APC (Agentic Principal Chain — formally proves Blast Radius Monotonicity), `2608.15008` Harness the Memory (empirical: no single memory substrate dominates, you need **substrate routing**).

---

## 2. Top 3 thematically-adjacent GitHub repos

| # | Repo | ★ | Why Quilt cares |
|---|------|---|-----------------|
| 1 | **astrid-runtime/astrid** | 10,274 | **"A portable, capability-secure operating system for composable software."** Wasmtime-sandboxed capsules, ed25519 capability grants, signed hash-linked audit chain, dumb kernel, per-principal namespaces, MCP-compatible. Pushed **2026-08-31**. This is the closest existing public system to Quilt's cellular capability model. Treat as primary benchmark + threat model. |
| 2 | **electric-sql/electric** | 10,346 | Tagline: **"The agent platform built on sync."** Postgres-native + CRDTs + agents. Validates the bet that **sync IS the substrate** for agent platforms — same bet Quilt makes with cells as the sync unit. |
| 3 | **loro-dev/loro** | 6,095 | A new, very active CRDT (Rust) for collaborative/versioned JSON. Pushed 2026-08-29. Cleaner performance than Yjs for tree-shaped data — relevant if Quilt's cell graph ever needs cross-replica merge. |

**Runners-up:** `pubkey/rxdb` (23,371★ — local-first DB with CRDT replication, the de-facto browser substrate), `yjs/yjs` (22,724★ — still the CRDT reference implementation), `orbitdb/orbitdb` (8,798★ — P2P databases on IPFS/libp2p, merkle-CRDTs).

### From the cowboy's own pile (SuperInstance, top 10 fresh non-fork)

Already canon, not duplicating in canon table: `quilt-llvm`, `quilt-rust`, `quilt-verilog`, `quilt-cuda`, `quilt-esp32`, `quilt-edge-arch`, `quilt-cellular-arch`, `quilt-mhs`, `quilt-scratch`, `SmartCRDT`. **External canon (must cite):** `astrid`, `electric-sql/electric`, `loro-dev/loro`.

---

## 3. Where the field is going — synthesis

> **Three convergence lines** are collapsing into one stack. **First**, agent safety is moving from "trust the prompt" to **runtime contracts**: capability-mediated effects, ed25519 grants, signed audit chains, and formal blast-radius proofs (Astrid, Agentao, InterSAGE, Bounded Agents/APC, ClawSentry). **Second**, local-first CRDTs are graduating from "offline edit" toys into **agent coordination substrates** — AgentRoom proves N agents can share a workspace via op-based CRDTs; Electric calls this the agent platform; the field is finally saying out loud what Kleppmann said in 2019: *the device is the primary copy*. **Third**, tiny lattice/CA substrates are being shown to do work thought to require large models — Emergent Models, Semantic Lenia, TextNCA, Neural CA consensus — pushing the field toward *intelligence as a property of a cellular substrate*, not a parameter count. The synthesis: by 2027 the serious stack is **capability-secured cellular substrate + CRDT sync + local-first replication + signed audit + tiny emergent models** — and Quilt is already most of the way there.

---

## 4. The 3 ideas Quilt should adopt

| # | Idea (source) | Design sketch (1 line) |
|---|--------------|-----------------------|
| 1 | **Signed, hash-linked audit chain as a first-class cell type** (Astrid; InterSAGE kernel-mediated audit) | Add a `PROOF` opcode to the 5+1 set that appends a `prev_hash || ed25519_sig || cell_state` triple to an immutable ring per cell; `cudaclaw` and `quilt-llvm` expose it as a primitive. Replaces ad-hoc logging with cryptographic replay. |
| 2 | **Substrate routing for memory (the Harness-the-Memory finding)** — no single memory substrate dominates; long-context QA vs. sequential decision-making want different ones | Add a `ROUTE` effect: a cell declares `memory_substrate ∈ {dense_vec, sparse_idx, text_log, hier_store, param_update}` and a small router cell in the lattice picks per-call; `quilt-llm` cells use it for retrieval vs. scratchpad selection. |
| 3 | **CRDT-backed multi-agent shared workspace as a cell graph, not a file system** (AgentRoom, Electric, Loro) | Promote each Quilt cell's local state to a **state-based CRDT with Lamport timestamps**; `BIND` between cells becomes an op-CRDT merge; the cowboy can fork a fleet of 100 cells, mutate offline, and converge on re-`LINK` — no central coordinator. `SmartCRDT` repo is the seed. |

---

## 5. The 1 idea Quilt should resist

**"Trust the WASM sandbox and Wasmtime for capability enforcement" (Astrid's bet).**

Wasmtime is great, but it locks you to a single execution substrate, a single ABI (WIT), and a single trust root (the host kernel). Quilt's power is the opposite: cells live on **ESP32, CUDA, Verilog, LLVM IR, the browser, Workers/DOs, and Cloudflare Containers** — and the contract is the **5+1 opcode set**, not a particular runtime. Adopting Astrid's "dumb kernel + Wasm capsules" model wholesale would force every edge device, every FPGA, and every GPU kernel into a Wasmtime-shaped hole. The cutting edge is *wrong* here for anyone who isn't a server-side agent platform: **Quilt's bet is that the cellular opcode set IS the kernel**, portable across substrates, with capability checks happening in the opcode semantics (EFFECT) not in a sandbox. Keep the kernel dumb — but make the kernel *the cell graph*, not Wasmtime.

---

## Appendix — sources

- arXiv API: cs.PL + cs.DC + cs.MA (rate-limited 3×; supplemented via web_search with `arxiv.org` site filter for last-6-months)
- GitHub API: `search/repositories` for `cellular|reactive|CRDT`, `capability|lattice|substrate`, topic:crdt, topic:reactive-programming, plus `users/SuperInstance/repos?per_page=100`
- arXiv papers cited: 2608.14019, 2608.13574, 2608.23740, 2608.11657, 2608.13030, 2608.15888, 2608.15008
- GitHub repos profiled: astrid-runtime/astrid, electric-sql/electric, loro-dev/loro, pubkey/rxdb, yjs/yjs, orbitdb/orbitdb
- Venues scanned: cloudflare.com changelog (DO deployments tab 2026-08-20, 10-dynamic-workers 2026-08-28), oxide.computer (Hubris/Propolis stable, no fresh blog post in window), martin.kleppmann.com (local-first book 2026 reprint noted in Polish vendor listing, not direct), anthropic.com/news (MHS already in canon), jepsen.io (no new cutting-edge Jepsen report in window)
- Notable absences: **martin.kleppmann.com** had no new 2026 post in the 6-month window; **jepsen.io** has no new report matching the cellular/CRDT theme; **hytradynamic.com** blog is dormant in this window.
