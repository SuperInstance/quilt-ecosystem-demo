"""tit MCP server — JSON-RPC 2.0 over stdio, hand-rolled (no SDK).

Three tiers:
  atomic        tit.<tool>          -> {value, cell_ref, witness[]}
  pipe          tit.pipe            -> run steps / replay_last with new inputs
  introspection tit.graph.get / tit.witness.trace / tit.sessions.list

The MCP call IS a link: any string argument that matches a live cell_ref
("cell@ver" or "session/cell@ver") is resolved to the upstream cell and
wired as an input edge — the agent chains by pointer, not by payload.

Session derivation mirrors the CLI door (TIT_SESSION, else tmux+cwd), so
both front doors land on the same graph. Crons advance lazily on every
request: kill the agent, wake another, the schedule keeps ticking.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

from . import __version__
from . import importers
from .cells import KIND_ROOT, cell_ref as fmt_cell_ref, parse_cell_ref
from .engine import pipe_last, run_pipe, tick
from .store import SessionStore, derive_session_name, list_sessions
from .tools import TOOLS

PROTOCOL_VERSIONS = {"2024-11-05", "2025-03-26", "2025-06-18"}
DEFAULT_PROTOCOL = "2024-11-05"


def _tool_schema(spec: dict) -> dict:
    return {
        "type": "object",
        "properties": spec.get("params", {}),
        "required": spec.get("required", []),
    }


def _tool_entry(name: str, description: str, schema: dict) -> dict:
    return {"name": name, "description": description, "inputSchema": schema}


class TitServer:
    def __init__(self, session_name: str | None = None):
        self.session_name = session_name or derive_session_name()
        self.store = SessionStore(self.session_name)
        self._n = int(time.time()) % 100000

    # ------------------------------------------------------------- helpers

    def _next_cell_id(self, tool: str) -> str:
        self._n += 1
        return f"mcp.{self._n}.{tool}"

    def _resolve_pointers(self, g, args: dict[str, Any]) -> tuple[dict, dict, list]:
        """Split args into literals vs linked inputs (cell_ref pointers)."""
        literals: dict[str, Any] = {}
        links: dict[str, str] = {}
        notes: list[str] = []
        for k, v in args.items():
            if isinstance(v, str):
                ref = parse_cell_ref(v)
                if ref is not None:
                    cell_id, ver = ref
                    target = g.cells.get(cell_id)
                    if target is not None:
                        links[k] = cell_id
                        if target.version != ver:
                            notes.append(
                                f"{k}: ref {cell_id}@{ver} resolved at current "
                                f"version {target.version}")
                        continue
                    notes.append(
                        f"{k}: ref {cell_id}@{ver} not live (tombstoned or "
                        "foreign); passed through as literal")
            literals[k] = v
        return literals, links, notes

    # -------------------------------------------------------------- atomic

    def call_atomic(self, g, tool: str, args: dict) -> dict:
        literals, links, notes = self._resolve_pointers(g, args)
        cell_id = self._next_cell_id(tool)
        g.bind_fn(cell_id, tool, inputs=links, literals=literals)
        tick(g)
        cell = g.cells[cell_id]
        if cell.error:
            return {"error": cell.error, "cell_ref": fmt_cell_ref(g, cell)}
        closure = g.witness_closure(cell.cell_id)
        closure.pop(cell.cell_id, None)
        out = {
            "value": cell.value,
            "cell_ref": fmt_cell_ref(g, cell),
            "witness": sorted(f"{c}@{v}" for c, v in closure.items()),
        }
        if notes:
            out["notes"] = notes
        g.push_result(cell.cell_id)
        return out

    # ---------------------------------------------------------------- pipe

    def call_pipe(self, g, args: dict) -> dict:
        if args.get("replay_last"):
            result_id, report = pipe_last(g, args.get("inputs") or {})
            cell = g.cells[result_id]
            return {
                "value": cell.value,
                "cell_ref": fmt_cell_ref(g, cell),
                "replayed": {
                    "evaluated": report.evaluated,
                    "skipped_clean": report.skipped_clean,
                    "crons_fired": report.fired_crons,
                },
            }
        steps = args.get("steps") or []
        result_id, created = run_pipe(g, steps)
        cell = g.cells[result_id]
        return {
            "value": cell.value,
            "cell_ref": fmt_cell_ref(g, cell),
            "cells": created,
        }

    # -------------------------------------------------------- introspection

    def call_graph_get(self, g, args: dict) -> dict:
        cell_id = args.get("cell_id")
        if cell_id:
            cell = g.cells.get(cell_id)
            if cell is None:
                tb = g.tombstone_by_id(cell_id)
                if tb is None:
                    raise ValueError(f"no such cell: {cell_id}")
                return {"tombstone": tb.to_dict()}
            return {"cell": cell.to_dict(),
                    "downstream": sorted(g.downstream(cell_id))}
        cells = []
        for c in g.cells.values():
            cells.append({
                "cell_id": c.cell_id, "kind": c.kind, "version": c.version,
                "fn": c.fn, "inputs": c.inputs, "cold": c.cold,
                "error": c.error, "cron": c.cron,
            })
        edges = [{"from": uid, "to": c.cell_id, "param": param}
                 for c in g.cells.values()
                 for param, uid in c.inputs.items()]
        return {"session": g.name, "root_id": g.root_id, "cells": cells,
                "edges": edges, "tombstones": len(g.tombstones)}

    def call_witness_trace(self, g, args: dict) -> dict:
        cell_id = args.get("cell_id")
        if not cell_id:
            raise ValueError("cell_id is required")
        closure = g.witness_closure(cell_id)
        trace = []
        for cid in sorted(closure):
            ver = closure[cid]
            live = g.cells.get(cid)
            if live is not None:
                trace.append({"cell": cid, "version": ver, "state": "live",
                              "kind": live.kind, "fn": live.fn,
                              "vhash": live.vhash})
            else:
                tb = g.tombstone_by_id(cid)
                trace.append({"cell": cid, "version": ver, "state": "tombstone",
                              "kind": tb.kind if tb else None,
                              "value_hash": tb.value_hash if tb else None})
        return {"cell_id": cell_id, "witness": trace}

    # ------------------------------------------------------ foreign import

    def call_mcp_import(self, g, args: dict) -> dict:
        """Superpower 1 stub (SUPERPOWERS.md §1.3): a foreign MCP server's
        tools/list manifest becomes registry rows (callable by the same
        verbs), and the import itself binds a cell — the manifest summary
        is a witnessed value in the graph. No transport crosses a process
        boundary: rows register honestly, calls surface an honest error
        until a live transport exists (DESIGN.md §8)."""
        summary = importers.import_mcp_manifest(
            args.get("manifest") or {}, args.get("prefix"))
        cell = importers.bind_import_cell(g, summary)
        tick(g)
        cell = g.cells[cell.cell_id]
        out = {"value": cell.value, "cell_ref": fmt_cell_ref(g, cell)}
        g.push_result(cell.cell_id)
        return out

    # ------------------------------------------------------------- listing

    def tool_entries(self) -> list[dict]:
        entries = []
        for name, spec in TOOLS.items():
            desc = spec["description"]
            if name == "jwt_decode":
                desc += " Decode-only: no signature verification."
            desc += (" Every call binds a cell; pass a cell_ref string as an "
                     "argument to LINK instead of copying.")
            entries.append(_tool_entry(f"tit.{name}", desc, _tool_schema(spec)))
        entries.append(_tool_entry(
            "tit.pipe",
            "Pipe tier: run a chain of steps [{tool, args}] in one wavefront, "
            "or replay_last with new inputs (only changed edges re-fire).",
            {"type": "object", "properties": {
                "steps": {"type": "array", "description": "Steps to run",
                          "items": {"type": "object"}},
                "replay_last": {"type": "boolean",
                                "description": "Replay the last pipeline"},
                "inputs": {"type": "object",
                           "description": "New inputs for replay"},
             }, "required": []}))
        entries.append(_tool_entry(
            "tit.graph.get", "Introspection: cells + edges of the session graph.",
            {"type": "object", "properties": {
                "cell_id": {"type": "string", "description": "Focus one cell"}},
             "required": []}))
        entries.append(_tool_entry(
            "tit.witness.trace",
            "Introspection: transitive witness closure of a cell (resolves "
            "through tombstones — nothing witness-referenced is destroyed).",
            {"type": "object", "properties": {
                "cell_id": {"type": "string"}}, "required": ["cell_id"]}))
        entries.append(_tool_entry(
            "tit.sessions.list", "Introspection: all persisted sessions.",
            {"type": "object", "properties": {}, "required": []}))
        entries.append(_tool_entry(
            "tit.mcp_import",
            "Universal import (stub): register a foreign MCP server's "
            "tools/list manifest as cells under <prefix>.<tool>. The import "
            "binds a cell — the manifest summary is witnessed in the graph. "
            "Rows are process-local; calls need a live transport (honest "
            "stub scope — DESIGN.md §8).",
            {"type": "object", "properties": {
                "manifest": {"type": "object",
                             "description": "A tools/list result: "
                                            "{tools: [{name, description, "
                                            "inputSchema}]}"},
                "prefix": {"type": "string",
                           "description": "Dotted prefix for imported rows"},
             }, "required": ["manifest", "prefix"]}))
        # imported tools surface as first-class tools on the next list
        for fname in importers.foreign_listing():
            spec = importers.FOREIGN_TOOLS[fname]
            entries.append(_tool_entry(
                f"tit.{fname}",
                f"[imported:{spec['imported_from']}] "
                f"{spec['description']}", _tool_schema(spec)))
        return entries

    # -------------------------------------------------------------- server

    def handle_call(self, name: str, args: dict) -> tuple[dict, bool]:
        """Returns (result payload, is_error)."""
        g = self.store.load()
        tick(g)  # lazy cron advance: the graph keeps time on every request
        try:
            if name.startswith("tit."):
                tool = name[4:]
                if tool in TOOLS:
                    out = self.call_atomic(g, tool, args)
                elif tool == "pipe":
                    out = self.call_pipe(g, args)
                elif tool == "graph.get":
                    out = self.call_graph_get(g, args)
                elif tool == "witness.trace":
                    out = self.call_witness_trace(g, args)
                elif tool == "sessions.list":
                    out = {"sessions": list_sessions()}
                elif tool == "mcp_import":
                    out = self.call_mcp_import(g, args)
                elif importers.has_foreign(tool):
                    out = self.call_atomic(g, tool, args)
                else:
                    raise ValueError(f"unknown tool: {name}")
            else:
                raise ValueError(f"unknown tool: {name}")
        except Exception as exc:  # noqa: BLE001 — surface as MCP tool error
            self.store.save(g)
            return {"error": f"{type(exc).__name__}: {exc}"}, True
        self.store.save(g)
        return out, False

    def dispatch(self, msg: dict) -> dict | None:
        method = msg.get("method", "")
        msg_id = msg.get("id")
        is_notification = "id" not in msg
        params = msg.get("params") or {}

        if method.startswith("notifications/"):
            return None

        if method == "initialize":
            requested = params.get("protocolVersion", DEFAULT_PROTOCOL)
            version = requested if requested in PROTOCOL_VERSIONS else DEFAULT_PROTOCOL
            return {"jsonrpc": "2.0", "id": msg_id, "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "tit-quilt", "version": __version__},
                "instructions": (
                    "tit: the session is a graph. Atomic calls return "
                    "{value, cell_ref, witness[]}; pass a cell_ref as an "
                    "argument to chain by pointer. tit.pipe runs/replays "
                    "pipelines; tit.graph.get / tit.witness.trace / "
                    "tit.sessions.list introspect. Nothing "
                    "witness-referenced is ever destroyed."),
            }}

        if method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": msg_id,
                    "result": {"tools": self.tool_entries()}}

        if method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments") or {}
            try:
                payload, is_err = self.handle_call(name, args)
            except Exception as exc:  # noqa: BLE001
                payload, is_err = {"error": f"{type(exc).__name__}: {exc}"}, True
            result: dict = {
                "content": [{"type": "text",
                             "text": json.dumps(payload, ensure_ascii=False,
                                                default=str)}],
                "isError": is_err,
            }
            if not is_err:
                result["structuredContent"] = payload
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}

        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": msg_id, "error": {
            "code": -32601, "message": f"method not found: {method}"}}

    def serve(self, stdin=None, stdout=None) -> None:
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                resp = {"jsonrpc": "2.0", "id": None, "error": {
                    "code": -32700, "message": "parse error"}}
            else:
                if not isinstance(msg, dict):
                    resp = {"jsonrpc": "2.0", "id": None, "error": {
                        "code": -32600, "message": "invalid request"}}
                else:
                    resp = self.dispatch(msg)
            if resp is not None:
                stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                stdout.flush()


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    session = None
    if "--session" in argv:
        session = argv[argv.index("--session") + 1]
    TitServer(session).serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
