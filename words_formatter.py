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


def test():
    words = spanish_dict.vocab_content_by_name('Beginner')[0:60]
    return create_vocabulary(words, from_lang="Spanish", to_lang="Russian", vocab_source="spanishDict",
                             vocab_name="Beginner", level="A1", folder='results', create_new=True, overwrite=False)

def test2():
    vocab = Vocabulary(from_lang="Spanish", to_lang="Russian", vocabulary_source="spanishDict",
                       vocabulary_name="Beginner", level="", folder='results', threads_workers=20)
    words = spanish_dict.vocab_content_by_name('Beginner')
    return vocab.add_new_words(words, overwrite=False)

def test3():
    vocab = Vocabulary(from_lang="Spanish", to_lang="Russian", vocabulary_source="spanishDict",
                       vocabulary_name="Beginner", level="", folder='results', threads_workers=3)
    words = spanish_dict.vocab_content_by_name('Beginner')[0:200]
    result = vocab.add_new_words(words)
    words = Vocabulary.anki_tags_add(result['file'])
    extra_functions.save_as_csv(words, result['file'])
    return result

def test4():
    v = Vocabulary.load_vocabulary('results/spanish_russian.spanishdict_beginner.4.csv')
    words = spanish_dict.vocab_content_by_name('Beginner')
    return v.add_new_words(words, overwrite=True)
