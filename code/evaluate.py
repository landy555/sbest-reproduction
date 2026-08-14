#!/usr/bin/env python3
"""Reproduces notebook 9 (analyseOchiaiOutputs) evaluation logic.

Computes Top-K, MAP, MRR for:
- Stack Trace baseline
- modifiedOchiai3.1.7 (SBEST)

Then compares with the paper's stored results (top_k_data.csv, per-project CSV).
"""

import os
import sys
import glob
import csv
import copy

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
RESULTS_DIR = os.path.join(BASE, "results")

paths_dict = {
    "ochiai_scores_path": os.path.join(RESULTS_DIR, "ochiaiScores"),
    "ranking_files_path": os.path.join(RESULTS_DIR, "ochiaiRankings"),
    "data_file_path": os.path.join(DATA_DIR, "bug_reports_with_stack_traces_details.json"),
    "paper_top_k": os.path.join(RESULTS_DIR, "paper_top_k_data.csv"),
    "paper_per_project": os.path.join(RESULTS_DIR, "paper_metrics_per_project.csv"),
    "output_top_k": os.path.join(RESULTS_DIR, "reproduced_top_k_data.csv"),
    "output_per_project": os.path.join(RESULTS_DIR, "reproduced_metrics_per_project.csv"),
}

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paper_utils as utils

top_k = [1, 3, 5, 10]
top_k_obj = {}
top_k_per_project_obj = {}

bugs_data = utils.json_file_to_dict(paths_dict["data_file_path"])
bug_metrics = {}
project_metrics = {}

problematic_bugs = ["Mockito_17", "Mockito_22", "Mockito_25", "Mockito_30", "Mockito_31", "Mockito_35"]

# Only evaluate modifiedOchiai3.1.7
ochiai_identificator = "modifiedOchiai3.1.7"
top_k_obj[ochiai_identificator] = {}
top_k_per_project_obj[ochiai_identificator] = {}

ochiai_scores_path = os.path.join(paths_dict["ochiai_scores_path"], ochiai_identificator)
failing_tests_file_name = utils.json_file_to_dict(
    os.path.join(ochiai_scores_path, ochiai_identificator + "_fake_failing_tests_info.json"))

print("=" * 60)
print("Phase 3: Evaluating " + ochiai_identificator)
print("=" * 60)

