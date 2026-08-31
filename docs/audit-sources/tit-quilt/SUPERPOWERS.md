# TIT — THE UNIVERSAL COMPUTE FABRIC

*The general-purpose spec. Superpowers lane (TIT-SUPERPOWERS), Casey's
directive 2026-08-27: "Make our quilt version of TIT far more general
purpose. think superpowers."*

The prototype (DESIGN.md) ships a terminal toolbox whose session is a
graph. The performance spec (PERFORMANCE.md) shows the graph's math buys
scale for free. This document is the third leg: **the same laws buy
universality for free.** TIT is not a toolbox of developer utilities. It
is a **metatoolbox** — machinery whose subject matter is *any function,
anywhere*:

> **Any function is a cell. Any composition is a program. Any session is
> a world. Any answer carries receipts.**

Nothing below is a new architecture. Every superpower is a consequence of
four laws the prototype already enforces: (1) the MCP call IS a link,
(2) the purity boundary (EFFECT is the only world-touch), (3) the
provenance integrity law (nothing witness-referenced is ever destroyed),
(4) one graph, many front doors. General-purpose is not a tax the
prototype pays later — it is the payoff the laws already purchased.

## Contents

1. Universal tool import — everything becomes a cell
2. Composition as artifact — pipelines are the unit of software
3. Session-as-world — persistent, addressable, multi-agent graphs
4. Mergeable graphs — CRDT reconciliation across machines
5. Universal routing — providers compete, the graph chooses
6. Witness as trust fabric — receipts on everything, forever
7. Hardware reach — the MHS seam, cells that drive devices
8. The routing law as physics — why general-purpose is free
9. The deep dimensions — recursion, time, trust, scale, meaning,
   embodiment, social, accountability

---

## 1. Universal tool import — everything becomes a cell

### 1.1 The claim

No function is second-class. A tool written for TIT, a tool behind an MCP
server, a tool that is a CLI binary, a tool that is an HTTP endpoint, a
tool that is a Python file on disk — all five become cells in the same
registry, callable by the same verbs (BIND / LINK / TICK), chainable by
the same `cell_ref` pointers, and witnessed by the same receipt protocol.
**Import-as-a-cell is automatic: nothing is written twice, everything
composes.**

### 1.2 The registry protocol

The registry's key insight: **a tool id is an interface, not an
implementation.** The atomic tier's `TOOLS` table already maps
`name → {description, params, required, fn}`. The general form separates
the two halves of that entry:

```
interface   name, param schema, description          — what it means
providers[] native | mcp | http | cli | code         — how to run it
```

