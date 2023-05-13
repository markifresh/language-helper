from pathlib import Path
from json import load as j_load
from json import dumps as j_dumps
from time import sleep
import concurrent.futures
from csv import writer as csv_writer
from csv import DictWriter as csv_DictWriter
from traceback import format_exc as traceback_format_exc


def format_words_list(words: list, chunk_size=20):
    words = [{'id': index, 'word': word} for index, word in enumerate(words)]
    return [
        words[i: i + chunk_size]
        for i in range(0, len(words), chunk_size)
    ]


# file_prefix - filename, f.e. Spanish_vocab-name
def make_offset_file(file_prefix, offset_value, folder_path: str):
    file = Path(folder_path)
    file = file.joinpath(f'{file_prefix}.offset-{offset_value}.json')
    if not file.exists():
        file.touch()
    return file


def offsets_files_get(file_prefix: str, folder_path: str):
    offsets_path = Path(folder_path)
    return [offset_file for offset_file in offsets_path.glob(f'{file_prefix}.offset*')]


def offset_file_data_get(file: Path):
    with file.open() as file_data:
        json_data = j_load(file_data)
    return json_data


def merge_dicts(dicts_list: list):
    merged_dict = {}
    res = [merged_dict.update(dictionary) for dictionary in dicts_list]
    return merged_dict


def merge_lists(lists: list):
    merged_list = []

    for one_list in lists:
        merged_list += one_list

    return merged_list


def check_missing(words_origin: list, words_modified: list):
    is_string = isinstance(words_origin[0], str)
    if is_string:
        ids_origin = list(range(0, len(words_origin)))
    else:
        ids_origin = [word['id'] for word in words_origin]

    ids_modified = [word['id'] for word in words_modified]

    return [word_id for word_id in ids_origin if word_id not in ids_modified]


"""
    to check all missing words after creating, need to 
        - load all json files
        - merge them to variable
        - run check_missing()
"""


def make_gpt_request(words: list):
    sleep(5)
    return {'modified': words, 'unmodified': words}



def thread_func(words_list: list, from_lang, to_lang):

    new_words = make_gpt_request(words_list)
    pass


# words lists has structure [ [{},{}], [{},{}], ... ]
def threads_run(function, function_data: list = None, function_kwargs: list = None, max_workers=5, ):
    result_list = []
    if function_kwargs is None:
        function_kwargs = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(function, data_chunk, *function_kwargs) for data_chunk in function_data]

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                result_list.append({'result': result, 'error': None})
            except Exception as e:
                result_list.append({'result': None, 'error': e})

    return result_list
    # Merge all dictionaries into a single dictionary
    # handle exception in thread? If function fails returns empty list and empty file
    # take chunk from pool till the pool is empty
    # create file (offset number takes from words list, by id[-1] - len(words) or some other way
    # return combined results


def find_matching_files(directory, string, extension):
    pattern = f"*{string}*{extension}"
    path = Path(directory)
    matching_files = list(path.glob(pattern))
    return matching_files


def write_data_to_csv_file(file_name: str, data_list: list):
    file_name = file_name + '.csv' if '.csv' not in file_name else file_name
    file = Path(file_name)
    with open(file.absolute(), encoding="utf-8", mode="w", newline='') as new_file:
        writer = csv_writer(new_file)
        headers = data_list[0].keys()
        other_rows = [obj.values() for obj in data_list]
        writer.writerow(headers)
        writer.writerows(other_rows)
    return file


def write_data_to_json_file(file: Path, data):
    data = j_dumps(data)
    file.write_text(data, encoding='UTF-8')
    return file


def save_as_csv(list_of_dicts, file_name: str, folder_path: str):
    file = Path(folder_path)
    if not file_name.endswith('.csv'):
        file_name += '.csv'
    file = file.joinpath(file_name)
    file_path = str(file)
    keys = list_of_dicts[0].keys() if list_of_dicts else []

    with open(file_path, 'w', newline='') as csvfile:
        writer = csv_DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(list_of_dicts)

    return Path(file_path)