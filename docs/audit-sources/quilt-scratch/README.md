# quilt-scratch

*A no-code cellular game engine for young builders. Cells are tiles; tiles
are runtimes; wiring tiles together IS programming.*

**Status: hull-2 floating.** The Deep Caverns is playable — open `index.html`, pick **🕳️ the deep caverns**, and walk a kid named Wren down: ride the lift (8 ticks down, 8 up, dir/phase in the inspector), grab the key (it pops and sets a bit on its own cell), cross Theo's crumble bridge (the first brick is worn — watch `touches` climb, then the countdown painted on its face), unlock the gate, and reach the goal, which pops its confetti through the SAME Sparks tile the space invaders use. Falling is safe — respawn at the start, key KEPT, the bridge knits back — a fall is a retry, not a spiral. And mid-bridge you can swap the Crumble bridge for a Solid one: wires stay, touches carry, the shaking stops. Open `test.html` (or run `node run-tests.js`) for the contract tests — every palette tile is checked against M1–M4 / N1–N4 from the TILE-CONTRACT. House law applies to kids' tools too.

This repo exists because of one
observation: Scratch taught a generation to snap blocks together, but the
blocks were instructions. In quilt-scratch the blocks are **cells** — each one
a small running thing with state, a tick loop, and ports. Snap them together
and you haven't written a program; you've founded a tiny community that runs
itself.

- [index.html](index.html) — the engine. Zero install: open it in a browser.
- [test.html](test.html) — the contract tests (M1–M4 / N1–N4), also runnable with `node run-tests.js`.
- [docs/VISION.md](docs/VISION.md) — the founding brief, the tile taxonomy, and the canonical worked example (space invaders in cells).
- [docs/TILE-CONTRACT.md](docs/TILE-CONTRACT.md) — what every tile must and must not do.

## Hull-2: the deep caverns

Four new mechanics from the hull-2 spec — **Lift** (a deck whose position is a wire; standing on it IS riding), **Key/Lock** (a pickup that pops and sets a bit; a barrier that pops open only when that bit arrives — the same one-bit plumbing that arms the harbor's dock guard), **Crumble** (bridge bricks that count touches, shake out a visible countdown, pop, and knit back), and **Sign** (one authored line of story, zero IO) — plus exactly ONE justified extra tile, the **Explorer**: some cell must own "walk on floors, ride a deck, fall when unsupported", and wiring cannot inject a tick. The ledges of the level are the explorer's authored starting state; the deck, the bridge, and the gate arrive by wire (N1). The Key and the Goal are the SAME tile (a pickup) with different starting states — the goal's pop routes to the existing Sparks confetti, so no new effect tile was needed. The Solid bridge is the crumble tile with `fragile=0` — that's the mid-game swap, not a new mechanic.

**Deliberately not built (cut-and-named):** enemies/pathfinding, sound, save/continue, touch input. Wiring covered everything else.

## The one-sentence version

**A game is a fabric of visible, swappable, living cells — and a kid can
watch the numbers change inside every one of them.**

## Playing with hull-1

- **🪟 room** — the game. Arrows/A-D fly the ship, space fires. Click any face to watch its numbers; drag an actor and its x/y move.
- **🧵 fabric** — the program. Drag cards; drag output ● → input ● to wire; click a wire to unwind it (history keeps it). Flagged wires are drawn red-dashed — flagged, never coerced.
- **Inspector** (right panel) — every state field of the selected tile, updating every tick. Swap a tile from its dropdown: wires survive by port name (M2).
- **💾 save / 📂 load** — the fabric is a JSON file. Rewire history is append-only (N4); retired tiles are kept in the file.
- **Hop the explosion** — select the Boom: Pop tile in the invaders fabric and swap it for Ring or Sparks mid-game. Same wire, different channel.

## Design laws (inherited from the quilt substrate)

1. **Every cell is inspectable.** Open any tile at any time and see its state —
   the ship's position is a number in a cell, not a mystery inside a sprite.
2. **Every cell is swappable.** The explosion when a bullet hits is whichever
   tile the crash-physics cell routes to. Don't like it? Flip the tile. The
   wiring never changes.
3. **Cells live even when nothing talks to them.** A shopkeeper NPC ticks on
   her own loop — walking the shop, watering plants — whether or not any IO
   ever arrives. The room renders; the cells live in it.
4. **Nothing is destroyed.** Rewire a game and the old wiring is saved. (Kids
   deserve the archive-by-rename rule too.)
5. **Numbers over magic.** Conservation, ports, and state are visible. The
   "why" is always a number a kid can find.
