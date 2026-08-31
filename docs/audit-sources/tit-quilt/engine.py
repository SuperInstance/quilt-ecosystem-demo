"""TICK — the evaluator. Crons advance on-demand, dirty cells evaluate in a
topological wavefront, clean witnesses are skipped (incremental replay).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .cells import (
    KIND_EFFECT, KIND_FUNCTION, Graph, value_hash,
)
from .cronexpr import CronExpr
from .importers import FOREIGN_TOOLS, has_foreign
from .tools import EFFECTS, TOOLS, run_effect, run_tool

MAX_CRON_CATCHUP = 100


@dataclass
class TickReport:
    evaluated: list[str] = field(default_factory=list)
    skipped_clean: list[str] = field(default_factory=list)
    fired_crons: list[dict] = field(default_factory=list)
    effects_run: list[dict] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        parts = [f"evaluated={len(self.evaluated)}",
                 f"skipped_clean={len(self.skipped_clean)}",
                 f"crons_fired={len(self.fired_crons)}",
                 f"effects={len(self.effects_run)}"]
        if self.errors:
            parts.append(f"errors={len(self.errors)}")
        return " ".join(parts)


def _advance_crons(g: Graph, now: float, report: TickReport) -> None:
    """On-demand cron ticking with correct catch-up: every missed fire bumps
    the version (downstream goes dirty), last_fire walks forward fire-by-fire."""
    now_dt = datetime.fromtimestamp(now, tz=timezone.utc)
    for cell in list(g.cells.values()):
        if not cell.cron or cell.kind not in (KIND_FUNCTION, KIND_EFFECT):
            continue
        expr = CronExpr(cell.cron)
        after_ts = cell.last_fire if cell.last_fire is not None else now
        after = datetime.fromtimestamp(after_ts, tz=timezone.utc)
        for _ in range(MAX_CRON_CATCHUP):
            fire = expr.next_fire(after)
            if fire.timestamp() > now:
                break
            cell.last_fire = fire.timestamp()
            after = fire
            cell.dirty = True
            cell.literals["after"] = fire.timestamp()
            report.fired_crons.append(
                {"cell": cell.cell_id, "fired_at": fire.isoformat()})
        else:
            report.errors[cell.cell_id] = "cron catch-up cap exceeded"


def _resolve_params(g: Graph, cell) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for k, uid in cell.inputs.items():
        upstream = g.cells.get(uid)
        if upstream is None:
            raise ValueError(f"input {uid!r} missing (tombstoned?)")
        if upstream.value is None and upstream.cold:
            raise ValueError(f"input {uid!r} is cold and cannot re-derive")
        params[k] = upstream.value
    params.update(cell.literals)
    return params


def _evaluate(g: Graph, cell, report: TickReport, effects: bool) -> None:
    if cell.kind == KIND_EFFECT:
        params = _resolve_params(g, cell)
        if not effects:
            new_value = {"deferred": True, "params": params}
        else:
            try:
                new_value = run_effect(cell.fn, params)
                report.effects_run.append(
                    {"cell": cell.cell_id, "effect": cell.fn})
            except Exception as exc:  # noqa: BLE001
                new_value, cell.error = None, f"{type(exc).__name__}: {exc}"
                report.errors[cell.cell_id] = cell.error
        _commit_value(g, cell, new_value, report)
        return

    # FUNCTION (or cold VALUE with inputs re-deriving)
    params = _resolve_params(g, cell)
    try:
        new_value = run_tool(cell.fn, params)
        cell.error = None
    except Exception as exc:  # noqa: BLE001
        new_value, cell.error = None, f"{type(exc).__name__}: {exc}"
        report.errors[cell.cell_id] = cell.error
    _commit_value(g, cell, new_value, report)


def _commit_value(g: Graph, cell, new_value, report: TickReport) -> None:
    """Seal a computed value: bump version only when content identity
    changes (vhash). Cold re-derivation of identical content keeps the
    version — provenance identity survives cold."""
    new_hash = value_hash(new_value)
    if cell.vhash is not None and new_hash != cell.vhash:
        cell.version += 1  # content identity: cell@version pins one value
    cell.value = new_value
    cell.vhash = new_hash
    cell.cold = False
    cell.witness = frozenset(
        (uid, g.cells[uid].version) for uid in cell.inputs.values())
    cell.dirty = False
    report.evaluated.append(cell.cell_id)


def _witness_matches(g: Graph, cell) -> bool:
    for uid, ver in cell.witness:
        up = g.cells.get(uid)
        if up is None or up.version != ver:
            return False
    return True


def tick(g: Graph, now: float | None = None, effects: bool = True) -> TickReport:
    """Evaluate the wavefront downstream of all dirty cells, in topo order.

    Cold FUNCTION cells re-derive (their recomputed hash must match the
    provenance they left behind — a free integrity check). Cells whose
    witness already matches are skipped: only changed edges replay.
    """
    now = now if now is not None else time.time()
    report = TickReport()
    _advance_crons(g, now, report)

    # cold function cells with inputs re-derive: mark dirty
    for cell in g.cells.values():
        if cell.cold and cell.kind == KIND_FUNCTION and cell.inputs:
            cell.dirty = True

    seeds = {cid for cid, c in g.cells.items() if c.dirty}
    closure: set[str] = set(seeds)
    for s in list(seeds):
        closure |= g.downstream(s)
    if not closure:
        return report

    # Kahn topological order over the induced subgraph
    children: dict[str, set[str]] = {cid: set() for cid in closure}
    indeg: dict[str, int] = {cid: 0 for cid in closure}
    for cid in closure:
        for uid in g.cells[cid].inputs.values():
            if uid in closure:
                children[uid].add(cid)
                indeg[cid] += 1
    queue = sorted(cid for cid, d in indeg.items() if d == 0)
    order: list[str] = []
    while queue:
        cid = queue.pop(0)
        order.append(cid)
        for child in sorted(children[cid]):
            indeg[child] -= 1
            if indeg[child] == 0:
                queue.append(child)
    # cycles can't be built via bind_fn/link (inputs must pre-exist) — but guard
    for cid in sorted(set(closure) - set(order)):
        report.errors[cid] = "cycle detected; skipped"

    for cid in order:
        cell = g.cells[cid]
        if cell.kind in (KIND_FUNCTION, KIND_EFFECT):
            if (not cell.dirty and cell.value is not None
                    and _witness_matches(g, cell)):
                report.skipped_clean.append(cid)
                continue
            _evaluate(g, cell, report, effects)
        else:
            # VALUE / INPUT / ROOT: value already bound; seal the witness
            cell.dirty = False
            report.evaluated.append(cid)
    return report


# ---------------------------------------------------------------- pipelines

def run_pipe(g: Graph, steps: list[dict], name_prefix: str = "pipe") -> tuple:
    """Build a chain: head VALUE cells for literal args of step 1, then one
    FUNCTION cell per step, each linked to the previous step's output.
    Returns (result_cell_id, created_cell_ids)."""
    if not steps:
        raise ValueError("pipe needs at least one step")
    created: list[str] = []
    heads: dict[str, str] = {}
    first = steps[0]
    for arg_name, arg_val in sorted(first.get("args", {}).items()):
        head_id = f"{name_prefix}.in.{arg_name}"
        g.bind_value(head_id, arg_val)
        heads[arg_name] = head_id
        created.append(head_id)

    prev: str | None = None
    for i, step in enumerate(steps):
        tool = step["tool"]
        if tool not in TOOLS and not has_foreign(tool):
            raise ValueError(f"unknown tool: {tool}")
        spec = TOOLS.get(tool) or FOREIGN_TOOLS[tool]
        cell_id = f"{name_prefix}.{i}.{tool}"
        inputs: dict[str, str] = {}
        if prev is not None:
            primary = _primary_param(tool)
            if primary:
                inputs[primary] = prev
        for arg_name, head_id in heads.items():
            if arg_name in spec["params"] and arg_name not in inputs:
                inputs[arg_name] = head_id
        literals = {k: v for k, v in step.get("args", {}).items()
                    if k not in inputs and k in spec["params"]}
        g.bind_fn(cell_id, tool, inputs=inputs, literals=literals)
        created.append(cell_id)
        prev = cell_id

    g.last_pipe = list(created)
    tick(g)
    g.push_result(prev)
    return prev, created


def _primary_param(tool_name: str) -> str | None:
    spec = TOOLS.get(tool_name) or FOREIGN_TOOLS.get(tool_name) or {}
    req = spec.get("required", [])
    return req[0] if req else None


def pipe_last(g: Graph, inputs: dict[str, Any]) -> tuple:
    """Replay the last pipeline with new inputs — only changed edges re-fire.
    Returns (result_cell_id, TickReport)."""
    if not g.last_pipe:
        raise ValueError("no previous pipeline to replay")
    head_ids = [cid for cid in g.last_pipe if ".in." in cid]
    for arg_name, new_val in inputs.items():
        matches = [h for h in head_ids if h.endswith(f".in.{arg_name}")]
        if not matches:
            raise ValueError(f"no pipeline head for input {arg_name!r}")
        g.bind_value(matches[0], new_val)
    result_id = g.last_pipe[-1]
    report = tick(g)
    g.push_result(result_id)
    return result_id, report


def again(g: Graph, inputs: dict[str, Any]) -> tuple:
    """Re-BIND VALUE cells inside the last result's witness closure and
    re-tick — re-attaching a persisted subgraph after agent death."""
    result = g.last_result
    if result is None:
        raise ValueError("no previous result to re-run")
    closure = g.witness_closure(result.cell_id)
    bound: list[str] = []
    for key, new_val in inputs.items():
        targets = [cid for cid in closure
                   if cid in g.cells and g.cells[cid].kind in ("VALUE", "INPUT")
                   and (cid == key or cid.endswith(f".{key}")
                        or cid.endswith(f".in.{key}"))]
        if not targets:
            raise ValueError(f"no VALUE cell matching --in {key!r} in witness closure")
        g.bind_value(targets[0], new_val)
        bound.append(targets[0])
    report = tick(g)
    g.push_result(result.cell_id)
    return result.cell_id, report
