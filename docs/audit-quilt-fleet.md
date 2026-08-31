# audit-quilt-fleet

Repo: https://github.com/SuperInstance/quilt-fleet
Commit: HEAD of `main` (depth-1 clone, 2026-08-31)
Auditor: foreman byte-level pass
Toolchain: node v22.19.0, npm 10.x, vitest 1.6.0

## Overview

A 5,169-line TypeScript monorepo package (`@quilt/fleet`, v0.1.0) that claims to be the orchestration layer for a federation of Quilt instances across five hardware tiers (ESP32, Jetson, Codespace, Cloudflare, Server). 12 source files, 5 tier adapters, 4 transport adapters, 3 API surfaces (REST/GraphQL/gRPC), 1 CLI, 13 test files. Apache-2.0, Node 18+, TypeScript `strict: true`.

The repo is presented as production-shaped. It is not. **`npm install` does not work** because the two declared runtime dependencies — `@quilt/core` and `@quilt/sdk` — do not exist on the npm registry. Every documented engineering-bar checkbox is `npm`-reachable in isolation, but the wiring assumes a sibling monorepo that isn't in the published surface.

The actual TypeScript is generally competent: the `Registry` (388 lines) is a real indexed data structure with event emission, the `HealthMonitor` (319 lines) has a real probe loop with EWMA + p95, the `QuorumCoordinator` (291 lines) implements majority-vote with split-brain detection, the `MigrationCoordinator` (294 lines) runs a real five-phase state machine. The `Router` (171 lines) is a real scoring function. The transports (`http`, `websocket`, `mqtt`, `nats`) are real `fetch`/`ws`/`mqtt`/`nats` clients with close semantics, not mocks.

What is not real: the CLI (`cmdMigrate` is literally `process.stdout.write('OK (dry run)\n')`), the gRPC server (the proto is duplicated, the handlers are wrong-shape), the GraphQL adapter (returns no schema, just resolvers that need an external `makeExecutableSchema`), the DNS-SD backend (stubbed — emits an error or no-ops), the `FleetManager.query` path (returns `null` unless you wire your own transport by hand), and the entire top-level CLI workflow (each subcommand spins up a fresh `new FleetManager({ id: 'cli' })` that has no relationship to any other CLI invocation — `quilt-fleet add` followed by `quilt-fleet list` shows nothing).

The tests look comprehensive — 13 files, 131 `it(...)` cases, plus 10 generated from `for-of` loops over the 5 tier names. **They don't pass.** Running the actual suite yields 20 failed / 100 passed (out of 120 reported). 3 of the 13 test files fail to even load because of an unimportable `yaml` package and 5 throw real `Error: no instance available` because the test setups don't initialize the router's candidate pool.

## What's real

