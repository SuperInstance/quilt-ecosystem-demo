# Byte-Level Audit: quilt-vault

**Repo:** https://github.com/SuperInstance/quilt-vault
**Clone SHA:** `222bfe0` (single commit: "feat: add splash image for repo branding")
**Date:** 2025
**Auditor:** foreman / general subagent

---

## Overview

quilt-vault positions itself as the encryption primitive of the Quilt ecosystem — "encrypted cells, end-to-end, server never sees plaintext." It's a single-file JavaScript library (`src/index.js`, 222 lines) using Node's `webcrypto` for ECDH P-256 + AES-GCM 256. No dependencies. No build step. Runs as a Node ESM module.

| File | Bytes | Lines | Purpose |
|---|---|---|---|
| `src/index.js` | 7,472 | 222 | The library — `generateKey`, `Vault` class, `encryptToViewers`, `decryptForViewer` |
| `test/test.js` | 5,829 | 162 | Hand-rolled test runner, 10 tests |
| `README.md` | 10,549 | 226 | Docs (and — see below — partially fictional) |
| `package.json` | 377 | 20 | name, `main: src/index.js`, `type: module`, single `npm test` script |
| `assets/splash.png` | 2,974,617 | — | Marketing splash image (~2.8 MB) |
| `.gitignore` | 86 | — | Standard ignores |
| **Total source** | **13,301** | **384** | Two files actually do work |

**Public surface (actual exports):**
- `export async function generateKey()` → `{ id, publicKey, privateKey, publicJwk }`
- `export class Vault` with `addViewer / set / get / getEnvelope / ids / grant / revoke`
- `export default Vault`

---

## What's real

The cryptographic core is real and works. Verified by running `node test/test.js` → **10 passed, 0 failed**.

- **ECDH P-256 key agreement** via `subtle.generateKey` (line 32) and `subtle.deriveKey` (line 51). Real WebCrypto, not a toy implementation.
- **AES-GCM 256** with random 12-byte IV per encryption (line 64, 69). Per-cell content key generated fresh on each `set()`.
- **Content-key wrapping pattern**: random AES key encrypts the value; that content key is then AES-GCM-wrapped once per viewer using the ECDH-derived shared key (lines 76–91). This is the correct standard pattern for per-viewer access without re-encrypting the payload.
- **Per-cell ACLs** implemented via the `wrapped` map keyed by viewer fingerprint id (line 87).
- **Grant/revoke** both re-encrypt the cell from scratch under the new viewer set (lines 184–219). Owner always kept in the list (line 150, 194, 214). Revoke explicitly refuses to remove the owner (line 206).
- **Envelope opacity**: the stored blob is base64 ciphertext + base64 IVs + per-viewer wrapped keys. No plaintext, no key material, no plaintext-derived strings (verified by test at line 121).

**Real test coverage** (10/10 passing, each one exercises a real path):
1. owner round-trips a numeric cell
2. owner round-trips number / string / nested object / mixed array
3. ACL: granted viewer reads successfully
4. ACL: non-granted viewer throws
5. ACL: per-cell `viewers` opt restricts access
6. `grant()` adds a viewer to an existing cell
7. `revoke()` removes a viewer
8. Envelope contains no plaintext strings and contains the right wrapped keys
9. `set()` twice keeps latest value
10. `set()` produces different ciphertext each time (IV + key freshness)

Tests use the real crypto stack — no mocks, no `node:crypto` stubs. The 10/10 badge in the README is honest.

---

## What's stub

More than the README admits.

1. **README describes an API that does not exist in the code.** The README's "API reference" section documents a class called `QuiltVault` with methods `addPeer`, `setIdentity`, `removePeer`, `get`, `set`, `getCipher`, `setCipher`, `list`. The actual export is a class called `Vault` with `addViewer`, `set`, `get`, `getEnvelope`, `ids`, `grant`, `revoke`. There is no `QuiltVault`, no `addPeer`, no `setIdentity`, no `getCipher`, no `setCipher`, no `list` symbol anywhere in `src/index.js` (verified with `grep "^export"`). The 30-second code snippet at the top of the README would crash on import.

2. **Source comment self-declares as a sketch** (src/index.js line 20–24): *"This is a sketch. The real implementation will use libsodium, X25519, Ed25519, Argon2id."* So the author is on record that what shipped is a prototype. No argument against it; just don't market it as the final primitive.

3. **No persistent storage.** Cells live in a `Map` in memory. The README badge for "encrypted-at-rest" is aspirational — there's no IndexedDB, no file write, no driver. `setCipher` (the README-documented restore method) doesn't exist. `getCipher` doesn't exist. A consumer can't actually round-trip a vault through disk.

4. **No `LICENSE` file.** The README footer says "MIT" and the package.json declares `"license": "MIT"`, but the actual `LICENSE` file is not in the repo.

