# tit-quilt — DESIGN (the merged quilt-native TIT)

Registration doc for the prototype. Winner: **Design C** ("THE SESSION IS A
GRAPH, NOT A PROCESS", 3/4 first-place judge votes). Runner-up **Design B**
contributed the one-process/two-front-doors insight. This is the merge.

## 1. Core ontology

- **Cell** — atomic unit: `{cell_id, kind, value, version, fn, inputs,
  literals, witness, dirty, error, cron, last_fire}`.
  Kinds: `VALUE`, `INPUT`, `FUNCTION`, `EFFECT`, `ROOT`.
- **Edge (LINK)** — a function cell's `inputs` map `{param → upstream cell_id}`.
  The MCP call *is* a link: calling `tit.sha256` with a `cell_ref` argument
  creates a FUNCTION cell whose input edge points at that cell. The protocol
  is an edge in the graph, not a layer bolted on.
- **Witness set** — `frozenset{(cell_id, version)}` of *direct* inputs at
  evaluation time. A cell is clean iff every input's current version equals
  the witness-recorded version. Transitive closures (for `tit.witness.trace`
  and retention checks) walk live cells, then tombstones.
- **Version** — bumps on content change (value, edges, literals, cron fire).
  Identity for provenance; the `cell_ref` format is `session/cell_id@version`.

## 2. TICK — topological wavefront

1. **Cron advance** (on-demand, catch-up correct): for each cron cell,
   `next = cron_next(expr, after=last_fire)`; while `next ≤ now`: bump
   version, set `last_fire = next`, mark dirty. Crons tick whenever any door
   touches the session — kill the agent, wake another, it inherits the
   schedule because the schedule lives in the graph.
2. **Wavefront** — seed set = dirty cells ∪ their downstream closure.
   Kahn topological order over the induced subgraph.
3. **Evaluate** — FUNCTION cells resolve params from upstream values +
   literals, call the pure tool fn, record `witness`, clear `dirty`.
   Cells whose witness already matches are skipped — this *is*
   `pipe --last` incremental replay: only changed edges re-fire.
4. **EFFECT boundary** — EFFECT cells are the only world-touch (file write,
   clipboard, cron registration). Everything else is pure. Effects run at
   the end of a wavefront, in topo order, idempotently where possible.

## 3. Retention — hot → cold → tombstone

- **hot**: value present, in `sessions/<name>.json`.
- **cold**: value dropped, structure kept, in `.cold.json`. FUNCTION cells
  re-derive on next tick (hash must match — free provenance check); VALUE
  cells need an explicit re-bind.
- **tombstone**: `FORGET` writes `{cell_id, kind, version, value_hash,
  witness, fn, inputs, literals, ts}` into `.tombstones.json` (append-only,
  never deleted) and removes the live cell.
- **Provenance integrity law**: nothing witness-referenced is ever destroyed.
  Tombstones keep identity + hash + witness chain; `tit.witness.trace`
  resolves through them. There is no code path that deletes a tombstone.

## 4. Sessions

- Session-root cell id: `root:<tmux-session>:<cwd>` — keyed by tmux session
  and working directory, so any door (CLI argv, MCP stdio) attaching from the
  same pane/cwd lands on the same graph. Survives agent death by
  construction: it's a file.
- One store = single source of truth. Lock file + atomic temp-rename writes.
  (Design B's "one process" realized as "one store, two front doors" for the
  prototype; a resident daemon is the natural next step.)
- Keystrokes: `tit in` writes an INPUT cell. Many writes, one wavefront —
  debounce happens at *evaluation* level, not write level.
- `tit again --in=k=v` re-BINDs VALUE cells inside the last result's witness
  closure and re-ticks — re-attaching a persisted subgraph after death.

## 5. MCP surface (hand-rolled JSON-RPC 2.0 over stdio)

- `initialize` → protocol 2024-11-05, capabilities `{tools}`.
- `tools/list` → atomic tier (`tit.<tool>`), pipe tier (`tit.pipe`),
  introspection tier (`tit.graph.get`, `tit.witness.trace`,
  `tit.sessions.list`).
- `tools/call` → atomic: `{value, cell_ref, witness[]}` (witness = transitive
  closure as `cell@ver` strings). String args matching a live `cell@ver`
  (or `session/cell@ver`) are treated as pointers → LINK, don't copy.
- Notifications (`notifications/initialized`) get no response; `ping` → `{}`.

## 6. Cron expressions

5-field vixie-cron semantics: `min hour dom mon dow`, `*`/`,`/`-`/`/` steps,
3-letter month/day names, `@hourly @daily @weekly @monthly @yearly`.
DOM/DOW OR-rule when both restricted. UTC, minute resolution. Next-fire by
day/hour scan with month skips (bounded 5 years).

## 7. What this is not (yet)

Resident daemon, background ticker thread, real YAML lib, signature
verification, multi-user auth, compaction of tombstone files. All deliberate
prototype scope — the graph, the laws, and the two front doors are real.

## 8. General-purpose scope — the superpowers lane

The third spec ([`docs/SUPERPOWERS.md`](docs/SUPERPOWERS.md)) argues the
four laws above make TIT a **metatoolbox**: any function is a cell, any
composition is a program, any session is a world, any answer carries
receipts. One superpower ships here as a concrete stub:

- **`tit_quilt/importers.py` — universal tool import, MCP family.** A
  foreign MCP server's `tools/list` manifest becomes registry rows under
  `<prefix>.<tool>`: `translate_schema` maps `inputSchema` → the registry's
  param format; rows carry a forwarding provider. `run_tool` falls through
  to `call_foreign` on unknown names, so imported tools are callable by
  the same verbs as native ones — BIND/LINK/TICK, pipes, pointers, the
  works (`run_pipe` accepts them too).
- **The import itself binds a cell.** `bind_import_cell` writes the
  manifest summary as a witnessed VALUE cell (`import.<prefix>`), so
  "what tools existed when this pipeline ran" is a queryable fact in the
  graph. Re-import is idempotent by prefix; a new manifest under the same
  prefix replaces the rows (the registry follows the manifest).
- **Surfaces on both doors.** MCP: `tit.mcp_import` (+ imported rows in
  `tools/list` as `tit.<prefix>.<tool>`). CLI: `tit import-mcp
  <manifest.json> --prefix wx`.
- **Honest stub limits.** Registry rows are process-local; a transport is
  a callable attached at import time (in-process); the doors import
  manifest-only — a call without a live transport binds a cell whose
  evaluation records the honest refusal. Not shipped (spec only): http /
  cli / code-file providers, named versioned pipelines (`tit pipe --name`,
  content-addressed `addr`), CRDT merge, routing/health tables, MHS
device-cells.

The depth dimensions (recursion, time, trust, scale, meaning, embodiment,
social, accountability) are §9 of the superpowers doc — latent in the
laws, not yet machinery.