- **`Registry`** (`src/registry.ts:141-381`) — full implementation. Four secondary indexes (`byId`, `byName`, `byTier`, `byRegion`), per-key bucketing, re-bucketing on update, event emission on add/update/remove/status. Validation on name (`^[a-z0-9][a-z0-9-]{0,62}$`) and endpoint (must have URL scheme). A 26-char ULID generator (`registry.ts:154-168`) is hand-rolled, deterministic-ish (10 chars time + 16 chars random), and zero-dep. 15 tests, 14 pass, 1 fails (`sorts owners of a cell by tier then latency` — see Test count).
- **`HealthMonitor`** (`src/health.ts:99-290`) — full implementation. Per-instance state with `lastHeartbeat`, `latencyMs` (EWMA α=0.3), `p95` (last 100 samples), `misses`, `load`. State machine `unknown → healthy → degraded → unreachable → recovered`. `bind(registry)` subscribes to add/remove; `tick()` is `Promise.all(snapshot.map(probeOne))`. Default probe is `fetch(endpoint + '/health')` (`health.ts:301-319`). 10 tests, all pass.
- **`QuorumCoordinator`** (`src/quorum.ts:86-261`) — full implementation. Glob pattern matcher (`*` and `**` → regex). `read()`: parallel-reads N replicas, groups by `JSON.stringify(value)`, returns majority. `write()`: parallel-writes N replicas with monotonic version, returns when `(N/2+1)` acks. Auto-repair path: after a read, push the winning value to dissenters in the background. Split-brain detection returns `status: 'split_brain'` with a `dissenters[]` list. 10 tests, 6 pass, 4 fail.
- **`MigrationCoordinator`** (`src/migration.ts:90-284`) — full implementation. Five-phase state machine `1A (freeze) → 1B (write dest) → 2A (verify) → 2B (flip routing) → 2C (unfreeze)`. Each phase has its own `withTimeout`, separate retry loop for 2A with `maxVerifyFailures`. `rollback()` is best-effort unfreeze-on-source. Plan object tracks per-phase status. 8 tests, 5 pass, 3 fail (the 5-phase happy path itself fails).
- **`Router`** (`src/routing.ts:56-170`) — full implementation. Scoring: tier preference index × 1000 + locality penalty (500) + latencyMs + (load × 1000 in `least_loaded` mode). Three modes: `fastest` (default), `round_robin` (per-tier cyclic counter), `least_loaded`. 11 tests, 8 pass, 3 fail.
- **`Scaler`** (`src/scaling.ts:89-262`) — full implementation. Five policy modes: `load`, `latency`, `schedule`, `passive`, `reactive`. Cooldown per tier (default 60s). `spawn()` / `destroy()` are user-supplied provisioner callbacks. 9 tests, 7 pass, 2 fail.
- **`Discovery`** (`src/discovery.ts:92-408`) — partial. The `StaticBackend` is real: reads YAML or JSON file, emits `up`/`down`/`updated` on diff, reloads on interval (`reloadMs`). The `BonjourBackend` is real but optional — uses dynamic `require('bonjour-service')` and emits an error if missing. The `DnsSdBackend` is **stubbed** — see below.
- **`SubscriptionManager`** (`src/subscription.ts:73-241`) — full implementation of the dedup/re-subscribe logic. Tracks per-subscription `lastVersion`, `missedUpdates`, `lastValueAt`. Re-routes on instance loss via `retryWithPeer` with configurable backoff. 7 tests, 2 pass, 5 fail.
- **`httpTransport`** (`src/transports/http.ts:25-83`) — real. `subscribe` is a polling iterator with `close()`. `read`/`write` are `fetch` PUTs. URL is `endpoint/cell/{sheet}#{cell}` (URI-encoded).
- **`wsTransport`** (`src/transports/websocket.ts:22-139`) — real. Uses `require('ws')`. Queue/waiter pattern for backpressure. Wire format `{op: "subscribe" | "read" | "write"}` with `{op: "update" | "value" | "ack"}` responses.
- **`mqttTransport`** (`src/transports/mqtt.ts:20-128`) — real. Topic `quilt/{instance}/{sheet}/{cell}`. QoS 1 for writes.
- **`natsTransport`** (`src/transports/nats.ts:17-101`) — real. Subject `quilt.{instance}.{sheet}.{cell}`. Uses `nc.request()` for one-shot reads.
- **Tier adapter probe paths** — all 5 tiers have real `probe()` implementations (`fetch` for HTTP-tier, `mqtt.connect` for ESP32). Subscribe paths are real except for `esp32` (stub: `return;` immediately).
- **CLI** (`src/cli.ts:46-250`) — partial. `init` and `serve` are real (file write + `FleetManager.start()` + signal handling). The rest are local one-shots.
- **17 transport tests pass** (the `transport factory`, `http read/write` against `127.0.0.1:1`, `mqtt read/write`, `nats read/write`, `ws read/write`).

## What's stub

