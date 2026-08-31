# TIT — THE HIGH-PERFORMANCE ENGINE

*The scalability spec the functional prototype grows into. Perf lane
(TIT-PERF), Casey's directive 2026-08-27: "think of higher-performance
methods for TIT for quilt. we know the underlying math. we can make this
innately scalable."*

**Innate** is the operative word. Nothing in this document bolts a cache
onto the side of tit-quilt or threads a lock through it. Every mechanism
below is the *direct hardware realization of a law the prototype already
enforces*: witness arithmetic (W13), the purity boundary (EFFECT), the
provenance integrity law (nothing witness-referenced is ever destroyed).
The graph's invariants ARE the performance model. We are not optimizing
TIT; we are noticing what TIT's math already buys us at scale.

Grounding (verified fleet math, 2026-08-27):

- **W13 witness-trit arithmetic** (experiment-wheel/W13 + ai-writings
  reverse-actualization/08c): L1 `w(a⊕b) = w(a) ∪ w(b)` — provenance unions
  through arithmetic. 1M-round L1 check (Python) and 10M-round native check
  (x86-64), zero violations; ESP32 cross-chip ports compile clean.
- **Consensus fringes** (W13 cross-chip Monte Carlo, 200,000 trials):
  7 independent witnesses at 15% noise → **0.9989** consensus correctness
  vs **0.9004** single-witness baseline.
- **Prototype baseline** (tit-quilt v0.1.0, this repo): session-as-graph,
  cell_ref chaining, topological TICK wavefront with witness-match skip,
  hot→cold→tombstone retention, one store / two front doors.

## Contents

1. Witness-keyed memoization — the tick costs what the change costs
2. Content-addressed cells — duplicate work is structurally impossible
3. Dataflow parallelism — the wavefront is a DAG scheduler
4. Retention as cache hierarchy — eviction that never invalidates
5. Batched evaluation — consensus fringes as a throughput primitive
6. The scaling law, stated — with the worked example
7. Build roadmap — P0 → P3, functional-first

## 1. Witness-keyed memoization — the tick costs what the change costs

### 1.1 The witness as a machine word

The prototype stores a cell's witness as `frozenset{(cell_id, version)}`.
The engine's first representation change: **the witness set becomes a
bitset of `uint32` words** — the W13 word geometry, straight off the chip.

- The engine maintains a *witness index*: a monotonically-growing table
  mapping `(cell_id, version) → bit index`. Each `uint32` word of a
  cell's witness covers 32 upstream identities (W13's 32-cell word; the
  engine simply chains words when a closure exceeds 32 refs).
- **L1 in silicon**: witness union — the heart of every evaluation — is
  bitwise OR: `w_out = w_a | w_b | …`, one instruction per word, 32
  upstreams per instruction. The 10M-round verified law is not simulated;
  it is *executed* by the ALU.
- **Change detection** is XOR against the previously-recorded witness:
  zero ⇒ inputs unchanged, `popcount` ⇒ how many changed. One instruction
  per word to know a cell is clean.

### 1.2 The memo key

```
key = ( kind, fn_id, fn_version,
        H(literals),                 -- canonical bytes of literal args
        H(witness words) )           -- the L1-unioned input witness bitmask
  →  { output_hash, value_ref, epoch, hit_count }
```

Semantics: *if the function is the same (versioned), the literals are the
same, and every input is the same version it was last time, then the
output is the same.* That implication is valid **because of the purity
boundary** — FUNCTION cells cannot touch the world (world-touch is
EFFECT-only), so output is a mathematical function of `(fn, literals,
inputs)`. The memo table is not a heuristic cache that can go stale; it is
as sound as arithmetic. L1 guarantees the witness bitmask is a *sound*
summary of what influenced the output (it unions — it never loses an
upstream).

Note the key hashes the canonical witness *words* — order-independent by
construction (a bitset has no order), so two derivations reached by
different call paths but fed identical `(cell@version)` inputs produce the
same key. That property is what makes cross-session and cross-tick hits
possible, not just within-pipeline hits.

### 1.3 The receipt IS the key

