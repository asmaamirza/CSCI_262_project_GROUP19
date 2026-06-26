"""
app.py
Flask web server for the CSCI_262_project_GROUP19 Password Similarity Checker.

Routes
------
GET  /              Serve the single-page HTML UI.
POST /check         Accept a JSON password, run the Bloom-filter comparison,
                    return full JUSTIF table + verdict as JSON.
GET  /bloom/<int>   Return the Bloom filter bit-vector for the nth dataset entry.
"""

import os
from flask import Flask, render_template, request, jsonify

from bloom_filter import compute_beta, get_bigrams
from similarity import jaccard, dice, cosine, JACCARD_THRESHOLD

app = Flask(__name__)

# Pre-computed list of (plaintext, beta_vector) built once at startup.
database = []


def load_passwords(path):
    """Read dataset.txt and return only passwords that are 8–10 characters."""
    passwords = []
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            p = line.strip()
            if 8 <= len(p) <= 10:
                passwords.append(p)
    return passwords


def init_db():
    """Load dataset and pre-compute every password's Bloom filter once at startup.

    Pre-computing betas avoids re-hashing the dataset on every /check request —
    each query becomes a plain integer-comparison scan with no hashing at runtime.
    """
    global database
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
    2. Compute beta(candidate).
    3. Score every dataset entry with Jaccard, Dice, and Cosine.
    4. Track the best Jaccard match for the verdict.
    5. Sort all rows by Jaccard descending — this is the JUSTIF table.
    6. Apply the threshold to produce ACCEPT / REJECT.

    Returns JSON with the full JUSTIF table, verdict, Bloom bit data, and bigrams.
    """
    data = request.get_json()
    candidate = data.get("password", "").strip()

    if len(candidate) < 8:
        return jsonify({"error": "Password must be at least 8 characters."})
    if len(candidate) > 10:
        return jsonify({"error": "Password must be at most 10 characters."})

    bigrams     = get_bigrams(candidate)
    padded      = " " + candidate + " "
    beta_c      = compute_beta(candidate)
    beta_snippet = "".join(str(b) for b in beta_c[:40])
    bits_set    = sum(beta_c)

    # Score every stored password; build the full JUSTIF table in one pass.
    all_rows = []
    best_j, best_d, best_c, best_match = 0.0, 0.0, 0.0, None
    best_gamma, best_k2 = 0, 0

    for (stored, beta_s) in database:
        j = jaccard(beta_c, beta_s)
        d = dice(beta_c, beta_s)
        c = cosine(beta_c, beta_s)
        all_rows.append({
            "password": stored,
            "jaccard":  round(j, 4),
            "dice":     round(d, 4),
            "cosine":   round(c, 4),
        })
        if j > best_j:
            best_j, best_d, best_c, best_match = j, d, c, stored
            best_gamma = sum(a & b for a, b in zip(beta_c, beta_s))
            best_k2    = sum(beta_s)

    # Sort descending by Jaccard so the most similar password appears first.
    all_rows.sort(key=lambda r: r["jaccard"], reverse=True)

    reject = best_j >= JACCARD_THRESHOLD

    return jsonify({
        "reject":       reject,
        "best_match":   best_match,
        "jaccard":      round(best_j, 3),
        "dice":         round(best_d, 3),
        "cosine":       round(best_c, 3),
        "gamma":        best_gamma,
        "k1":           bits_set,
        "k2":           best_k2,
        "bigrams":      bigrams,
        "padded":       padded,
        "beta_snippet": beta_snippet,
        "threshold":    JACCARD_THRESHOLD,
        "all_rows":     all_rows,      # full JUSTIF table for the UI
    })


@app.route("/bloom/<int:index>")
def bloom_entry(index):
    """Return the full Bloom filter for the nth dataset entry (1-based index).

    Used by the UI's Bloom Filter Viewer to display and screenshot individual
    entries — specifically entries #17 and #55 required by the assignment.
    """
    if index < 1 or index > len(database):
        return jsonify({"error": f"Index must be between 1 and {len(database)}."})

    password, beta = database[index - 1]
    return jsonify({
        "index":    index,
        "password": password,
        "bits_set": sum(beta),
        "beta":     "".join(str(b) for b in beta),   # full 1000-bit string
    })


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
