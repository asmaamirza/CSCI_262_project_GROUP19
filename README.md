# Password Similarity Checker
### CSCI262 — Spring 2026 · University of Wollongong in Dubai

Detects whether a candidate password is identical to, or a tweaked version of, a commonly used password — using **Bloom filters**, **bi-gram hashing**, and three **set-similarity metrics**.

---

## How It Works

### 1. Bloom Filter Fingerprint `β(p)`

Every password in the dataset is converted to a **1 000-bit fingerprint** at startup:

1. Pad the password with spaces: `"cat"` → `" cat "`
2. Extract all consecutive 2-character pairs (bi-grams): `[" c", "ca", "at", "t "]`
3. For each bi-gram, compute 20 bit positions using double-hashing:

```
h_i(b) = (SHA-256(b) + i × MD5(b)) mod 1000    for i = 0 … 19
```

4. Set those positions to `1` in a 1 000-bit vector
5. OR all per-bigram vectors together → final filter `β(p)`

Parameters: **L = 1 000 bits · k = 20 hash functions · f = SHA-256 · g = MD5**

### 2. Similarity Metrics

Three metrics compare any two filters. All use:
- **γ** — number of bit positions where both filters are `1` (bitwise AND count)
- **k_β** — total number of `1`-bits in a filter

| Metric | Formula | Role |
|--------|---------|------|
| Jaccard | `γ / (k_β₁ + k_β₂ − γ)` | **Primary decision metric** |
| Dice | `2γ / (k_β₁ + k_β₂)` | Reference |
| Cosine | `γ / (√k_β₁ × √k_β₂)` | Reference |

### 3. Decision Rule

```
Jaccard(β(candidate), β(stored)) ≥ 0.30  →  REJECT
                                  < 0.30  →  ACCEPT
```

The threshold 0.30 sits inside a 0.41-wide gap between two measured clusters:
- Similar / tweaked pairs score **0.59 – 0.75**
- Unrelated pairs score **0.07 – 0.18**

---

## Project Structure

```
csci262_project/
├── app.py              # Flask web server (GET / · POST /check)
├── bloom_filter.py     # β(p) computation: bi-grams, double-hashing, OR
├── similarity.py       # Jaccard, Dice, Cosine + JACCARD_THRESHOLD
├── main.py             # CLI interface (interactive / --demo / --threshold)
├── dataset.txt         # 250 common passwords (8–10 characters, RockYou subset)
├── templates/
│   └── index.html      # Single-page web UI
├── requirements.txt    # flask
└── run.bat             # One-click launcher (Windows)
```

---

## Quick Start

### Web App (recommended)

```bash
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000** in your browser.

Or on Windows, double-click **`run.bat`**.

### Command Line

```bash
# Interactive mode — type passwords one at a time
python main.py

# Step-by-step demo: exact match, tweaked version, unrelated string
python main.py --demo

# Print full threshold justification with scored pair tables
python main.py --threshold

# Use a custom dataset file
python main.py --dataset path/to/passwords.txt
```

---

## Web UI Features

| Panel | Contents |
|-------|----------|
| **Left — How It Works** | Six interactive accordions: Bloom Filter (with live bit visualiser), Jaccard, Dice, Cosine, Threshold Justification (gap chart + pair score table), Critical Analysis (false positives, bit saturation, trade-offs) |
| **Right — Checker** | Password input, animated score bars for all three metrics, γ / k_β₁ / k_β₂ raw values, ACCEPT / REJECT verdict |
| **Right — Bi-gram Breakdown** | Padded string, individual bi-gram chips, first 40 bits of β(p) |

Hovering a metric name in the left panel highlights the corresponding score bar on the right.

---

## Dataset

`dataset.txt` contains **250 passwords** drawn from the RockYou leak, filtered to **8–10 characters** (the accepted input range). All filters are pre-computed once at startup — queries require no hashing at runtime (assignment LO VI(e): efficient algorithm design).

---

## Learning Outcomes Covered

| # | Outcome | Where |
|---|---------|-------|
| 1 | Bloom filter techniques to reject tweaked common passwords | `bloom_filter.py`, `app.py`, web UI |
| 2 | Cryptographic hash functions (SHA-256, MD5) in a security context | `bloom_filter.py` |
| 3 | Bi-gram analysis and Jaccard coefficient for password similarity | `bloom_filter.py`, `similarity.py` |
| 4 | Threshold justification | `similarity.py`, `main.py --threshold`, Threshold accordion in UI |
| 5 | Critical discussion of results | Critical Analysis accordion in UI |
| 6 | Python implementation | All source files |

---

## References

- Antognini, C. and Trivadis, A. (2008). *Bloom Filters.*
- Berardi, D. et al. (2021). *Password similarity using probabilistic data structures.* Journal of Cybersecurity and Privacy 1(1): 78–92.
- Blustein, J. and El-Maazawi, A. (2002). *Bloom filters: a tutorial, analysis, and survey.* Dalhousie University.
- Kroll, M. and Steinmetzer, S. (2015). *Automated Cryptanalysis of Bloom Filter Encryptions of Databases with Several Personal Identifiers.* BIOSTEC, Springer.
