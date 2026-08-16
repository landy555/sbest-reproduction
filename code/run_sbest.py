#!/usr/bin/env python3
"""Reproduces modifiedOchiai3.1.7 notebook exactly.

Runs the SBEST algorithm (3.1.7):
1. Read coverage data (methods_matrix, methods_spectra, test_results_original_ochiai)
2. Define fake failing tests (Top 5 ST × 0.5×lines + 0.5×methods → Top 15)
3. Compute Ochiai with fake failing tests
4. Add ST scores (1/rank for rank ≤ 10, else 0.1) for ALL stack trace methods
5. Save scores to results/ochiaiScores/modifiedOchiai3.1.7/
"""

import os
import sys
import math
import copy

# Paths
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
RESULTS_DIR = os.path.join(BASE, "results")

paths_dict = {
    "gzoltar_files_path": os.path.join(DATA_DIR, "gzoltar_files"),
    "output_file": os.path.join(RESULTS_DIR, "ochiaiScores", "modifiedOchiai3.1.7"),
    "data_file_path": os.path.join(DATA_DIR, "bug_reports_with_stack_traces_details.json"),
    "failing_tests_info_file_name": "modifiedOchiai3.1.7_fake_failing_tests_info.json",
    "tests_analysis_results": os.path.join(DATA_DIR, "rq1_results.json"),
    "fake_test_results_file_name": "fake_test_results_modifiedOchiai3.1.7.csv",
    "tests_covering_stack_traces_folder": os.path.join(DATA_DIR, "tests_covering_stack_traces_details_per_bug"),
}

N_FAKE_FAILING_TESTS = 15

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import utils


# ============ Cell 3: Reading the coverage data ============
print("=" * 60)
print("Phase 1: Reading coverage data")
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
        print("Number of tests in bug " + project + "-" + bug_id + " - " + str(len(test_names)))
        coverage["test_results"] = [True] * len(test_names)  # Erasing the real test results
        coverage_data[project][bug_id] = coverage
    except FileNotFoundError:
        print("The bug " + project + "-" + bug_id + " does not contain one of the required files. Skipping it")
        continue

print("Done reading coverage data.\n")


# ============ Cell 5: Defining fake failing tests and Running Ochiai ============
print("=" * 60)
print("Phase 2: Computing SBEST (modifiedOchiai3.1.7) scores")
print("=" * 60)

