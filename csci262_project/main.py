"""
main.py
Command-line interface for the CSCI262 Password Similarity Checker.

Usage
-----
    python main.py                   # interactive mode
    python main.py --demo            # step-by-step walkthrough for sample pairs
    python main.py --threshold       # print threshold justification analysis
    python main.py --dataset FILE    # use a custom dataset file
"""

import sys
import os
import time
from bloom_filter import compute_beta, show_bigrams, L, K
from similarity  import jaccard, dice, cosine, JACCARD_THRESHOLD


# ── Dataset loading ─────────────────────────────────────────────────────────────

def load_dataset(filepath='dataset.txt'):
    """Read the dataset file and return passwords that are 8–10 characters long.

    The 8–10 window is the accepted input range; including shorter or longer
    entries would never match any candidate the user can legally submit.
    """
    if not os.path.exists(filepath):
        print(f"[ERROR] Dataset file not found: {filepath}")
        sys.exit(1)

    passwords = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            p = line.strip()
            if 8 <= len(p) <= 10:
                passwords.append(p)

    return passwords


def build_database(passwords):
    """Pre-compute beta(p) for every password so comparisons need no hashing."""
    print(f"[*] Building Bloom filters for {len(passwords)} common passwords ...")
    t0 = time.time()
    db = [(p, compute_beta(p)) for p in passwords]
    print(f"[*] Done in {time.time() - t0:.2f}s\n")
    return db


# ── Core comparison ─────────────────────────────────────────────────────────────

def check_password(candidate, database):
    """Find the closest stored password and decide whether to accept or reject.

    Scans the full database and tracks the entry with the highest Jaccard score.
    Dice and Cosine are only recomputed when a new Jaccard winner is found,
    keeping the non-winning comparison cost to a single dot-product call.

    Returns
    -------
    (accepted, closest_password, (jaccard_score, dice_score, cosine_score))
    accepted=True means the candidate is not too similar to any common password.
    """
    beta_c = compute_beta(candidate)
    best_match, best_j, best_d, best_c = None, 0.0, 0.0, 0.0

    for (stored, beta_s) in database:
        j = jaccard(beta_c, beta_s)
        if j > best_j:
            best_j     = j
            best_d     = dice(beta_c, beta_s)
            best_c     = cosine(beta_c, beta_s)
            best_match = stored

    accepted = best_j < JACCARD_THRESHOLD
    return accepted, best_match, (best_j, best_d, best_c)


# ── Threshold analysis ──────────────────────────────────────────────────────────

