"""
app.py
Flask web server for the CSCI262 Password Similarity Checker.

Routes
------
GET  /        Serve the single-page HTML UI.
POST /check   Accept a JSON password, run the Bloom-filter comparison,
              return scores and verdict as JSON.
"""

import os
from flask import Flask, render_template, request, jsonify

from bloom_filter import compute_beta, get_bigrams
from similarity import jaccard, dice, cosine, JACCARD_THRESHOLD

app = Flask(__name__)

# In-memory list of (plaintext, beta_vector) tuples built at startup.
# Storing pre-computed betas avoids re-hashing the dataset on every request.
database = []


def load_passwords(path):
    """Read dataset.txt and return only passwords that are 8–10 characters.

    The 8–10 limit matches the accepted input range, so the comparison set
    is always length-compatible with any candidate the user can type.
    """
    passwords = []
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            p = line.strip()
            if 8 <= len(p) <= 10:
                passwords.append(p)
    return passwords


def init_db():
    """Load the dataset and pre-compute every password's Bloom filter.

    Without pre-computation each /check request would re-hash every stored
    password (250 entries × 20 positions × ~10 bigrams ≈ 50 000 hash
    operations per request). Pre-computing once at startup reduces every
    query to an integer-comparison scan — O(n) in dataset size with zero
    hashing at query time. This is the efficient algorithm design required
    by assignment learning outcome VI(e).

    Called once before the first request is served.
    """
    global database
    # Resolve dataset path relative to this file, not the working directory
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset.txt")
    passwords = load_passwords(path)
    database = [(p, compute_beta(p)) for p in passwords]
    print(f"[*] Loaded {len(database)} passwords from dataset.")


@app.route("/")
def index():
    """Render the main UI, injecting dataset size and threshold into the template."""
    return render_template(
        "index.html",
        db_size=len(database),
        threshold=JACCARD_THRESHOLD
    )


@app.route("/check", methods=["POST"])
def check():
    """Compare the submitted password against every entry in the database.

    Algorithm
    ---------
    1. Validate length (8–10 characters).
    2. Compute beta(candidate) via the Bloom filter.
    3. Linear scan: track the entry with the highest Jaccard score.
       Dice and Cosine are only computed when a new Jaccard best is found,
       so we never pay for them on non-winning comparisons.
    4. Apply the threshold to produce the ACCEPT / REJECT verdict.

    Returns JSON with scores, verdict, bi-gram data, and beta snippet for the UI.
    """
    data = request.get_json()
    candidate = data.get("password", "").strip()

    # Server-side length validation (client also validates, but never trust only client)
    if len(candidate) < 8:
        return jsonify({"error": "Password must be at least 8 characters."})
    if len(candidate) > 10:
        return jsonify({"error": "Password must be at most 10 characters."})

    # Bi-gram data for the UI breakdown panel
    bigrams = get_bigrams(candidate)
    padded  = " " + candidate + " "    # space-padded form shown in the UI

    # Compute the candidate's Bloom filter and extract display fields
    beta_c       = compute_beta(candidate)
    beta_snippet = "".join(str(b) for b in beta_c[:40])   # first 40 bits for the visualiser
    bits_set     = sum(beta_c)

    # Linear scan — find the stored password most similar to the candidate
    best_j, best_d, best_c, best_match = 0.0, 0.0, 0.0, None
    best_gamma, best_k2 = 0, 0

    for (stored, beta_s) in database:
        j = jaccard(beta_c, beta_s)
        if j > best_j:          # new best: update all metrics for this entry
            best_j     = j
            best_d     = dice(beta_c, beta_s)
            best_c     = cosine(beta_c, beta_s)
            best_match = stored
            # γ = common 1-bits; k_β₂ = 1-bits in the stored filter
            best_gamma = sum(a & b for a, b in zip(beta_c, beta_s))
            best_k2    = sum(beta_s)

    reject = best_j >= JACCARD_THRESHOLD   # True → password is too common

    return jsonify({
        "reject":     reject,
        "best_match": best_match,
        "jaccard":    round(best_j, 3),
        "dice":       round(best_d, 3),
        "cosine":     round(best_c, 3),
        "gamma":      best_gamma,          # γ: shared 1-bits between candidate and best match
        "k1":         bits_set,            # k_β₁: 1-bits in candidate's filter
        "k2":         best_k2,             # k_β₂: 1-bits in best match's filter
        "bigrams":    bigrams,
        "padded":     padded,
        "beta_snippet": beta_snippet,
        "threshold":  JACCARD_THRESHOLD,
    })


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
