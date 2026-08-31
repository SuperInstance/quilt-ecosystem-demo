"""Session store — one graph, two front doors (CLI argv + MCP stdio).

Hot cells / cold cells / tombstones live in separate files under
$TIT_HOME/sessions/<name>.{json,cold.json,tombstones.json}. Writes are
lock-guarded and atomic (temp + rename). The store IS the single source of
truth; there is no second in-memory authority to drift.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

from .cells import KIND_ROOT, Cell, Graph, Tombstone

LOCK_STALE_SECONDS = 15.0


def tit_home() -> Path:
    return Path(os.environ.get("TIT_HOME", str(Path.home() / ".tit")))


def sessions_dir() -> Path:
    return tit_home() / "sessions"


def slugify(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    if len(s) > 48:
        s = s[:40] + "-" + format(abs(hash(name)) & 0xFFFFFFFF, "08x")
    return s or "session"


def tmux_session_name() -> str | None:
    if not os.environ.get("TMUX"):
        return None
    try:
        out = subprocess.run(
            ["tmux", "display-message", "-p", "#S"],
            capture_output=True, text=True, timeout=5, check=True)
        return out.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def derive_session_name(cwd: str | None = None, tmux_sess: str | None = None) -> str:
    """Session file name from tmux session + cwd, so both front doors
    attaching from the same pane land on the same graph."""
    if os.environ.get("TIT_SESSION"):
        return slugify(os.environ["TIT_SESSION"])
    tmux_sess = tmux_sess if tmux_sess is not None else tmux_session_name()
    cwd = cwd or os.getcwd()
    if tmux_sess:
        raw = f"{tmux_sess}.{cwd}"
    else:
        raw = f"solo.{cwd}"
    return slugify(raw)


def root_cell_id(cwd: str, tmux_sess: str | None) -> str:
    return f"root:{tmux_sess or 'none'}:{cwd}"


class _Lock:
    """Simple O_EXCL lockfile with stale breaking. Prototype-grade."""

    def __init__(self, path: Path):
        self.path = path
        self.held = False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(50):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                self.held = True
                return self
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                    if age > LOCK_STALE_SECONDS:
                        self.path.unlink(missing_ok=True)  # stale — break it
                except FileNotFoundError:
                    pass
                time.sleep(0.05)
        raise TimeoutError(f"could not acquire lock {self.path}")

    def __exit__(self, *exc):
        if self.held:
            self.path.unlink(missing_ok=True)
        return False


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


class SessionStore:
    def __init__(self, name: str):
        self.name = slugify(name)
        self.dir = sessions_dir()
        self.hot_path = self.dir / f"{self.name}.json"
        self.cold_path = self.dir / f"{self.name}.cold.json"
        self.tomb_path = self.dir / f"{self.name}.tombstones.json"
        self.lock_path = self.dir / f"{self.name}.lock"

    def exists(self) -> bool:
        return self.hot_path.exists()

    def load(self) -> Graph:
        g = Graph(name=self.name)
        if self.hot_path.exists():
            doc = json.loads(self.hot_path.read_text(encoding="utf-8"))
            g = Graph.from_doc(doc)
        if self.cold_path.exists():
            cold_doc = json.loads(self.cold_path.read_text(encoding="utf-8"))
            for cd in cold_doc.get("cells", []):
                cd["cold"] = True
                cell = Cell.from_dict(cd)
                g.cells[cell.cell_id] = cell
        if self.tomb_path.exists():
            tb_doc = json.loads(self.tomb_path.read_text(encoding="utf-8"))
            g.tombstones = [Tombstone.from_dict(d) for d in tb_doc.get("tombstones", [])]
        return g

    def save(self, g: Graph) -> None:
        with _Lock(self.lock_path):
            hot = [c.to_dict() for c in g.cells.values() if not c.cold]
            cold = [c.to_dict() for c in g.cells.values() if c.cold]
            doc = g.to_doc()
            doc["cells"] = hot
            doc["saved_at"] = time.time()
            _atomic_write(self.hot_path, json.dumps(doc, indent=1, ensure_ascii=False))
            _atomic_write(self.cold_path, json.dumps(
                {"format": 1, "name": g.name, "cells": cold},
                indent=1, ensure_ascii=False))
            _atomic_write(self.tomb_path, json.dumps(
                {"format": 1, "tombstones": [t.to_dict() for t in g.tombstones]},
                indent=1, ensure_ascii=False))

    # ------------------------------------------------------------ attach

    def attach(self, cwd: str | None = None, tmux_sess: str | None = None) -> Graph:
        """Bind/create the session-root cell keyed by (tmux session, cwd).
        Survives agent death: the graph is a file; any door re-attaches."""
        g = self.load()
        cwd = cwd or os.getcwd()
        tmux_sess = tmux_sess if tmux_sess is not None else tmux_session_name()
        rid = root_cell_id(cwd, tmux_sess)
        now = time.time()
        root = g.cells.get(rid)
        if root is None:
            root = Cell(cell_id=rid, kind=KIND_ROOT, version=1, dirty=True,
                        value={"tmux_session": tmux_sess, "cwd": cwd,
                               "created": now, "last_seen": now})
            g.cells[rid] = root
        else:
            root.value = dict(root.value or {}, last_seen=now)
        g.root_id = rid
        self.save(g)
        return g

    def mutate(self, fn):
        """Load-modify-save under one lock — the drift-free door."""
        g = self.load()
        result = fn(g)
        self.save(g)
        return result


def list_sessions() -> list[dict]:
    out: list[dict] = []
    d = sessions_dir()
    if not d.exists():
        return out
    for hot in sorted(d.glob("*.json")):
        if hot.name.endswith((".cold.json", ".tombstones.json")):
            continue
        name = hot.stem
        try:
            doc = json.loads(hot.read_text(encoding="utf-8"))
            cells = doc.get("cells", [])
            roots = [c for c in cells if c.get("kind") == KIND_ROOT]
            tb = d / f"{name}.tombstones.json"
            n_tb = 0
            if tb.exists():
                n_tb = len(json.loads(tb.read_text(encoding="utf-8"))
                           .get("tombstones", []))
            out.append({
                "session": name,
                "cells": len(cells),
                "tombstones": n_tb,
                "root": roots[0]["value"] if roots else None,
                "saved_at": doc.get("saved_at"),
            })
        except (json.JSONDecodeError, OSError):
            continue
    return out
