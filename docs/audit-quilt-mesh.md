# Audit: quilt-mesh

Repo: https://github.com/SuperInstance/quilt-mesh
Commit: HEAD of `main` (depth-1 clone, 2026-08-31)
Auditor: foreman byte-level pass
Toolchain: rustc 1.98.0 stable

## Overview

A 256-line Rust crate that sketches the protocol for a broker-less CRDT mesh. Single source file (`src/lib.rs`), zero dependencies (all commented out in `Cargo.toml`), MIT-licensed, README-heavy. The crate's own opening comment is candid:

> *"This is a design sketch. The real implementation will be 4-5x this size and will use a real CRDT library (Yrs, Automerge, or a custom design)."*

That self-assessment is accurate. The protocol surface is real, the data structures are real, the tests run. The transport, the persistence, the auth, the conflict semantics — those are words on a page.

## What's real

- **`Lamport` clock** (`lib.rs:36-41`) — `tick()` and `observe()` are correct, causal-ordering correct.
- **`CellState::apply`** (`lib.rs:65-85`) — duplicate detection by `(lamport, author)`, recomputes value as max-by-lamport. Correct LWW-by-Lamport semantics.
- **`Mesh::set` / `receive` / `get`** (`lib.rs:129-160`) — three public methods, all working, tested.
- **`Mesh::pending_for`** (`lib.rs:164-179`) — diff-by-Lamport-filter against a peer's last-seen clock. Returns full event log if peer is unknown. Sorted by Lamport on output.
- **`CellEvent`** (`lib.rs:46-53`) — 5-field struct, `Clone + Debug`, the gossip payload. Carries `cell`, `value` (raw `Vec<u8>`), `author`, `lamport`, `wall_time_ms`.
- **3 unit tests pass** under `cargo test`:
  - `tests::two_peers_sync_a_cell` — ok
  - `tests::duplicate_events_are_ignored` — ok
  - `tests::offline_then_sync` — ok
- **`BTreeSet<PeerId>` field in `RoomState`** declared (dead, see below).
- **`ApplyResult::Conflict` variant** declared, never constructed.

## What's stub

- **No transport.** `gossip_with` (`lib.rs:184-190`) iterates `pending_for` and calls `self.receive` on its own events. The doc-comment even admits: *"In a real impl: send this ev to `peer` over the network."* Two `Mesh` instances in the same process call each other. That's it. No TCP, no UDP, no WebRTC, no LoRa, no Bluetooth — despite six of seven roadmap items being transports.
- **No persistence.** `wall_time_ms` is hard-coded to `0` in `set` (`lib.rs:139`). No `bincode`/`serde`/`rocksdb`/`sled` — all three are commented out in `Cargo.toml`.
- **No auth.** No signatures, no `ed25519`, no `PeerId` validation. A malicious peer can write any `author` it wants into a `CellEvent`.
- **No `Value` type.** README's API reference (`README.md:188-198`) advertises `pub fn set(..., value: Value)` and `pub fn get(...) -> Option<Value>`. Code uses `Vec<u8>` (`lib.rs:132, 158`). README lies.
- **No `VersionVector` type.** README advertises `pub fn version_vector(&self) -> &VersionVector;` (`README.md:197`). Code has no such struct — it stores per-peer Lamport as `HashMap<PeerId, Lamport>` (`lib.rs:116`) and only the leaf `pending_for` filters on it. No public accessor.
- **No `pending_events_for` method** (README:195). Real method is `pending_for`.
- **README API signatures are wrong.** Real `gossip_with` takes `(&mut self, room: &RoomId, peer: &PeerId)`; README claims `(&mut self, peer: &mut QuiltMesh)`. Real `set` takes a room; README shows none. Real `tick` / `observe` exist on `Lamport`, not on `QuiltMesh` as the README implies.
- **`ApplyResult::Conflict` is unreachable.** Declared at `lib.rs:91`, never returned anywhere. The merge is silent LWW.
- **`peers: BTreeSet<PeerId>`** field on `RoomState` (`lib.rs:114`) is never written, never read. Dead. (Compiler warns.)
- **`use BTreeMap`** and **`use std::time::Duration`** at top of `lib.rs:10-11` are both unused. Compiler warns.
- **No README `LICENSE` file** despite the badge pointing at one. Just the badge, no file.
- **No CI config.** No `.github/`. No `target/` ignores beyond `Cargo.lock`.

