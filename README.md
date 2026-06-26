# CSCI_262_project_GROUP19 — Password Similarity Checker
### CSCI262 — Spring 2026 · University of Wollongong in Dubai · Group 19

Detects whether a candidate password is too similar to a commonly used password — using **Bloom filters**, **bi-gram hashing**, and three **set-similarity metrics** (Jaccard, Dice, Cosine).

---

## How It Works

### 1. Bloom Filter Fingerprint `β(p)`

Every password is converted to a **1 000-bit fingerprint** at startup:

1. Pad the password with spaces: `"cat"` → `" cat "`
2. Extract consecutive 2-character pairs (bi-grams): `[" c", "ca", "at", "t "]`
3. For each bi-gram, compute 20 bit positions using double-hashing:

```
f = SHA-256(bigram)
g = MD5(bigram)
h_i(b) = (f + i × g) mod 1000    for i = 0 … 19
```

4. Set those positions to `1` in a 1 000-bit vector
5. OR all per-bigram vectors together → final filter `β(p)`

**Parameters: L = 1 000 bits · k = 20 hash functions**

### 2. Similarity Metrics

All three metrics operate on the pre-computed beta vectors:

| Metric | Formula | Role |
|--------|---------|------|
| Jaccard | `γ / (k_β₁ + k_β₂ − γ)` | **Primary decision metric** |
| Dice | `2γ / (k_β₁ + k_β₂)` | Reference |
| Cosine | `γ / (√k_β₁ × √k_β₂)` | Reference |

Where **γ** = bits set in both filters (bitwise AND count), **k_β** = total 1-bits in a filter.

### 3. Decision Rule

```
Jaccard(β(UserP), β(stored)) >= 0.30  →  REJECT  (too similar to a common password)
                               <  0.30  →  ACCEPT
```

The threshold 0.30 sits in a 0.41-wide gap between two measured clusters:
- Similar / tweaked pairs score **0.59 – 0.75**
- Unrelated pairs score **0.07 – 0.18**

---

## Project Structure

```
CSCI_262_project_GROUP19/
├── app.py              # Flask web server (GET / · POST /check · GET /bloom/<n>)
├── bloom_filter.py     # beta(p) computation: bi-grams, SHA-256 + MD5, double-hashing
├── similarity.py       # Jaccard, Dice, Cosine + JACCARD_THRESHOLD = 0.30
├── main.py             # CLI interface (interactive / --demo / --threshold / --bloom)
├── dataset.txt         # 250 common passwords (8-10 characters, RockYou subset)
├── templates/
│   └── index.html      # Single-page web UI
├── requirements.txt    # flask
├── run.bat             # One-click launcher (Windows)
└── .gitignore
```

---

## Quick Start

### Web App (recommended)

```bash
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000** in your browser.

On Windows, double-click **`run.bat`** instead.

### Command Line

```bash
# Interactive mode — enter passwords one at a time, prints full JUSTIF table
python main.py

# Step-by-step demo: exact match, tweaked version, unrelated string
python main.py --demo

# Print full threshold justification with scored pair tables
python main.py --threshold

# Display the Bloom filter bit-vector for the Nth dataset entry (1-based)
python main.py --bloom 17
python main.py --bloom 55

# Use a custom dataset file
python main.py --dataset path/to/passwords.txt
```

---

## Web UI Features

| Panel | Contents |
|-------|----------|
| **Left — How It Works** | Six accordions: Bloom Filter (live 40-bit visualiser), Jaccard, Dice, Cosine, Threshold Justification (gap chart + pair score table), Critical Analysis (false positives, bit saturation, trade-offs) |
| **Right — Input** | Password field (8–10 chars), Show/Hide toggle, Check button |
| **Right — Result** | Animated score bars for Jaccard / Dice / Cosine, γ / k_β₁ / k_β₂ raw values, ACCEPT / REJECT verdict with closest match |
| **Right — Bi-gram Breakdown** | Padded string, bi-gram chips, first 40 bits of β(p) |
| **Right — JUSTIF Table** | All 250 dataset passwords ranked by Jaccard against the candidate — appears after every check |
| **Right — Bloom Filter Viewer** | Preset buttons for Entry #17 and Entry #55; arbitrary index input; full 1 000-bit grid (20 rows × 50 bits) |

Hovering a metric name in the left panel highlights the corresponding score bar on the right.

---

## JUSTIF Table

After each check the app displays the full **JUSTIF** table required by the assignment:

| Column | Description |
|--------|-------------|
| # | Rank by Jaccard (1 = most similar) |
| Password | Dataset entry |
| Jaccard | `γ / (k_β₁ + k_β₂ − γ)` between β(UserP) and β(P) |
| Dice | `2γ / (k_β₁ + k_β₂)` |
| Cosine | `γ / (√k_β₁ × √k_β₂)` |

The closest-match row is highlighted. In the CLI, the full table is printed to the terminal with the best match starred (`*`).

---

## Bloom Filter Viewer

The web UI can display the full 1 000-bit Bloom filter for any dataset entry:

- Click **Entry #17** or **Entry #55** for the two entries required by the assignment
- Or type any index (1–250) and click **View**
- Each cell shows one bit; blue = 1, grey = 0; hover for the exact bit index

CLI equivalent: `python main.py --bloom 55`

---

## Dataset

`dataset.txt` contains **250 passwords** drawn from the RockYou leak, filtered to 8–10 characters. Bloom filters are pre-computed once at startup — no hashing occurs at query time.

---

## Learning Outcomes Covered

| # | Outcome | Where |
|---|---------|-------|
| 1 | Bloom filter to reject tweaked common passwords | `bloom_filter.py`, `app.py` |
| 2 | SHA-256 and MD5 in a cryptographic hashing context | `bloom_filter.py` |
| 3 | Bi-gram analysis and Jaccard / Dice / Cosine similarity | `bloom_filter.py`, `similarity.py` |
| 4 | Threshold justification (empirical gap analysis) | `similarity.py`, `main.py --threshold`, UI accordion |
| 5 | Critical discussion: false positives, bit saturation, trade-offs | Critical Analysis accordion in UI |
| 6 | Full JUSTIF table comparing UserP against all dataset passwords | `/check` route, `main.py` interactive mode |

---

## References

- Antognini, C. and Trivadis, A. (2008). *Bloom Filters.*
- Berardi, D. et al. (2021). *Password similarity using probabilistic data structures.* Journal of Cybersecurity and Privacy 1(1): 78–92.
- Blustein, J. and El-Maazawi, A. (2002). *Bloom filters: a tutorial, analysis, and survey.* Dalhousie University.
- Kroll, M. and Steinmetzer, S. (2015). *Automated Cryptanalysis of Bloom Filter Encryptions of Databases with Several Personal Identifiers.* BIOSTEC, Springer.
