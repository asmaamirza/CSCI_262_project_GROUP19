"""
similarity.py
Three set-similarity metrics applied to Bloom-filter bit vectors.

All three metrics operate on pre-computed beta vectors (lists of 0/1 integers)
and return a float in [0, 1].  Jaccard is the primary decision metric;
Dice and Cosine are computed for reference / display purposes only.
"""

import math


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _ones(beta):
    """Count the number of 1-bits in a filter vector (its cardinality)."""
    return sum(beta)

def _common(beta1, beta2):
    """Count positions where both filters are 1 (bitwise AND cardinality = γ)."""
    return sum(a & b for a, b in zip(beta1, beta2))


# ── Jaccard coefficient  (PRIMARY decision metric) ─────────────────────────────
#
#   J(β1, β2) = γ / (k_β1 + k_β2 − γ)
#
# Divides shared bits by the union of all set bits.  The denominator avoids
# double-counting the overlap, so Jaccard is always ≤ Dice and ≤ Cosine.

def jaccard(beta1, beta2):
    gamma = _common(beta1, beta2)
    k1    = _ones(beta1)
    k2    = _ones(beta2)
    denom = k1 + k2 - gamma          # |union| in bit-vector terms
    return gamma / denom if denom > 0 else 0.0


# ── Dice coefficient  (reference) ─────────────────────────────────────────────
#
#   δ(β1, β2) = 2γ / (k_β1 + k_β2)
#
# Doubles the intersection before dividing, so it weights overlap more heavily
# than Jaccard.  δ ≥ J always; for identical filters both equal 1.

def dice(beta1, beta2):
    gamma = _common(beta1, beta2)
    k1    = _ones(beta1)
    k2    = _ones(beta2)
    denom = k1 + k2
    return (2 * gamma) / denom if denom > 0 else 0.0


# ── Cosine similarity  (reference) ────────────────────────────────────────────
#
#   φ(β1, β2) = γ / (√k_β1 · √k_β2)
#
# Treats each filter as a binary vector in L-dimensional space and returns the
# cosine of the angle between them.  φ ≈ δ when the two filters have similar
# cardinality; it diverges when one filter is much denser than the other.

def cosine(beta1, beta2):
    gamma = _common(beta1, beta2)
    k1    = _ones(beta1)
    k2    = _ones(beta2)
    denom = math.sqrt(k1) * math.sqrt(k2)   # product of vector magnitudes
    return gamma / denom if denom > 0 else 0.0


# ── Decision threshold ────────────────────────────────────────────────────────
# Chosen empirically: run `python main.py --threshold` for the full analysis.
# Similar/tweaked password pairs score ≥ 0.59; unrelated pairs score ≤ 0.18.
# 0.30 sits cleanly in the gap — 0 false positives, 0 false negatives on the
# test set — and is biased toward accepting rather than over-rejecting.
JACCARD_THRESHOLD = 0.30
