"""Cells, edges, witness sets — the graph at the heart of tit.

A session is a directed graph of cells. VALUE/INPUT cells hold data,
FUNCTION cells compute (pure), EFFECT cells touch the world, ROOT cells key
a session to (tmux session, cwd). Edges are function-cell input wires.
Witness sets record the exact upstream versions a value was computed from.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from hashlib import sha256 as _sha256
from typing import Any, Iterable

KIND_VALUE = "VALUE"
KIND_INPUT = "INPUT"
KIND_FUNCTION = "FUNCTION"
KIND_EFFECT = "EFFECT"
KIND_ROOT = "ROOT"

CELL_REF_RE = re.compile(r"^(?:[A-Za-z0-9._-]+/)?([A-Za-z0-9._:@-]+)@(\d+)$")


def canon(value: Any) -> str:
    """Canonical JSON serialization — the hashing basis for provenance."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def value_hash(value: Any) -> str:
    return _sha256(canon(value).encode("utf-8")).hexdigest()


def parse_cell_ref(text: str) -> tuple[str, int] | None:
    """Accept 'cell@3' or 'session/cell@3' -> ('cell', 3)."""
    m = CELL_REF_RE.match(text.strip())
    if not m:
        return None
    return m.group(1), int(m.group(2))


@dataclass
class Cell:
    cell_id: str
    kind: str = KIND_VALUE
    value: Any = None
    version: int = 1
    fn: str | None = None
    inputs: dict[str, str] = field(default_factory=dict)      # param -> upstream cell_id
    literals: dict[str, Any] = field(default_factory=dict)
    witness: frozenset[tuple[str, int]] = field(default_factory=frozenset)
    dirty: bool = True
    error: str | None = None
    cron: str | None = None
    last_fire: float | None = None
    cold: bool = False
    vhash: str | None = None  # content identity; survives cold (value=None)
    created: float = field(default_factory=time.time)

    def witness_strs(self) -> list[str]:
        return sorted(f"{cid}@{ver}" for cid, ver in self.witness)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "kind": self.kind,
            "value": self.value,
            "version": self.version,
            "fn": self.fn,
            "inputs": dict(sorted(self.inputs.items())),
            "literals": self.literals,
            "witness": self.witness_strs(),
            "dirty": self.dirty,
            "error": self.error,
            "cron": self.cron,
            "last_fire": self.last_fire,
            "cold": self.cold,
            "vhash": self.vhash,
            "created": self.created,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Cell":
        wit = frozenset(
            (part.rsplit("@", 1)[0], int(part.rsplit("@", 1)[1]))
            for part in d.get("witness", [])
        )
        return cls(
            cell_id=d["cell_id"],
            kind=d.get("kind", KIND_VALUE),
            value=d.get("value"),
            version=int(d.get("version", 1)),
            fn=d.get("fn"),
            inputs=dict(d.get("inputs", {})),
            literals=dict(d.get("literals", {})),
            witness=wit,
            dirty=bool(d.get("dirty", False)),
            error=d.get("error"),
            cron=d.get("cron"),
            last_fire=d.get("last_fire"),
            cold=bool(d.get("cold", False)),
            vhash=d.get("vhash"),
            created=float(d.get("created", time.time())),
        )


@dataclass
class Tombstone:
    """Hash-only record of a FORGOTTEN cell. Append-only, never deleted."""

    cell_id: str
    kind: str
    version: int
    value_hash: str
    fn: str | None
    inputs: dict[str, str]
    literals: dict[str, Any]
    witness: frozenset[tuple[str, int]]
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "kind": self.kind,
            "version": self.version,
            "value_hash": self.value_hash,
            "fn": self.fn,
            "inputs": dict(sorted(self.inputs.items())),
            "literals": self.literals,
            "witness": sorted(f"{c}@{v}" for c, v in self.witness),
            "ts": self.ts,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Tombstone":
        wit = frozenset(
            (p.rsplit("@", 1)[0], int(p.rsplit("@", 1)[1]))
            for p in d.get("witness", [])
        )
        return cls(
            cell_id=d["cell_id"], kind=d.get("kind", KIND_VALUE),
            version=int(d.get("version", 1)), value_hash=d.get("value_hash", ""),
            fn=d.get("fn"), inputs=dict(d.get("inputs", {})),
            literals=dict(d.get("literals", {})), witness=wit,
            ts=float(d.get("ts", 0)),
        )