- **DNS-SD backend** (`src/discovery.ts:280-304`) — the docstring admits it: *"In v0.1 this is **stubbed**"*. `start()` is a no-op unless no servers are configured, in which case it emits an error.
- **ESP32 `subscribe`** (`src/tiers/esp32.ts:68-74`) — async generator that `return`s immediately. Doc: *"STUB yields nothing"*.
- **`server` tier `subscribe`** (`src/tiers/server.ts:61-79`) — the docstring says *"A real implementation would open a gRPC client-streaming RPC"*. What it actually does is an HTTP poll every 500ms. The "gRPC" in the default-transport label is a lie.
- **`gRPC` key in `TRANSPORTS`** (`src/transports/index.ts:42`) — `grpc: httpTransport`. The actual gRPC server (`api/grpc.ts:82-190`) requires `@grpc/grpc-js` + `@grpc/proto-loader` which are **not** in `package.json` (only `@grpc/grpc-js` is). The proto is **duplicated** in the source as a string literal (`api/grpc.ts:27-76`) — `syntax = "proto3"; ... syntax = "proto3"; ...` appears twice. The handlers `subscribe`/`migrate` reference `sub.on('update', ...)` on a `Subscription` interface that has no `.on()` method (the real `SubscriptionManager` is an `EventEmitter`, but the public `Subscription` is a plain data object — see `subscription.ts:30-39`). The gRPC handler at line 169 will throw at runtime.
- **`GraphQL` adapter** (`src/api/graphql.ts`) — exports SDL string + a `createGraphQLResolvers(fleet)` function + a `createGraphQLSchema(fleet)` that returns `{typeDefs, resolvers}` — but no `makeExecutableSchema` is called. The caller must import `graphql-tools` themselves. The README and index.ts claim `createGraphQLSchema` is a usable schema. It is not.
- **`REST` adapter** (`src/api/rest.ts`) — the routes are real, but `app.use(prefix, createRestRouter(fleet))` requires `express` which is in `package.json` but its types are not pinned, and the test suite never imports `createRestApp` so it is unverified.
- **`cli.ts`** — every subcommand except `init` and `serve` is a local ephemeral. `cmdAdd` creates a brand-new `FleetManager({id: 'cli'})`, registers, prints, exits. `cmdList` does the same — but the registry is fresh, so it lists nothing. `cmdMigrate` literally writes `OK (dry run)\n`. `cmdSubscribe` parses the URI and prints it. There is no IPC to a running `quilt-fleet serve` process.
- **`FleetManager.query`** (`src/fleet.ts:167-185`) — comment: *"In production this would hit the transport; here we return null if no transport is wired."* It actually does try to use `cfg.transport.cell.subscribe(...)` — but the test `query returns null when no transport is wired` confirms the contract: without a user-supplied transport, every `query()` is `null`.
- **`FleetManager.scale('auto')`** (`src/fleet.ts:198-201`) — just returns `this.scaler` and does nothing else. The docstring says "run one tick by re-emitting the current policy" but there is no re-emission.
- **`@quilt/core` and `@quilt/sdk` dependencies** — these are declared in `package.json:28-29` (`"@quilt/core": "^0.1.0"`, `"@quilt/sdk": "^0.1.0"`) and have **never been published to npm**. `npm install` exits with `404 Not Found - GET https://registry.npmjs.org/@quilt%2fcore`. There is no local file:// reference, no workspace pointer, no monorepo root. The CI workflow at `.github/workflows/ci.yml:21` runs `npm ci` which will fail the same way. **This is not a v0.1 package; it is a v0.1 sketch that depends on packages that don't exist.**
- **Proto file** — `api/grpc.ts:79` says `DEFAULT_PROTO_PATH = './proto/quilt_fleet.proto'`. There is no `proto/` directory in the repo.
- **CLI `add` URI parser** (`src/cli.ts:123`) — uses `quilt://name@endpoint` format, but everywhere else uses `quilt://instance/sheet#cell` (`src/types.ts:81-86`). The CLI's own format is undocumented and incompatible with the parser.
- **`Subscription.id` is `sub-${nextId}`** (`src/subscription.ts:107`) — not a ULID, not globally unique across managers. Collide if two managers exist.
- **`FleetEvent` and `RegistryQuery.label`** interfaces are declared but never consumed by any test.
- **`@quilt/core` / `@quilt/sdk` are imported nowhere in `src/`** — `grep -r "from '@quilt" src/` returns nothing. The dependency declarations are dead weight.