for bug_report_analysis_file in glob.glob(ochiai_scores_path + os.sep + "*" + os.sep + "*.json"):
    project = bug_report_analysis_file.split(os.sep)[-2]
    if project not in top_k_per_project_obj[ochiai_identificator].keys():
        top_k_per_project_obj[ochiai_identificator][project] = {}

    bug_id = bug_report_analysis_file.split(os.sep)[-1].replace(".json", "")

    if f"{project}_{bug_id}" in problematic_bugs:
        continue

    if "buggyMethods" not in bugs_data[project][bug_id].keys() or bugs_data[project][bug_id]["buggyMethods"] == {}:
        continue

    buggyMethods = bugs_data[project][bug_id]["buggyMethods"]
    stack_trace_files = bugs_data[project][bug_id]["stack_trace_files"]
    stack_trace_methods_not_formatted = bugs_data[project][bug_id]["stack_trace_methods"]
    stack_trace_methods = []
    for method in stack_trace_methods_not_formatted:
        method_formatted = method
        if "$" in method_formatted:
            method_formatted = utils.remove_between_dollar_and_dot(method_formatted)
        stack_trace_methods.append(method_formatted)

    ochiai_scores_data = utils.json_file_to_dict(bug_report_analysis_file)
    ochiai_scores_data = utils.sort_dict_by_values_reverse_order(ochiai_scores_data)
    if len(ochiai_scores_data) == 0:
        print("No Ochiai scores for " + project + "_" + bug_id + ". Skipping.")
        continue

    ranking = utils.rank_methods(ochiai_scores_data)

    ranking_file_name = os.path.join(paths_dict["ranking_files_path"], ochiai_identificator, project, bug_id + ".json")
    utils.dict_to_json_file(ranking_file_name, ranking)

    buggy_methods_list = utils.extract_buggy_methods_list(ranking, buggyMethods)
    st_ranking = utils.get_st_raking_dict(stack_trace_methods)

    N = 10
    if project not in bug_metrics.keys():
        bug_metrics[project] = {}
    if bug_id not in bug_metrics[project].keys():
        bug_metrics[project][bug_id] = {}
    bug_obj = bug_metrics[project][bug_id]

    if project not in failing_tests_file_name.keys() or bug_id not in failing_tests_file_name[project].keys():
        continue

    # Stack Trace baseline (computed once per bug)
    if 'Stack Trace (ST) size' not in bug_obj.keys():
        bug_obj['Stack Trace (ST) size'] = len(stack_trace_files)
        number_buggy_methods = 0
        for file in buggyMethods.keys():
            number_buggy_methods += len(buggyMethods[file])
        bug_obj['Number of buggy methods'] = number_buggy_methods
        bug_obj['Position of the first buggy method into the ST'] = utils.get_first_buggy_method_in_stack_trace(buggy_methods_list, stack_trace_methods)
        bug_obj['Precision ST Top 10'] = utils.get_precision_top_n(st_ranking, N, buggy_methods_list)
        bug_obj['Recall ST Top 10'] = utils.get_recall_top_n(st_ranking, N, buggy_methods_list)
        bug_obj['F1 ST Top 10'] = utils.get_f1_top_n(st_ranking, N, buggy_methods_list)

        if 'Stack Trace' not in top_k_obj.keys():
            top_k_obj['Stack Trace'] = {}
            top_k_per_project_obj['Stack Trace'] = {}
        if project not in top_k_per_project_obj['Stack Trace'].keys():
            top_k_per_project_obj['Stack Trace'][project] = {}
        for k in top_k:
            if f"Top {k}" not in top_k_obj['Stack Trace'].keys():
                top_k_obj['Stack Trace'][f"Top {k}"] = 0
            if f"Top {k}" not in top_k_per_project_obj['Stack Trace'][project].keys():
                top_k_per_project_obj['Stack Trace'][project][f"Top {k}"] = 0
            try:
                pos = int(bug_obj['Position of the first buggy method into the ST'])
            except ValueError:
                continue
            if pos <= k:
                top_k_obj['Stack Trace'][f"Top {k}"] += 1
                top_k_per_project_obj['Stack Trace'][project][f"Top {k}"] += 1

    # SBEST (modifiedOchiai3.1.7)
    bug_obj['Position of the first buggy method into the ' + ochiai_identificator] = utils.get_best_classified_buggy_method(ranking, buggy_methods_list)
    bug_obj['Precision ' + ochiai_identificator + ' Top 10'] = utils.get_precision_top_n(ranking, N, buggy_methods_list)
    bug_obj['Recall ' + ochiai_identificator + ' Top 10'] = utils.get_recall_top_n(ranking, N, buggy_methods_list)
    bug_obj['F1 ' + ochiai_identificator + ' Top 10'] = utils.get_f1_top_n(ranking, N, buggy_methods_list)

    for k in top_k:
        if f"Top {k}" not in top_k_obj[ochiai_identificator].keys():
            top_k_obj[ochiai_identificator][f"Top {k}"] = 0
        if f"Top {k}" not in top_k_per_project_obj[ochiai_identificator][project].keys():
            top_k_per_project_obj[ochiai_identificator][project][f"Top {k}"] = 0
        try:
            pos = int(bug_obj['Position of the first buggy method into the ' + ochiai_identificator])
        except ValueError:
            continue
        if pos <= k:
            top_k_obj[ochiai_identificator][f"Top {k}"] += 1
            top_k_per_project_obj[ochiai_identificator][project][f"Top {k}"] += 1

    bug_obj['Number of fake failing tests ' + ochiai_identificator] = failing_tests_file_name[project][bug_id]["fake_failing_tests_number"]
    bug_obj['Number of fake passing tests ' + ochiai_identificator] = failing_tests_file_name[project][bug_id]["fake_passing_tests_number"]

# ============ Per-project MAP/MRR ============
print("\n" + "=" * 60)
print("Phase 4: Computing per-project MAP/MRR")
print("=" * 60)

for project in bugs_data.keys():
    if project not in project_metrics.keys():
        project_metrics[project] = {}
    proj_obj = project_metrics[project]
    if project not in failing_tests_file_name.keys():
        continue

    project_bugs_data = bugs_data[project]
    bug_ids = []
    for id in project_bugs_data.keys():
        bug_ids.append(f"{project}_{id}")
    for id in bug_ids:
        if id in problematic_bugs:
            id_to_delete = id.split("_")[1]
            del project_bugs_data[id_to_delete]

    if 'Map  Stack Traces' not in proj_obj.keys():
        proj_obj['Map Stack Traces'] = utils.get_map(project, "stackTraces", project_bugs_data, None)
        proj_obj['MRR Stack Traces'] = utils.get_mrr(project, "stackTraces", project_bugs_data, None)

    proj_obj['Map ' + ochiai_identificator] = utils.get_map(project, ochiai_identificator, bugs_data[project], paths_dict["ranking_files_path"])
    proj_obj['MRR ' + ochiai_identificator] = utils.get_mrr(project, ochiai_identificator, bugs_data[project], paths_dict["ranking_files_path"])

    print(f"\n---- {project}")
    print(f"Map Stack Traces      = {proj_obj['Map Stack Traces']:.6f}")
    print(f"MRR Stack Traces      = {proj_obj['MRR Stack Traces']:.6f}")
    print(f"Map {ochiai_identificator} = {proj_obj['Map ' + ochiai_identificator]:.6f}")
    print(f"MRR {ochiai_identificator} = {proj_obj['MRR ' + ochiai_identificator]:.6f}")

