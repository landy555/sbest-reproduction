"""functions from the paper's code/utils.py.

Only the functions needed for experiment + evaluation are included.
No my_secrets dependency — paths are passed as arguments.
"""

import os
import re
import json
import csv
import glob


def json_file_to_dict(file_path):
    with open(file_path, 'r', encoding='utf-8') as fp:
        data = json.load(fp)
    return data


def dict_to_json_file(file_path, dic):
    folder = os.path.dirname(file_path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)
    with open(file_path, 'w') as fp:
        json.dump(dic, fp, sort_keys=True, indent=4)


def read_methods_matrix_file(file_path):
    statements_covered_per_test = []
    with open(os.path.join(file_path, "methods_matrix.txt"), 'r') as f:
        for line in f:
            row = [int(num) for num in line.strip().split()]
            statements_covered_per_test.append(row)
    return statements_covered_per_test


def read_methods_spectra_file(file_path):
    lines_of_code_obj_list = []
    with open(os.path.join(file_path, "methods_spectra.csv"), 'r') as file:
        first_line = True
        for line in file:
            if first_line:
                first_line = False
                continue
            lines_of_code_obj_list.append(line.replace("\n", ""))
    return lines_of_code_obj_list


def convert_to_boolean(value):
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def read_tests_csv_to_lists(file_path):
    with open(os.path.join(file_path, "test_results_original_ochiai.csv"), 'r') as csvfile:
        reader = csv.reader(csvfile)
        test_names = []
        test_results = []
        for row in reader:
            test_names.append(row[0].replace("\n", ""))
            test_results.append(convert_to_boolean(row[1]))
    return test_names, test_results


def get_list_of_bugs_with_coverage(data):
    bugs_list = list(
        data["bugs_with_stack_traces"][
            "bugs_without_failing_tests_in_commons_with_defects4j"].keys()) + \
        list(data["bugs_with_stack_traces"][
            "bugs_with_failing_tests_in_commons_with_defects4j"].keys())
    return bugs_list


def write_two_lists_to_csv(list1, list2, filename):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        for item1, item2 in zip(list1, list2):
            writer.writerow([item1, item2])


def store_fake_test_results(coverage, project, bug_id, gzoltar_files_path, file_name):
    project_gzoltar_folder = os.path.join(gzoltar_files_path, project)
    bug_gzoltar_folder = os.path.join(project_gzoltar_folder, bug_id)
    test_names = coverage["test_names"]
    fake_test_results = coverage["fake_test_results"]
    fake_test_results_file_path = os.path.join(bug_gzoltar_folder, file_name)
    write_two_lists_to_csv(test_names, fake_test_results, fake_test_results_file_path)


def find_file_complete_name(file, bug_data):
    for file_complete_name in bug_data["stackTraceMethodsDetails"].keys():
        if file_complete_name.endswith(file):
            return file_complete_name
    return None


def get_top_n_keys(dictionary, keys_to_consider, n):
    sorted_dict = sorted(dictionary.items(), key=lambda x: x[1], reverse=True)
    filtered_dict = [(key, value) for key, value in sorted_dict if key in keys_to_consider]
    top_n_pairs = filtered_dict[:n]
    top_n_keys = [pair[0] for pair in top_n_pairs]
    return top_n_keys


def sort_dict_by_values_reverse_order(dictionary):
    return dict(sorted(dictionary.items(), key=lambda item: item[1], reverse=True))


def remove_between_dollar_and_dot(st_method):
    return re.sub(r'\$[^.]*\.', '.', st_method)


def remove_between_dollar_and_hash(st_method):
    return re.sub(r'\$[^#]*#', '#', st_method)


def rank_methods(ochiai_scores_data):
    sorted_methods = sorted(ochiai_scores_data.items(), key=lambda x: x[1], reverse=True)
    ranked_methods = {}
    i = 0
    while i < len(sorted_methods):
        same_score_count = 1
        current_score = sorted_methods[i][1]
        for j in range(i + 1, len(sorted_methods)):
            if sorted_methods[j][1] == current_score:
                same_score_count += 1
            else:
                break
        for j in range(same_score_count):
            ranked_methods[sorted_methods[i + j][0]] = i + same_score_count
        i += same_score_count
    return ranked_methods


def get_st_raking_dict(stack_trace_methods):
    st_method_formated = []
    for st_method in stack_trace_methods:
        last_dot_index = st_method.rfind('.')
        if last_dot_index != -1:
            st_method_id = st_method[:last_dot_index] + '#' + st_method[last_dot_index + 1:]
            if '$' in st_method_id:
                st_method_id = remove_between_dollar_and_hash(st_method_id)
            st_method_formated.append(st_method_id)
    return {item: index + 1 for index, item in enumerate(st_method_formated)}


def get_first_buggy_method_in_stack_trace(buggy_methods_list, stack_trace_methods):
    best_position = float('inf')
    for buggy_method in buggy_methods_list:
        for index, st_method in enumerate(stack_trace_methods):
            st_method_id = st_method
            if '#' not in st_method:
                last_dot_index = st_method.rfind('.')
                if last_dot_index != -1:
                    st_method_id = st_method[:last_dot_index] + '#' + st_method[last_dot_index + 1:]
            if buggy_method.endswith(st_method_id):
                if (index + 1) < best_position:
                    best_position = index + 1
                break
    if best_position == float('inf'):
        best_position = "not found"
    return best_position


def get_best_classified_buggy_method(ranking_data, buggy_methods_list):
    best_position = float('inf')
    for method in buggy_methods_list:
        try:
            if ranking_data[method] < best_position:
                best_position = ranking_data[method]
        except:
            continue
    if best_position == float('inf'):
        best_position = "not found"
    return best_position


