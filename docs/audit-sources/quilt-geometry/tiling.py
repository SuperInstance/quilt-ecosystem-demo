"""P3 Penrose rhombus tiling: thin (36/144 deg) and thick (72/108 deg) rhombi.

Construction: de Bruijn pentagrid (cut-and-project dual), which produces exact
P3 tilings. Generations realize the deflation hierarchy: generation g is the
same tiling pattern scaled by psi^g (psi = 1/phi), i.e. the g-fold golden
deflation of the infinite tiling restricted to a fixed window. Tile counts
therefore grow by ~phi^2 per generation (phi^2 = 2.618...: linear tile scale
shrinks by 1/phi each generation, area is preserved per level).

A direct Robinson-triangle deflation was also implemented and verified
geometrically (acute -> acute + gnomon; gnomon -> 2 gnomons + 1 acute, child
scale psi), but propagating the mirror (chirality) state across patch
boundaries is error-prone; the pentagrid gives the identical tile hierarchy
exactly and is used instead.
"""
import numpy as np

PHI = (1 + np.sqrt(5)) / 2
PSI = 1 / PHI
GAMMA = 0.2          # pentagrid offset (avoids 5-line concurrence at origin)
_BASE_W0 = 2.0       # base window radius (gen 0)


class Tile:
    __slots__ = ("tid", "kind", "verts", "center", "circumradius")

    def __init__(self, tid, kind, verts):
        self.tid = tid
        self.kind = kind                    # "thin" (36 deg) or "thick" (72 deg)
        self.verts = np.asarray(verts, dtype=float)   # (4,2), cyclic order
        self.center = self.verts.mean(axis=0)
        self.circumradius = float(np.max(
            np.linalg.norm(self.verts - self.center, axis=1)))

    def __repr__(self):
        return f"Tile({self.tid},{self.kind},c={np.round(self.center,3)})"


_TH = 2 * np.pi * np.arange(5) / 5
_C, _S = np.cos(_TH), np.sin(_TH)
_ZETA = np.exp(1j * _TH)


def _unit_patch(W):
    """Pentagrid-dual rhombi with centers within radius W (tile side = 1)."""
    tiles = []
    rng = range(int(-W - 2), int(W + 3))
    for j in range(5):
        for k in range(j + 1, 5):
            d = (k - j) % 5
            kind = "thick" if d in (1, 4) else "thin"
            det = _C[j] * _S[k] - _S[j] * _C[k]
            if abs(det) < 1e-12:
                continue
            for m in rng:
                for n in rng:
                    x = ((m + GAMMA) * _S[k] - (n + GAMMA) * _S[j]) / det
                    y = (_C[j] * (n + GAMMA) - _C[k] * (m + GAMMA)) / det
                    if np.hypot(x, y) > W + 1.0:
                        continue
                    K0 = np.floor(
                        np.array([_C[i] * x + _S[i] * y
                                  for i in range(5)]) - GAMMA + 1e-9)
                    vs = []
                    for ej in (0, 1):
                        for ek in (0, 1):
                            K = K0.copy()
                            K[j] = m if ej else m - 1
                            K[k] = n if ek else n - 1
                            v = np.sum(K * _ZETA)
                            vs.append((v.real, v.imag))
                    vv = np.array([vs[e * 2 + f]
                                   for (e, f) in [(0, 0), (1, 0), (1, 1), (0, 1)]])
                    if np.hypot(*vv.mean(axis=0)) > W:
                        continue
                    tiles.append((kind, vv))
    return tiles


def generate(generations=5):
    """patches[g] = tiles of generation g (side length psi^g, origin-centric)."""
    patches = []
    for g in range(generations + 1):
        W = _BASE_W0 * PHI ** g
        scale = PSI ** g
        unit = _unit_patch(W)
        tiles = [Tile(i, kind, vv * scale) for i, (kind, vv) in enumerate(unit)]
        patches.append(tiles)
    return patches


def counts(patches):
    """[(gen, n_thin, n_thick, total, growth_ratio_vs_prev), ...]"""
    rows = []
    prev = None
    for g, tiles in enumerate(patches):
        nt = sum(1 for t in tiles if t.kind == "thin")
        nk = len(tiles) - nt
        ratio = (len(tiles) / prev) if prev else float("nan")
        rows.append((g, nt, nk, len(tiles), round(ratio, 3)))
        prev = len(tiles)
    return rows