# ============ Save reproduced results ============
with open(paths_dict["output_top_k"], 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    headers = ["Technique"] + [f"Top {k}" for k in top_k]
    writer.writerow(headers)
    for technique in ['Stack Trace', ochiai_identificator]:
        if technique in top_k_obj:
            row = [technique] + [top_k_obj[technique].get(f"Top {k}", 0) for k in top_k]
            writer.writerow(row)

# ============ Compare with paper ============
print("\n" + "=" * 60)
print("COMPARISON: Reproduced vs Paper")
print("=" * 60)

# Top-K comparison
print("\n--- Top-K ---")
print(f"{'Technique':<25} {'Metric':<8} {'Reproduced':>12} {'Paper':>12} {'Match':>8}")
print("-" * 67)

paper_top_k = {}
with open(paths_dict["paper_top_k"]) as f:
    reader = csv.DictReader(f)
    for row in reader:
        paper_top_k[row['Técnica']] = row

for technique in ['Stack Trace', ochiai_identificator]:
    repro = top_k_obj.get(technique, {})
    paper = paper_top_k.get(technique, {})
    for k in top_k:
        r_val = repro.get(f"Top {k}", 0)
        p_val = int(paper.get(f"Top {k}", 0)) if paper else 'N/A'
        match = '✓' if r_val == p_val else '✗'
        print(f"{technique:<25} Top-{k:<5} {r_val:>12} {p_val:>12} {match:>8}")

# Per-project MAP/MRR comparison
print("\n--- Per-Project MAP/MRR ---")
paper_pp = {}
with open(paths_dict["paper_per_project"]) as f:
    reader = csv.DictReader(f)
    for row in reader:
        paper_pp[row['Project']] = row

print(f"\n{'Project':<18} {'Metric':<8} {'Reproduced':>12} {'Paper':>12} {'Diff':>10}")
print("-" * 62)

repro_maps_st = []
repro_maps_sbest = []
paper_maps_st = []
paper_maps_sbest = []

for project in sorted(project_metrics.keys()):
    proj_obj = project_metrics[project]
    p_row = paper_pp.get(project, {})

    for label, repro_key, paper_col, repro_list, paper_list in [
        ('Map ST', 'Map Stack Traces', 'Map Stack Traces', repro_maps_st, paper_maps_st),
        ('MRR ST', 'MRR Stack Traces', 'MRR Stack Traces', repro_maps_st, paper_maps_st),
        ('Map SBEST', 'Map ' + ochiai_identificator, 'Map modifiedOchiai3.1.7', repro_maps_sbest, paper_maps_sbest),
        ('MRR SBEST', 'MRR ' + ochiai_identificator, 'MRR modifiedOchiai3.1.7', repro_maps_sbest, paper_maps_sbest),
    ]:
        repro_val = proj_obj.get(repro_key)
        paper_val_str = p_row.get(paper_col, '').strip()
        if paper_val_str == '':
            paper_val = None
        else:
            paper_val = float(paper_val_str)

        if repro_val is not None and paper_val is not None:
            diff = repro_val - paper_val
            print(f"{project:<18} {label:<8} {repro_val:>12.6f} {paper_val:>12.6f} {diff:>+10.6f}")
            if 'Map' in label:
                repro_list.append(repro_val)
                paper_list.append(paper_val)
        elif repro_val is not None:
            print(f"{project:<18} {label:<8} {repro_val:>12.6f} {'N/A':>12} {'N/A':>10}")
        elif paper_val is not None:
            print(f"{project:<18} {label:<8} {'N/A':>12} {paper_val:>12.6f} {'N/A':>10}")

# Overall (mean of non-empty per-project)
print("\n--- Overall (mean of per-project) ---")
if repro_maps_st:
    print(f"Stack Trace  MAP: reproduced={sum(repro_maps_st)/len(repro_maps_st):.4f}  paper={sum(paper_maps_st)/len(paper_maps_st):.4f}")
if repro_maps_sbest:
    print(f"SBEST        MAP: reproduced={sum(repro_maps_sbest)/len(repro_maps_sbest):.4f}  paper={sum(paper_maps_sbest)/len(paper_maps_sbest):.4f}")

print("\nDone. Results saved to:")
print(f"  {paths_dict['output_top_k']}")
print(f"  {paths_dict['output_per_project']}")
