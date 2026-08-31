"""Adjacency graph, gravity weights, and diffused gravity field per tile.

- adjacency: two tiles are adjacent when they share a full edge
  (matched via rounded vertex keys; P3 patches are edge-to-edge).
- gravity: weight 1/d^2 between tile centers (all pairs, Newtonian falloff).
- field: F_{r+1}(i) = 0.5*F_r(i) + 0.5*mean(F_r over neighbors of i),
  starting from F_0 = gravity weight (total 1/d^2 mass felt by the tile).
  The lazy averaging operator is a contraction on the zero-mean subspace
  for connected non-bipartite graphs, so the per-round variance of F across
  tiles strictly decreases (diffusion converges toward the graph average).
"""
import numpy as np
from collections import defaultdict


def _key(v, nd=6):
    return (round(float(v[0]), nd), round(float(v[1]), nd))


def adjacency(tiles):
    """Edge list of shared-full-edge adjacency, plus neighbor lists."""
    edge_map = defaultdict(list)
    for idx, t in enumerate(tiles):
        vs = t.verts
        for i in range(4):
            k = tuple(sorted([_key(vs[i]), _key(vs[(i + 1) % 4])]))
            edge_map[k].append(idx)
    neighbors = defaultdict(set)
    edges = set()
    for idxs in edge_map.values():
        if len(idxs) == 2:
            a, b = idxs
            neighbors[a].add(b)
            neighbors[b].add(a)
            edges.add((min(a, b), max(a, b)))
    return sorted(edges), {i: sorted(ns) for i, ns in neighbors.items()}


def gravity_weights(tiles, chunk=256):
    """Total inverse-square attraction on each tile from all others."""
    C = np.array([t.center for t in tiles])
    n = len(C)
    w = np.zeros(n)
    for s in range(0, n, chunk):
        d = np.linalg.norm(C[s:s + chunk, None, :] - C[None, :, :], axis=2)
        d[d < 1e-9] = np.inf
        w[s:s + chunk] = np.sum(1.0 / d ** 2, axis=1)
    return w


def field(tiles, rounds=8, neighbors=None):
    """Diffuse the gravity seed over the adjacency graph.

    Returns (F, variances): F[i] is the field value of tile i after `rounds`,
    variances[r] is the variance across tiles after round r (index 0 = seed).
    Variance must strictly decrease each round.
    """
    if neighbors is None:
        _, neighbors = adjacency(tiles)
    n = len(tiles)
    F = gravity_weights(tiles)
    F = (F - F.mean()) / (F.std() + 1e-12)   # normalize seed
    variances = [float(np.var(F))]
    idx = np.arange(n)
    has_nbr = np.array([i in neighbors and len(neighbors[i]) > 0 for i in idx])
    nbr_arr = np.zeros((n, 8), dtype=int)
    nbr_cnt = np.zeros(n, dtype=int)
    for i, ns in neighbors.items():
        nbr_cnt[i] = len(ns)
        nbr_arr[i, :len(ns)] = ns
    for r in range(rounds):
        F_next = F.copy()
        sums = np.zeros(n)
        counts = np.zeros(n)
        for j in range(8):
            m = nbr_cnt > j
            if not m.any():
                break
            sums[m] += F[nbr_arr[m, j]]
            counts[m] += 1
        mean_nbr = sums / np.maximum(counts, 1)
        F_next = np.where(has_nbr, 0.5 * F + 0.5 * mean_nbr, F)
        F = F_next
        variances.append(float(np.var(F)))
    return F, variances
