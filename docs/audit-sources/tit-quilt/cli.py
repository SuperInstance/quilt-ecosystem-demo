"""tit CLI — the argv front door (the MCP server is the other one).

Both doors operate on the same persisted session store: one graph, no
second source of truth. The session root is keyed by (tmux session, cwd),
so a new agent process attaching from the same pane inherits the pipeline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from . import importers
from .cells import KIND_EFFECT, KIND_FUNCTION, Graph, value_hash
from .engine import again as again_op
from .engine import pipe_last, run_pipe, tick
from .store import SessionStore, derive_session_name, list_sessions
from .tools import ATOMIC_TOOL_NAMES, EFFECTS, TOOLS


def _parse_kv(pairs: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for p in pairs:
        if "=" not in p:
            raise SystemExit(f"expected key=value, got {p!r}")
        k, v = p.split("=", 1)
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v
    return out


def _emit(obj: Any, pretty: bool = False) -> None:
    if pretty:
        print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))
    else:
        print(json.dumps(obj, ensure_ascii=False, default=str))


def _store(args) -> SessionStore:
    return SessionStore(getattr(args, "session", None) or derive_session_name())


def _out_n(g: Graph, n: int) -> int:
    idx = n
    results = list(g.results)
    if not results:
        print("no results yet", file=sys.stderr)
        return 1
    try:
        cell_id = results[idx]
    except IndexError:
        print(f"only {len(results)} results", file=sys.stderr)
        return 1
    cell = g.cells.get(cell_id)
    if cell is None:
        tb = g.tombstone_by_id(cell_id)
        if tb:
            _emit({"tombstoned": tb.to_dict()})
            return 0
        print("result cell gone", file=sys.stderr)
        return 1
    _emit({"cell": cell.cell_id, "version": cell.version,
           "value": cell.value, "error": cell.error})
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tit",
        description="a terminal toolbox that outlives its terminal — "
                    "the session is a graph, not a process")
    p.add_argument("--version", action="version", version=f"tit-quilt {__version__}")
    p.add_argument("--session", help="explicit session name (default: tmux+cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("attach", help="bind/create the session root (tmux+cwd)")
    sp.add_argument("name", nargs="?", help="pin an explicit session name")
    sp.add_argument("--cwd", default=None)

    sp = sub.add_parser("in", help="keystroke write -> INPUT cell (debounced at tick)")
    sp.add_argument("text")
    sp.add_argument("--cell", default="input:0")

    sp = sub.add_parser("bind", help="bind/update a VALUE cell")
    sp.add_argument("cell_id")
    sp.add_argument("value", help="JSON value (fallback: raw string)")

    sp = sub.add_parser("link", help="wire a function cell input to an upstream cell")
    sp.add_argument("cell_id")
    sp.add_argument("param")
    sp.add_argument("upstream")

    sp = sub.add_parser("fn", help="bind a FUNCTION/EFFECT cell")
    sp.add_argument("cell_id")
    sp.add_argument("tool", help=f"one of: {', '.join(ATOMIC_TOOL_NAMES + list(EFFECTS))}")
    sp.add_argument("--in", dest="ins", action="append", default=[],
                    help="param=upstream_cell (LINK)")
    sp.add_argument("--lit", dest="lits", action="append", default=[],
                    help="param=literal")
    sp.add_argument("--effect", action="store_true", help="bind as EFFECT cell")

    sp = sub.add_parser("cron", help="bind a live cron cell (ticks on demand)")
    sp.add_argument("expr")
    sp.add_argument("--cell", default=None)
    sp.add_argument("--start", type=float, default=None,
                    help="epoch of first reference (default: now)")

    sp = sub.add_parser("tick", help="evaluate the wavefront; advance crons")

    sp = sub.add_parser("pipe", help="run a tool pipeline")
    sp.add_argument("tool", nargs="?", help=f"one of: {', '.join(ATOMIC_TOOL_NAMES)}")
    sp.add_argument("--in", dest="ins", action="append", default=[],
                    help="key=value literal input")
    sp.add_argument("--last", action="store_true", help="replay last pipeline")

    sp = sub.add_parser("out", help="read a result (default: last)")
    sp.add_argument("n", nargs="?", type=int, default=-1,
                    help="-1 = last, -2 = before that, ...")

    sp = sub.add_parser("again", help="re-bind the persisted subgraph and re-tick")
    sp.add_argument("--in", dest="ins", action="append", default=[],
                    help="key=new_value")

    sp = sub.add_parser("forget", help="FORGET -> tombstone (hash-only, forever)")
    sp.add_argument("cell_id")

    sp = sub.add_parser("cold", help="hot -> cold (drop value, keep identity)")
    sp.add_argument("cell_id")

    sp = sub.add_parser("graph", help="print the session graph")
    sp.add_argument("cell_id", nargs="?")

    sp = sub.add_parser("witness", help="trace a cell's witness closure")
    sp.add_argument("cell_id")

    sp = sub.add_parser("sessions", help="list persisted sessions")

    sp = sub.add_parser("tools", help="list atomic tools (+ imported rows)")

    sp = sub.add_parser("import-mcp",
                        help="import a foreign MCP tools/list manifest as cells")
    sp.add_argument("manifest", help="path to a tools/list JSON result")
    sp.add_argument("--prefix", required=True,
                    help="dotted prefix; rows register as <prefix>.<tool>")
    sp = sub.add_parser("mcp", help="start the stdio MCP server")
    sp.add_argument("--session", default=None)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "mcp":
        from .mcp import TitServer
        TitServer(args.session).serve()
        return 0

    if args.cmd == "tools":
        _emit(ATOMIC_TOOL_NAMES + importers.foreign_listing())
        return 0

    if args.cmd == "sessions":
        _emit(list_sessions(), pretty=True)
        return 0

    if args.cmd == "attach":
        import os
        store = SessionStore(args.name) if args.name else _store(args)
        g = store.attach(cwd=args.cwd or os.getcwd())
        _emit({"session": store.name, "root": g.root_id,
               "cells": len(g.cells), "tombstones": len(g.tombstones)})
        return 0

    store = _store(args)

    if args.cmd == "import-mcp":
        try:
            manifest = json.loads(
                Path(args.manifest).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"cannot read manifest: {exc}", file=sys.stderr)
            return 1

        def op(g: Graph):
            summary = importers.import_mcp_manifest(manifest, args.prefix)
            cell = importers.bind_import_cell(g, summary)
            rep = tick(g)
            return {"import": summary, "cell": cell.cell_id,
                    "version": g.cells[cell.cell_id].version,
                    "tick": rep.summary()}
        _emit(store.mutate(op), pretty=True)
        return 0

    if args.cmd == "in":
        def op(g: Graph):
            # pure write: keystrokes are cheap; evaluation debounces to tick
            g.set_input(args.cell, args.text)
            return {"cell": args.cell, "version": g.cells[args.cell].version,
                    "pending": True}
        _emit(store.mutate(op))
        return 0

    if args.cmd == "bind":
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError:
            value = args.value
        def op(g: Graph):
            c = g.bind_value(args.cell_id, value)
            return {"cell": c.cell_id, "version": c.version}
        _emit(store.mutate(op))
        return 0

    if args.cmd == "link":
        def op(g: Graph):
            c = g.link(args.cell_id, args.param, args.upstream)
            return {"cell": c.cell_id, "version": c.version}
        _emit(store.mutate(op))
        return 0

    if args.cmd == "fn":
        inputs = _parse_kv(args.ins)
        literals = _parse_kv(args.lits)
        kind = KIND_EFFECT if args.effect else KIND_FUNCTION
        def op(g: Graph):
            c = g.bind_fn(args.cell_id, args.tool, inputs=inputs,
                          literals=literals, kind=kind)
            rep = tick(g)
            return {"cell": c.cell_id, "version": g.cells[c.cell_id].version,
                    "value": g.cells[c.cell_id].value,
                    "tick": rep.summary()}
        _emit(store.mutate(op))
        return 0

    if args.cmd == "cron":
        import time as _t
        def op(g: Graph):
            cell_id = args.cell or f"cron:{args.expr}"
            g.bind_fn(cell_id, "cron_next", literals={"expr": args.expr},
                      cron=args.expr)
            g.cells[cell_id].last_fire = (args.start if args.start is not None
                                          else _t.time())
            rep = tick(g)
            c = g.cells[cell_id]
            return {"cell": cell_id, "version": c.version,
                    "value": c.value, "fired": rep.fired_crons}
        _emit(store.mutate(op))
        return 0

    if args.cmd == "tick":
        def op(g: Graph):
            rep = tick(g)
            return {"tick": rep.summary(), "evaluated": rep.evaluated,
                    "skipped_clean": rep.skipped_clean,
                    "crons_fired": rep.fired_crons,
                    "effects": rep.effects_run, "errors": rep.errors}
        _emit(store.mutate(op))
        return 0

    if args.cmd == "pipe":
        def op(g: Graph):
            if args.last:
                result_id, rep = pipe_last(g, _parse_kv(args.ins))
                return {"value": g.cells[result_id].value,
                        "cell": result_id, "replayed": rep.summary(),
                        "evaluated": rep.evaluated,
                        "skipped_clean": rep.skipped_clean}
            if not args.tool:
                raise SystemExit("pipe needs a tool or --last")
            result_id, created = run_pipe(
                g, [{"tool": args.tool, "args": _parse_kv(args.ins)}])
            return {"value": g.cells[result_id].value,
                    "cell": result_id, "cells": created}
        _emit(store.mutate(op))
        return 0

    if args.cmd == "out":
        g = store.load()
        return _out_n(g, args.n)

    if args.cmd == "again":
        def op(g: Graph):
            result_id, rep = again_op(g, _parse_kv(args.ins))
            return {"value": g.cells[result_id].value,
                    "cell": result_id, "tick": rep.summary(),
                    "evaluated": rep.evaluated}
        _emit(store.mutate(op))
        return 0

    if args.cmd == "forget":
        def op(g: Graph):
            tb = g.forget(args.cell_id)
            referenced = g.witness_referenced(args.cell_id)
            return {"tombstoned": tb.cell_id, "value_hash": tb.value_hash,
                    "witness_referenced": referenced,
                    "note": "hash-only record kept forever; trace still resolves"}
        _emit(store.mutate(op))
        return 0

    if args.cmd == "cold":
        def op(g: Graph):
            g.cold_downgrade(args.cell_id)
            return {"cold": args.cell_id,
                    "vhash": g.cells[args.cell_id].vhash,
                    "note": "value dropped; identity kept; re-derives on tick"}
        _emit(store.mutate(op))
        return 0

    if args.cmd == "graph":
        def op(g: Graph):
            if args.cell_id:
                c = g.cells.get(args.cell_id)
                if c is not None:
                    return c.to_dict()
                tb = g.tombstone_by_id(args.cell_id)
                if tb is not None:
                    return {"tombstone": tb.to_dict()}
                raise SystemExit(f"no such cell: {args.cell_id}")
            cells = [{"id": c.cell_id, "kind": c.kind, "v": c.version,
                      "fn": c.fn, "in": c.inputs, "cold": c.cold,
                      "err": c.error, "cron": c.cron}
                     for c in g.cells.values()]
            edges = [{"from": u, "to": c.cell_id, "param": p}
                     for c in g.cells.values()
                     for p, u in c.inputs.items()]
            return {"session": g.name, "root": g.root_id, "cells": cells,
                    "edges": edges, "tombstones":
                    [t.to_dict() for t in g.tombstones]}
        _emit(store.mutate(op), pretty=True)
        return 0

    if args.cmd == "witness":
        def op(g: Graph):
            closure = g.witness_closure(args.cell_id)
            trace = []
            for cid in sorted(closure):
                ver = closure[cid]
                live = g.cells.get(cid)
                if live is not None:
                    trace.append(f"{cid}@{ver} live/{live.kind}")
                else:
                    tb = g.tombstone_by_id(cid)
                    trace.append(f"{cid}@{ver} tombstone"
                                 f"/hash={tb.value_hash[:12] if tb else '?'}")
            return {"closure": trace}
        _emit(store.mutate(op), pretty=True)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