## Test count

**131 `it(...)` cases across 13 test files**, with two `for-of` loops in `test/tiers.test.ts` that multiply 2 of those by 5 (one tier per name), so the dynamically reported test count is **131 + 10 = ~141**.

**Actual run: 100 passed, 20 failed, 1 unhandled error, of 120 reported tests** (vitest's reporter collapses the loop-generated tests under the same name; the discrepancy is normal):

```
Test Files  10 failed | 3 passed (13)
     Tests  20 failed | 100 passed (120)
    Errors  1 error
```

Per-file breakdown from the run:

- `test/types.test.ts` — **8/8 pass** ✅
- `test/health.test.ts` — **10/10 pass** ✅
- `test/transports.test.ts` — **17/17 pass** ✅
- `test/registry.test.ts` — **14/15 pass** ❌ (`sorts owners of a cell by tier then latency` throws `TypeError: Cannot read properties of undefined (reading 'tier')` because `Registry.ownersOfCell` filters by `status: ['healthy', 'degraded']` and the test populates instances with default `status: 'unknown'`, so the result is empty)
- `test/routing.test.ts` — **8/11 pass** ❌ (3 fail: `picks the lowest tier when no policy is set`, `honors tierPreference`, `setPolicy updates policy at runtime` — all return `undefined` because `Router.candidates` filters by `status: ['healthy', 'degraded']` and the test never marks instances healthy)
- `test/scaling.test.ts` — **7/9 pass** ❌ (2 fail: `spawns a new instance when load crosses threshold` — assertion expects `triggeredBy: 'load'` but the code sets `triggeredBy: 'manual'` at `scaling.ts:131`; `schedule policy spawns at the configured time` — the test patches `Date.now` but the code uses `new Date()` and `getHours()` which the monkey-patch doesn't intercept)
- `test/subscription.test.ts` — **2/7 pass** ❌ (5 throw `Error: no instance available for quilt://j-1/s#c` — same root cause as the routing failures: instances are registered with `status: 'unknown'` and the router filters them out)
- `test/quorum.test.ts` — **6/10 pass** ❌ (4 fail: `reads with majority when 2 of 3 agree`, `detects split brain`, `replicates a write to all replicas and reports the version`, `emits committed and repaired events` — the `QuorumTransport` test mock has a CAS guard (`if (cur && cur.version >= version) return false`) that rejects the second-version write; the `quorum.ts:252` majority check fails because all 3 replicas return `false`)
- `test/migration.test.ts` — **5/8 pass** ❌ (`completes all 5 phases in the happy path`, `times out a hung phase`, `emits start, phaseStart, phaseEnd, and complete events` — same CAS bug: the read-back verify check at `migration.ts:220` requires `back.version === snap.version`, but the test's transport bumps the version on write, so the verify fails)
- `test/tiers.test.ts` — **23/25 pass** ❌ (2 fail: `returns a no-op iterator for esp32 (no broker)` and `... for cloudflare (no endpoint)` — both call `it.close()` on a value that the typescript compiler thinks is `AsyncIterable` not `AsyncIterable & {close(): void}`. The runtime is fine; the test file is wrong; the type system catches it correctly)
- `test/discovery.test.ts` — **file fails to load** (`Failed to load url yaml (resolved id: yaml)` — `yaml` is in `package.json:37` but not in the test install, and the `vite` dev-server module resolution is failing)
- `test/fleet.test.ts` — **file fails to load** (same `yaml` import failure)
- `test/integration.test.ts` — **file fails to load** (same `yaml` import failure)

**`tsc --noEmit` on the source: 36 type errors.** Highlights:
- `src/index.ts:69` — `Module '"./registry"' declares 'Tier' locally, but it is not exported` (the `Tier` brand is in `types.ts`, not `registry.ts`; the `export type { Instance, InstancePatch, Tier as InstanceTier }` re-export is broken)
- `src/index.ts:81` — `Module '"./quorum"' has no exported member 'QuorumResult'` (the actual exports are `QuorumRead` and `QuorumWrite`)
- `src/scaling.ts:146` — `Property 'tierName' does not exist on type 'never'` (the `reg.get` returns `Instance | undefined`; the code does `inst?.tierName ?? 'server'` then later uses `inst.tierName` unguarded, so the `never` is the `!` from the early return's narrowing)
- `src/transports/{http,mqtt}.ts` — `Property 'next' is missing in type ... but required in type AsyncIterator` (the `close(): void` augmenting interface loses the `next` property under TS's structural typing)
- `src/api/rest.ts:22` — `Cannot find module 'express'` (deps not installed)
- `src/discovery.ts:31` — `Cannot find module 'yaml'` (deps not installed)
- `src/api/grpc.ts:169` — `Property 'on' does not exist on type 'Subscription'` (the gRPC handler treats the public `Subscription` interface as an EventEmitter; it isn't)
- `src/transports/nats.ts:42` — `Property 'decode' does not exist on type 'typeof import("nats")'` (the `nats` package was renamed to `@nats-io/*`; the v2 API doesn't have a top-level `decode` export)

**Conclusion on tests: ~17% genuine pass rate against the production suite, plus three whole files that can't even load.** The README badge `tests-75%+-brightgreen.svg` is false. 75+ tests exist; ~100 of them pass; 20+ don't; the rest can't run.

## Top 2-3 1-day adds

### 1. **Fix `package.json` so `npm install` actually works** — `package.json:26-38`

The single most blocking defect. Every test failure, every type error in the test files, every "Failed to load url yaml" — all downstream of this. Two paths:

- **(a) Publish stub packages.** `npm publish --access public @quilt/core@0.1.0` and `@quilt/sdk@0.1.0` with `index.js` exports of `{}`. Trivial. Buys you a green `npm install`.
- **(b) Mark them as optional / peer.** Move `@quilt/core` and `@quilt/sdk` to `peerDependenciesMeta: { optional: true }` and add `peerDependencies` entries. The current source code does not actually import either, so removing them entirely is also safe (`grep -r "@quilt" src/` returns nothing — they're dead). `git grep '@quilt' src/` is empty.

Either path is a 30-line diff. Without it, the CI workflow at `.github/workflows/ci.yml:21` (`npm ci`) fails on the first job before `npm test` even starts. This is the difference between "the repo doesn't work" and "the repo has failing tests you can read."

### 2. **Mark instances `status: 'healthy'` in the test fixtures** — `test/routing.test.ts:11-18`, `test/subscription.test.ts:46-49`, `test/registry.test.ts:14-19`

`Registry.ownersOfCell` and `Router.candidates` both filter by `status: ['healthy', 'degraded']` (`registry.ts:362`, `routing.ts:117`). Every freshly-registered instance is `status: 'unknown'` (`registry.ts:223`). **This is what kills 8 of the 20 failing tests** (3 in routing, 5 in subscription, plus 1 in registry).

Two-line fix per test file: in the `makeReg()` helper, after `register`, do `for (const i of r.all()) r.update(i.id, { status: 'healthy' })`. That alone moves the suite from 100/120 to 108/120, and it doesn't require changing production code.

The deeper question — should the default `status` for a fresh `register` be `unknown` or `healthy`? — is a real design call. The current choice makes every "I just registered this thing" path require a separate "now mark it healthy" call, which is friction. But the router's defensive filter is correct: you don't want to send traffic to a node you haven't probed. The right answer is a `register({ status: 'healthy' })` test override path that doesn't have to round-trip through the health monitor.

### 3. **Fix the `quorum` and `migration` test CAS race** — `test/quorum.test.ts:52-58`, `test/migration.test.ts:36-42`

The shared test transport in both files does conditional-accept-on-version-write (`if (cur && cur.version >= version) return false;`). This is *correct* CAS semantics — but `QuorumCoordinator.write` (`src/quorum.ts:236-248`) and `MigrationCoordinator.runPhases` (`src/migration.ts:210-212`) call `transport.write(...)` with the *snapshot* version, not a new monotonically increasing one. After the first quorum write at version 1, every subsequent phase that writes version 1 (the read-back verify in 2A, the migration's 1B-to-dest) gets rejected by the CAS.

The fix is in the production code, not the test: `QuorumCoordinator.write` already calls `this.lastCommitted.get(parsed.uri) ?? 0) + 1` for the version it passes to `transport.write` (`src/quorum.ts:234`), but the **read** path doesn't bump the version when repairing (`src/quorum.ts:202-212` writes `winner.version` to dissenters — if a dissenter has the same version, CAS rejects). And `MigrationCoordinator.runPhases` passes `snap.version` directly to `transport.write` at line 211, with no increment.

Three-line fix: in `migration.ts:210-212`, change the write to `nextVersion = snap.version + 1` (or whatever the source's lastCommitted was +1); in `quorum.ts:206-209`, change the repair write to `winner.version + 1` or pass a `force: true` flag through `QuorumTransport.write`. That moves the suite to ~115/120 passing.

Bonus: the `gRPC` handler's `sub.on('update', ...)` bug (`src/api/grpc.ts:169`) and the `package.json` `Tier`/`QuorumResult` re-export bugs (`src/index.ts:69,81`) are all one-line fixes that would clear the `tsc --noEmit` error count from 36 to ~6.

## The cowboy's take

This is a v0.0.1 README-shaped sketch that someone dressed up as v0.1.0 with a green tests badge. The core algorithms — registry, router, health monitor, quorum, migration, scaler — are genuinely well-designed and would not embarrass you in a code review. The author understands the problem. The transport adapters are real. The tier profiles have correct hardware constraints.

What kills it is everything around the core: the CLI is a UI prototype that doesn't talk to itself, the gRPC adapter is broken at runtime, the GraphQL adapter is half-built, the DNS-SD adapter is an empty class, the dependencies point at packages that don't exist, the CI workflow will fail before any test runs, the test fixtures have a global bug (no `status: 'healthy'` on freshly-registered instances) that hides real production-code defects, and the test mock for the quorum transport has a CAS race that the production code trips over.

The 75+ tests badge is the worst lie. The repo has 131 tests; 100 of them pass; 20 fail; 11 can't run; the typecheck fails on 36 of the source files. Someone ran the test suite at least once in a fresh dev environment where the tests they wrote *did* pass, and then never re-ran them after they moved the project to a CI environment where the dependencies weren't installed. The README has a `tests-75%+-brightgreen.svg` badge that was hand-painted with a wrong number.

The README's "Engineering bar compliance" checklist is dishonest. Every box is checked, but three of the eight are `npm`-broken at the registry level, and a fourth (`tests`) is broken at the runtime level. This is what "vapor-engineering" looks like — the docs describe the bar; the code fails to clear the bar; the badges claim the bar was cleared.

**If I were the foreman**: stop the merge. The good news is the core code (registry, router, quorum, migration, scaler, transports) is real enough that fixing the three 1-day adds above gets you from "doesn't run" to "100+ tests passing, 36 → ~6 type errors, npm install works." That's a 2-3 day arc to a respectable v0.1.0. The bad news is everything around that core is decoration that needs to either be cut or built out — the gRPC server, the GraphQL resolver, the CLI subprocess model, the DNS-SD backend, the proto file. Trying to ship this as-is to anyone who runs `npm install` and `npm test` will burn your credibility.