def find_method_in_ranking_data(method, ranking_data):
    best_match = None
    for m in ranking_data.keys():
        if method.endswith(m):
            if best_match is None or len(m) > len(best_match):
                best_match = m
    return best_match


def get_number_of_buggy_methods_in_top_n(ranking_data, n, buggy_methods_list):
    buggy_methods_in_top_n = 0
    for method in buggy_methods_list:
        try:
            method_in_pattern = find_method_in_ranking_data(method, ranking_data)
            if ranking_data[method_in_pattern] <= n:
                buggy_methods_in_top_n += 1
        except:
            continue
    return buggy_methods_in_top_n


def get_precision_top_n(ranking_data, n, buggy_methods_list):
    buggy_methods_in_top_n = get_number_of_buggy_methods_in_top_n(ranking_data, n, buggy_methods_list)
    precision = buggy_methods_in_top_n / n
    return precision


def get_recall_top_n(ranking_data, n, buggy_methods_list):
    if not buggy_methods_list:
        return 0
    buggy_methods_in_top_n = get_number_of_buggy_methods_in_top_n(ranking_data, n, buggy_methods_list)
    recall = buggy_methods_in_top_n / len(buggy_methods_list)
    return recall


def get_f1_top_n(ranking_data, n, buggy_methods):
    precision = get_precision_top_n(ranking_data, n, buggy_methods)
    recall = get_recall_top_n(ranking_data, n, buggy_methods)
    try:
        f1 = 2 * precision * recall / (precision + recall)
    except ZeroDivisionError:
        return 0.0
    return f1


def get_method_rank(ranking_info, method):
    for method_rank in ranking_info.keys():
        if method.endswith(method_rank):
            return ranking_info[method_rank]
    return float('inf')


def extract_buggy_methods_list(ranking_data, buggyMethods):
    buggy_methods_list = []
    temp = []
    for file in buggyMethods.keys():
        class_id = file.replace(".java", "")
        class_id = class_id.replace("/", ".")
        for method_name in buggyMethods[file]:
            method_id = class_id + "#" + method_name
            temp.append(method_id)
    for temp_method_id in temp:
        found = False
        for method_name in ranking_data.keys():
            if temp_method_id.endswith(method_name):
                buggy_methods_list.append(method_name)
                found = True
                break
        if not found:
            buggy_methods_list.append(temp_method_id)
    return buggy_methods_list


def convert_buggy_methods_dict_into_list(data):
    result = []
    for file, methods in data.items():
        class_name = file.replace(".java", "")
        class_name = class_name.replace("/", ".")
        for method, _ in methods.items():
            result.append(f"{class_name}#{method}")
    return result


def get_mrr(project, ochiai_identificator, project_bugs_data, ranking_files_path):
    sum_for_mrr = 0
    number_of_bugs = len(project_bugs_data)
    for bug_id in project_bugs_data.keys():
        no_classification_available = False
        buggy_methods = project_bugs_data[bug_id]["buggyMethods"]
        if not buggy_methods:
            number_of_bugs -= 1
            continue
        buggy_methods_list = convert_buggy_methods_dict_into_list(buggy_methods)
        if ochiai_identificator == "stackTraces":
            ranking_info = get_st_raking_dict(project_bugs_data[bug_id]["stack_trace_methods"])
        else:
            try:
                ranking_file = os.path.join(ranking_files_path, ochiai_identificator, project, bug_id + ".json")
                ranking_info = json_file_to_dict(ranking_file)
            except FileNotFoundError:
                no_classification_available = True
        best_rank_found = float('inf')
        if not no_classification_available and len(ranking_info.keys()) > 0:
            for buggy_method in buggy_methods_list:
                if get_method_rank(ranking_info, buggy_method) < best_rank_found:
                    best_rank_found = get_method_rank(ranking_info, buggy_method)
        sum_for_mrr += 1 / best_rank_found
    mrr = sum_for_mrr / number_of_bugs if number_of_bugs else 0
    return mrr


def get_map(project, ochiai_identificator, project_bugs_data, ranking_files_path):
    sum_for_map = 0
    number_of_bugs = 0
    for bug_id in project_bugs_data.keys():
        no_classification_available = False
        buggy_methods = project_bugs_data[bug_id]["buggyMethods"]
        if not buggy_methods:
            continue
        buggy_methods_list = convert_buggy_methods_dict_into_list(buggy_methods)
        if ochiai_identificator == "stackTraces":
            ranking_info = get_st_raking_dict(project_bugs_data[bug_id]["stack_trace_methods"])
        else:
            ranking_file = os.path.join(ranking_files_path, ochiai_identificator, project, bug_id + ".json")
            try:
                ranking_info = json_file_to_dict(ranking_file)
            except FileNotFoundError:
                no_classification_available = True
        number_of_bugs += 1
        relevant_docs = 0
        sum_for_ap = 0
        buggy_methods_found = 0
        if not no_classification_available:
            sorted_ranking_info = {k: v for k, v in
                                   sorted(ranking_info.items(), key=lambda item: item[1], reverse=False)}
            for method in sorted_ranking_info.keys():
                rank = sorted_ranking_info[method]
                for buggy_method in buggy_methods_list:
                    if buggy_method.endswith(method):
                        relevant_docs += 1
                        precision_at_rank = relevant_docs / rank
                        sum_for_ap += precision_at_rank
                        buggy_methods_found += 1
                        break
        n_buggy_methods = len(buggy_methods_list)
        sum_for_map += sum_for_ap / n_buggy_methods if n_buggy_methods else 0
    return sum_for_map / number_of_bugs if number_of_bugs else 0