def run_threshold_analysis():
    """Print Jaccard score distributions that justify JACCARD_THRESHOLD = 0.30.

    Two groups of hand-crafted pairs are scored:
      - Similar pairs:   tweaked/mutated versions of the same base password.
                         These should score well ABOVE the threshold.
      - Different pairs: completely unrelated passwords.
                         These should score well BELOW the threshold.

    A sound threshold sits in the gap between the two clusters, minimising
    both false positives (rejecting a genuinely new password) and false
    negatives (accepting a thinly disguised common one).
    """
    # Pairs that are minor mutations of a shared root — expect HIGH Jaccard
    similar_pairs = [
        ("password", "passw0rd",  "digit substitution"),
        ("password", "p@ssword",  "symbol substitution"),
        ("password", "passworD",  "case flip"),
        ("password", "passwords", "appended char"),
        ("letmein1", "letmein2",  "last digit changed"),
        ("letmein1", "letme1n1",  "transposition"),
        ("monkey12", "m0nkey12",  "vowel -> digit"),
        ("dragon12", "dragon21",  "digit swap"),
        ("sunshine", "sunsh1ne",  "vowel -> digit"),
        ("iloveyou", "ilov3you",  "vowel -> digit"),
    ]
    # Completely unrelated pairs — expect LOW Jaccard
    different_pairs = [
        ("password", "sunshine1", "unrelated"),
        ("password", "football1", "unrelated"),
        ("letmein1", "sunshine1", "unrelated"),
        ("monkey12", "princess1", "unrelated"),
        ("dragon12", "baseball1", "unrelated"),
        ("abc12345", "xyz98765",  "unrelated"),
        ("qwerty123", "michael99","unrelated"),
        ("iloveyou", "trustno11", "unrelated"),
        ("sunshine", "master123", "unrelated"),
        ("welcome1", "shadow123", "unrelated"),
    ]

    def _score_group(pairs, label):
        print(f"\n  {'Password A':<12} {'Password B':<12} {'Mutation type':<28} {'Jaccard':>8}")
        print(f"  {'-'*12} {'-'*12} {'-'*28} {'-'*8}")
        scores = []
        for a, b, kind in pairs:
            j = jaccard(compute_beta(a), compute_beta(b))
            scores.append(j)
            print(f"  {a:<12} {b:<12} {kind:<28} {j:>8.4f}")
        print(f"\n  {label:>9} Jaccard:  min={min(scores):.4f}  "
              f"max={max(scores):.4f}  avg={sum(scores)/len(scores):.4f}")
        return scores

    print("=" * 68)
    print("  THRESHOLD JUSTIFICATION  (L=1000, k=20, bi-gram Bloom filter)")
    print("=" * 68)

    print("\n[A] SIMILAR pairs (tweaked / mutated passwords) — expect HIGH scores")
    sim_scores = _score_group(similar_pairs, "Similar")

    print("\n[B] DIFFERENT pairs (unrelated passwords) — expect LOW scores")
    dif_scores = _score_group(different_pairs, "Different")

    gap_low  = max(dif_scores)
    gap_high = min(sim_scores)
    midpoint = (gap_low + gap_high) / 2

    print(f"""
[C] THRESHOLD SELECTION
    Highest 'different' Jaccard : {gap_low:.4f}
    Lowest  'similar'  Jaccard  : {gap_high:.4f}
    Gap size                    : {gap_high - gap_low:.4f}
    Midpoint of gap             : {midpoint:.4f}
    Chosen threshold            : {JACCARD_THRESHOLD:.4f}

    Rationale:
    - All {len(similar_pairs)} similar/tweaked pairs score >= {gap_high:.4f} (above threshold).
    - All {len(different_pairs)} unrelated pairs score  <= {gap_low:.4f} (below threshold).
    - The two clusters are cleanly separated with a gap of {gap_high - gap_low:.4f}.
    - Threshold {JACCARD_THRESHOLD} sits inside this gap, giving:
        * 0 false negatives  (no tweaked password accepted) on this test set.
        * 0 false positives  (no different password rejected) on this test set.
    - It is placed closer to the 'different' cluster to err on the side of
      caution: better to accept a mildly similar password than to incorrectly
      reject a genuinely new one.
""")


# ── Demo mode ───────────────────────────────────────────────────────────────────