5. **No CI, no lint, no type definitions, no examples, no changelog.** `.github/` directory doesn't exist. No `.eslintrc`, no `tsconfig`, no `examples/`.

6. **No node_modules lockfile committed** (and `package-lock.json` is gitignored), so `npm test` is the only script and there's no reproducible install.

7. **2.8 MB splash.png in `assets/`** is the largest file in the repo and has no code relationship. The single commit's message ("feat: add splash image for repo branding") confirms this is the entire history.

8. **Forward secrecy is not implemented** (acknowledged in the README's roadmap as item #3). The same ECDH keypair is reused for every cell.

---

## Test count

- **Tests defined:** 10 (`test()` calls in `test/test.js`, lines 33, 41, 56, 67, 77, 94, 109, 121, 140, 149)
- **Tests passing:** 10 / 10
- **Tests failing:** 0
- **Test framework:** none — 33-line hand-rolled `assertEq` + `assertThrows` + `test()` runner (lines 7–29)
- **External test deps:** 0
- **Mocks used:** 0
- **Execution time:** sub-second (sub-ms per test, dominated by WebCrypto keygen)

Honest count. The README's "10 tests, all pass" claim matches reality.

---

## Top 1-day adds

Three high-leverage changes that would close the gap between what's shipped and what's documented. Each scoped to a day.

### 1. Reconcile the API: ship what the README promises (or rewrite the README)

Either:
- Rename `Vault` → `QuiltVault` and add the missing methods: `setIdentity(jwk)`, `addPeer(name, pubJwk)`, `removePeer(name)`, `getCipher(id)`, `setCipher(id, blob)`, `list()`. ~50–80 LOC. This makes the README code snippet runnable.
- Or rewrite the README's "API reference" and the 30-second snippet to match the real class.

Right now someone following the README's first code block hits `TypeError: QuiltVault is not a constructor` on import. This is a credibility bug.

### 2. Implement persistent storage (closes roadmap item #1)

The README's "encrypted-at-rest" badge is currently marketing-only. Add an `IndexedDB` driver in Node and the browser:
- `vault.persist(driver)` / `vault.restore(driver)` taking a `{ get(id), set(id, blob) }` driver
- Serialize the cells Map to envelopes + viewer registry
- ~80–120 LOC. One day if you don't bikeshed the driver interface.

This unblocks the "local-only backup" and "device-to-device sync" use cases the README claims. Also enables a real `LICENSE`-clean restoration story so a `getCipher`/`setCipher` pair (item #1) isn't fictional.

### 3. Replace ECDH-then-ECDH with proper key wrapping + add `Ed25519` signing (closes sketch comment + roadmap)

The sketch comment explicitly says the real implementation should use:
- **X25519** for key agreement (P-256 is fine but X25519 is the modern default and ~30% less code in libsodium-wrappers)
- **Ed25519** for cell signatures (proves the cell was authored by the claimed owner — currently nothing prevents a malicious server from swapping envelopes)
- **Argon2id** for password-derived key wrapping (currently there's no path from "user types a password" to "vault unlocks")

libsodium-wrappers adds one dependency, ~150 KB. The auth tag also closes a gap: today, an attacker who controls the storage layer can replay or substitute cells and only the ciphertext authenticity (within AES-GCM) is preserved — there's no binding to the owner's identity.

Bonus: add signature + chain-hash to each cell so the README's "Audit without surveillance" use case actually holds.

---

## The cowboy's take

quilt-vault is a **working sketch masquerading as a primitive**. The crypto is real — the 10 tests genuinely exercise the round-trip and the envelope opacity claim is honestly verified. The author clearly knows what they're doing; the ECDH-then-wrap-key pattern is the right one and the IV handling is correct.

But the repo is a **single 222-line file with a single commit, no storage, no CI, no LICENSE file, and a README that documents an API that doesn't exist in the code.** The most-visited section of the README (the 30-second code snippet) is broken on first import. The source itself contains a "this is a sketch" comment that's still there in the shipped version. The `LICENSE: MIT` field is in `package.json` but no `LICENSE` file exists on disk.

For the Quilt ecosystem to treat this as a load-bearing primitive for sync, mesh, time-travel, and live cells, three things need to happen in order, and none of them are big:
1. **Make the README code run** (the API surface is a 1-day rewrite).
2. **Make the cells survive a reload** (IndexedDB driver, 1 day).
3. **Sign the envelopes** (libsodium swap, 1–2 days, and removes the sketch comment).

Total: maybe a week to go from "demo that passes 10 tests" to "primitive the rest of the stack can actually depend on." Until then, it's a proof of concept, not infrastructure — and the README's badges and live-demo link are doing the work that the code isn't.

**Verdict:** honest about the tests, dishonest about the API. Crypto is real, story is not. Ship the three 1-day adds and this becomes a real primitive.
