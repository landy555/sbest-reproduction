# SBEST Reproduction — SBEST, Traditional Ochiai & Stack Trace Baselines

Standalone reproduction of the key algorithms from:

> **SBEST: Spectrum-Based Fault Localization Without Fault-Triggering Tests** (Rafi et al., 2024). arXiv:2405.00565

This repository runs **only the core algorithm code** (no data-collection pipeline):

- `code/run_sbest.py` — SBEST algorithm (modifiedOchiai3.1.7), line-by-line port of `8-Ochiai_implementations/modifiedOchiai3.1.7_...ipynb`
- `code/run_ochiai.py` — traditional SBFL Ochiai baseline, line-by-line port of `8-Ochiai_implementations/OriginalOchiai.ipynb`
- `code/evaluate.py` — unified evaluation (Top-K / MAP / MRR) of all three techniques, line-by-line port of `9-analyseOchiaiOutputs.ipynb`
- `code/paper_utils.py` — the helper functions from the original `code/utils.py`

## Verified results

The reproduced numbers match the paper's stored results **exactly** (all diffs = 0):

| Technique | Top-1 | Top-3 | Top-5 | Top-10 |
|-----------|:---:|:---:|:---:|:---:|
| Stack Trace | 16 | 27 | 34 | 38 |
| SBEST (modifiedOchiai3.1.7) | 17 | 32 | 33 | 34 |
| Traditional Ochiai (originalOchiai) | 0 | 1 | 2 | 2 |

Per-project MAP/MRR also match the paper's `ochiaiResultsMetricsPerProject.csv` with zero difference.

## Required data

The reproduction needs three datasets that are **not included in this repo** (too large):

1. **GZoltar coverage data** (`data/gzoltar_files/`)
   - Method-level coverage matrices (`methods_matrix.txt`), method lists (`methods_spectra.csv`), and pre-computed test results (`test_results_original_ochiai.csv`) per bug.
   - Source: Zenodo record **https://zenodo.org/records/11062413** (extract to `data/gzoltar_files/`).

2. **Test-coverage-of-stack-trace details** (`data/tests_covering_stack_traces_details_per_bug/`)
   - For each bug, which tests cover which lines of each stack-trace method.
   - Source: the original repository's `data/tests_covering_stack_traces_details_per_bug/` (or regenerate via its notebook `6-extract_covered_lines_details.ipynb`).

3. **Bug reports + RQ1 results** (`data/bug_reports_with_stack_traces_details.json`, `data/rq1_results.json`)
   - Bug metadata (stack traces, buggy methods, commits) and the RQ1 bug classification.
   - Source: the original repository's `data/` folder (or Zenodo record above).

### Original repository

- Code & data: Zenodo https://zenodo.org/records/11062413
- Paper: https://arxiv.org/abs/2405.00565

## Setup & run

```bash
# 1. Get the data (see "Required data" above)
mkdir -p data
ln -s /path/to/gzoltar_files data/gzoltar_files
ln -s /path/to/tests_covering_stack_traces_details_per_bug data/tests_covering_stack_traces_details_per_bug
cp /path/to/bug_reports_with_stack_traces_details.json data/
cp /path/to/rq1_results.json data/

# 2. Generate the scores
python3 code/run_sbest.py    # -> results/ochiaiScores/modifiedOchiai3.1.7/
python3 code/run_ochiai.py   # -> results/ochiaiScores/originalOchiai/

# 3. Evaluate all techniques + compare with the paper
python3 code/evaluate.py
```

## Outputs

- `results/ochiaiScores/modifiedOchiai3.1.7/` — per-bug SBEST scores
- `results/ochiaiScores/originalOchiai/` — per-bug traditional Ochiai scores
- `results/ochiaiRankings/{modifiedOchiai3.1.7,originalOchiai}/` — per-bug method rankings
- `results/reproduced_comparison.csv` — unified comparison (Top-K + per-project MAP/MRR, reproduced vs paper)
- `results/paper_top_k_data.csv` — paper's stored Top-K (for comparison)
- `results/paper_metrics_per_project.csv` — paper's stored per-project MAP/MRR

## Notes

- The 6 problematic Mockito bugs (`Mockito_17/22/25/30/31/35`) are excluded, matching the paper.
- **SBEST** erases the real test results (`[True] * len(test_names)`) before selecting proxy failing tests; **traditional Ochiai** uses the real test results and skips bugs with no failing tests — both exactly as in the original notebooks.