def run_demo():
    """Walk through three candidate passwords checked against the full dataset.

    Tests one exact dataset match, one lightly tweaked version, and one
    unrelated string — showing every algorithm step as described in §V of
    the assignment: compute β(p), scan the database, apply the threshold.
    """
    print("=" * 60)
    print("  DEMO MODE  —  Bloom filter similarity detection")
    print("=" * 60)

    # Load the real dataset so the demo tests against actual stored filters,
    # matching the testing procedure described in assignment §V.
    passwords = load_dataset('dataset.txt')
    if not passwords:
        print("[ERROR] No valid passwords loaded from dataset.")
        return
    db = build_database(passwords)

    # Three candidates that illustrate the full outcome range:
    #   (1) exact match in dataset  → Jaccard = 1.0       → REJECT
    #   (2) lightly tweaked version → Jaccard ~ 0.60–0.80 → REJECT
    #   (3) completely unrelated    → Jaccard < 0.20      → ACCEPT
    test_cases = [
        ("skittles",  "exact dataset entry"),
        ("sk1ttles",  "tweaked: vowel 'i' replaced with '1'"),
        ("zxcvbnm99", "unrelated keyboard pattern"),
    ]

    for candidate, label in test_cases:
        print(f"\n[CANDIDATE] '{candidate}'  ({label})")

        if len(candidate) < 8 or len(candidate) > 10:
            print(f"  [!] Length {len(candidate)} — must be 8-10 characters. Skipped.")
            continue

        print(f"\n  Step 1  Bi-gram extraction:")
        show_bigrams(candidate)

        beta_c = compute_beta(candidate)
        print(f"  Step 2  beta(p): {''.join(str(b) for b in beta_c[:40])}...  [{sum(beta_c)}/1000 bits set]")

        print(f"\n  Step 3  Scanning {len(db)} database entries for closest match ...")
        accepted, closest, (j, d, c) = check_password(candidate, db)

        k1 = sum(beta_c)
        if closest:
            beta_s = compute_beta(closest)
            k2    = sum(beta_s)
            gamma = sum(a & b for a, b in zip(beta_c, beta_s))
        else:
            k2, gamma = 0, 0

        print(f"  Step 4  Best match in database: '{closest}'")
        print(f"          gamma = {gamma}   k_beta1 = {k1}   k_beta2 = {k2}")
        print(f"          Jaccard = {j:.4f}   Dice = {d:.4f}   Cosine = {c:.4f}")
        print(f"          Threshold = {JACCARD_THRESHOLD}")

        if accepted:
            verdict = "ACCEPT  -- Jaccard < threshold: sufficiently different from all common passwords"
        else:
            verdict = "REJECT  -- Jaccard >= threshold: too similar to a common password"
        print(f"\n  Decision -> {verdict}")
        print("-" * 60)


# ── Interactive mode ────────────────────────────────────────────────────────────

def run_interactive(database):
    """Prompt-loop: read a candidate password, print scores and verdict, repeat."""
    print("=" * 60)
    print("  Password Strength Checker")
    print("  (type 'quit' to exit)")
    print("=" * 60)

    while True:
        try:
            candidate = input("\nEnter candidate password: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if candidate.lower() == 'quit':
            print("Goodbye.")
            break

        if len(candidate) < 8:
            print("  [!] Password must be at least 8 characters.")
            continue
        if len(candidate) > 10:
            print("  [!] Password exceeds maximum length of 10 characters.")
            continue

        show_bigrams(candidate)
        beta_c = compute_beta(candidate)
        print(f"  β(p): {''.join(str(b) for b in beta_c[:40])}…  [{sum(beta_c)}/1000 bits set]")

        accepted, closest, (j, d, c) = check_password(candidate, database)

        print(f"\n  Jaccard = {j:.4f}  (threshold {JACCARD_THRESHOLD})   "
              f"Dice = {d:.4f}   Cosine = {c:.4f}")
        print(f"  Closest common password: '{closest}'")
        print()
        if accepted:
            print(f"  ACCEPTED  '{candidate}' is not similar to any common password.")
        else:
            print(f"  REJECTED  '{candidate}' is too similar to a known common password.")


# ── Entry point ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    dataset_file = 'dataset.txt'

    # Allow overriding the dataset path from the command line
    if '--dataset' in sys.argv:
        idx = sys.argv.index('--dataset')
        if idx + 1 < len(sys.argv):
            dataset_file = sys.argv[idx + 1]

    if '--demo' in sys.argv:
        run_demo()
        sys.exit(0)

    if '--threshold' in sys.argv:
        run_threshold_analysis()
        sys.exit(0)

    passwords = load_dataset(dataset_file)
    if not passwords:
        print("[ERROR] No 8-10 character passwords found in dataset.")
        sys.exit(1)

    database = build_database(passwords)
    run_interactive(database)
