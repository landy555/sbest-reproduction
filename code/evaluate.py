#!/usr/bin/env python3
"""Unified evaluation for all baselines + SBEST.

Evaluates, using the paper's exact functions (rank_methods / get_map / get_mrr):
  - Stack Trace baseline (uses ST position directly)
  - SBEST (modifiedOchiai3.1.7)
  - traditional Ochiai (originalOchiai)

Then compares against the paper's stored results (top_k_data.csv,
per-project metrics CSV) and exports one summary CSV.

Run the score generators first:
  python run_sbest.py     # produces results/ochiaiScores/modifiedOchiai3.1.7/
  python run_ochiai.py    # produces results/ochiaiScores/originalOchiai/
"""

import os
import sys
import glob
import csv

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
RESULTS_DIR = os.path.join(BASE, "results")

paths_dict = {
    "ochiai_scores_path": os.path.join(RESULTS_DIR, "ochiaiScores"),
    "ranking_files_path": os.path.join(RESULTS_DIR, "ochiaiRankings"),
    "data_file_path": os.path.join(DATA_DIR, "bug_reports_with_stack_traces_details.json"),
    "paper_top_k": os.path.join(RESULTS_DIR, "paper_top_k_data.csv"),
    "paper_per_project": os.path.join(RESULTS_DIR, "paper_metrics_per_project.csv"),
    "output_summary": os.path.join(RESULTS_DIR, "reproduced_comparison.csv"),
}

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import utils

problematic_bugs = ["Mockito_17", "Mockito_22", "Mockito_25", "Mockito_30", "Mockito_31", "Mockito_35"]
top_k = [1, 3, 5, 10]

# Each Ochiai variant has its own score folder + failing-tests info file.
OCHIAI_VARIANTS = [
    {"id": "modifiedOchiai3.1.7", "failing_info_file": "modifiedOchiai3.1.7_fake_failing_tests_info.json"},
    {"id": "originalOchiai", "failing_info_file": "failing_tests_info.json"},
]

bugs_data = utils.json_file_to_dict(paths_dict["data_file_path"])

top_k_obj = {}          # technique -> { "Top k": count }
project_metrics = {}    # project -> { metric_key: value }


# ============ Evaluate each Ochiai variant ============
for idx, variant in enumerate(OCHIAI_VARIANTS):
    ident = variant["id"]
    scores_path = os.path.join(paths_dict["ochiai_scores_path"], ident)
    failing_info = utils.json_file_to_dict(os.path.join(scores_path, variant["failing_info_file"]))

    print("=" * 60)
    print("Evaluating " + ident)
    print("=" * 60)

    top_k_obj[ident] = {f"Top {k}": 0 for k in top_k}

    # ---- Phase 1: ranking + Top-K ----
    for score_file in glob.glob(scores_path + os.sep + "*" + os.sep + "*.json"):
        project = score_file.split(os.sep)[-2]
        bug_id = score_file.split(os.sep)[-1].replace(".json", "")

        if f"{project}_{bug_id}" in problematic_bugs:
            continue
        if "buggyMethods" not in bugs_data[project][bug_id] or bugs_data[project][bug_id]["buggyMethods"] == {}:
            continue
        if project not in failing_info or bug_id not in failing_info[project]:
            continue

        buggyMethods = bugs_data[project][bug_id]["buggyMethods"]
        scores = utils.sort_dict_by_values_reverse_order(utils.json_file_to_dict(score_file))
        if len(scores) == 0:
            continue

        ranking = utils.rank_methods(scores)
        utils.dict_to_json_file(os.path.join(paths_dict["ranking_files_path"], ident, project, bug_id + ".json"), ranking)
        buggy_methods_list = utils.extract_buggy_methods_list(ranking, buggyMethods)

        # Stack Trace baseline: computed once, on the first variant's bug set
        if idx == 0:
            if 'Stack Trace' not in top_k_obj:
                top_k_obj['Stack Trace'] = {f"Top {k}": 0 for k in top_k}
            stack_trace_methods = []
            for m in bugs_data[project][bug_id]["stack_trace_methods"]:
                stack_trace_methods.append(utils.remove_between_dollar_and_dot(m) if "$" in m else m)
            pos_st = utils.get_first_buggy_method_in_stack_trace(buggy_methods_list, stack_trace_methods)
            for k in top_k:
                try:
                    p = int(pos_st)
                except ValueError:
                    continue
                if p <= k:
                    top_k_obj['Stack Trace'][f"Top {k}"] += 1

        # Current variant Top-K
        pos = utils.get_best_classified_buggy_method(ranking, buggy_methods_list)
        for k in top_k:
            try:
                p = int(pos)
            except (ValueError, TypeError):
                continue
            if p <= k:
                top_k_obj[ident][f"Top {k}"] += 1

    # ---- Phase 2: per-project MAP/MRR ----
    for project in bugs_data.keys():
        if project not in project_metrics:
            project_metrics[project] = {}
        proj_obj = project_metrics[project]

        # Skip projects with no failing tests (their column stays empty in the paper)
        if project not in failing_info:
            continue

        project_bugs_data = bugs_data[project]
        bug_ids = [f"{project}_{pid}" for pid in project_bugs_data.keys()]
        for bid in bug_ids:
            if bid in problematic_bugs:
                del project_bugs_data[bid.split("_")[1]]

        # Stack Trace MAP/MRR (computed once, on the first variant)
        if idx == 0:
            proj_obj['Map Stack Traces'] = utils.get_map(project, "stackTraces", project_bugs_data, None)
            proj_obj['MRR Stack Traces'] = utils.get_mrr(project, "stackTraces", project_bugs_data, None)

        proj_obj['Map ' + ident] = utils.get_map(project, ident, bugs_data[project], paths_dict["ranking_files_path"])
        proj_obj['MRR ' + ident] = utils.get_mrr(project, ident, bugs_data[project], paths_dict["ranking_files_path"])