- **native** — a Python fn in the process (the prototype's eleven tools).
- **mcp** — a foreign MCP server's tool, wrapped (see §1.3).
- **http** — a fetch provider: `{method, url_template, param_map}`; the
  cell's literals fill the template, the response body is the value.
- **cli** — a subprocess provider: argv template from literals, stdout is
  the value (structured output via a parser fn when the CLI is JSON).
- **code** — an eval/source provider: a file path or inline snippet; the
  module is loaded once, its exported functions register as native.

The registry is an *interface table*; providers are rows in a
*provider table* keyed `(tool_id, provider_kind, endpoint)`. Routing
between providers is §5. Health weighting makes imports honest: a dead
endpoint degrades to the next provider instead of failing the interface.

### 1.3 The MCP-importer (shipped as a stub)

`tit.mcp_import` (see DESIGN.md §8 and `tit_quilt/importers.py`) is the
first concrete instance: given a server command, it performs the MCP
handshake (`initialize` → `tools/list`), translates each foreign tool's
`inputSchema` into the registry's param format, and registers
`<prefix>.<tool>` entries whose provider fn speaks JSON-RPC to the
foreign server. The import *itself* binds a cell — the manifest of what
was imported is a witnessed value in the session graph, so "what tools
existed when this pipeline ran" is a queryable fact, not a memory.
Re-import is idempotent by prefix. The same pattern generalizes: an
importer is any cell whose *value* is new registry rows.

### 1.4 Why this is a superpower

Every MCP server ever written, every CLI in `$PATH`, every HTTP API with
a URL, every `.py` on disk: instant cells with provenance. TIT never
needs its own tool ecosystem to be complete — it inherits everyone
else's. The eleven native tools are a seed, not a corpus.

---

## 2. Composition as artifact — pipelines are the unit of software

### 2.1 The claim

`tit pipe 'a | b | c'` is not a command that runs — it is a **program
that gets built**: a named, versioned, witness-carrying cell graph,
addressable like any other value. Files were never the unit of software;
derivations are. A pipeline is a derivation, and TIT makes derivations
first-class objects.

### 2.2 The mechanism

The prototype already compiles a pipe into cells (`run_pipe`): head VALUE
cells for inputs, one FUNCTION cell per step, edges between them, a
witness on every node. The general form adds naming and addressing, which
PERFORMANCE.md §2 already supplies:

```
addr(pipeline) = H( kind=PIPELINE ‖ H(step fns + versions)
                    ‖ sort([ addr(input_i) ]) ‖ version )
```

Content-addressed (identical pipelines are identical objects, anywhere),
versioned (a pipeline that changes is a *new* pipeline — old receipts
still trace to the old one, forever, via tombstones), and
witness-carrying (the receipt of a pipeline run is the union witness of
its output closure — W13 L1 makes the union one instruction per word).

### 2.3 The pipeline registry

- **`tit pipe 'a|b|c' --name weather --semver 2`** — compile, run, and
  register the graph under `weather@2`.
- **`tit import fleet/pipeline:weather-v2`** — import a registered
  pipeline as a *single cell* in another graph: one node whose evaluation
  expands to the subgraph (call-by-need — the subgraph only ticks when
  the composite's witness changes, per the scaling law, §8).
- **Publish = share an address.** No marketplace needed: a pipeline is
  bytes; its address certifies it; the Merkle root (PERFORMANCE.md §2.2)
  certifies a whole fleet's worth. "Installing software" degenerates to
  "linking a cell."

### 2.4 Why this is a superpower

Programs stop being files that rot in repos and start being artifacts
that carry their own proofs: what ran, on what inputs, producing what
witness. Reuse stops being copy-paste and becomes an edge. A thousand
pipelines compose into pipelines. Software becomes a graph because it
always was one — TIT just stops pretending otherwise.

---

## 3. Session-as-world — persistent, addressable, multi-agent graphs

### 3.1 The claim

A session is not a conversation with an agent. It is a **world**: a
persistent, addressable, witness-carrying graph that survives process
death, agent death, and machine death — because it was never alive in
the process to begin with. The prototype proves the seed: kill your
agent, start another, `tit attach` — the pipeline, crons, and witness
chains are all still there. The schedule lives in the graph, not the
process.

### 3.2 Multi-agent, multi-front-door

Front doors are already plural (CLI argv, MCP stdio — one store, no
second truth). The general form is doors all the way down:

- **TUI door** — a human attaches to a world and types; keystrokes are
  INPUT cells (the prototype's `tit in`), debounced at evaluation level.
- **MCP door** — any agent (Claude, GLM, a boat brain) attaches; every
  call is a link.
- **web door** — a browser view of a world; the glass-shape (§6.3).
- **engine door** — `titd`, the resident daemon (PERFORMANCE.md §3.2):
  wavefronts run continuously, doors become thin clients.
- **GPU door** — cudaclaw-class compute attached as a provider tier.

Multiple agents in one world is not concurrency risk — it is the design:
each agent's calls bind cells with disjoint or shared witnesses; the
wavefront reconciles (§4); EFFECTs serialize at the boundary (§2 of
DESIGN.md). Agents are processes; the world is a file.

### 3.3 The world protocol

The tmux daemon pattern (the R4 winner: a daemon keyed by tmux session)
is the seed of a **distributed session fabric**. The protocol is four
verbs:

- **attach** `world:<name>` — land on the graph; identity is the root
  cell, not a PID.
- **detach** — leave; nothing dies because nothing lived.
- **share** `world:<name> → <peer>` — grant a peer the address; the
  Merkle root proves you both see the same world.
- **merge** — reconcile two world-histories (§4).

A hundred boats each hold worlds; the fabric is whatever subset is in
range; merge happens whenever boats meet. The world outlives every
process that ever touched it, including the ones that built it.

---

## 4. Mergeable graphs — CRDT reconciliation across machines

### 4.1 The claim

Cell graphs merge across machines without a coordinating server.
cudaclaw's SmartCRDT is the precedent — CRDT structures resident on GPU,
reconciling across devices — and the same algebra applies at session
level: two agents, two boats, two data-centers hold divergent copies of
a world; when they meet, the graphs reconcile deterministically. No
conflicts, by construction — except where conflict is *semantically
real*, and there TIT refuses to pretend.

### 4.2 The merge law

Purity does most of the work before any CRDT machinery is needed:

1. **Identical witnesses merge trivially.** Two machines that derived
   the same cell (same fn version, same input versions — PERFORMANCE.md
   §2.1 says they have the same address) hold the *same object*.
   Merging is set-union of interned addresses. This is the common case:
   boats that observed the same inputs converge by content addressing
   alone.
2. **Divergent pure derivations coexist.** Two machines that bound
   different inputs produced different addresses — both are facts with
   different witnesses (W13 L2: facts with different witnesses are
   different facts). Merge keeps both; the graph is a DAG, not a tree —
   divergence is representable, so it is not a conflict.
3. **Conflicting EFFECTs are the only arbitration points.** Two agents
   that wrote the same file, moved the same rudder, fired the same
   cron-adjacent action — *that* is a real conflict, and the merge
   surfaces it instead of silently resolving it. Policy is per-effect:
   LWW (last-writer-wins by content-address timestamp) for cheap
   effects; explicit (quorum of witness fringes, §5.3 of PERFORMANCE.md
   — the 0.9989 number) for expensive ones. The EFFECT boundary is what
   makes the conflict set *tiny and enumerable* — purity guaranteed
   everything else reconciles.

### 4.3 Why this is a superpower

Offline-first is not a feature bolted on; it is what content-addressed
pure graphs do when you connect two of them. The fleet's hundred boats
are a hundred CRDT replicas with sensors. Sync is delta-subtree exchange
under Merkle proofs (PERFORMANCE.md §2.2). Consensus is only ever spent
where the world was actually touched.

---

## 5. Universal routing — providers compete, the graph chooses

### 5.1 The claim

Every cell is an interface; every provider is an implementation; the
graph chooses. A request for `weather.now` may be servable by a native
fn, a cached receipt (memo hit), an HTTP provider on the boat's Starlink,
or a peer boat's copy in range. Routing is not configuration — it is
evaluation.

### 5.2 The doctrine

The ascending-provider doctrine (W7): **cheapest-first, escalate on
evidence.**

```
route(tool_id) →
  1. memo hit            (receipt exists for this exact witness — free)
  2. native provider     (in-process, ~µs)
  3. local peer          (another attached door/session — IPC)
  4. remote provider     (http/mcp/cli — escalate by health weight)
```

Health weighting: each `(tool_id, provider)` row carries an EWMA of
latency and failure count. Providers are tried in `cost × risk` order;
failure demotes, success promotes; a provider that errors three times
drops out of the rotation until its health half-life recovers it. The
registry (§1.2) is the table this policy runs over — which is why tool
ids must be interfaces, not implementations.

### 5.3 The route record in the witness chain

Every receipt records not just *what* produced it but *which provider*:
the witness entry for a routed cell carries `{cell@ver, provider,
latency}`. Consequences: routing decisions are auditable (why did this
answer come from the slow provider? — trace it); provider health is
derived from witnessed evidence, not guessed; and a receipt from a
peer can be fringe-verified (PERFORMANCE.md §5.3) before its provider
earns promotion. **The routing table is itself a cell graph** —
introspectable, witnessed, mergeable (§4).

---

## 6. Witness as trust fabric — receipts on everything, forever

### 6.1 The claim

Every value in the system carries its own proof of derivation. Not as an
audit-log bolted on — as the *identity* of the value (§2.1 of
PERFORMANCE.md: provenance is part of the address). Auditability is the
default state; unauditable results are unrepresentable.

### 6.2 The mechanism

The receipt protocol already ships: `{value, cell_ref, witness[]}` per
call, tombstones that keep `{cell_id, kind, version, value_hash,
witness, fn, inputs}` forever, traces that resolve through them.
"Verifiable forever" is the provenance integrity law plus content
addressing: a receipt from any epoch can be checked against the Merkle
root of the epoch's journals; a tombstoned upstream still certifies its
descendants (hash equality needs no value — PERFORMANCE.md §4.3).

### 6.3 The introspection API (the glass-shape)

The system can study its own shape — the graph is transparent to
itself:

- `tit.graph.get` — cells, edges, cold/tombstone states: *what am I?*
- `tit.witness.trace` — full provenance closure of any value, through
  tombstones: *where did this come from?*
- `tit.sessions.list` — all worlds on this machine: *what worlds exist?*
- (general form) `tit.routes.get` — provider health/rotation (§5.3):
  *who has been answering, and how well?*
- (general form) `tit.imports.list` — which foreign registries fed this
  world, witnessed when (§1.3): *what did I absorb?*

Introspection tools are themselves cells whose inputs are graphs — the
system's self-model composes like everything else. An agent that can
see the shape of its own world can refactor it, compress it, or explain
it. That is the glass-shape: not a black box that reports, a glass one
that shows.

---

## 7. Hardware reach — the MHS seam

### 7.1 The claim

Cells drive devices. Boat sensors and actuators, the lab laser, fleet
radios — hardware joins the graph through the same interface/provider
split as software tools, with one addition: the message seam is MHS.

### 7.2 The device-cell pattern

quilt-mhs (the message-handling seam already proven in the fleet) defines
the shape: `{src, dst, kind, payload, ts}` routed over whatever transport
is real (serial, radio, CAN, TCP). The device-cell pattern maps it onto
the ontology:

- **sensor → INPUT cell** — a device publisher emits MHS messages; an
  adapter binds each message as an INPUT cell version-bump. The sensor
  stream becomes a cell whose witness history *is* the log.
- **actuator ← EFFECT cell** — world-touch is already EFFECT-confined;
  an actuator EFFECT emits an MHS message. The purity boundary holds:
  sensors are reads (pure), actuators are writes (serialized, replayable,
  merged per §4.2's arbitration rules).
- **device driver = provider** — a device registers like any provider
  (§1.2), health-weighted like any other (§5.2): the laser answers or it
  doesn't; the graph routes around dead hardware the way it routes
  around dead endpoints.

The boat's EILEEN-class brain (Liquid LFM2.5, local, offline) attaches
as a front door (§3.2) to a world whose cells include its own sensors
and actuators. Sixty miles offshore with no cloud, the world still
ticks: it's a file, and the file is aboard.

### 7.3 Why this is a superpower

Software and hardware become the same kind of citizen in one graph:
addressed, witnessed, routed, merged. The fleet doctrine (hundred boats,
cheap local agents) is not a deployment target TIT supports — it is a
shape TIT *is*: a fleet of worlds reconciling when in range (§4),
routing to whatever provider is alive (§5), every sensor reading a
witnessed fact (§6).

---

## 8. The routing law as physics — why general-purpose is free

### 8.1 The scaling law, restated

> **T_tick = O(|closure(Δ)|)** — a tick costs what the change costs
> (PERFORMANCE.md §6). A 10,000-cell world with three changed inputs
  ticks within a small factor of a 5-cell world with the same change.

### 8.2 The consequence

Generality has a reputation for costing something: frameworks tax every
operation to pay for flexibility nobody asked for. TIT's math inverts
this. Universality *increases* |graph| — ten thousand imported tools,
pipelines of pipelines, sensor streams, peer worlds — and the tick cost
doesn't care, because graph size is not a term in the cost function.
A cell you never touch is a cell you never pay for; a tool you imported
and never call costs its registry row and nothing else; a world with a
hundred doors open ticks exactly its own delta.

So the honest engineering answer to "should we keep TIT general or keep
it small?" is: **the question is malformed.** Small was never cheaper.
The laws (purity, witnessing, content addressing, the wavefront) were
paid for once, in the prototype; generality is the compound interest.
The eight superpowers are not eight features to build — they are eight
consequences the math already funds:

| Superpower | Paid for by |
|---|---|
| Universal import | interface/provider split (registry) |
| Composition as artifact | content addressing (addr = H(…)) |
| Session-as-world | graph-on-file, doors are clients |
| Mergeable graphs | purity + witnessing (conflicts = EFFECTs only) |
| Universal routing | interface registry + health from witnessed routes |
| Trust fabric | provenance integrity law + tombstone hashes |
| Hardware reach | EFFECT boundary + INPUT cells (MHS-shaped) |
| Free generality | T_tick = O(|closure(Δ)|) |

General-purpose is not a tax. It's the payoff of the math.

---

## 9. THE DEEP DIMENSIONS — what the fabric is

*Captain's addendum to the directive, 21:58: "it can have deep
dimensions." The eight superpowers say what the fabric **does**. The
deep dimensions say what the fabric **is** — the directions a toolbox
has no words for. None of them needs new machinery to be true; each is
latent in laws the prototype already enforces, waiting only to be
exploited.*

### 9.1 Recursion — worlds all the way down

A cell's value can be anything JSON-safe — including a world. `tit
import fleet/pipeline:weather-v2` (§2.3) makes one cell whose
evaluation expands to a subgraph; nothing in the ontology forbids the
subgraph from being an entire imported session. TIT imports TIT: a
session whose cells include other sessions is just a graph whose nodes
contain graphs, and BIND never asked how big a cell's interior is.
The introspection tier is the proof this is real rather than poetic:
`tit.graph.get` and `tit.witness.trace` are tools whose subject matter
is a graph — computing *over* cell graphs with the same verbs used to
compute *in* them. A tool that studies a graph is a cell; its subject
can be the world that contains it. The mirror holds a mirror.

### 9.2 Time — the ledger is a history, not a snapshot

Versions bump; tombstones accumulate append-only; cron cells carry
`last_fire` and answer "what is due" by computing forward from
recorded history, not by sampling a clock. The graph is not a
structure that has a state — it is a ledger that has a past. That is
why trust here has a time axis: a receipt says not just *what* was
derived but *at which versions of its inputs*, so "was this true when
you acted on it?" is a query (`witness.trace` at `cell@ver`), not an
archaeology project. Replay (`tit again`) is time travel with the
receipts intact: re-derive yesterday's answer under yesterday's
inputs — or today's — and the two answers coexist as two facts with
two witnesses (W13 L2), because they are two facts.

### 9.3 Trust — witnesses of witnesses, audit the auditor

Every witness chain bottoms out at INPUT cells — the places the world
was read. Above them, each step is a witnessed derivation, so a
receipt's receipt is its closure: epistemology made computational. A
claim is exactly as trustworthy as its fringe (PERFORMANCE.md §5.3 —
sampled verification at 0.9989), and the auditor can be audited,
because the introspection tools are themselves cells whose outputs
carry witnesses. "Who checked the checker?" is answered the same way
as every other question here: trace it. Trust stops being a social
estimate and becomes a graph metric — depth to inputs, fringe size,
provider health along the route (§5.3).

### 9.4 Scale — the same laws at every depth

One cell. Ten thousand cells (T_tick = O(|closure(Δ)|), §8). A warp
of 32 lanes (wavefronts are dataflow-parallel, PERFORMANCE.md §3). A
fleet of 45 machines (the merge law, §4). A society of fleets (worlds
sharing addresses, §3.3). Nothing in the ontology changes between
tiers: BIND, LINK, TICK, EFFECT, FORGET — the same five verbs, the
same four laws, the same receipts, at every size. The fabric is
scale-free the way power laws are: not designed at one size and
stretched, but governed by an equation with no size term. A cell does
not know how big its world is — that ignorance is what makes growth
free.

### 9.5 Meaning — the glass-shape

A black-box model answers; a glass-shape answers *and shows its work,
by identity*. Every value in TIT is inseparable from its provenance —
not an explanation bolted on afterward, but the address of the thing
itself. So the question that matters — *where did this belief come
from?* — always has a grounded answer: this cell, these inputs at
these versions, that provider, this route, checked by this fringe. An
agent living in a TIT world cannot hallucinate a provenance, because
provenance is not speech; it is structure. Meaning here is not
semantics solved — it is semantics **anchored**: every claim is a node
with its derivation attached, and honest uncertainty is representable
(an INPUT with nothing above it yet; an ERROR cell that keeps its
witness).

### 9.6 Embodiment — a body of sensors and actuators

The MHS seam (§7) gives the graph a body: sensors as INPUT cells (the
witness history *is* the sensor log), actuators as EFFECT cells
(serialized, replayable, arbitrable). The EILEEN-class boat is the
emblem — sixty miles offshore, a local brain attached to a world
whose cells are its own hull: water temperature, catch count, radio
range, rudder angle. The boat's mind is not a model *about* the world;
it is a graph *containing* the world's edges. When the fabric ticks,
the body acts; when the body senses, the fabric learns. Embodiment
stops being a philosophical upgrade to a chat model and becomes an
engineering property of where the EFFECT boundary sits.

### 9.7 Social — mergeable minds

Two agents in one world is already the design (§3.2); two worlds
meeting is the merge law (§4). Minds that are graphs can share
*structure*, not just messages: hand over a cell_ref and the recipient
inherits the derivation, not the conclusion. Disagreement is
representable (two facts, two witnesses, both true), consensus is
fringe-verification, and arbitration is by receipt — not by rank,
volume, or charisma. A fleet of boats that merges worlds when in
range is not a metaphor; it is the CRDT algebra doing what CRDT
algebra does. Social cognition becomes a graph operation: union the
pure, serialize the EFFECTs, surface the conflicts.

### 9.8 Accountability — wrong until proven right by disk

The fleet's cowboy doctrine — an operator's claim is wrong until the
disk proves it right — is usually culture. Here it is a runtime
property. Nothing witness-referenced is ever destroyed: every claim
keeps its receipts, every receipt keeps its closure, every closure
resolves through tombstones forever. "Prove it" is not a
confrontation; it is `tit.witness.trace`. An answer that cannot show
its witness is unrepresentable; a claim whose inputs were forgotten
still traces, by hash-equality through tombstones (PERFORMANCE.md
§4.3). The ledger cannot be argued with after the fact — only
re-derived. Accountability is not a policy layered over the system;
it is the system's memory discipline, the one law with no exceptions.

### 9.9 The one-line form

> The fabric is a **recursive, time-aware, self-auditing, scale-free
> substrate** — a model that can hold a mirror to itself, remember
> what it saw, and prove it.

---

*Spec: TIT-SUPERPOWERS lane, 2026-08-27. Grounded in tit-quilt v0.1.0
(DESIGN.md), PERFORMANCE.md (witness memo, content addressing, scaling
law), W7 ascending-provider doctrine, W13 witness arithmetic (L1/L2,
consensus fringes 0.9989), cudaclaw SmartCRDT (GPU-resident CRDT
precedent), quilt-mhs (MHS message seam), R4 tmux-daemon winner
(session-fabric seed), and the fleet/hundred-boats doctrine
(memory/kimi-infrastructure-proposal.md). Depth dimensions added per
the captain's addendum, 21:58 AKDT.*
