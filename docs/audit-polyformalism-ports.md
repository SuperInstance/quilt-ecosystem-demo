# Quilt Polyformalism Ports — Audit (2026-08-20)

**Auditor:** API scout · **Scope:** 10 new ports under `github.com/SuperInstance/*` · **Method:** GitHub REST metadata + tree + key-file fetch

## TL;DR

**The polyformalism promise is not real for 9 of 10 ports.** Only `quilt-pydantic-ai` ships code. The other 9 are READMEs-only: a license, a splash image, and a *manifesto* describing what the port *should* be. They are consistent, well-written manifestos — but a README is not a port.

## 1. Per-port verdict

| # | Port | Lang | Files (blobs) | Src files | Tests | Opcodes (5+1) | Polyformalism real? |
|---|------|------|---------------|-----------|-------|----------------|---------------------|
| 1 | quilt-pydantic-ai | Python | 27 | 7 | **41** | VALUE, FORMULA, LISTENER, API, AI (+PROGRAM/SENSOR/ROUTER/VECTOR in enum) | **YES** — the only real port |
| 2 | quilt-swift | Swift | 3 | 0 | 0 | none in code | NO — README only |
| 3 | quilt-metal | Metal | 3 | 0 | 0 | none | NO — README only |
| 4 | quilt-csharp | C# | 3 | 0 | 0 | none | NO — README only |
| 5 | quilt-cpp | C++ | 3 | 0 | 0 | none | NO — README only |
| 6 | quilt-cobol | COBOL | 3 | 0 | 0 | none | NO — README only |
| 7 | quilt-c | C | 3 | 0 | 0 | none | NO — README only |
| 8 | quilt-chapel | Chapel | 3 | 0 | 0 | none | NO — README only |
| 9 | quilt-julia | Julia | 3 | 0 | 0 | none | NO — README only |
| 10 | quilt-mojo | Mojo | 3 | 0 | 0 | none | NO — README only |

**Opcode presence** is checked against the 5+1 model (SET, GET, COMPUTE, LISTEN, FETCH + ROUTE). In `quilt-pydantic-ai`: `set`, `get`, `compute` (formula), `fire_sync` (listener), `add_cell` (the API), and `ask` (agent/route) are all present as methods on `ReactiveEngine`, `Sheet`, and `QuiltAgent`. CellKind enum declares all 9 kinds even though only 5 are class-implemented. **Test count breakdown for the Python port:**

| Test file | Tests |
|-----------|-------|
| test_engine.py | 13 |
| test_reactive.py | 11 |
| test_query.py | 11 |
| test_agent.py | 6 |
| **Total** | **41** |

## 2. The 3 most complete ports

There is only one. Ranking the rest by *promise* of the manifesto:

1. **quilt-pydantic-ai** — 7 source modules, 41 tests, full reactive engine, 5 implemented cell kinds, Pydantic-AI integration, LINQ-style query language. The polyformalism *works*: the same engine model is "what Python's runtime would look like if you gave it Pydantic types."
2. **quilt-c** (README-only) — the manifesto is the most concrete: "a `struct`, a function pointer, a list of dependents." This is the smallest possible *real* implementation, so the README almost is a spec.
3. **quilt-swift** (README-only) — strongest polyformalism *thesis*: `@Published` ≅ ValueCell, Combine ≅ reactive engine, actors ≅ cell isolation. The 1:1 mapping claim is sharpest here.

## 3. The 3 weakest ports

All 9 empty ports are equally weak. The three with the *weakest manifestos* (most hand-waving, least code-shaped):

1. **quilt-metal** — "GPU-evaluated cells" is a slogan. The README never explains host/device split, kernel launch, or how reactive graph updates survive a compute pass. A Metal port needs a `.metal` file and a host wrapper; neither exists.
2. **quilt-cobol** — the "cell model is older than spreadsheets" thesis is interesting but the README is pure nostalgia. No mention of fixed-format vs free-form, no record schema, no paragraph chain.
3. **quilt-mojo** — "cells as types, SIMD-friendly" promises compile-time cell kinds but Mojo's stdlib moved since the README was written; no `Package.toml`, no example.

## 4. Cross-port gaps — where polyformalism breaks

| Gap | Evidence | Impact |
|-----|----------|--------|
| **1 real + 9 manifestos** | Tree returns 3 files for 9/10 repos | The "N languages" claim is **9/10 false**. The reader is sold a quilt and given one patch. |
| **No shared conformance test** | Each empty port can't run any test | A "polyformalism port" without a test suite is a vibe, not a port. |
| **No cross-port serializer** | TypeScript ↔ Python works; Swift/COBOL/Metal have no JSON ↔ native schema | Federation story is half-told. |
| **Opcodes ≠ in code** | All 10 READMEs claim 5+1 opcodes; only Python has 5 of them as methods | The 5+1 contract is a slide, not a spec. |

**Which 2-3 ports to bring up to match pydantic-ai (priority order):**

1. **quilt-c** — smallest spec, runs anywhere, easy CI, and it is the "mathematical core" the others implicitly depend on.
2. **quilt-csharp** — the README claims LINQ + records + events. Records *are* cells, `IEnumerable<T>` *is* a sheet. One .csproj, one file, one test project, and this port becomes the enterprise flagship.
3. **quilt-julia** — multiple dispatch maps to `CellKind` cleanly. Julia's `struct` + `Method` overloads = the 9 cell kinds as a 1:1 dispatch table. ~200 lines for a real port.

## 5. Recommendation — the cowboy has 1 day

| Hours | Port | What "done" looks like |
|-------|------|------------------------|
| 0–4 | **quilt-c** | `cell.h`, `engine.c`, `Makefile`, `tests/test_engine.c`, README updated to point at `make test` |
| 4–7 | **quilt-csharp** | `Quilt.csproj`, `Cell.cs`, `Sheet.cs`, `ReactiveEngine.cs`, xUnit project, ≥10 tests |
| 7–9 | **quilt-julia** | `src/Quilt.jl`, test/runtests.jl, ≥10 tests, dispatch on `CellKind` |
| 9–10 | cross-port | Add a `conformance/` test fixture (10 cells, 1 API, 1 listener) and run it from the Python port as the spec |

**Why this order:** C is the *minimum viable cell* — if `quilt-c` works, the polyformalism thesis ("same cell, same 5+1 opcodes, N languages") is no longer a single-language claim. C# gives you LINQ-validated enterprise reach. Julia gives you the dispatch-shaped port (the README's whole thesis). Metal/COBOL/Mojo can stay as manifestos for another day — none of them proves anything C# and Julia don't prove first.

**Skip for day 1:** quilt-metal (needs GPU CI), quilt-cobol (no free CI), quilt-mojo (toolchain churn). Their READMEs are fine; the code can wait.

---

**Bottom line:** The "polyformalism" of these 10 ports is currently *polyformalism = 1*. The cowboy doesn't have a quilt — he has a patch and 9 post-it notes saying where the other patches should go.