@dataclass
class Graph:
    """A session: live cells + tombstones + result history."""

    name: str
    cells: dict[str, Cell] = field(default_factory=dict)
    tombstones: list[Tombstone] = field(default_factory=list)
    results: list[str] = field(default_factory=list)      # stack of result cell ids
    last_pipe: list[str] = field(default_factory=list)    # head cells of last pipeline
    root_id: str | None = None
    created: float = field(default_factory=time.time)

    # ------------------------------------------------------------------ bind

    def bind_value(self, cell_id: str, value: Any, kind: str = KIND_VALUE) -> Cell:
        cell = self.cells.get(cell_id)
        if cell is None:
            cell = Cell(cell_id=cell_id, kind=kind, value=value, version=1, dirty=True)
            self.cells[cell_id] = cell
            return cell
        if canon(cell.value) == canon(value) and not cell.cold:
            return cell  # same content — no bump, no churn
        cell.kind, cell.cold, cell.error = kind, False, None
        cell.value = value
        cell.vhash = value_hash(value)
        cell.version += 1
        cell.dirty = True
        return cell

    def set_input(self, cell_id: str, text: str) -> Cell:
        """Keystroke write. Always an event: every write bumps the version.
        Debounce happens at evaluation level — many writes, one wavefront."""
        cell = self.cells.get(cell_id)
        if cell is None:
            cell = Cell(cell_id=cell_id, kind=KIND_INPUT, value=text, version=1,
                        dirty=True)
            self.cells[cell_id] = cell
            return cell
        cell.kind, cell.cold = KIND_INPUT, False
        cell.value, cell.version, cell.dirty = text, cell.version + 1, True
        cell.vhash = value_hash(text)
        return cell

    def bind_fn(
        self,
        cell_id: str,
        fn: str,
        inputs: dict[str, str] | None = None,
        literals: dict[str, Any] | None = None,
        kind: str = KIND_FUNCTION,
        cron: str | None = None,
    ) -> Cell:
        inputs = dict(inputs or {})
        literals = dict(literals or {})
        cell = self.cells.get(cell_id)
        sig = {"fn": fn, "inputs": inputs, "literals": literals, "cron": cron}
        if cell is None:
            cell = Cell(cell_id=cell_id, kind=kind, fn=fn, inputs=inputs,
                        literals=literals, cron=cron, version=1, dirty=True)
            self.cells[cell_id] = cell
            return cell
        same = (cell.fn == fn and dict(cell.inputs) == inputs
                and canon(cell.literals) == canon(literals) and cell.cron == cron
                and not cell.cold)
        if same:
            return cell
        cell.kind, cell.fn = kind, fn
        cell.inputs, cell.literals, cell.cron = inputs, literals, cron
        cell.cold, cell.error = False, None
        cell.version += 1
        cell.dirty = True
        return cell

    def link(self, cell_id: str, param: str, upstream_id: str) -> Cell:
        """Wire (or rewire) one input edge. Structural change -> version bump."""
        cell = self.cells[cell_id]
        if cell.inputs.get(param) == upstream_id:
            return cell
        cell.inputs[param] = upstream_id
        cell.version += 1
        cell.dirty = True
        return cell

    # ------------------------------------------------------------- structure

    def children_of(self, cell_id: str) -> set[str]:
        return {c.cell_id for c in self.cells.values()
                if cell_id in c.inputs.values()}

    def downstream(self, cell_id: str) -> set[str]:
        """Transitive downstream closure (excluding the seed)."""
        seen: set[str] = set()
        frontier = {cell_id}
        while frontier:
            nxt: set[str] = set()
            for cid in frontier:
                for child in self.children_of(cid):
                    if child not in seen:
                        seen.add(child)
                        nxt.add(child)
            frontier = nxt
        return seen

    # ---------------------------------------------------------------- witness

    def witness_closure(self, cell_id: str) -> dict[str, int]:
        """Transitive witness {cell_id: version}, walking live cells then
        tombstones. The provenance integrity law: tombstoned upstreams still
        resolve here — identity + version survive FORGET."""
        out: dict[str, int] = {}
        frontier: list[tuple[str, int]] = []
        cell = self.cells.get(cell_id)
        if cell is not None:
            out[cell_id] = cell.version
            frontier = list(cell.witness)
        else:
            tb = self.tombstone_by_id(cell_id)
            if tb is None:
                return out
            out[cell_id] = tb.version
            frontier = list(tb.witness)
        while frontier:
            cid, ver = frontier.pop()
            if cid in out:
                continue
            out[cid] = ver
            live = self.cells.get(cid)
            if live is not None and live.version == ver:
                frontier.extend(live.witness)
            else:
                tb = self.tombstone_by_id(cid)
                if tb is not None:
                    frontier.extend(tb.witness)
        return out

    def tombstone_by_id(self, cell_id: str) -> Tombstone | None:
        for tb in reversed(self.tombstones):
            if tb.cell_id == cell_id:
                return tb
        return None

    def witness_referenced(self, cell_id: str) -> bool:
        """Is cell_id inside any live cell's (or tombstone's) witness closure?"""
        for cell in self.cells.values():
            if cell_id in self.witness_closure(cell.cell_id) and cell.cell_id != cell_id:
                return True
        for tb in self.tombstones:
            closure = {cid for cid, _ in self._tombstone_closure(tb)}
            if cell_id in closure and cell_id != tb.cell_id:
                return True
        return False

    def _tombstone_closure(self, tb: Tombstone) -> list[tuple[str, int]]:
        out: dict[str, int] = {tb.cell_id: tb.version}
        frontier = list(tb.witness)
        while frontier:
            cid, ver = frontier.pop()
            if cid in out:
                continue
            out[cid] = ver
            live = self.cells.get(cid)
            if live is not None and live.version == ver:
                frontier.extend(live.witness)
            else:
                t2 = self.tombstone_by_id(cid)
                if t2 is not None:
                    frontier.extend(t2.witness)
        return list(out.items())

    # ------------------------------------------------------------- retention

    def cold_downgrade(self, cell_id: str) -> Cell:
        """hot -> cold: drop the value, keep structure AND content identity
        (vhash). FUNCTION cells re-derive on next tick — if the recomputed
        hash matches vhash, the version does NOT bump: identity survives cold."""
        cell = self.cells[cell_id]
        cell.value = None
        cell.cold = True
        cell.dirty = True  # needs re-derivation if it has inputs
        return cell

    def forget(self, cell_id: str) -> Tombstone:
        """FORGET -> tombstone. The value is dropped and replaced by its hash;
        identity, version, and witness chain survive forever. Idempotent:
        re-forgetting returns the existing record. There is no delete path
        in tit — witness-referenced or not, the record stays."""
        existing = self.tombstone_by_id(cell_id)
        if existing is not None:
            return existing
        cell = self.cells[cell_id]
        h = cell.vhash or value_hash(cell.value)
        tb = Tombstone(
            cell_id=cell.cell_id, kind=cell.kind, version=cell.version,
            value_hash=h, fn=cell.fn, inputs=dict(cell.inputs),
            literals=dict(cell.literals), witness=frozenset(cell.witness),
        )
        self.tombstones.append(tb)
        del self.cells[cell_id]
        self.results = [r for r in self.results if r != cell_id]
        return tb

    # ------------------------------------------------------------- results

    def push_result(self, cell_id: str) -> None:
        if cell_id in self.cells:
            self.results.append(cell_id)
            del self.results[:-64]

    @property
    def last_result(self) -> Cell | None:
        while self.results:
            cell = self.cells.get(self.results[-1])
            if cell is not None:
                return cell
            self.results.pop()
        return None

    # ---------------------------------------------------------- persistence

    def to_doc(self) -> dict[str, Any]:
        return {
            "format": 1,
            "name": self.name,
            "root_id": self.root_id,
            "created": self.created,
            "cells": [c.to_dict() for c in self.cells.values()],
            "results": list(self.results),
            "last_pipe": list(self.last_pipe),
        }

    @classmethod
    def from_doc(cls, doc: dict[str, Any]) -> "Graph":
        g = cls(name=doc.get("name", "session"))
        g.root_id = doc.get("root_id")
        g.created = float(doc.get("created", time.time()))
        for cd in doc.get("cells", []):
            c = Cell.from_dict(cd)
            g.cells[c.cell_id] = c
        g.results = list(doc.get("results", []))
        g.last_pipe = list(doc.get("last_pipe", []))
        return g


def cell_ref(g: Graph, cell: Cell) -> str:
    return f"{g.name}/{cell.cell_id}@{cell.version}"
