import extra_functions
from pathlib import Path
import gpt_lang
import gpt_helper
import spanish_dict
from traceback import format_exc as traceback_format_exc
from json import loads as json_loads
from unicodedata import normalize as uni_normalize

# to make as class WordsClient
# as functions have a lot of parameters, which should be set with object creation
supported_from_lang = {}
supported_to_lang = {}


class Vocabulary:

    words_unmodified = []
    words_modified = []
    words_missing = []

    def __init__(self, from_lang, to_lang, vocabulary_source='custom', vocabulary_name='custom', level='A1',
                 folder='results', threads_workers=5, chunks_size=20):
        self.from_lang = from_lang
        self.to_lang = to_lang
        self.vocabulary_source = vocabulary_source.replace(' ', '_')
        self.vocabulary_name = vocabulary_name.replace(' ', '_')
        self.level = level
        self.folder = folder
        self.file_name = f'{self.from_lang}_{self.to_lang}.{self.vocabulary_source}_{self.vocabulary_name}'
        self.threads_workers = threads_workers
        self.chunks_size = chunks_size

    def is_similar(self, other_vocab):
        return (
                self.from_lang == other_vocab.from_lang and
                self.to_lang == other_vocab.to_lang and
                self.vocabulary_source == other_vocab.vocabulary_source and
                self.vocabulary_name == other_vocab.vocabulary_name and
                self.level == other_vocab.level
               )

    def set_words_unmodified(self, words: list):
        self.words_unmodified = words
        return words

    def set_words_modified(self, words: list):
        self.words_modified = words
        return words

    def set_words_missing(self, words: list):
        self.words_missing = words
        return words

    @staticmethod
    def load_words_from_csv(file_path, column_name):
        file = extra_functions.make_file_object(file_path, with_exception=True)
        return [word[column_name] for word in extra_functions.load_data_from_csv_file(file)]

    @staticmethod
    def load_vocabulary(file_path):
        file = extra_functions.make_file_object(file_path, with_exception=True)
        folder = str(file.parent)
        file_data = extra_functions.load_data_from_csv_file(str(file))
        one_line = file_data[0]
        vocab = Vocabulary(
                            from_lang=one_line['language'],
                            to_lang=one_line['to_language'],
                            vocabulary_source=one_line['source'].split(', ')[0],
                            vocabulary_name=one_line['source'].split(', ')[1],
                            level=one_line.get('level', 'A1'),
                            folder=folder
                         )
        vocab.set_words_modified(file_data)
        return vocab

    def merge_vocabularies(self, other_vocab):

        if not self.is_similar(other_vocab):
            raise Exception('Vocabularies should be identical in from_lang,to_lang, vocabulary_source, vocabulary_name, level')

        merged_list = self.words_modified
        for obj in other_vocab.words_modified:
            if obj not in merged_list:
                merged_list.append(obj)

        self.set_words_modified(merged_list)
        self.write_to_file()
        other_vocab.delete()

    def delete(self, remove_related_search=True):
        file = Path(self.folder)
        file = file.joinpath(self.file_name)
        file.unlink()

        if remove_related_search:
            self.search_cleanup()

    def update(self, modified_words: list):
        self.set_words_modified(modified_words)
        return self.write_to_file()

    def add_new_words(self, words: list, overwrite=True):
        words = extra_functions.words_standardize(words)
        words_to_search = extra_functions.check_missing(new_words=words, existing_words=self.words_modified)
        thread_results = self.search_make(words=words_to_search)
        self.search_save(thread_results)
        found_words = self.search_results()
        self.set_words_modified(self.words_modified + found_words)

        file = self.write_to_file(overwrite=overwrite)
        self.search_cleanup()
        missing_words = extra_functions.check_missing(new_words=words, existing_words=self.words_modified)
        return {'success': not missing_words,
                'thread_results': thread_results,
                'added_words': found_words,
                'missing_words': missing_words,
                'file': file}

    def write_to_file(self, overwrite=False):
        file_name = f'{self.from_lang}_{self.to_lang}.{self.vocabulary_source}_{self.vocabulary_name}'.lower()
        current_files = extra_functions.find_matching_files(self.folder, file_name, '.csv')
        current_index = len(current_files) - 1

        if not overwrite:
            current_index += 1

        index = '' if current_index < 1 else f'.{current_index}'
        file_name = f'{file_name}{index}'
        file = Path(self.folder)
        file = file.joinpath(file_name)
        return extra_functions.write_data_to_csv_file(str(file), self.words_modified)

    def search_make(self, words: list):
        words_chunked = extra_functions.format_words_list(words, self.chunks_size)
        gpt_requests_msg = gpt_lang.create_request_message(self.from_lang, self.to_lang, self.vocabulary_source,
                                                           self.vocabulary_name, self.level)
        gpt_requests = [gpt_requests_msg + str(words_list) for words_list in words_chunked]
        return extra_functions.threads_run(gpt_helper.send_question, gpt_requests, max_workers=self.threads_workers)

    def search_save(self, results: list):
        whole_result = []
        for result in results:
            if not result['error'] and result['result']['success']:
                message = result['result']['data']['message']
                json_result = []
                try:
                    json_result = json_loads(message)
                    whole_result += json_result
                except Exception:
                    result['error'] = traceback_format_exc()

                if not result['error'] and json_result:
                    json_result = sorted(json_result, key=lambda k: k['id'])
                    offset_value = f"{json_result[0]['id']}_{json_result[-1]['id']}"
                    file = extra_functions.make_offset_file(self.file_name, offset_value, self.folder)
                    try:
                        extra_functions.write_data_to_json_file(file, data=json_result)
                    except Exception:
                        file.unlink()
                        result['error'] = traceback_format_exc()
        return whole_result

    def search_results(self):
        files = extra_functions.offsets_files_get(self.file_name, folder_path=self.folder)
        files_contents = [extra_functions.offset_file_data_get(file) for file in files]
        return extra_functions.merge_lists(files_contents)

    def search_cleanup(self):
        files = extra_functions.offsets_files_get(self.file_name, folder_path=self.folder)
        for file in files:
            file.unlink()

    def words_modify(self, words, max_workers=5):
        words_chunked = extra_functions.format_words_list(words, 20)
        gpt_requests_msg = gpt_lang.create_request_message(self.from_lang, self.to_lang, self.vocabulary_source, self.vocabulary_name, self.level)
        gpt_requests = [gpt_requests_msg + str(words_list) for words_list in words_chunked]
        # res = gpt_threads_run(gpt_requests, max_workers=5)

        results = extra_functions.gpt_threads_run(words_chunked, max_workers=max_workers, file_name=self.file_name,
                                                  folder_path=self.folder)
        files = extra_functions.offsets_files_get(self.file_name, folder_path=self.folder)
        # files = [result['file'] for result in results]

        files_contents = [extra_functions.offset_file_data_get(file) for file in files]
        files_contents = extra_functions.merge_lists(files_contents)
        missing_words = extra_functions.check_missing(new_words=words, existing_words=files_contents)
        return {'success': not missing_words,
                'thread_results': results,
                'modified_words': files_contents,
                'missing_words': missing_words,
                'files': files}

    def words_export_to_csv(self, words: list):
        return extra_functions.save_as_csv(words, self.file_name, folder_path=self.folder)

    @staticmethod
    def anki_tags_add(file, folder=''):
        file = extra_functions.make_file_object(file, folder)
        file_data = extra_functions.load_data_from_csv_file(file)
        for i, file_line in enumerate(file_data):
            tags = []
            if file_line.get('id'):
                tags.append(f'language_tags::language::{file_line["language"]}')
                tags.append(f'language_tags::level::{file_line["level"]}')
                topics_list = (file_line['topics']).split(', ')
                tags += [f'language_tags::topics::{topic}' for topic in topics_list ]
                tags.append(f'language_tags::type::{file_line["type"]}')
                if 'true' in file_line.get('is_irregular', '').lower():
                    tags.append('language_tags::irregular')

                source = file_line.get('source', '')
                if not source:
                    print(file_line)
                if ', ' in source:
                    source, sub_source = (file_line['source']).split(', ')
                    tags.append(f'language_tags::source::{source}::{sub_source}')
                else:
                    tags.append(f'language_tags::source::{source}')
                file_line['anki_tags'] = ' '.join(tags)
                file_line['anki_tags_notion'] = ', '.join(tags)
                file_data[i] = file_line
        extra_functions.save_as_csv(file_data, file)
        return file_data


