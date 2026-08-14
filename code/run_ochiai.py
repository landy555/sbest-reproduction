#!/usr/bin/env python3
"""Reproduce OriginalOchiai.ipynb — the traditional SBFL Ochiai baseline.

This script ONLY generates the Ochiai suspicion scores (one JSON per bug),
using the REAL test pass/fail results from the GZoltar execution.

Run this BEFORE evaluate.py:
  python run_ochiai.py   -> results/ochiaiScores/originalOchiai/
  python evaluate.py     -> evaluates Stack Trace + SBEST + Ochiai together

Bugs without failing tests are skipped (no score file), matching the paper's
OriginalOchiai.ipynb.
"""

import os
import sys
import math

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
RESULTS_DIR = os.path.join(BASE, "results")

paths_dict = {
    "gzoltar_files_path": os.path.join(DATA_DIR, "gzoltar_files"),
    "output_file": os.path.join(RESULTS_DIR, "ochiaiScores", "originalOchiai"),
    "data_file_path": os.path.join(DATA_DIR, "bug_reports_with_stack_traces_details.json"),
    "failing_tests_info_file_name": "failing_tests_info.json",
    "tests_analysis_results": os.path.join(DATA_DIR, "rq1_results.json"),
}

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paper_utils as utils


# ============ Phase 1: Reading the coverage data ============
print("=" * 60)
print("Phase 1: Reading coverage data (REAL test results)")
print("=" * 60)

bugs_data = utils.json_file_to_dict(paths_dict["data_file_path"])
tests_analysis_results = utils.json_file_to_dict(paths_dict["tests_analysis_results"])
bugs = utils.get_list_of_bugs_with_coverage(tests_analysis_results)
coverage_data = {}

for bug in bugs:
    project, bug_id = bug.split("_")
    project_gzoltar_folder = os.path.join(paths_dict["gzoltar_files_path"], project)
    if not os.path.exists(project_gzoltar_folder):
        print("Gzoltar folder not found for project " + project + ". Skipping!")
        continue
    if project not in coverage_data.keys():
        coverage_data[project] = {}

    bug_gzoltar_folder = os.path.join(project_gzoltar_folder, bug_id)
    if not os.path.exists(bug_gzoltar_folder):
        print("Gzoltar folder not found for bugId " + project + "-" + bug_id + ". Skipping!")
        continue

    coverage = {}
    try:
        coverage["methods_covered_per_test"] = utils.read_methods_matrix_file(bug_gzoltar_folder)
        coverage["methods_obj_list"] = utils.read_methods_spectra_file(bug_gzoltar_folder)
        test_names, test_results = utils.read_tests_csv_to_lists(bug_gzoltar_folder)
        coverage["test_names"] = test_names
        coverage["test_results"] = test_results  # REAL results — do NOT erase
        coverage_data[project][bug_id] = coverage
    except FileNotFoundError:
        print("The bug " + project + "-" + bug_id + " does not contain one of the required files. Skipping it")
        continue

print("Done reading coverage data.\n")


# ============ Phase 2: Running the original Ochiai (real failing tests) ============
print("=" * 60)
print("Phase 2: Computing originalOchiai scores (real failing tests)")
print("=" * 60)

failing_tests_info = {}
for project in coverage_data.keys():
    for bug_id in coverage_data[project].keys():
        bug = project + "_" + bug_id
        coverage = coverage_data[project][bug_id]
        print(bug)

        failing_tests = []
        for index, test in enumerate(coverage["test_names"]):
            if not coverage["test_results"][index]:  # failing test
                failing_tests.append(test)
        failing_tests = list(set(failing_tests))

        if not failing_tests:
            print("The bug " + project + "_" + bug_id + " does not contain failing tests. Skipping it")
            continue

        # Executing Ochiai with the REAL test results
        methods_ochiai_scores = {}
        for index_m, method_name in enumerate(coverage["methods_obj_list"]):
            n11 = 0
            n01 = 0
            n10 = 0
            s_o = 0
            for index_t in range(len(coverage["test_names"])):
                if str(coverage["methods_covered_per_test"][index_t][index_m]) == "1":
                    if not coverage["test_results"][index_t]:
                        n11 += 1
                    else:
                        n10 += 1
                else:
                    if not coverage["test_results"][index_t]:
                        n01 += 1
            try:
                s_o = n11 / math.sqrt((n11 + n01) * (n11 + n10))
            except ZeroDivisionError:
                s_o = 0
            methods_ochiai_scores[method_name] = s_o

        if project not in failing_tests_info.keys():
            failing_tests_info[project] = {}

        failing_tests_info[project][bug_id] = {}
        failing_tests_info[project][bug_id]["passing_tests_number"] = len(coverage["test_results"]) - len(failing_tests)
        failing_tests_info[project][bug_id]["failing_tests_number"] = len(failing_tests)

        print("Number of passing tests: " + str(failing_tests_info[project][bug_id]["passing_tests_number"]))
        print("Number of failing tests: " + str(failing_tests_info[project][bug_id]["failing_tests_number"]) + "\n")
        utils.dict_to_json_file(os.path.join(paths_dict["output_file"], project, bug_id + ".json"), methods_ochiai_scores)

utils.dict_to_json_file(os.path.join(paths_dict["output_file"], paths_dict["failing_tests_info_file_name"]), failing_tests_info)
print("\nScore generation completed. Scores saved to " + paths_dict["output_file"])
