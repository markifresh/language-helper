import extra_functions
from pathlib import Path
import gpt_lang
import gpt_helper
import spanish_dict
from traceback import format_exc as traceback_format_exc
from json import loads as json_loads

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
    def load_vocabulary(file_path: str):
        file = Path(file_path)
        if not file.exists():
            raise Exception(f'can not find file "{file_path}"')

        folder = str(file.parent)
        file_data = extra_functions.load_data_from_csv_file(str(file))
        file_data = file_data[0]
        vocab = Vocabulary(
                            from_lang=file_data['language'],
                            to_lang=file_data['to_language'],
                            vocabulary_source=file_data['source'].split(', ')[0],
                            vocabulary_name=file_data['source'].split(', ')[1],
                            level=file_data.get('level', 'A1'),
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

    def add_new_words(self, words: list):
        words_to_search = extra_functions.check_missing(words_origin=words, words_modified=self.words_modified)
        thread_results = self.search_make(words=words_to_search)
        self.search_save(thread_results)
        results = self.search_results()

        new_words = [word for word in results if word not in self.words_modified]
        self.set_words_modified(self.words_modified + new_words)

        file = self.write_to_file(overwrite=True)
        self.search_cleanup()
        missing_words = extra_functions.check_missing(words_origin=words, words_modified=self.words_modified)
        return {'success': not missing_words,
                'thread_results': thread_results,
                'added_words': new_words,
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
        for result in results:
            if not result['error'] and result['result']['success']:
                message = result['result']['data']['message']
                json_result = []
                try:
                    json_result = json_loads(message)
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
        missing_words = extra_functions.check_missing(words_origin=words, words_modified=files_contents)
        return {'success': not missing_words,
                'thread_results': results,
                'modified_words': files_contents,
                'missing_words': missing_words,
                'files': files}


    def words_export_to_csv(self, words: list):
        return extra_functions.save_as_csv(words, self.file_name, folder_path=self.folder)




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
        missing_words = extra_functions.check_missing(words_origin=words, words_modified=files_contents)
        words = [words[word_id] for word_id in missing_words]

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
    words = spanish_dict.vocab_content_by_name('Beginner')[0:60]
    return create_vocabulary(words, from_lang="Spanish", to_lang="Russian", vocab_source="spanishDict",
                             vocab_name="Beginner", level="A1", folder='results', create_new=True, overwrite=False)

def test2():
    vocab = Vocabulary(from_lang="Spanish", to_lang="Russian", vocabulary_source="spanishDict",
                       vocabulary_name="Beginner", level="A1", folder='results')
    words = spanish_dict.vocab_content_by_name('Beginner')[0:60]
    return vocab.add_new_words(words)


test_val = [{'id': 0, 'article': 'el', 'word': 'artista', 'word_translation': 'художник, исполнитель', 'sentence': 'El artista pintó un hermoso paisaje.', 'sentence_translation': 'Художник нарисовал красивый пейзаж.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'arte', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 1, 'article': '', 'word': 'pagar', 'word_translation': 'платить', 'sentence': 'Tengo que pagar la factura de la luz.', 'sentence_translation': 'Я должен заплатить счет за свет.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'dinero', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 2, 'article': '', 'word': 'ver', 'word_translation': 'видеть', 'sentence': 'No puedo ver sin mis gafas.', 'sentence_translation': 'Я не могу видеть без очков.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'sentidos', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 3, 'article': '', 'word': 'venir', 'word_translation': 'приходить', 'sentence': 'Voy a venir a tu fiesta.', 'sentence_translation': 'Я приду на твою вечеринку.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'acciones', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 4, 'article': 'el', 'word': 'abrigo', 'word_translation': 'пальто', 'sentence': 'Me compré un abrigo nuevo para el invierno.', 'sentence_translation': 'Я купил новое пальто на зиму.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'ropa, clima', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 5, 'article': 'la', 'word': 'cama', 'word_translation': 'кровать', 'sentence': 'Me gusta dormir en una cama cómoda.', 'sentence_translation': 'Мне нравится спать в удобной кровати.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'hogar', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 6, 'article': '', 'word': 'buenas noches', 'word_translation': 'спокойной ночи', 'sentence': 'Buenas noches, hasta mañana.', 'sentence_translation': 'Спокойной ночи, до завтра.', 'type': '', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'saludos', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 7, 'article': 'el', 'word': 'terremoto', 'word_translation': 'землетрясение', 'sentence': 'El terremoto fue muy fuerte.', 'sentence_translation': 'Землетрясение было очень сильным.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'desastres naturales', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 8, 'article': '', 'word': 'poder', 'word_translation': 'мочь, иметь возможность', 'sentence': 'No puedo ir al cine con ustedes hoy.', 'sentence_translation': 'Я не могу пойти с вами в кино сегодня.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'habilidades, acciones', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 9, 'article': '', 'word': 'enviar', 'word_translation': 'отправлять', 'sentence': 'Voy a enviarle un correo electrónico mañana.', 'sentence_translation': 'Я отправлю ему электронное письмо завтра.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'comunicación', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 10, 'article': 'el', 'word': 'país', 'word_translation': 'страна', 'sentence': 'Vivo en un país hermoso.', 'sentence_translation': 'Я живу в красивой стране.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'geografía', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 11, 'article': 'el', 'word': 'periodista', 'word_translation': 'журналист', 'sentence': 'Mi amigo es periodista, trabaja en el periódico.', 'sentence_translation': 'Мой друг журналист, работает в газете.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'trabajo, comunicación', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 12, 'article': 'el', 'word': 'desarrollo', 'word_translation': 'развитие', 'sentence': 'El desarrollo tecnológico es muy importante en la sociedad moderna.', 'sentence_translation': 'Технологическое развитие очень важно в современном обществе.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'sociedad, tecnología', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 13, 'article': '', 'word': 'seguro', 'word_translation': 'уверенный, безопасный', 'sentence': 'Estoy seguro de que todo saldrá bien.', 'sentence_translation': 'Я уверен, что все будет хорошо.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'emociones, seguridad', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 14, 'article': 'el', 'word': 'oro', 'word_translation': 'золото', 'sentence': 'Mi abuela tiene una cadena de oro muy bonita.', 'sentence_translation': 'У моей бабушки есть очень красивая золотая цепочка.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'joyería, metales', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 15, 'article': 'el', 'word': 'avión', 'word_translation': 'самолет', 'sentence': 'Vamos a viajar en avión a Europa.', 'sentence_translation': 'Мы собираемся путешествовать в Европу на самолете.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'viajes, transporte', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 16, 'article': 'la', 'word': 'estación', 'word_translation': 'станция, сезон', 'sentence': 'La estación de tren está muy cerca de mi casa.', 'sentence_translation': 'Вокзал находится очень близко к моему дому.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'transporte, tiempo', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 17, 'article': '', 'word': 'enseñar', 'word_translation': 'учить, обучать', 'sentence': 'Mi madre es profesora y enseña en una escuela.', 'sentence_translation': 'Моя мама преподает и учит в школе.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'educación', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 18, 'article': '', 'word': 'competir', 'word_translation': 'соревноваться', 'sentence': 'Me gusta competir en carreras de bicicletas.', 'sentence_translation': 'Мне нравится участвовать в гонках на велосипедах.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'deportes', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 19, 'article': '', 'word': 'gris', 'word_translation': 'серый', 'sentence': 'Mi abrigo nuevo es de color gris.', 'sentence_translation': 'Мое новое пальто серого цвета.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'colores, ropa', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 20, 'article': 'el', 'word': 'pequeño', 'word_translation': 'маленький', 'sentence': 'Mi perro es muy pequeño.', 'sentence_translation': 'Моя собака очень маленькая.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'size', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 21, 'article': '', 'word': 'cien', 'word_translation': 'сто', 'sentence': 'Hay cien personas en la plaza.', 'sentence_translation': 'На площади сто человек.', 'type': 'number', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'quantity', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 22, 'article': 'la', 'word': 'plaza', 'word_translation': 'площадь', 'sentence': 'Hoy vamos a la plaza del pueblo.', 'sentence_translation': 'Сегодня мы идем на главную площадь города.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'city, place', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 23, 'article': '', 'word': 'simpático', 'word_translation': 'симпатичный', 'sentence': 'Mi amigo es muy simpático.', 'sentence_translation': 'Мой друг очень милый.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'personality', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 24, 'article': '', 'word': 'cerrado', 'word_translation': 'закрытый', 'sentence': 'Hoy la tienda está cerrada.', 'sentence_translation': 'Сегодня магазин закрыт.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'state', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 25, 'article': 'el', 'word': 'deporte', 'word_translation': 'спорт', 'sentence': 'Me gusta hacer deporte.', 'sentence_translation': 'Я люблю заниматься спортом.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'sports', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 26, 'article': '', 'word': 'siglo', 'word_translation': 'век', 'sentence': 'Este edificio es del siglo XIX.', 'sentence_translation': 'Это здание 19 века.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'time, history', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 27, 'article': '', 'word': 'inteligente', 'word_translation': 'умный', 'sentence': 'Mi hermana es muy inteligente.', 'sentence_translation': 'Моя сестра очень умная.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'personality', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 28, 'article': 'el', 'word': 'favor', 'word_translation': 'польза, помощь', 'sentence': 'Gracias por tu favor.', 'sentence_translation': 'Спасибо за твою помощь.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'emotion', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 29, 'article': '', 'word': 'animar', 'word_translation': 'охрабрять, бодрить', 'sentence': 'Vamos, anímate!', 'sentence_translation': 'Давай, не унывай!', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'emotion, social', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 30, 'article': 'el', 'word': 'lápiz', 'word_translation': 'карандаш', 'sentence': 'Me puedes prestar un lápiz, por favor?', 'sentence_translation': 'Ты можешь мне одолжить карандаш, пожалуйста?', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'education, stationery', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 31, 'article': 'el', 'word': 'río', 'word_translation': 'река', 'sentence': 'El río está muy ancho.', 'sentence_translation': 'Река очень широкая.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'nature', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 32, 'article': '', 'word': 'fácil', 'word_translation': 'легкий', 'sentence': 'Esta tarea es muy fácil.', 'sentence_translation': 'Это задание очень легкое.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'complexity', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 33, 'article': 'el', 'word': 'profesor', 'word_translation': 'преподаватель', 'sentence': 'Mi profesor es muy bueno.', 'sentence_translation': 'Мой преподаватель очень хороший.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'professions, education', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 34, 'article': '', 'word': 'sano', 'word_translation': 'здоровый', 'sentence': 'Esta comida es sana.', 'sentence_translation': 'Это еда здоровая.', 'type': 'adjective', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'health', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 35, 'article': '', 'word': 'rezar', 'word_translation': 'молиться', 'sentence': 'La mujer está rezando en la iglesia.', 'sentence_translation': 'Женщина молится в церкви.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'religion, social', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 36, 'article': 'el', 'word': 'cocinero', 'word_translation': 'повар', 'sentence': 'El cocinero prepara la comida.', 'sentence_translation': 'Повар готовит еду.', 'type': 'noun', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'professions, food', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 37, 'article': '', 'word': 'cenar', 'word_translation': 'ужинать', 'sentence': 'Vamos a cenar en un restaurante.', 'sentence_translation': 'Мы пойдем ужинать в ресторане.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'food, social', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 38, 'article': '', 'word': 'quitar', 'word_translation': 'убрать, снять', 'sentence': 'Por favor, quita la ropa de la mesa.', 'sentence_translation': 'Пожалуйста, сними одежду со стола.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'actions', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 39, 'article': '', 'word': 'ser', 'word_translation': 'быть', 'sentence': 'Yo soy una persona feliz.', 'sentence_translation': 'Я счастливый человек.', 'type': 'verb', 'is_exception': True, 'level': 'A1', 'language': 'russian', 'categories': 'grammar', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 40, 'article': '', 'word': 'ir', 'word_translation': 'идти', 'sentence': 'Voy a la tienda.', 'sentence_translation': 'Я иду в магазин.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'movement, transportation', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 41, 'article': '', 'word': 'irse', 'word_translation': 'уйти', 'sentence': 'Me voy a casa.', 'sentence_translation': 'Я ухожу домой.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'movement, transportation', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 42, 'article': '', 'word': 'hacer', 'word_translation': 'делать', 'sentence': 'Hago mi tarea.', 'sentence_translation': 'Я делаю своё задание.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'activities', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 43, 'article': '', 'word': 'de repente', 'word_translation': 'внезапно', 'sentence': 'De repente empieza a llover.', 'sentence_translation': 'Внезапно начинает дождь.', 'type': '', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'time, emotions', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 44, 'article': '', 'word': 'tener', 'word_translation': 'иметь', 'sentence': 'Tengo una bicicleta.', 'sentence_translation': 'У меня есть велосипед.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'possession', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 45, 'article': '', 'word': 'decir', 'word_translation': 'говорить', 'sentence': '¿Qué dices?', 'sentence_translation': 'Что ты говоришь?', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'communication', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 46, 'article': '', 'word': 'querer', 'word_translation': 'хотеть', 'sentence': 'Quiero un té, por favor.', 'sentence_translation': 'Я хочу чай, пожалуйста.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'emotions, food', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 47, 'article': '', 'word': 'saber', 'word_translation': 'знать', 'sentence': 'Sé hablar español.', 'sentence_translation': 'Я умею говорить на испанском.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'knowledge', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 48, 'article': '', 'word': 'dar', 'word_translation': 'дать', 'sentence': 'Dame una manzana.', 'sentence_translation': 'Дай мне яблоко.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'actions', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 49, 'article': '', 'word': 'poner', 'word_translation': 'положить', 'sentence': 'Pon el libro en la mesa.', 'sentence_translation': 'Положи книгу на стол.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'actions', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 50, 'article': '', 'word': 'ponerse', 'word_translation': 'надеть (одежду)', 'sentence': 'Me pongo la chaqueta.', 'sentence_translation': 'Я надеваю куртку.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'clothing, actions', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 51, 'article': '', 'word': 'haber', 'word_translation': 'быть, иметь', 'sentence': 'Hay muchas flores en el jardín.', 'sentence_translation': 'В саду много цветов.', 'type': '', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'existence, quantity', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 52, 'article': '', 'word': 'salir', 'word_translation': 'выйти', 'sentence': 'Salgo de casa a las ocho.', 'sentence_translation': 'Я выхожу из дома в восемь.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'movement, time', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 53, 'article': '', 'word': 'comer', 'word_translation': 'есть, кушать', 'sentence': '¿Qué quieres comer?', 'sentence_translation': 'Что ты хочешь поесть?', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'food', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 54, 'article': '', 'word': 'pedir', 'word_translation': 'просить', 'sentence': 'Pido ayuda.', 'sentence_translation': 'Я прошу помощи.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'communication, actions', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 55, 'article': '', 'word': 'leer', 'word_translation': 'читать', 'sentence': 'Leo un libro interesante.', 'sentence_translation': 'Я читаю интересную книгу.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'activities', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 56, 'article': '', 'word': 'traer', 'word_translation': 'приносить', 'sentence': 'Traigo una sorpresa.', 'sentence_translation': 'Я принес сюрприз.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'actions', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 57, 'article': '', 'word': 'dormir', 'word_translation': 'спать', 'sentence': 'Duerme ocho horas por día.', 'sentence_translation': 'Он спит восемь часов в день.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'activities', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 58, 'article': '', 'word': 'dormirse', 'word_translation': 'уснуть', 'sentence': 'Me duermo temprano.', 'sentence_translation': 'Я засыпаю рано.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'activities', 'vocabulary_source': 'spanishDict,Beginner'}, {'id': 59, 'article': '', 'word': 'llegar', 'word_translation': 'прибывать', 'sentence': 'Llego tarde.', 'sentence_translation': 'Я опаздываю.', 'type': 'verb', 'is_exception': False, 'level': 'A1', 'language': 'russian', 'categories': 'time, movement', 'vocabulary_source': 'spanishDict,Beginner'}]