The MCP tool returns `{value, cell_ref, witness[]}` — a *receipt*. In the
engine, the receipt is the memo entry re-expressed for the wire: the
`witness[]` strings are the bit indices resolved back to `cell@version`
form for human/agent legibility, and `cell_ref` points at the
content-addressed cell (§2). Consequences:

- **`tit pipe --last` is a memoization hit.** Replay with unchanged edges
  = every step's key reconstructs = every step returns its cached receipt;
  only edges whose witness XOR'd non-zero re-fire. The prototype's
  "witness already matches ⇒ skip" rule is memoization with the table
  inlined into the cell record; the engine simply externalizes it so hits
  work *across ticks, sessions, and processes*.
- **The dirty-closure walk is the miss path.** Tick cost = O(witness
  compare) for clean cells + O(evaluate) for the dirty closure. With the
  reverse-dependency index (prototype: "seed set = dirty ∪ downstream
  closure"), clean cells outside the closure are never even visited:
  **per-tick cost O(|changed closure|), not O(|graph|)**.

### 1.4 Cost model

| Operation | Cost | Order |
|---|---|---|
| Witness compare (32 upstreams) | XOR + test, ~2 ns | O(k/32) |
| Memo hit (hash lookup + entry) | ~50–100 ns | O(1) |
| Full re-evaluation (pure tool) | ~10–100 µs | O(payload) |

Hit-to-miss cost ratio ≈ **500–1000×**. A pipeline that is 99% unchanged
runs at ~1/500th the cost of naive re-evaluation. Memo table memory: ~64
bytes/entry; 1M derivations ≈ 64 MB — bounded by LRU on heat, and entries
whose witnesses are fully tombstoned remain *valid* (hash equality needs
no value), so eviction of the underlying values never invalidates entries
(§4).

---

## 2. Content-addressed cells — duplicate work is structurally impossible

### 2.1 The address

```
addr(cell) = H( kind ‖ fn_id ‖ fn_version ‖ H(literals)
                ‖ sort([ addr_or_ref(input_i) ]) )
```

Inputs enter the address as `cell@version` identity refs (or their content
addresses), sorted for canonical order. Two properties fall out:

1. **Identical derivations are identical objects.** Same function, same
   version, same literals, same upstream versions → same address,
   anywhere in the store, in any session, computed by anyone. The store is
   an intern table: creating a cell whose address exists is a no-op that
   returns the existing object. *Duplicate work is not detected and
   skipped — it is structurally unrepresentable.* Two agents in two tmux
   panes deriving `sha256("hello")` write one cell and read it twice.
2. **Provenance is part of identity.** Because inputs enter as
   `cell@version`, two cells with byte-identical values but different
   upstream histories have different addresses — the witness chain is
   *inside* the name. This is W13 L2 promoted to addressing: a value is a
   claim, a value-with-witness is a fact, and facts with different
   witnesses are different facts. (Interning still happens for truly
   identical provenance, which is exactly when sharing is sound.)

### 2.2 MerkleMesh — many journals, one root

The store's persistence layout becomes a Merkle dag:

- Each session's journal (`journal.jsonl`) is an append-only list of cell
  addresses and their payloads.
- The store root = Merkle root over all journals. Many journals, one root
  — the MerkleMesh doctrine. Sync between hosts, backup verification, and
  compaction audit are all *recompute the root and compare*: O(changed
  leaves) with Merkle inclusion proofs, O(0) trust in the transport.
- Delta sync = exchanging subtrees the peer's root hash proves it lacks.
  Content addressing makes every cell a natural content-defined chunk.

### 2.3 What this buys at scale

| Property | Mechanism | Scaling behavior |
|---|---|---|
| Dedup | intern by address | work ∝ *distinct* derivations, not calls |
| Verification | Merkle root | audit cost ∝ changed leaves |
| Sync | subtree exchange | bandwidth ∝ delta, not store size |
| History | append-only journal | identical replays are free (memo + address) |

The memo table (§1) and the intern table (§2) are two views of the same
fact: *pure derivations are values*. §1 keys them by witness for fast
lookup; §2 names them by content for permanent identity.

---

## 3. Dataflow parallelism — the wavefront is a DAG scheduler

### 3.1 Kahn levels are parallel layers

The TICK evaluator already computes a Kahn topological order. The engine
reads the same computation as a **level structure**: layer *L* = all cells
whose longest upstream path is *L*. Within a layer, no cell can depend on
another — they are mutually data-independent by construction of
topological order. The wavefront is therefore a fork-join DAG schedule:

```
for each level L of the dirty closure:
    fork:  every cell in L evaluates in parallel (pure, no locks)
    join:  publish outputs, compute next layer's witness words
join-all:
    EFFECT queue commits in topological order (§3.3)
```

### 3.2 Zero locks: immutability + content addressing

- **Cells are immutable once evaluated.** A cell's content address and
  payload are written exactly once (publish-once semantics); subsequent
  readers either see it or don't — there is no in-place mutation to race.
  New versions are new objects (address includes version).
- **The memo/intern table is sharded** by hash prefix (e.g. 64 shards).
  A shard is only contended when two workers derive the *same* key — in
  which case one wins, the other's lookup converts to a hit. Contention
  is self-extinguishing: it only occurs on duplicate work, which §2
  exists to eliminate.
- **Work stealing over levels**: per-worker deques (Chase–Lev), steal
  from the victim's tail. Level tags give stealing a priority order —
  shallower levels first — so the schedule stays near the critical path.

**`titd`, the resident daemon**: N−1 evaluation workers + 1 coordinator.
The prototype's "one store, two front doors" becomes "one daemon, two
front doors" — CLI and MCP both speak to `titd` over a local socket;
the daemon holds the hot tier (§4) and runs wavefronts continuously.
Scaling to cores is by construction: the schedule *is* the dataflow graph.

The GIL is a prototype-lane problem, not an architecture problem (§7):
the same scheduler runs as (a) process pool over content-addressed shards
— inputs/outputs are hashes, natural IPC — or (b) a compiled core with
identical laws.

### 3.3 EFFECTs are the only serialization points

Everything inside the wavefront is pure — no world state, no ordering
requirements beyond data availability. EFFECT cells (file writes,
clipboard, cron registration) are the only world-touch. Discipline:

- EFFECT cells **never evaluate in parallel with anything**. They are
  collected during the wavefront into a queue and committed at the final
  join, **in topological order** — deterministic, replayable, and
  serialized exactly where serialization is semantically required.
- Purity is what makes §1 and §2 sound; the EFFECT boundary is what makes
  purity *provable* rather than hoped-for. The three sections are one
  mechanism: boundary → memoizable → parallelizable.

### 3.4 The scheduling bound (Brent's theorem)

T_P ≤ T₁/P + T_∞ — wall time bounded by work/processors plus the critical
path. Tool pipelines are wide and shallow by nature (fan-out: one
payload decoded, hashed, formatted, sliced; each output feeding many
consumers). Worked bound: a 10,000-cell closure with average wavefront
width 250 and critical path 40 levels on 8 workers gives
T_P ≤ 10000/8 + 40 = 1290 units vs 10,040 serial — **7.8× on 8 cores**,
with the residue being the irreducible critical path, not lock overhead.

---

## 4. Retention as cache hierarchy — eviction that never invalidates

### 4.1 The mapping is exact, not metaphorical

| Hardware hierarchy | TIT tier | Contents | Latency class |
|---|---|---|---|
| registers / L1 | hot, in-wavefront | full value + witness, pinned for the tick | ns — in-process |
| L2/L3 / RAM | hot, resident in `titd` | full value + witness | ns — in-process |
| disk | cold (`journal.jsonl`, `.cold.json`) | structure, no value | µs–ms — deserialize/derive |
| archival / off-site | tombstone (`.tombstones.json`) | hash + witness chain only | recompute or fetch by hash |

Demotion **is** eviction. The mapping is the memory hierarchy — the only
question a real cache asks is the one the provenance integrity law already
answers: *when is it safe to evict a line?*

### 4.2 The law as the coherence invariant

A hardware cache may not evict a line another live line references (it
must write it back). The TIT analogue, stated once as doctrine and
enforced structurally:

> **A value may be demoted only if no live cell's evaluation requires it;
> and demotion never destroys what a witness references — the hash chain
> survives every tier.**

- **hot → cold**: allowed iff the cell is outside the current wavefront's
  closure and no scheduled evaluation needs its value. FUNCTION cells in
  cold are re-derived on demand — the derivation is a pure function of
  the graph, so *the graph is its own backing store*. This is stronger
  than hardware: evicting a cold value loses no data at all, only
  recompute latency.
- **cold → tombstone**: only by explicit `FORGET`. The tombstone keeps
  `{cell_id, kind, version, value_hash, witness, fn, inputs, literals}`
  — identity and provenance without payload.
- **tombstone → nothing**: no code path exists. Append-only, never
  compacted away. (Compaction may *merge* journals; the Merkle root over
  tombstone hashes preserves the audit.)

### 4.3 Memo entries survive eviction (the payoff)

Because the memo key (§1) and the tombstone agree on `value_hash`, a memo
  hit on a fully-tombstoned witness needs **no value at all** — hash
equality certifies the output. The cache hierarchy therefore never
invalidates a live line: downstream receipts remain checkable when their
upstreams are cold or tombstoned; they become *recomputable* when needed,
in topological order, from the graph itself. `tit witness.trace` resolves
through tombstones today; in the engine the same property means **provenance
queries are O(path length), independent of how much data was evicted.**

---

## 5. Batched evaluation — consensus fringes as a throughput primitive

### 5.1 The verified number

W13 cross-chip Monte Carlo, 200,000 trials: 7 independent witnesses at 15%
per-witness noise reach **0.9989** consensus correctness against a **0.9004**
single-witness baseline. Independent attestations of the same claim
correct each other exponentially — that is a *replication theorem*, and it
applies twice in the engine:

### 5.2 Throughput batching (SIMD tool families)

Within a wavefront layer (§3), group cells by `(fn_id, fn_version)`. The
atomic tier is deliberately homogeneous — base64 encode/decode, the SHA
family, JSON format/parse, url codec — and homogeneous string kernels
vectorize: multi-buffer SHA-256, table-driven base64 over strided input
lanes, per-item parallel JSON parse.

- **Witness bookkeeping vectorizes with the work**: the L1 union across a
  batch is the bitwise OR of a k×w witness-word matrix — the same
  one-instruction-per-word op, amortized across the batch width.
- Throughput scales with batch width until memory-bandwidth-bound; for the
  hash/codec families the compute:byte ratio is high enough that width 16–32
  reaches near-linear scaling on AVX2/AVX-512-class hardware.

### 5.3 Verification fringes (shared errors cancel)

When trusting cached receipts (memo hits) or receipts replicated across
hosts (MerkleMesh sync), verify by **fringe sampling**: draw k independent
derivations of the same content and require agreement. k=7 at 15%
per-copy corruption ⇒ 0.9989 — the Monte Carlo number, applied as a
*verification budget*: 7× work buys two nines over single-check.
Structurally identical cells cross-check each other for free when batched
(§5.2): two derivations of the same address that diverge are a
nondeterminism detector — **shared errors cancel; divergent errors are
caught by the fringe.** k is a dial: k=1 for trusted local memory,
k=7 for untrusted replication.

### 5.4 When to batch / when not to

**Batch when:** same `(fn_id, fn_version)`; pure (always true inside the
wavefront); batch width ≥ 8 (below that, grouping overhead exceeds SIMD
gain); inputs share witness structure — overlapping witness words mean
shared memo prefixes and shared upstream reads, so the batch reuses
memory traffic as well as instructions.

**Do not batch:** EFFECT cells — never batched, never parallel, they exist
to serialize (§3.3). Heterogeneous functions (grouping is pure overhead).
Giant divergent payloads where the win is bandwidth-bound anyway (batching
adds working-set pressure). Anything order-sensitive — which, by the
purity law, cannot exist inside the wavefront in the first place; the
prohibition is enforced by construction, not by discipline.

---

## 6. The scaling law, stated

> **Per-tick cost is proportional to the changed set, not the graph size.**
> T_tick = β·|dirty closure of Δ| + α·|witness checks|, with Δ = changed
> inputs, α ≪ β (≈500–1000×), and — with the reverse-dependency index —
> the second term vanishes: **T_tick = O(|closure(Δ)|)**. A tick costs
> what the change costs. Nothing else.

Every mechanism above is this law wearing a different hat: §1 makes it
true across ticks, §2 makes it true across sessions and hosts, §3 divides
the numerator by cores, §4 keeps the constant α tiny at any store size,
§5 divides β by the batch width.

### 6.1 Worked example

Two pipelines, same change: **3 inputs re-bound.** β = 25 µs/evaluation,
α = 0.05 µs/witness-check.

| | 10,000-tool pipeline | 5-tool pipeline |
|---|---|---|
| Changed inputs (Δ) | 3 | 3 |
| Dirty closure | 17 cells | 2 cells |
| Evaluations (β·E) | 20 × 25 µs = 500 µs | 5 × 25 µs = 125 µs |
| Witness checks (α·H) | 9,980 × 0.05 µs ≈ 0.5 ms | 0 |
| Reverse-index walk | closure only: 20 × 25 µs = **0.5 ms** | 5 × 25 µs = **0.125 ms** |
| Naive full re-eval | 10,000 × 25 µs = **250 ms** | 125 µs |
| Speedup vs naive | witness-check path **250×**; reverse-index path **500×** | 1× (already all-dirty) |

The 10,000-tool pipeline with 3 changed inputs lands within **4–8×** of
the 5-tool pipeline with the same change (0.5–1.0 ms vs 0.125 ms) despite
being 2,000× larger — while naive re-evaluation pays 250 ms for the
privilege of recomputing 9,980 identical derivations. The 10k pipeline is
*not slower because it is big*; it is slower only by the size of the
*change*. And with §3, even the
closure term divides by cores: the 20-cell closure on 8 workers is
critical-path-bound (~4 levels × 25 µs ≈ 100 µs).

That is what "innately scalable" means: the architecture's cost function
does not contain the graph size as a term.

---

## 7. Build roadmap — P0 → P3, functional-first

The prototype (v0.1.0) is deliberately functional-first: single-threaded,
stdlib-only, file-persisted, one store with lock discipline. That is not
debt — it is the correct order. **Every performance phase below is enabled
by an invariant the prototype already enforces**; the engine is a growth
path along existing laws, not a rewrite.

| Phase | Ships | Prototype seed already present | Effort |
|---|---|---|---|
| **P0** witness-memo | witness words as uint32 bitsets; external memo table keyed `(kind, fn, fn_ver, H(lit), H(witness))`; receipt = entry; reverse-dep index on cell links | witness-match skip in TICK; `pipe --last` incremental replay | small — bookkeeping + a dict |
| **P1** content-address | canonical serialization; `addr = H(kind, fn, ver, H(lit), sorted inputs)`; intern table; `journal.jsonl` cold tier; Merkle root over journals (MerkleMesh) | append-only tombstones with `value_hash` + witness; `cell@version` refs | medium — serialization is the work |
| **P2** parallelism | `titd` daemon; Kahn-level DAG scheduler; work stealing; sharded memo; EFFECT queue as the single join | topological wavefront + EFFECT-at-end-of-wavefront discipline | large — daemon lifecycle, IPC doors |
| **P3** batching | fn-grouped vector kernels (base64/SHA/JSON/url families); witness-matrix OR; fringe verification (k=7 ⇒ 0.9989) for replicated/cached receipts | homogeneous atomic tool tier | medium — kernels are independent |

Dependencies: P0 ⊥ P1 (compose anywhere); P2 wants P1's publish-once
immutability to be lock-free honestly; P3 wants P2's layer grouping to
have batches to fill. Honest note: the prototype stays the reference
semantics — the engine must reproduce its observable behavior law-for-law
(witness trace, forget semantics, cron catch-up), verified by running both
against the same session corpora and comparing Merkle roots.

---

*Spec: TIT-PERF lane, 2026-08-27. Math grounded in experiment-wheel/W13
(1M + 10M round L1 verification; 200k-trial consensus fringes,
cross-chip) and ai-writings reverse-actualization/08c. Prototype baseline:
tit-quilt v0.1.0 (this repo, DESIGN.md).*