## Test count

**Real tests: 3.** All in `src/lib.rs` under `#[cfg(test)] mod tests`. All pass under `cargo test` (3 passed, 0 failed, 0 ignored). No integration tests, no doc tests, no examples, no fuzz targets, no property tests.

```
$ cargo test
running 3 tests
test tests::duplicate_events_are_ignored ... ok
test tests::offline_then_sync ... ok
test tests::two_peers_sync_a_cell ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

Test coverage gaps:
- No test for three+ peers.
- No test for `pending_for` itself.
- No test for `gossip_with` (the only thing that could catch the self-loop bug, but it's structurally incapable of failing because it only writes to self).
- No test for clock `observe()` advancing past an event with a higher Lamport.
- The `offline_then_sync` test (`lib.rs:232-255`) doesn't actually assert convergence — the comment at lines 251-253 admits it: *"Actually depends on order of operations — but the test is just that they converge."* It just checks both peers have *some* value.

## Top 1-day adds

In rough order of value-per-hour:

1. **Fix the `ApplyResult::Conflict` branch and write the test it deserves.** Add a peer-id tiebreak in `CellState::apply` (`lib.rs:70-84`) so two events at the same Lamport from different authors don't silently lose one. Then a test that constructs `(lamport=1, alice)` and `(lamport=1, bob)` and asserts both are preserved in `events` with a deterministic winner for `value`. ~50 lines, one afternoon, makes the CRDT claim actually true.

2. **`Value` newtype + bincode persistence.** Replace `Vec<u8>` with a `Value` enum (or just `serde_json::Value`) gated behind `#[cfg(feature = "persist")]`. Add `Mesh::save(&self, path: &Path)` / `Mesh::load(path: &Path) -> Result<Self, _>` that round-trips the whole rooms map. One file, two functions, ~80 lines, no design work needed because the event log is already the source of truth.

3. **Make `gossip_with` actually cross a boundary.** Add a `Transport` trait (`fn send(&self, peer: &PeerId, ev: CellEvent); fn recv(&mut self) -> Option<(PeerId, CellEvent)>;`) and a `LoopbackTransport` that pipes two meshes via `mpsc`. Rewrite `gossip_with` to call `transport.send` and drain `transport.recv` into `receive`. Now the README's "Phone ↔ laptop" use case has a shape. ~120 lines including the trait, and you can demo two threads syncing without the self-loop trick.

## The cowboy's take

This is a protocol sketch wearing a crate's clothes. It compiles, it tests, it doesn't lie about what it isn't — the file's first comment is "design sketch" and the author means it. The README is where the dishonesty lives: it ships a fictional API (`Value`, `VersionVector`, `pending_events_for`, the `gossip_with` signature) and pins a badge to a count that happens to be true for once.

For a 256-line file with zero deps and three passing tests, that's actually respectable. The `Mesh::set` / `receive` / `pending_for` triangle is the right shape for a CRDT-by-event-log mesh, and the Lamport logic is clean. The author knows where this is going (Yrs/Automerge in the doc-comment) and is using this crate to lock down the protocol surface before bolting on the real CRDT engine.

What it's *not*: a working mesh. Calling `gossip_with` on two `Mesh` values in the same process and watching them converge is a unit test, not a network. Six of seven roadmap items are transports, and the crate has zero transport code. The "phone ↔ laptop" demo in the README needs a transport it doesn't have.

Verdict: ship the protocol sketch, but don't put it in a use-case table next to "Phone ↔ laptop sync" until at least one of the three 1-day adds above lands. Number 3 is the one that earns the badge.
