"""Dependency-free data generator and Jane Street exponent estimator."""
import math
import random

VOCAB = 84

def exponent(weights, gains):
    """Cumulative-discrepancy estimator, equivalent to d' K d for unique ranks.

    K_ij=min(r_i,r_j). Since sum(d)=0, cumulative prefix and suffix versions
    coincide. Sorting avoids materializing an N by N matrix.
    """
    w = [float(x) for x in weights]
    g = [float(x) for x in gains]
    if max(w) - min(w) < 1e-12:
        return {"p": None, "reason": "constant_weights"}
    if sum(g) <= 1e-10:
        return {"p": None, "reason": "nonpositive_total_gain"}
    order = sorted(range(len(w)), key=w.__getitem__)
    logw = [math.log(w[i]) for i in order]
    total_gain = sum(g)
    gn = [g[i] / total_gain for i in order]

    def objective(p):
        z = [p * x for x in logw]
        m = max(z)
        z = [math.exp(x - m) for x in z]
        total = sum(z)
        c = 0.0
        loss = 0.0
        for a, b in zip(gn, z):
            c += a - b / total
            loss += c * c
        return loss / len(w)

    grid = [i / 20 for i in range(161)]
    j = min(range(len(grid)), key=lambda i: objective(grid[i]))
    lo, hi = grid[max(0, j - 1)], grid[min(len(grid) - 1, j + 1)]
    for _ in range(50):
        a, b = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        if objective(a) < objective(b):
            hi = b
        else:
            lo = a
    candidates = [0.0, (lo + hi) / 2, 8.0]
    p = min(candidates, key=objective)
    return {"p": p, "objective": objective(p), "at_upper_bound": p >= 7.999,
            "mean_gain": sum(g) / len(g)}

def make_data_lists(seed, regime, ntrain, nval, ntest):
    rng = random.Random(seed)
    permutations = [rng.sample(range(16), 16) for _ in range(16)]
    ids = rng.sample(range(32 ** 3), ntrain + nval + ntest)
    counts = {"mixed": [4, 4, 4], "structured": [6, 6, 0], "shared": [12, 0, 0]}[regime]
    rows, labels = [], []
    for i, key in enumerate(ids):
        group = i % 16
        row = [0, 1 + group, 17 + key // 1024, 17 + (key // 32) % 32, 17 + key % 32]
        types = [t for t, count in enumerate(counts) for _ in range(count)]
        rng.shuffle(types)
        xs = rng.sample(range(16), 12)  # No repeated query keys within a sequence.
        random_answers = [rng.randrange(16) for _ in xs]
        mask = [-1] * 5
        for typ, x, random_answer in zip(types, xs, random_answers):
            y = (x + 1) % 16 if typ == 0 else permutations[group][x] if typ == 1 else random_answer
            row += [49 + typ, 52 + x, 68 + y]
            mask += [-1, -1, typ]
        rows.append(row)
        labels.append(mask[1:])  # Labels align with next-token targets.
    bounds = [0, ntrain, ntrain + nval, len(rows)]
    splits = {name: (rows[bounds[j]:bounds[j+1]], labels[bounds[j]:bounds[j+1]])
              for j, name in enumerate(("train", "validation", "test"))}
    meta = {"seed": seed, "regime": regime, "counts_per_sequence": counts,
            "length": len(rows[0]), "vocab_size": VOCAB, "unique_keys": len(set(ids)),
            "ntrain": ntrain, "nval": nval, "ntest": ntest,
            "group_permutations": permutations, "sequence_keys": ids}
    return splits, meta