def create_vocabulary(words, from_lang, to_lang, vocab_source, vocab_name, level='', folder='results', overwrite=False,
                      create_new=False):
    vocab_source = vocab_source.replace(' ', '_')
    vocab_name = vocab_name.replace(' ', '_')
    file_name = f'{from_lang}_{to_lang}.{vocab_source}_{vocab_name}'.lower()

    current_files = extra_functions.find_matching_files(folder, file_name, '.csv')
    current_index = len(current_files) - 1

    if not create_new:
        index = f'.{current_index}' if current_index > 0 else ''
        file_name = f'{file_name}{index}'
        csv_file = Path(folder)
        csv_file = csv_file.joinpath(f'{file_name}.csv')
        if csv_file.exists():
            return {
                'success': True,
                'thread_results': [],
                'modified_words': [],
                'missing_words': [],
                'file': csv_file
            }

    if not overwrite:
        current_index += 1

    index = '' if current_index < 1 else f'.{current_index}'
    file_name = f'{file_name}{index}'

    files = extra_functions.offsets_files_get(file_name, folder_path=folder)
    if files:
        files_contents = [extra_functions.offset_file_data_get(file) for file in files]
        files_contents = extra_functions.merge_lists(files_contents)
        missing_words = extra_functions.check_missing(new_words=words, existing_words=files_contents)
        # words = [words[word_id] for word_id in missing_words]
        words = missing_words

    words_chunked = extra_functions.format_words_list(words, 20)
    gpt_requests_msg = gpt_lang.create_request_message(from_lang, to_lang, vocab_source, vocab_name, level)
    gpt_requests = [gpt_requests_msg + str(words_list) for words_list in words_chunked]
    # res = gpt_threads_run(gpt_requests, max_workers=5)

    results = extra_functions.threads_run(gpt_helper.send_question, gpt_requests, max_workers=5)
    for result in results:
        if not result['error'] and result['result']['success']:
            message = result['result']['data']['message']
            try:
                json_result = json_loads(message)
            except Exception:
                result['error'] = traceback_format_exc()

            if not result['error']:
                json_result = sorted(json_result, key=lambda k: k['id'])
                offset_value = f"{json_result[0]['id']}_{json_result[-1]['id']}"
                file = extra_functions.make_offset_file(file_name, offset_value, folder)
                try:
                    extra_functions.write_data_to_json_file(file, data=json_result)
                except Exception:
                    file.unlink()
                    raise Exception(traceback_format_exc())

    files = extra_functions.offsets_files_get(file_name, folder_path=folder)
    #files = [result['file'] for result in results]

    files_contents = [extra_functions.offset_file_data_get(file) for file in files]
    files_contents = extra_functions.merge_lists(files_contents)
    missing_words = extra_functions.check_missing(new_words=words, existing_words=files_contents)
    file = None
    if not missing_words:
        res = [file.unlink() for file in files]
        file = extra_functions.save_as_csv(files_contents, file_name, folder_path=folder)

    return {
                'success': not missing_words,
                'thread_results': results,
                'modified_words': files_contents,
                'missing_words': missing_words,
                'file': file
           }


