from pathlib import Path
from json import load as j_load
from json import dumps as j_dumps
from time import sleep
import concurrent.futures

# to make as class WordsClient
# as functions have a lot of parameters, which should be set with object creation

def format_words_list(words: list, chunk_size=20):
    words = [{'id': index, 'word': word} for index, word in enumerate(words)]
    return [
                words[i: i+chunk_size]
                for i in range(0, len(words), chunk_size)
           ]


# file_prefix - filename, f.e. Spanish_vocab-name
def make_file(file_prefix, offset_value):
    file = Path(f'{file_prefix}.offset-{offset_value}.json')
    if not file.exists():
        file.touch()
    return file


def offsets_files_get(file_prefix: str, path: str):
    offsets_path = Path(path)
    return [offset_file for offset_file in offsets_path.glob(f'{file_prefix}.offset*')]


def offsets_files_cleanup(file_prefix: str):
    offset_files = offsets_files_get(file_prefix, '')
    for file in offset_files:
        file.unlink()


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
        ids_origin = range(0, len(words_origin))
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
    return words


def write_data_to_file(file: Path, data):
    data = j_dumps(data)
    file.write_text(data)
    return file


def thread_func(words_list: list):
    new_words = make_gpt_request(words_list)




# words lists has structure [ [{},{}], [{},{}], ... ]
def gpt_threads_run(words_lists: list, max_workers=5):
    result_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(make_gpt_request, words_list) for words_list in words_lists]

        # Retrieve results as they become available
        for future in concurrent.futures.as_completed(futures):
            result_list += future.result()

    return result_list
    # Merge all dictionaries into a single dictionary

    # take chunk from pool till the pool is empty
    # create file (offset number takes from words list, by id[-1] - len(words) or some other way
    # return combined results



def test():
    # get words
    import spanish_dict
    vocabs = spanish_dict.vocabs_get()
    beginner = [vocab for vocab in vocabs if vocab.get('name') == 'Beginner'][0]
    words = spanish_dict.vocab_content_get(beginner['id'], beginner['slug'])
    words = [word['source'] for word in words]

    # format words
    words_lists = format_words_list(words, 20)



    pass
