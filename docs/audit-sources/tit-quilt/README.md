# tit-quilt

![banner](assets/banner.jpg)

**A terminal toolbox that outlives its terminal.**

Longer name, same object: **a recursive, time-aware, self-auditing,
scale-free substrate — a model that can hold a mirror to itself,
remember what it saw, and prove it.** The toolbox is the seed; the
fabric is the shape ([`docs/SUPERPOWERS.md`](docs/SUPERPOWERS.md)).

`tit` treats your session as a *graph*, not a process. Every tool call is a
cell; every data flow is an edge; every result is a pointer you can hand to
the next call. Kill the agent, kill the terminal, come back tomorrow — the
graph is still on disk, crons still know when they're due, and the next
process that attaches (CLI or MCP) inherits the pipeline mid-stride.

This is a prototype of the quilt-native TIT.RUN design: **Design C**
("the session is a graph, not a process" — the judges' winner, 3/4 first-place
votes) merged with **Design B's** one-process / two-front-doors insight.

---

## The model in 60 seconds

| Verb | Meaning |
|------|---------|
| `BIND` | create/update a **cell** (value, function, effect, input, or session root) |
| `LINK` | wire a function cell's parameter to an upstream cell — an *edge* |
| `TICK` | evaluate dirty cells in topological wavefront order, downstream only |
| `EFFECT` | the only place the world gets touched (file, clipboard, cron registration) |
| `FORGET` | hot → cold → **tombstone**: the value is dropped, replaced by its hash |

Three laws hold the quilt together:

1. **The MCP call IS a link.** An atomic tool call binds a cell into the
   session graph and returns `{value, cell_ref, witness[]}`. Pass a `cell_ref`
   back as an argument to any tool and it is *linked*, not copied — the agent
   chains by pointer in ~40 tokens instead of re-shipping payloads.
2. **Provenance integrity law.** Nothing witness-referenced is ever destroyed.
   `FORGET` never deletes: it tombstones — cell identity, version, witness
   chain, and a content hash survive forever, so any result can still be
   traced and re-derived.
3. **One graph, two front doors.** The CLI (`tit …`) and the MCP server
   (`tit mcp`) operate on the *same* persisted session store — there is no
   second source of truth to drift.

## Tools (atomic tier, all pure cells)

`base64_encode` · `base64_decode` · `sha256` · `json_format` · `json_to_yaml` ·
`cron_next` · `jwt_decode` (payload only, **no signature verification**) ·
`uuid4` · `password_gen` · `url_encode` · `url_decode`

**Plus imported ones:** `tit.mcp_import` (MCP door) and `tit import-mcp`
(CLI door) register a foreign MCP server's `tools/list` manifest as cells
under `<prefix>.<tool>` — callable by the same verbs, and the import itself
binds a witnessed cell recording what was absorbed. First shipped
superpower; see [`docs/SUPERPOWERS.md`](docs/SUPERPOWERS.md) §1.

## MCP tiers

- **Atomic** — `tit.sha256`, `tit.base64_decode`, … each returns
  `{value, cell_ref, witness[]}` and binds into the session graph.
- **Pipe** — `tit.pipe`: run a chain of steps, or `replay_last` with new
  inputs; only edges whose witness changed re-evaluate.
- **Introspection** — `tit.graph.get`, `tit.witness.trace`, `tit.sessions.list`.

Hand-rolled JSON-RPC 2.0 over stdio (`initialize` / `tools/list` /
`tools/call`). No SDK, no dependencies.

## tmux companion

```bash
tit attach                    # bind/create session root (tmux session + cwd keyed)
tit in "hello world"          # keystroke → input cell (evaluation-level debounce)
tit pipe sha256 --in text="hello world"
tit out -1                    # last result
tit pipe --last --in text="goodbye"   # replay only changed edges
tit again --in text=hello     # re-bind a persisted subgraph after agent death
tit tick                      # on-demand cron advance (correct next-fire math)
tit forget <cell>             # hot → cold → tombstone; the trace never dies
```

Kill your agent. Start another one. `tit attach` → the pipeline, the crons,
the witness chains are all still there. That's the point.

## Install / run

Python **3.11+**, zero dependencies (stdlib only).

```bash
pipx install .        # or: python -m tit_quilt.cli …
tit mcp               # stdio MCP server; point any MCP client at it
python -m unittest discover -s tests   # or: pytest
```

State lives under `~/.tit/` (override with `TIT_HOME`):
`sessions/<name>.json` (hot) · `.cold.json` (cold) · `.tombstones.json`
(hash-only, append-only).

## Honest prototype scope

- One store, lock-disciplined file persistence — not a resident daemon yet.
- Crons advance on-demand (any `tit` interaction or explicit `tick`), with
  correct catch-up; no background ticker thread yet.
- `json_to_yaml` uses a minimal built-in emitter (maps/lists/scalars); no
  anchors, tags, or exotic YAML.
- `jwt_decode` is decode-only — it never verifies signatures. Never trust a
  decoded JWT for auth decisions.

The performance path out of this scope is specified in
[`docs/PERFORMANCE.md`](docs/PERFORMANCE.md): witness-keyed memoization,
content-addressed cells, dataflow parallelism, retention-as-cache-hierarchy,
batched evaluation — each phase enabled by a law the prototype already
enforces. The general-purpose path is specified in
[`docs/SUPERPOWERS.md`](docs/SUPERPOWERS.md) (eight superpowers + the deep
dimensions), of which exactly one ships today: universal MCP import —
manifest-to-registry rows, import-as-cell, honest refusal without a
transport. Everything else (http/cli/code providers, named versioned
pipelines, CRDT merge, routing tables, MHS device-cells) is spec, built
honestly on laws that are already real.

## Lineage

Winning design C (GLM-5.3): session-as-graph, MCP-call-is-a-link, cell_ref
chaining, hot→cold→tombstone retention with the provenance integrity law,
session roots that survive agent death, three MCP tiers. Merged from runner-up
design B (kimi): one process serving CLI argv + MCP from the same graph,
EFFECT-confined purity boundary, keystrokes debouncing into input-cell writes,
`pipe --last` incremental replay.

MIT license. Prototype built August 2026.
