from pathlib import Path
from unicodedata import normalize as uni_normalize
from json import load as j_load
from json import dumps as j_dumps
from time import sleep
import concurrent.futures
from csv import writer as csv_writer
from csv import DictWriter as csv_DictWriter
from csv import DictReader as csv_DictReader
from traceback import format_exc as traceback_format_exc


def make_file_object(file, folder='', with_exception=False):
    file = file if isinstance(file, Path) else Path(folder, file)
    if with_exception:
        if not file.exists():
            raise Exception(f'can not find file "{str(file)}"')
    return file


def words_standardize(words):
    return [uni_normalize('NFKD', word).strip() for word in words]


def format_words_list(words: list, chunk_size=20):
    words = [{'id': index, 'word': word} for index, word in enumerate(words)]
    return [
        words[i: i + chunk_size]
        for i in range(0, len(words), chunk_size)
    ]


# file_prefix - filename, f.e. Spanish_vocab-vocabulary_name
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


# def check_missing(new_words: list, existing_words: list):
#     is_string = isinstance(new_words[0], str)
#     if is_string:
#         ids_origin = list(range(0, len(new_words)))
#     else:
#         ids_origin = [word['id'] for word in new_words]
#
#     ids_modified = [word['id'] for word in existing_words]
#
#     return [word_id for word_id in ids_origin if word_id not in ids_modified]

def check_missing(new_words: list, existing_words: list):
    if isinstance(new_words[0], dict):
        new_words = [word['word'] for word in new_words]
    new_words = [word.lower().strip() for word in new_words]

    if existing_words and isinstance(existing_words[0], dict):
        existing_words = [word['whole_word'].lower() for word in existing_words] + \
                         [word['word'].lower() for word in existing_words]

    return [word for word in new_words if word not in existing_words]


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


def load_data_from_csv_file(file_path: str, folder=''):
    file_obj = make_file_object(folder, file_path, with_exception=True)
    data = []
    with open(str(file_obj), mode='r', encoding='utf-8') as file:
        reader = csv_DictReader(file)
        for row in reader:
            data.append(row)
    return data


def save_as_csv(list_of_dicts, file_name: str, folder_path=''):
    file = make_file_object(file_name, folder_path)
    if file.suffix != '.csv':
        file = file.with_suffix('.csv')

    if file.exists():
        file.unlink()

    file_path = str(file)
    keys = list_of_dicts[0].keys() if list_of_dicts else []

    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv_DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(list_of_dicts)

    return Path(file_path)