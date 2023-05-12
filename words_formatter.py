import extra_functions
import gpt_lang
from pathlib import Path
import gpt_lang
import spanish_dict
from traceback import format_exc as traceback_format_exc

# to make as class WordsClient
# as functions have a lot of parameters, which should be set with object creation
supported_from_lang = {}
supported_to_lang = {}


class Vocabulary:
    words_unmodified = []
    words_modified = []

    def __int__(self, from_lang, to_lang, source, name, level='A1', folder='results'):
        self.from_lang = from_lang
        self.to_lang = to_lang
        self.source = source.replaca(' ', '_')
        self.name = name
        self.level = level
        self.folder = folder
        self.file_name = f'{self.from_lang}_{self.to_lang}.{self.source}_{self.name}'

    def set_words_unmodified(self, words: list):
        self.words_unmodified = words
        return words

    def set_words_modified(self, words: list):
        self.words_modified = words
        return words

    def words_modify(self, words, max_workers=5):
        words_chunked = extra_functions.format_words_list(words, 20)
        gpt_requests_msg = gpt_lang.create_request_message(self.from_lang, self.to_lang, self.source, self.name, self.level)
        gpt_requests = [gpt_requests_msg + str(words_list) for words_list in words_chunked]
        # res = gpt_threads_run(gpt_requests, max_workers=5)

        results = extra_functions.gpt_threads_run(words_chunked, max_workers=max_workers, file_name=self.file_name,
                                                  folder_path=self.folder)
        files = extra_functions.offsets_files_get(self.file_name, folder_path=self.folder)
        # files = [result['file'] for result in results]

        files_contents = [extra_functions.offset_file_data_get(file) for file in files]
        files_contents = extra_functions.merge_lists(files_contents)
        missing_words = extra_functions.check_missing(words_origin=words, words_modified=files_contents)
        return {'success': not missing_words,
                'thread_results': results,
                'modified_words': files_contents,
                'missing_words': missing_words,
                'files': files}

    def clean_up(self):
        files = extra_functions.offsets_files_get(self.file_name, folder_path=self.folder)
        res = [file.unlink() for file in files]

    def words_export_to_csv(self, words: list):
        return extra_functions.save_as_csv(words, self.file_name, folder_path=self.folder)


def create_vocabulary(words, from_lang, to_lang, vocab_source, vocab_name, level='', folder='results', overwrite=False,
                      create_new=False):
    vocab_source = vocab_source.replace(' ', '_')
    vocab_name = vocab_name.replace(' ', '_')
    file_name = f'{from_lang}_{to_lang}.{vocab_source}_{vocab_name}'.lower()

    current_files = extra_functions.find_matching_files(folder, file_name, '.csv')
    index = len(current_files)

    if not create_new and current_files:
        csv_file = Path(folder)
        index = '' if index < 2 else str(index - 1)
        csv_file = csv_file.joinpath(f'{file_name}{index}.csv')
        if csv_file.exists():
            return {
                'success': True,
                'thread_results': [],
                'modified_words': [],
                'missing_words': [],
                'file': csv_file
            }

    if len(current_files) > 1:
        index = len(current_files) -1

        if not overwrite:
            index = len(current_files)

    file_name = f'{file_name}{index}'
    files = extra_functions.offsets_files_get(file_name, folder_path=folder)
    if files:
        files_contents = [extra_functions.offset_file_data_get(file) for file in files]
        files_contents = extra_functions.merge_lists(files_contents)
        missing_words = extra_functions.check_missing(words_origin=words, words_modified=files_contents)
        words = [words[word_id] for word_id in missing_words]

    words_chunked = extra_functions.format_words_list(words, 20)
    gpt_requests_msg = gpt_lang.create_request_message(from_lang, to_lang, vocab_source, vocab_name, level)
    gpt_requests = [gpt_requests_msg + str(words_list) for words_list in words_chunked]
    # res = gpt_threads_run(gpt_requests, max_workers=5)

    results = extra_functions.gpt_threads_run(words_chunked, max_workers=5, file_name=file_name, folder_path=folder)
    for result in results:
        if result['success']:
            offset_value = f"{result.get('modified')[0]['id']}_{result.get('modified')[-1]['id']}"
            file = extra_functions.make_offset_file(file_name, offset_value, folder)
            try:
                extra_functions.write_data_to_json_file(file, data=result.get('modified'))
            except Exception:
                file.unlink()
                raise Exception(traceback_format_exc())

    files = extra_functions.offsets_files_get(file_name, folder_path=folder)
    #files = [result['file'] for result in results]

    files_contents = [extra_functions.offset_file_data_get(file) for file in files]
    files_contents = extra_functions.merge_lists(files_contents)
    missing_words = extra_functions.check_missing(words_origin=words, words_modified=files_contents)
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


def test():
    words = spanish_dict.vocab_content_by_name('Beginner')
    return create_vocabulary(words, from_lang="Spanish", to_lang="Russian", vocab_source="spanishDict",
                             vocab_name="Beginner", level="A1", folder='results', create_new=True, overwrite=True)