test_val = [{'id': 0, 'article': 'el', 'word': 'artista', 'word_translation': 'художник, исполнитель', 'sentence': 'El artista pintó un hermoso paisaje.', 'sentence_translation': 'Художник нарисовал красивый пейзаж.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'arte', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 1, 'article': '', 'word': 'pagar', 'word_translation': 'платить', 'sentence': 'Tengo que pagar la factura de la luz.', 'sentence_translation': 'Я должен заплатить счет за свет.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'dinero', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 2, 'article': '', 'word': 'ver', 'word_translation': 'видеть', 'sentence': 'No puedo ver sin mis gafas.', 'sentence_translation': 'Я не могу видеть без очков.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'sentidos', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 3, 'article': '', 'word': 'venir', 'word_translation': 'приходить', 'sentence': 'Voy a venir a tu fiesta.', 'sentence_translation': 'Я приду на твою вечеринку.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'acciones', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 4, 'article': 'el', 'word': 'abrigo', 'word_translation': 'пальто', 'sentence': 'Me compré un abrigo nuevo para el invierno.', 'sentence_translation': 'Я купил новое пальто на зиму.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'ropa, clima', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 5, 'article': 'la', 'word': 'cama', 'word_translation': 'кровать', 'sentence': 'Me gusta dormir en una cama cómoda.', 'sentence_translation': 'Мне нравится спать в удобной кровати.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'hogar', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 6, 'article': '', 'word': 'buenas noches', 'word_translation': 'спокойной ночи', 'sentence': 'Buenas noches, hasta mañana.', 'sentence_translation': 'Спокойной ночи, до завтра.', 'type': '', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'saludos', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 7, 'article': 'el', 'word': 'terremoto', 'word_translation': 'землетрясение', 'sentence': 'El terremoto fue muy fuerte.', 'sentence_translation': 'Землетрясение было очень сильным.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'desastres naturales', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 8, 'article': '', 'word': 'poder', 'word_translation': 'мочь, иметь возможность', 'sentence': 'No puedo ir al cine con ustedes hoy.', 'sentence_translation': 'Я не могу пойти с вами в кино сегодня.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'habilidades, acciones', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 9, 'article': '', 'word': 'enviar', 'word_translation': 'отправлять', 'sentence': 'Voy a enviarle un correo electrónico mañana.', 'sentence_translation': 'Я отправлю ему электронное письмо завтра.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'comunicación', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 10, 'article': 'el', 'word': 'país', 'word_translation': 'страна', 'sentence': 'Vivo en un país hermoso.', 'sentence_translation': 'Я живу в красивой стране.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'geografía', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 11, 'article': 'el', 'word': 'periodista', 'word_translation': 'журналист', 'sentence': 'Mi amigo es periodista, trabaja en el periódico.', 'sentence_translation': 'Мой друг журналист, работает в газете.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'trabajo, comunicación', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 12, 'article': 'el', 'word': 'desarrollo', 'word_translation': 'развитие', 'sentence': 'El desarrollo tecnológico es muy importante en la sociedad moderna.', 'sentence_translation': 'Технологическое развитие очень важно в современном обществе.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'sociedad, tecnología', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 13, 'article': '', 'word': 'seguro', 'word_translation': 'уверенный, безопасный', 'sentence': 'Estoy seguro de que todo saldrá bien.', 'sentence_translation': 'Я уверен, что все будет хорошо.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'emociones, seguridad', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 14, 'article': 'el', 'word': 'oro', 'word_translation': 'золото', 'sentence': 'Mi abuela tiene una cadena de oro muy bonita.', 'sentence_translation': 'У моей бабушки есть очень красивая золотая цепочка.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'joyería, metales', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 15, 'article': 'el', 'word': 'avión', 'word_translation': 'самолет', 'sentence': 'Vamos a viajar en avión a Europa.', 'sentence_translation': 'Мы собираемся путешествовать в Европу на самолете.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'viajes, transporte', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 16, 'article': 'la', 'word': 'estación', 'word_translation': 'станция, сезон', 'sentence': 'La estación de tren está muy cerca de mi casa.', 'sentence_translation': 'Вокзал находится очень близко к моему дому.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'transporte, tiempo', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 17, 'article': '', 'word': 'enseñar', 'word_translation': 'учить, обучать', 'sentence': 'Mi madre es profesora y enseña en una escuela.', 'sentence_translation': 'Моя мама преподает и учит в школе.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'educación', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 18, 'article': '', 'word': 'competir', 'word_translation': 'соревноваться', 'sentence': 'Me gusta competir en carreras de bicicletas.', 'sentence_translation': 'Мне нравится участвовать в гонках на велосипедах.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'deportes', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 19, 'article': '', 'word': 'gris', 'word_translation': 'серый', 'sentence': 'Mi abrigo nuevo es de color gris.', 'sentence_translation': 'Мое новое пальто серого цвета.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'colores, ropa', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 20, 'article': 'el', 'word': 'pequeño', 'word_translation': 'маленький', 'sentence': 'Mi perro es muy pequeño.', 'sentence_translation': 'Моя собака очень маленькая.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'size', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 21, 'article': '', 'word': 'cien', 'word_translation': 'сто', 'sentence': 'Hay cien personas en la plaza.', 'sentence_translation': 'На площади сто человек.', 'type': 'number', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'quantity', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 22, 'article': 'la', 'word': 'plaza', 'word_translation': 'площадь', 'sentence': 'Hoy vamos a la plaza del pueblo.', 'sentence_translation': 'Сегодня мы идем на главную площадь города.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'city, place', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 23, 'article': '', 'word': 'simpático', 'word_translation': 'симпатичный', 'sentence': 'Mi amigo es muy simpático.', 'sentence_translation': 'Мой друг очень милый.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'personality', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 24, 'article': '', 'word': 'cerrado', 'word_translation': 'закрытый', 'sentence': 'Hoy la tienda está cerrada.', 'sentence_translation': 'Сегодня магазин закрыт.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'state', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 25, 'article': 'el', 'word': 'deporte', 'word_translation': 'спорт', 'sentence': 'Me gusta hacer deporte.', 'sentence_translation': 'Я люблю заниматься спортом.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'sports', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 26, 'article': '', 'word': 'siglo', 'word_translation': 'век', 'sentence': 'Este edificio es del siglo XIX.', 'sentence_translation': 'Это здание 19 века.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'time, history', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 27, 'article': '', 'word': 'inteligente', 'word_translation': 'умный', 'sentence': 'Mi hermana es muy inteligente.', 'sentence_translation': 'Моя сестра очень умная.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'personality', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 28, 'article': 'el', 'word': 'favor', 'word_translation': 'польза, помощь', 'sentence': 'Gracias por tu favor.', 'sentence_translation': 'Спасибо за твою помощь.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'emotion', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 29, 'article': '', 'word': 'animar', 'word_translation': 'охрабрять, бодрить', 'sentence': 'Vamos, anímate!', 'sentence_translation': 'Давай, не унывай!', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'emotion, social', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 30, 'article': 'el', 'word': 'lápiz', 'word_translation': 'карандаш', 'sentence': 'Me puedes prestar un lápiz, por favor?', 'sentence_translation': 'Ты можешь мне одолжить карандаш, пожалуйста?', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'education, stationery', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 31, 'article': 'el', 'word': 'río', 'word_translation': 'река', 'sentence': 'El río está muy ancho.', 'sentence_translation': 'Река очень широкая.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'nature', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 32, 'article': '', 'word': 'fácil', 'word_translation': 'легкий', 'sentence': 'Esta tarea es muy fácil.', 'sentence_translation': 'Это задание очень легкое.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'complexity', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 33, 'article': 'el', 'word': 'profesor', 'word_translation': 'преподаватель', 'sentence': 'Mi profesor es muy bueno.', 'sentence_translation': 'Мой преподаватель очень хороший.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'professions, education', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 34, 'article': '', 'word': 'sano', 'word_translation': 'здоровый', 'sentence': 'Esta comida es sana.', 'sentence_translation': 'Это еда здоровая.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'health', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 35, 'article': '', 'word': 'rezar', 'word_translation': 'молиться', 'sentence': 'La mujer está rezando en la iglesia.', 'sentence_translation': 'Женщина молится в церкви.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'religion, social', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 36, 'article': 'el', 'word': 'cocinero', 'word_translation': 'повар', 'sentence': 'El cocinero prepara la comida.', 'sentence_translation': 'Повар готовит еду.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'professions, food', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 37, 'article': '', 'word': 'cenar', 'word_translation': 'ужинать', 'sentence': 'Vamos a cenar en un restaurante.', 'sentence_translation': 'Мы пойдем ужинать в ресторане.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'food, social', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 38, 'article': '', 'word': 'quitar', 'word_translation': 'убрать, снять', 'sentence': 'Por favor, quita la ropa de la mesa.', 'sentence_translation': 'Пожалуйста, сними одежду со стола.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'actions', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 39, 'article': '', 'word': 'ser', 'word_translation': 'быть', 'sentence': 'Yo soy una persona feliz.', 'sentence_translation': 'Я счастливый человек.', 'type': 'verb', 'is_exception': True, 'level': 'A1', 'language': 'russian', 'categories': 'grammar', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 40, 'article': '', 'word': 'ir', 'word_translation': 'идти', 'sentence': 'Voy a la tienda.', 'sentence_translation': 'Я иду в магазин.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'movement, transportation', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 41, 'article': '', 'word': 'irse', 'word_translation': 'уйти', 'sentence': 'Me voy a casa.', 'sentence_translation': 'Я ухожу домой.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'movement, transportation', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 42, 'article': '', 'word': 'hacer', 'word_translation': 'делать', 'sentence': 'Hago mi tarea.', 'sentence_translation': 'Я делаю своё задание.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'activities', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 43, 'article': '', 'word': 'de repente', 'word_translation': 'внезапно', 'sentence': 'De repente empieza a llover.', 'sentence_translation': 'Внезапно начинает дождь.', 'type': '', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'time, emotions', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 44, 'article': '', 'word': 'tener', 'word_translation': 'иметь', 'sentence': 'Tengo una bicicleta.', 'sentence_translation': 'У меня есть велосипед.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'possession', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 45, 'article': '', 'word': 'decir', 'word_translation': 'говорить', 'sentence': '¿Qué dices?', 'sentence_translation': 'Что ты говоришь?', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'communication', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 46, 'article': '', 'word': 'querer', 'word_translation': 'хотеть', 'sentence': 'Quiero un té, por favor.', 'sentence_translation': 'Я хочу чай, пожалуйста.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'emotions, food', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 47, 'article': '', 'word': 'saber', 'word_translation': 'знать', 'sentence': 'Sé hablar español.', 'sentence_translation': 'Я умею говорить на испанском.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'knowledge', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 48, 'article': '', 'word': 'dar', 'word_translation': 'дать', 'sentence': 'Dame una manzana.', 'sentence_translation': 'Дай мне яблоко.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'actions', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 49, 'article': '', 'word': 'poner', 'word_translation': 'положить', 'sentence': 'Pon el libro en la mesa.', 'sentence_translation': 'Положи книгу на стол.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'actions', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 50, 'article': '', 'word': 'ponerse', 'word_translation': 'надеть (одежду)', 'sentence': 'Me pongo la chaqueta.', 'sentence_translation': 'Я надеваю куртку.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'clothing, actions', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 51, 'article': '', 'word': 'haber', 'word_translation': 'быть, иметь', 'sentence': 'Hay muchas flores en el jardín.', 'sentence_translation': 'В саду много цветов.', 'type': '', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'existence, quantity', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 52, 'article': '', 'word': 'salir', 'word_translation': 'выйти', 'sentence': 'Salgo de casa a las ocho.', 'sentence_translation': 'Я выхожу из дома в восемь.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'movement, time', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 53, 'article': '', 'word': 'comer', 'word_translation': 'есть, кушать', 'sentence': '¿Qué quieres comer?', 'sentence_translation': 'Что ты хочешь поесть?', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'food', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 54, 'article': '', 'word': 'pedir', 'word_translation': 'просить', 'sentence': 'Pido ayuda.', 'sentence_translation': 'Я прошу помощи.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'communication, actions', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 55, 'article': '', 'word': 'leer', 'word_translation': 'читать', 'sentence': 'Leo un libro interesante.', 'sentence_translation': 'Я читаю интересную книгу.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'activities', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 56, 'article': '', 'word': 'traer', 'word_translation': 'приносить', 'sentence': 'Traigo una sorpresa.', 'sentence_translation': 'Я принес сюрприз.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'actions', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 57, 'article': '', 'word': 'dormir', 'word_translation': 'спать', 'sentence': 'Duerme ocho horas por día.', 'sentence_translation': 'Он спит восемь часов в день.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'activities', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 58, 'article': '', 'word': 'dormirse', 'word_translation': 'уснуть', 'sentence': 'Me duermo temprano.', 'sentence_translation': 'Я засыпаю рано.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'activities', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 59, 'article': '', 'word': 'llegar', 'word_translation': 'прибывать', 'sentence': 'Llego tarde.', 'sentence_translation': 'Я опаздываю.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'time, movement', 'vocabulary_source': 'spanishDict,Beginner'}]
# https://superuser.com/questions/698902/can-i-create-an-anki-deck-from-a-csv-file

def test5():
    # from 2000 words unique
    v = Vocabulary('spanish', 'russian', 'commonly', '2000-sp')
    unique = ['para introducir', 'sacudirse', 'para perforar', 'simpatía', 'para indicar', 'depender', 'siguiendo', 'de todas formas', 'pistola', 'culpa', 'claramente', 'condición', 'instante', 'ya sea', 'período', 'con rapidez', 'el respeto', 'silla de montar', 'él mismo', 'para presionar', 'escritura', 'dividir', 'respiración', 'cintura', 'al respecto', 'para quemar', 'misterioso', 'a la deriva', 'advertencia', 'sostener', 'túnica', 'ninguna', 'finca', 'para lanzar', 'para protestar', 'pendiente', 'algunas veces', 'para fijar', 'apoyarse', 'dos render', 'mirada', 'pronunciar', 'incidente', 'buque', 'privado', 'relacionarse', 'suciedad', 'cualquier cosa', 'oficial', 'a lo largo de', 'permanecer', 'posesión', 'vislumbre', 'arma', 'puño', 'para cruzar', 'camion', 'asesoramiento', 'pretender', 'el almuerzo', 'descripción', 'para encontrar', 'corredor', 'silencio', 'hasta que', 'azotar', 'echar una mirada', 'para mover', 'para ver', 'sólo', 'asentir', 'muslo', 'para alimentar', 'para participar', 'perfectamente', 'para confirmar', 'alabanza', 'ala', 'evento', 'tono', 'griego', 'suave', 'para avanzar', 'tal', 'junto a', 'opuesto', 'conexión', 'sangriento', 'ciertamente', 'a embrague', 'sospecha', 'para detener', 'para concluir', 'jadear', 'agente', 'vasto', 'raíz', 'totalmente', 'para siempre', 'maldecir', 'américa', 'distancia', 'para girar', 'consciente', 'capítulo', 'firme', 'patrón', 'navidad', 'para realizar', 'aparte', 'unir', 'emerger', 'agitar', 'gracia', 'traza', 'visión', 'debido', 'coraje', 'apertura', 'confesar', 'a sonreir', 'acero', 'para partir', 'naturalmente', 'vehículo', 'alguna', 'sexo', 'reclamar', 'literario', 'para determinar', 'muy cansado', 'para mantener', 'preguntarse', 'tierno', 'mando', 'duda', 'alguna cosa', 'apurarse', 'crédito', 'siendo', 'para cargar', 'granjero', 'espíritu', 'mí mismo', 'konkluderer', 'mediante', 'arreglo', 'para sobrevivir', 'forma', 'la carretera', 'cajas', 'estúpido', 'cabina', 'eventualmente', 'inteligencia', 'tia', 'desesperado', 'para agregar', 'imposible', 'sacrificio', 'para asegurar', 'reventar', 'sopas', 'a juicio', 'aplastar', 'multa', 'estructura', 'enteramente', 'intentar', 'de verdad', 'ataque', 'favorecer', 'para relajarse', 'paso', 'a hornos', 'dom', 'pesadamente', 'la chaqueta', 'volumen', 'gratis', 'rugir', 'para tratar', 'para exclamar', 'para aliviar', 'la felicidad', 'excusa', 'énorme', 'para apelar', 'agudo', 'para limpiar', 'distante', 'para establecer', 'alambre', 'para atender', 'sí mismos', 'arrastrar', 'obvio', 'magnífico', 'dos estremecimientos', 'línea', 'rodear', 'retirarse', 'disparo', 'desmayarse', 'extravagante', 'misión', 'en conjunto', 'nativo', 'expresión', 'polvo', 'silbar', 'senaste', 'corriente', 'desperdiciar', 'debería', 'comprensión', 'alentar', 'atrás', 'actual', 'envolver', 'europa', 'podría', 'deleite', 'energia', 'herméticamente', 'fila', 'generelt', 'pertenecer', 'plenamente', 'corona', 'para rescatar', 'vagón', 'malvado', 'gigante', 'ministro', 'desnudarse', 'rendimiento', 'para entregar', 'intención', 'para marchar', 'apresurarse', 'dos obligan', 'agarrar', 'plateado', 'mero', 'apariencia', 'sí mismo', 'militar', 'cinta', 'sacerdote', 'al sur', 'libra', 'para reflejar', 'poseer', 'para advertir', 'para observar', 'juntos', 'ocasión', 'ausencia', 'incluso', 'flotar', 'apagado', 'la risa', 'acordar', 'llama', 'tú mismo', 'dos reflejos', 'para construir', 'revelar', 'truco', 'porche', 'compañera', 'nación', 'dorado', 'para proteger', 'proyecto de ley', 'posiblemente', 'interrumpir', 'maquina', 'poli', 'virtud', 'orden', 'trozo', 'áspero', 'rama', 'tasa', 'suelto', 'cual', 'labio', 'para responder', 'para explicar', 'liderar', 'para expresar', 'el cielo', 'para reemplazar', 'para defender', 'enfermos', 'a lo largo', 'rueda', 'el pan', 'despertar', 'la barbilla', 'cuenco', 'apretar', 'lo que sea', 'evidencia', 'dedo meñique', 'pasantía', 'miembro', 'tronco', 'silenciosamente', 'para reunir', 'para ocultar', 'caballero', 'otra vez', 'tapa', 'tripulación', 'pasion', 'torcer', 'para hacer', 'a través de', 'espada', 'prisionero', 'para examinar', 'cargar', 'patear', 'enfermera', 'suspirar', 'satisfacción', 'magia', 'prisión', 'directamente', 'atención', 'para guiar', 'agradecido', 'criatura', 'de huelga', 'bonita', 'contener', 'alarma', 'percibir', 'comienzo', 'gentilmente', 'sensación', 'sólido', 'misa', 'caso', 'sus', 'fuera de', 'para doblar', 'ya que', 'para demandar', 'sección', 'en contra', 'lado', 'tomar un sorbo', 'desvanecerse', 'maldito', 'lampara', 'sí misma', 'dondequiera', 'talón', 'a gritar', 'zona', 'diablo', 'suavemente', 'servidor', 'indicio', 'lío', 'para llevar a cabo', 'vagar', 'extender', 'para empujar', 'curva', 'años', 'delicado', 'lodos', 'mierda', 'excepto', 'daño', 'a flash', 'ficción', 'inglaterra', 'exponer', 'criada', 'algun lado', 'hojas', 'grupo', 'para describir', 'lamentar', 'formación', 'incapaz', 'temeroso', 'yarda', 'aparentemente', 'más bien', 'amistoso', 'trasero', 'parcela', 'al oeste', 'capa', 'empacar', 'trayectos', 'parte superior', 'cuidadosamente', 'por lo tanto', 'murmurar', 'a la esperanza', 'el último', 'para poner', 'versión', 'tonto', 'para identificar', 'reacción', 'judio', 'hierro', 'para poder', 'excitar', 'guerrero', 'instar', 'hincharse', 'cigarrillo', 'telefono', 'arruinar', 'marco', 'multitud', 'pulgada', 'hace', 'intento', 'amante', 'när vez', 'a dormir', 'algunos', 'para asistir', 'agarre', 'evne', 'humano', 'valla', 'para difundir', 'americano', 'llegar a un acuerdo', 'borde', 'arrastrarse', 'impresión', 'para descubrir', 'término', 'para mostrar', 'para atar', 'el te', 'seriamente', 'trampa', 'me gusta', 'pálido', 'límite', 'botón', 'art º', 'para representar', 'enrollarse', 'minúsculo', 'pausar', 'rango', 'adjuntar', 'que debe', 'orgullo', 'costo', 'uña', 'presente', 'afortunado', 'efecto', 'mía', 'extremadamente', 'la velocidad', 'admirar', 'elemento', 'visitante', 'que se produzca', 'deslizarse', 'incorrecto', 'viktigheten', 'por separado', 'para tener éxito', 'cepillar', 'príncipe', 'longitud', 'que deberá', 'mirar fijamente', 'dirigirse', 'socio', 'circulo', 'que hacer', 'desnudo', 'diferente', 'repentino', 'casamiento', 'desesperación', 'a la hierba', 'grueso', 'esta noche', 'pipa', 'convertirse', 'repentinamente', 'para satisfacer', 'inocente', 'manga', 'amplio', 'konsekvens', 'terminado', 'para recordar', 'confundir', 'progreso', 'hacer eco', 'con indignación', 'gancho', 'solitario', 'darse prisa', 'palma', 'nosotros mismos', 'para resistir', 'para comenzar', 'para salvar', 'aceptar', 'trazo', 'culpar', 'tablero', 'para compartir', 'resplandor', 'para recuperar', 'cesar', 'para bloquear', 'formar', 'dos escalofríos', 'particularmente', 'brillar', 'noción', 'para evitar', 'para prevenir', 'sudor', 'para contar', 'viva', 'para volar', 'portón', 'lastimar', 'ordinario', 'ups', 'para proveer', 'dos perdidas', 'para producir', 'bala', 'infierno', 'milla', 'balancear', 'de lo contrario', 'tumba', 'para obtener', 'hambriento', 'de madera', 'campana', 'dos persuaden', 'regazo', 'enfocar', 'gemir', 'apagarse', 'muchos', 'a menos que', 'la moda', 'sistema', 'aventurarse', 'correcto', 'todos', 'imaginación', 'instancia', 'londres', 'más allá', 'encogerse de hombros', 'notar', 'pila', 'emplear', 'hidalgo', 'para complacer', 'elección', 'considerar', 'a montar', 'esta bien', 'asustar', 'oración', 'para desarrollar', 'haz', 'para cambiar', 'francia', 'resbalar', 'cercanamente', 'proceso', 'reflexión', 'dormido', 'cavar', 'rolle', 'el éxito', 'verificar', 'hundir', 'cubierta', 'hábito', 'firmemente', 'para romper', 'esclavo', 'dos cojos', 'mencionar', 'borracho', 'asunto', 'dejar caer', 'la ley', 'puerta de entrada', 'ansvarlig', 'calma', 'influencia', 'permitirse', 'despierto', 'justa', 'dos suspiros', 'mente', 'bloque', 'para liberar', 'brisa', 'para estudiar', 'escapar', 'de alguna manera', 'profundamente', 'ángel', 'recompensa', 'a pesar de que', 'posición', 'ignorar', 'para preguntar', 'instrucción', 'para verter', 'para conectar', 'moralidad', 'descender', 'fruncir el ceño', 'rehusar', 'bestia', 'cabaña', 'susurrar', 'batalla', 'simplemente', 'para lavar', 'indio', 'pequeña', 'paño', 'dama', 'almacenar', 'quizás', 'dominar', 'estirar', 'decisión', 'motor', 'al parecer', 'fluir', 'tio', 'hacer estallar', 'autoridad', 'a voluntad', 'propiedad', 'temblar', 'alivio', 'nervio', 'locura', 'temor', 'pocos', 'cristo', 'llanura', 'asumir', 'encanto', 'soplar', 'reir', 'para montar', 'arbusto', 'para recoger', 'corte', 'presencia', 'aferrarse', 'el tuyo', 'cuyo', 'posibilidad', 'vientre', 'sospechar', 'roma', 'frotar', 'sentencia', 'encuadernado', 'colar', 'dar palmaditas', 'todo el mundo', 'principal', 'ligeramente', 'para referir', 'gentil', 'fe', 'circunstancia', 'para resolver', 'para aumentar', 'mandíbula', 'enterrar', 'traicionar', 'cantidad', 'par', 'contactar', 'a aparecer', 'obviamente', 'otros', 'millones', 'capitán', 'involucrar', 'formulario', 'fortuna', 'acerca de', 'escasamente', 'instantáneamente', 'para disparar', 'papá', 'en todas partes', 'proceder', 'confusión', 'discusión', 'bruscamente', 'la realidad', 'para recibir', 'para rascar', 'para eliminar', 'propietario', 'culo', 'asi que', 'para atraer', 'a la preocupación', 'lika', 'guardia', 'diferencia', 'para comparar', 'para ganar', 'guay', 'muebles', 'pegarse', 'frase', 'probablemente', 'tropezar', 'afecto', 'a mayo', 'el domingo', 'apoderarse', 'suministro', 'tranquilamente', 'completo', 'conversacion', 'elevar', 'asociar', 'audiencia', 'así', 'causar', 'a la pulga', 'para decidir', 'trota', 'para capturar', 'absolutamente', 'revolver', 'para terminar', 'en su mayoría', 'característica', 'en lugar', 'conceder', 'agujero', 'inclinarse', 'apuntar', 'método', 'para impresionar', 'suma', 'estándar', 'descanso', 'profundidad', 'para discutir', 'arrodillarse', 'congelar', 'en efecto']
    uni2 = [' ¿Por\xa0qué\xa0no\xa0entras?', ' La\xa0cena\xa0incluye\xa0el\xa0vino', ' El hijo culpa a la madre y\xa0al\xa0padre', ' caber por', ' contar con', ' El\xa0mes\xa0acaba\xa0el\xa0lunes', ' El\xa0oso\xa0no\xa0cabe\xa0por\xa0la\xa0puerta', ' El\xa0largo\xa0invierno\xa0acaba', ' El policía conoce a mi primo', ' Cuento\xa0con\xa0ustedes', ' Él\xa0cabe\xa0en\xa0la\xa0cama', ' El\xa0teléfono\xa0no\xa0sirve', ' Los\xa0granjeros\xa0respetan\xa0a\xa0los\xa0animales', ' Ella\xa0visita\xa0a su familia', ' Ellos aparecen en la noche', ' Él aparece a la noche', ' Yo\xa0sueño\xa0con mi novia', ' Ellos\xa0están\xa0seguros', ' Ella\xa0sabe\xa0que yo recuerdo', ' me llamo ...', 'la botella', 'el bolígrafo', 'la palabra', 'el pasaporte', 'el taxi', ' pregunta', ' cuánto', ' cuándo', ' negro', ' azul', ' verde', ' blanco', ' amarillo', ' rojo', 'el coche', 'la camiseta', 'la taza', 'el color', ' gris', ' naranja', ' ni...ni', ' pero', ' porque', ' no... sino...', ' mientras', ' mientras que', ' aunque', ' cuando', 'la madre', 'el padre', 'el esposo(a)', 'el tío', 'la hermana', 'el hermano', 'el hijo', 'la hija', 'los hijos', 'el, la bebé', 'la familia', 'la abuela', 'el abuelo', 'la mamá', 'el marido', 'la tía', 'el papá', 'el novio', 'la novia', 'el primo', 'la prima', ' hacer', ' ver al', ' La mujer no\xa0ve\xa0al niño', ' Bajo\xa0su\xa0sombrero', ' ¿Qué tienes bajo la camisa?', ' El\xa0mono\xa0camina\xa0cerca\xa0del\xa0caballo\n', ' Hablamos\xa0acerca\xa0de\xa0libros', ' El libro es acerca de un caballo', ' ¿Acerca de qué es el libro?\n', ' No\xa0leemos\xa0durante\xa0la\xa0cena', ' Voy\xa0a\xa0Austria', ' Ella lee un libro a las mujeres', ' Yo\xa0camino\xa0hacia\xa0ella', ' Él\xa0paga\xa0al\xa0niño', ' ¿Vas al almuenzo?', ' Tú\xa0hablas\xa0con\xa0el\xa0niño', ' Con\xa0mucho gusto', ' Quiero\xa0un\xa0emparedado\xa0sin\xa0queso', ' Oso contro caballo', ' El pato del niño es blanco', ' entre verde y blanco', ' No es para usted', ' Ella escribe en español', ' El hombre escribe en el diarío', ' Yo hablo sobre el león', ' El\xa0gato\xa0duerme\xa0sobre\xa0el\xa0perro', ' Tú hablas de los libros', ' Yo soy de Argentina', 'el calendario', ' ayer', ' mañana', ' hoy', 'el lunes', 'el martes', 'el miércoles', ' De\xa0miércoles\xa0a\xa0martes', 'el año', ' en la noche', 'el viernes', ' los\xa0viernes', 'el jueves', 'el sábado', 'el domingo', ' Como un huevo al día', ' ¿Cuántos\xa0años\xa0tienes?', ' Yo\xa0como\xa0tarde\xa0por\xa0la\xa0noche', ' por la noche', 'el momento', 'el minuto', 'la semana', 'la hora', 'la vez', ' una\xa0vez', ' una\xa0vez\xa0por\xa0semana', ' tarde', 'el mes', ' a veces', ' A\xa0veces\xa0voy,\xa0a\xa0veces\xa0no', 'el enero', ' Enero\xa0es\xa0un\xa0mes\xa0del\xa0año', 'el julio', 'el abril', ' en\xa0abril', 'el junio', 'el febrero', 'el mayo', 'el marzo', ' Los patos no nadan en febrero', ' hasta', ' hasta\xa0mañana', 'el diciembre', 'el noviembre', ' desde hoy (día)', 'el octubre', 'el septiembre', 'el agosto', ' Desde marzo hasta noviembre', ' desde ... hasta', 'el segundo', 'la fiesta', 'las fiestas', 'la primavera', 'la estación', ' ¿Cómo\xa0voy\xa0a\xa0la\xa0estación?', 'el rato', 'la temporada', 'el invierno', ' El\xa0invierno\xa0es una estación', ' El\xa0invierno\xa0es\xa0una\xa0temporada', 'la madrugada', 'la vacación', 'la cita', 'el mediodía', ' Tengo una cita con él al\xa0mediodía', 'el cumpleaños', 'el verano', 'la fecha', ' anoche', ' ¿Cuándo\xa0es\xa0tu\xa0cumpleaños?', ' por\xa0la\xa0mañana', ' mañana\xa0por\xa0la\xa0mañana', ' A\xa0veces\xa0duermo\xa0en\xa0la\xa0mañana', ' Hoy\xa0no\xa0es\xa0mi\xa0día', ' Yo corro una vez por semana', ' durante\xa0la\xa0noche', 'la silla', 'el vaso', 'el plato', 'la cama', ' Un\xa0vaso\xa0de\xa0leche', 'la mesa', ' Los\xa0niños\xa0comen\xa0en\xa0la\xa0mesa', ' Tú\xa0vas\xa0a\xa0la\xa0cama', 'la cuna', 'la piscina', 'la ventana', 'la televisión', ' El\xa0bebé\xa0duerme\xa0en\xa0la\xa0cuna', 'la cocina', ' Ella\xa0cocina\xa0un\xa0huevo\xa0en\xa0la\xa0cocina', ' Yo\xa0hablo\xa0por\xa0teléfono\xa0con\xa0mi\xa0hija', 'la esponja', 'el espejo', 'la sartén', 'la lámpara', 'la puerta', 'el el sofá', 'el escritorio', ' Cocino\xa0el\xa0pollo\xa0en\xa0una\xa0sartén', 'la pared', 'el horno', 'el sótano', 'el techo', 'la escalera', 'el dormitorio', 'la habitación', ' ¿Cuál es mi\xa0habitación?', ' Él\xa0duerme\xa0en\xa0el\xa0piso', ' Ellas\xa0van\xa0a\xa0la\xa0habitación\xa0de\xa0mi\xa0padre', 'el cepillo', 'el diente', 'el refrigerador', 'la secadora', 'el baño', 'la lavadora', 'el cepillo de dientes', 'el paraguas', 'la cartera', 'el jabón', 'la sábana', 'la rasuradora', ' La piscina no tiene agua', ' corto', ' largo', ' grande', 'el tamaño', ' gran', ' Hoy\xa0es\xa0un\xa0gran\xa0día', ' alto', ' enorme', ' bajo', ' pequeño', ' ¿De\xa0qué\xa0tamaño\xa0es?', ' Vamos al trabajo', ' Quíen es nuestra mesera', ' La\xa0sopa\xa0es\xa0para\xa0el\xa0capitán', ' bilingüe', ' joven', ' mismo', ' No\xa0es\xa0el\xa0mismo\xa0color', ' Es\xa0un\xa0buen\xa0abogado', ' Mi\xa0hijo\xa0tiene\xa0un\xa0nuevo\xa0abrigo', ' mejor', ' Los\xa0caballos\xa0no\xa0son\xa0los\xa0mejores', ' mayor', ' Ella\xa0es\xa0mi\xa0hermana\xa0mayor', ' Él es\xa0mayor\xa0que ella', ' menor', 'el primero', ' No, tú eres la primera', ' Los\xa0últimos\xa0segundos', ' personal', ' ¿La\xa0pregunta\xa0es\xa0personal?', ' Hoy\xa0es\xa0un\xa0día\xa0diferente', ' Yo\xa0voy\xa0junto\xa0a\xa0él', ' ¡Nosotros\xa0somos\xa0los\xa0mejores!', ' Es peor para\xa0él', ' Ella\xa0es\xa0la\xa0peor\xa0estudiante', ' Yo no leo tantos libros', ' El\xa0año\xa0pasado', ' Eso\xa0no\xa0es\xa0justo', ' ¿Quién\xa0duerme\xa0en\xa0aquella\xa0cama?', ' ¿Para\xa0qué\xa0es\xa0esa\xa0cuchara?', ' ¿Qué\xa0es\xa0eso?', ' esto', ' aquella', ' Yo\xa0no\xa0hablo\xa0de\xa0esto', ' de esto', ' mucho', ' ambos', ' todo', ' Toda\xa0la\xa0comida', ' ¿Qué\xa0haces\xa0todo\xa0el\xa0día?', ' unos cuantos', ' poco', ' Tengo\xa0poca\xa0agua', ' alguno', ' el abrigo\xa0de\xa0invierno', ' en\xa0la\xa0noche', ' bello', ' lindo', ' simpático', ' hace poco', ' brasileño', 'el actor', 'la actriz', 'el bolso', 'el camarero', 'el compañero de trabajo', 'el dependiente', 'el médico', 'el móvil', 'el nieto', 'el ordenador', 'el periódico', 'el reloj', 'el veterinario', 'el estadounidense', ' marrón', ' No pasa nada', ' polaco', ' ruso', 'el bocadillo', 'el café solo', 'el hospital', 'el mercado', 'el restaurante', 'la cafetería', 'la clínica', 'la escuela', 'la oficina', ' la parada de autobús', 'la tienda', ' en la esquina', ' por aquí', 'la parada', 'la calle', ' en esta calle', ' hay', ' Hay muchas\xa0cafeterías en esta calle', ' allí', ' ¿Hay\xa0un\xa0mercado por aquí?', 'el supermercado', ' No hay parada de autobús en esta calle', 'la ciudad', 'el banco', ' entre', ' contento', ' ahora', ' bello', ' también', ' ¿A qué hora abrís?', ' Las tiendas cierran a las 20:30h', ' Tengo que comprar todos los ingredientes para el pastel', 'el pastel', 'la compra', ' la lista de la compra', ' el centro comercial', 'la frutería', 'la pescadería', ' En esa pescadería venden pescado de muy buena calidad', 'la carnicería', ' Quiero comprar pollo en la carnicería', 'la panadería', 'la papelería', 'el lápiz', 'la librería', ' Voy a hacer la\xa0lista de la compra', 'el papel', ' delicioso', ' Busco el\xa0centro comercial', ' La comida está salada, tiene mucha sal', ' Tengo que comprar una botella de un litro de aceite de oliva', ' Voy a comprar una docena de huevos', ' pronto', ' tener que', ' ir a', ' demasiado', ' bastante', ' ¿Cuántas habitaciones hay en tu casa?', ' fregar los platos', 'el cuarto de baño', ' todos los días', 'el garaje', ' alrededor', ' Todas las noches vemos la tele en el sofá', ' debajo de', 'el armario', ' Hay un armario en cada dormitorio', 'la estantería', 'la ducha', 'la cortina', 'el lavabo', ' encima de', ' El jabón está encima del lavabo', 'el frigorífico (разг. frigo)', ' Voy a cocinar el pescado en el horno', ' Tengo que comprar unas cortinas nuevas para la\xa0ducha', ' ¿Dónde vives?', ' Puedo\xa0venir a pie a la oficina', 'el piso', ' ¿Te apetece tomar una cerveza?', 'el refresco', ' Voy a tomar un refresco de naranja', ' ¿Pedimos una ración de tortilla?', ' Quiero un bocadillo de atún con tomate', ' ¿Me pone una copa de vino blanco?', ' Tienen que pedir en la barra', ' ¿Qué le pongo?', ' ¿Me pone un café?', ' ¿Nos trae un poco más de pan?', 'la tapa', 'el tomate', 'la reserva', ' Tengo una reserva a nombre de Pedro', 'el nombre', 'el número', ' el\xa0número\xa0de\xa0teléfono', ' ¿Podría traer nos la carta?', ' Una botella de agua con gas, por favor', ' Para mí, una copa de vino tinto', ' ¿Qué pedimos de entrantes?', 'el primer plato', ' De primer plato quiero la sopa del día', 'el segundo plato', ' De segundo plato, pollo con verduras', ' ¿Qué postre nos recomienda?', ' ¿Nos trae la cuenta, por favor?', 'la propina', ' ¿Cuánto dejamos de propina?', ' ¿Quieres un café solo o con leche?', ' un poco más', ' el vino tinto', ' siempre', ' aquí tienes', ' una caña es buena para aliviar el estrés', ' ¡Hasta luego!', ' Claro, te traigo la cuenta en un momentito', ' Normalmente, me despierto a las siete en punto', 'el fin de semana (разг. el finde)', ' Ella se levanta más tarde los fines de semana', ' Ella se ducha todos los días', ' Siempre me visto antes de desayunar', ' antes', ' Desayunamos a las siete y media', ' Me lavo los dientes después de comer', ' Salgo de casa a las ocho y cuarto', ' Normalmente, comemos a la una y media', ' Ella llega a casa a las seis en punto', ' Cenan a las ocho en punto', 'la mitad', ' Los jueves, como con mis amigos']


    return v.add_new_words(unique[:10], overwrite=False)