# ============ Compare with paper + export summary ============
print("\n" + "=" * 60)
print("COMPARISON: Reproduced vs Paper")
print("=" * 60)

# Techniques in display order
TECHNIQUES = ['Stack Trace', 'modifiedOchiai3.1.7', 'originalOchiai']

paper_top_k = {}
with open(paths_dict["paper_top_k"]) as f:
    reader = csv.DictReader(f)
    for row in reader:
        paper_top_k[row['Técnica']] = row

paper_pp = {}
with open(paths_dict["paper_per_project"]) as f:
    reader = csv.DictReader(f)
    for row in reader:
        paper_pp[row['Project']] = row

# metric key -> paper CSV column name
def paper_col(technique):
    return {
        'Stack Trace': ('Map Stack Traces', 'MRR Stack Traces'),
        'modifiedOchiai3.1.7': ('Map modifiedOchiai3.1.7', 'MRR modifiedOchiai3.1.7'),
        'originalOchiai': ('Map originalOchiai', 'MRR originalOchiai'),
    }[technique]


print("\n--- Top-K ---")
print(f"{'Technique':<22} {'Metric':<8} {'Reproduced':>12} {'Paper':>12} {'Match':>8}")
print("-" * 66)

all_match = True
for tech in TECHNIQUES:
    repro = top_k_obj.get(tech, {})
    paper = paper_top_k.get(tech, {})
    for k in top_k:
        r_val = repro.get(f"Top {k}", 0)
        p_val = int(paper.get(f"Top {k}", 0)) if paper else 'N/A'
        match = '✓' if r_val == p_val else '✗'
        if r_val != p_val:
            all_match = False
        print(f"{tech:<22} Top-{k:<5} {r_val:>12} {p_val:>12} {match:>8}")

print("\n--- Per-Project MAP/MRR ---")
print(f"{'Project':<16} {'Technique':<20} {'Metric':<6} {'Reproduced':>14} {'Paper':>14} {'Diff':>12}")
print("-" * 86)

for project in sorted(project_metrics.keys()):
    proj_obj = project_metrics[project]
    p_row = paper_pp.get(project, {})
    for tech in TECHNIQUES:
        map_col, mrr_col = paper_col(tech)
        for label, repro_key, pcol in [
            ('MAP', 'Map ' + tech if tech != 'Stack Trace' else 'Map Stack Traces', map_col),
            ('MRR', 'MRR ' + tech if tech != 'Stack Trace' else 'MRR Stack Traces', mrr_col),
        ]:
            repro_val = proj_obj.get(repro_key)
            paper_val_str = p_row.get(pcol, '').strip()
            paper_val = float(paper_val_str) if paper_val_str != '' else None
            if repro_val is not None and paper_val is not None:
                diff = repro_val - paper_val
                flag = '' if abs(diff) < 1e-9 else '  ✗'
                if abs(diff) >= 1e-9:
                    all_match = False
                print(f"{project:<16} {tech:<20} {label:<6} {repro_val:>14.9f} {paper_val:>14.9f} {diff:>+12.3e}{flag}")

print("\n" + ("ALL MATCH ✓" if all_match else "SOME MISMATCH ✗"))


# ---- Export unified summary CSV ----
with open(paths_dict["output_summary"], 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['section', 'technique', 'metric', 'project', 'reproduced', 'paper', 'diff'])
    for tech in TECHNIQUES:
        repro = top_k_obj.get(tech, {})
        paper = paper_top_k.get(tech, {})
        for k in top_k:
            r_val = repro.get(f"Top {k}", 0)
            p_val = int(paper.get(f"Top {k}", 0)) if paper else ''
            writer.writerow(['topk', tech, f'Top {k}', '', r_val, p_val, r_val - p_val if paper else ''])

    for project in sorted(project_metrics.keys()):
        proj_obj = project_metrics[project]
        p_row = paper_pp.get(project, {})
        for tech in TECHNIQUES:
            map_col, mrr_col = paper_col(tech)
            for label, repro_key, pcol in [
                ('map', 'Map ' + tech if tech != 'Stack Trace' else 'Map Stack Traces', map_col),
                ('mrr', 'MRR ' + tech if tech != 'Stack Trace' else 'MRR Stack Traces', mrr_col),
            ]:
                repro_val = proj_obj.get(repro_key)
                paper_val_str = p_row.get(pcol, '').strip()
                paper_val = float(paper_val_str) if paper_val_str != '' else ''
                diff = (repro_val - paper_val) if (repro_val is not None and paper_val != '') else ''
                writer.writerow([label, tech, 'MAP' if label == 'map' else 'MRR', project, repro_val, paper_val, diff])

print(f"\nSummary saved to: {paths_dict['output_summary']}")
