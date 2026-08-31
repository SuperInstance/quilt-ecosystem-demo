# penrose_quilt

<p align="center">
  <img src="assets/images/hero-penrose-draughtsman.jpg" width="680" alt="A draughtsman laying brass rhombi by lamplight — a pattern that fits everywhere and repeats nowhere.">
</p>

Penrose P3 rhombus tiling library (numpy + matplotlib) with origin-centric
coordinates, Pythagorean distance snapping, an adjacency-diffused gravity
field, an 8-dimensional locality-correlated embedding, and visualizations.

## Construction

Tiles are thin (36/144 deg) and thick (72/108 deg) rhombi generated with the
de Bruijn pentagrid (cut-and-project dual) method, which produces exact P3
tilings. Generations realize the deflation hierarchy: generation g is the
same tiling pattern scaled by psi^g (psi = 1/phi = 0.618...), i.e. the
g-fold golden deflation of the infinite tiling restricted to a fixed
origin-centric window. A direct Robinson-triangle deflation was implemented
and verified locally (acute -> acute + gnomon; gnomon -> 2 gnomons + 1
acute, child scale psi), but mirror-state propagation across patch
boundaries is error-prone; the pentagrid yields the identical deflation
hierarchy exactly, so it is what ships.

## Verified numbers

Tile counts per generation (window radius 2*phi^g at unit scale):

    gen  thin  thick  total  growth vs prev
    0      5      5     10      -
    1     15     20     35    3.500
    2     45     65    110    3.143
    3    110    165    275    2.500
    4    265    455    720    2.618
    5    735   1180   1915    2.660

Growth per generation converges to phi^2 = 2.618 (tile linear scale shrinks
by 1/phi per generation). Thick:thin ratio at gen 5 is 1180/735 = 1.605,
approaching phi = 1.618. Gen-5 patch: 1915 tiles, 3730 adjacency edges
(average degree 3.90; every interior edge is shared by exactly 2 tiles).

Snapping sample (unit-scale patch, radius 24, primitive hypotenuse list
5, 13, 17, 25, 29, 41, ...): raw tile distances span 0.81..23.99 and snap
to histogram {5: 320, 13: 535, 17: 855, 25: 530}; e.g. 12.17 -> 13,
17.07 -> 17, 22.54 -> 25. Angles are preserved.

Diffusion field, gen-5 patch (seed = normalized total 1/d^2 gravity weight,
8 lazy-neighbor-averaging rounds), variance across tiles per round:

    1.0000, 0.8775, 0.8228, 0.7875, 0.7608, 0.7390, 0.7204, 0.7040, 0.6894

Strictly decreasing (convergence toward the graph average).

Embedding (8-dim, seed 7, gen-5 patch): mean cosine similarity of adjacent
tile pairs = 0.7394 vs mean random-pair cosine = 0.0092.

## Run

    python3 -m pytest tests/ -q        # 9 tests
    python3 - <<'EOF'
    import numpy as np
    from penrose_quilt.tiling import generate
    from penrose_quilt.field import adjacency, field
    from penrose_quilt import viz
    p = generate(4)[-1]                # gen-4 patch (720 tiles)
    edges, nbrs = adjacency(p)
    F, variances = field(p, neighbors=nbrs)
    viz.heat_map(p, F, angle=np.radians(30))   # output/heat.png
    viz.tiling_svg(p, edges)                   # output/tiling.svg
    EOF

Outputs: `output/heat.png` (left: tile heat map of the diffused field with
cross-section rays; right: field-vs-distance profile for tiles in a
+-9 deg wedge of the chosen angle) and `output/tiling.svg` (tiles colored
by type, adjacency edges drawn).

## Modules

- `tiling.py`  P3 patches per generation; Tile with kind, 4 vertices, center, id
- `coords.py`  ring (floor(dist/circumradius)), polar angle, distance per tile
- `snapping.py` snap distance to nearest primitive Pythagorean hypotenuse
  (harmonic integer-lattice positions, Quilt opcode compatibility), angle kept
- `field.py`   shared-edge adjacency, 1/d^2 gravity weights, k-round lazy
  adjacency diffusion with per-round variance (must decrease)
- `embed.py`   8-dim embedding, locality-correlated init (random + 0.5 *
  neighbor average, normalized); embed(id); project(a, b) -> 2-d
- `viz.py`     heat map with split view + cross-section; tiling SVG