fake_failing_tests_info = {}
for project in coverage_data.keys():
    for bug_id in coverage_data[project].keys():

        bug_data = bugs_data[project][bug_id]
        coverage = coverage_data[project][bug_id]

        print(project + " ---- " + bug_id)

        fake_failed_tests = []
        methods_list = []

        if bug_data["stackTraceMethodsDetails"] == {}:
            print("The bug does not contain stackTraceMethodsDetails. Skipping.")
            print()
            continue

        print("* Part 1 - defining the fake failing tests")

        tests_covering_stack_traces_file_path = os.path.join(
            paths_dict["tests_covering_stack_traces_folder"], project, bug_id + ".json")
        tests_covering_stack_traces_details = utils.json_file_to_dict(tests_covering_stack_traces_file_path)

        stack_trace_methods_not_formatted_first_5 = bug_data["stack_trace_methods"][:5]
        stack_trace_methods_first_5 = []
        for method in stack_trace_methods_not_formatted_first_5:
            method_formatted = method
            if "$" in method_formatted:
                method_formatted = utils.remove_between_dollar_and_dot(method_formatted)
            stack_trace_methods_first_5.append(method_formatted)
        stack_trace_files_first_5 = bug_data["stack_trace_files"][:5]
        stack_traces_methods_test_count = {}
        num_lines_covered_per_test = {}
        for index, st_file in enumerate(stack_trace_files_first_5):
            st_method = stack_trace_methods_first_5[index].split(".")[-1]
            st_file_complete_name = utils.find_file_complete_name(st_file, bug_data) 
            if st_file_complete_name:     # Double-checked locking
                if st_method in bug_data["stackTraceMethodsDetails"][st_file_complete_name].keys() and \
                   "tests_covering_the_method" in tests_covering_stack_traces_details[st_file_complete_name][st_method].keys():
                    for test in tests_covering_stack_traces_details[st_file_complete_name][st_method]["tests_covering_the_method"]:
                        num_lines = len(tests_covering_stack_traces_details[st_file_complete_name][st_method]["tests_covering_the_method"][test])
                        if test in stack_traces_methods_test_count.keys():
                            stack_traces_methods_test_count[test] += 1
                            num_lines_covered_per_test[test] += num_lines
                        else:
                            stack_traces_methods_test_count[test] = 1    # Initial occurrence
                            num_lines_covered_per_test[test] = num_lines

        coverage["fake_test_results"] = [True for _ in coverage["test_results"]]
        number_of_failing_tests = 0
        methods_ochiai_scores = {}
        if stack_traces_methods_test_count != {}:

            scores_per_test = {}
            for test in stack_traces_methods_test_count.keys():
                scores_per_test[test] = 0.5 * num_lines_covered_per_test[test] + 0.5 * stack_traces_methods_test_count[test]

            selected_tests = utils.get_top_n_keys(scores_per_test, scores_per_test.keys(), N_FAKE_FAILING_TESTS)

            print("* Part 2 - preparing the fake_tests_status")
            for index, test in enumerate(coverage["test_names"]):
                if test in selected_tests:
                    number_of_failing_tests += 1
                    coverage["fake_test_results"][index] = False
                else:
                    coverage["fake_test_results"][index] = True

            if number_of_failing_tests > 0:

                print("Storing the fake test results")
                utils.store_fake_test_results(coverage, project, bug_id, paths_dict["gzoltar_files_path"], paths_dict["fake_test_results_file_name"])

                print("* Part 3 - Executing Ochiai")
                for index_m, method_name in enumerate(coverage["methods_obj_list"]):
                    n00 = 0
                    n01 = 0
                    n10 = 0
                    n11 = 0
                    s_o = 0
                    for index_t, test_name in enumerate(coverage["test_names"]):
                        if str(coverage["methods_covered_per_test"][index_t][index_m]) == "1":
                            if not coverage["fake_test_results"][index_t]:
                                n11 += 1
                            else:
                                n10 += 1
                        else:
                            if not coverage["fake_test_results"][index_t]:
                                n01 += 1
                            else:
                                n00 += 1
                    try:
                        s_o = n11 / math.sqrt((n11 + n01) * (n11 + n10))
                    except ZeroDivisionError:    # 防除零
                        s_o = 0
                    methods_ochiai_scores[method_name] = s_o

        # Stack traces part: sum 1/ranking to the calculated score
        stack_trace_methods_not_formatted = bugs_data[project][bug_id]["stack_trace_methods"]
        stack_trace_methods = []
        for method in stack_trace_methods_not_formatted:
            method_formatted = method
            if "$" in method_formatted:
                method_formatted = utils.remove_between_dollar_and_dot(method_formatted)
            stack_trace_methods.append(method_formatted)
        for index, st_method in enumerate(stack_trace_methods):
            found = False
            st_method_id = st_method
            score = 1 / (index + 1)
            if index > 9:
                score = 0.1

            if '#' not in st_method:       # 名字归一化
                last_dot_index = st_method.rfind('.')
                if last_dot_index != -1:
                    st_method_id = st_method[:last_dot_index] + '#' + st_method[last_dot_index + 1:]
            for method in methods_ochiai_scores:
                if method.endswith(st_method_id):       # 后缀匹配
                    methods_ochiai_scores[method] += score
                    found = True
                    break
            if not found:
                methods_ochiai_scores[st_method_id] = score

        if project not in fake_failing_tests_info.keys():
            fake_failing_tests_info[project] = {}

        # Store the number of fake passing and failing tests for this bug
        fake_failing_tests_info[project][bug_id] = {}
        fake_failing_tests_info[project][bug_id]["fake_passing_tests_number"] = len(coverage["fake_test_results"]) - number_of_failing_tests
        fake_failing_tests_info[project][bug_id]["fake_failing_tests_number"] = number_of_failing_tests

        print("Number of fake passing tests: " + str(fake_failing_tests_info[project][bug_id]["fake_passing_tests_number"]))
        print("Number of fake failing tests: " + str(fake_failing_tests_info[project][bug_id]["fake_failing_tests_number"]) + "\n")
        utils.dict_to_json_file(os.path.join(paths_dict["output_file"], project, bug_id + ".json"), methods_ochiai_scores)

utils.dict_to_json_file(os.path.join(paths_dict["output_file"], paths_dict["failing_tests_info_file_name"]), fake_failing_tests_info)
print("\nExecution completed. Scores saved to " + paths_dict["output_file"])
