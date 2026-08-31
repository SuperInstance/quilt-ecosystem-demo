#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CORPUS="$ROOT/corpus"
RAW="$ROOT/results/raw"
mkdir -p "$RAW"

QVM_C_SRC=/home/eileen/projects/quilt-vm-c/src
HASKELL_ENV=(env PATH="$HOME/.ghcup/bin:$PATH" LIBRARY_PATH="$HOME/.local/lib")

run_rust() {
  echo "== rust =="
  (cd "$ROOT/adapters/rust" && cargo build --release -q)
  "$ROOT/adapters/rust/target/release/conformance-rust" "$CORPUS" "$RAW/rust"
}

run_typescript() {
  echo "== typescript =="
  node "$ROOT/adapters/typescript/adapter.ts" "$CORPUS" "$RAW/typescript"
}

run_c() {
  echo "== c =="
  gcc -O2 -std=c99 -Wall -Wextra -o "$ROOT/adapters/c/conformance-c" \
    "$ROOT/adapters/c/main.c" "$QVM_C_SRC/quilt_vm.c" -I"$QVM_C_SRC"
  "$ROOT/adapters/c/conformance-c" "$CORPUS" "$RAW/c"
}

run_haskell() {
  echo "== haskell =="
  (cd "$ROOT/adapters/haskell" && \
    "${HASKELL_ENV[@]}" cabal build --extra-lib-dirs="$HOME/.local/lib" exe:conformance -v0)
  local bin
  bin="$(cd "$ROOT/adapters/haskell" && "${HASKELL_ENV[@]}" cabal list-bin exe:conformance)"
  "$bin" "$CORPUS" "$RAW/haskell"
}

run_wasm() {
  echo "== wasm =="
  node "$ROOT/adapters/wasm/adapter.cjs" "$CORPUS" "$RAW/wasm"
}

run_rust
run_typescript
run_c
run_haskell
run_wasm

echo
echo "raw outputs in $RAW"
echo "next: python3 scripts/diff.py"
