from pathlib import Path
from gpt_helper import send_question


# ask chat to define word Level optional?
def create_request_fields(from_lang, to_lang, vocab_source, vocab_name, level='A1'):
    return {
        'id': '(id of word)',
        'word': f'({from_lang} word without article)',
        'whole_word': f'(if article exists for this word - {from_lang} word with article, else {from_lang} word)',
        'word_translation': f'(translation to {to_lang})',
        'sentence': f'(create sentence (which you think can be useful, it is up to you) '
                    f'with {from_lang} word on {from_lang} (no need for translation here))',
        'sentence_translation': f'(translation of sentence to {to_lang})',
        'type':  f'(type of word: noun, verb, ..., but please use english language)',
        'is_irregular': f'(is this word irregular according to {from_lang} grammar rules? (True or False))',
        'level':   f'{level} if {level} else please define a level for this word/sentence from A1 to C2',
        'language': f'(full language name of {from_lang.lower()} in lowercase in english)',
        'to_language': f'(full language name of  {to_lang.lower()} in lowercase in english)',
        'topics':  f'(coma+space separated list of topics to which this word can be related. '
                   f'Can be few topics at the same time f.e. "weather, time".'
                   f'Please use only english language for this field)',
        'source':  f'("{vocab_source}, {vocab_name}" for all)'
        }


def create_request_message(from_lang, to_lang, vocab_source, vocab_name, level):
    from_lang = from_lang.title()
    to_lang = to_lang.title()
    fields = create_request_fields(from_lang, to_lang, vocab_source, vocab_name, level)
    fields_str = "\n".join([f'- {field} {fields[field]}' for field in fields])
    return f'I learn {from_lang}, but you please speak English. Please make a list of dictionaries (json). ' \
           'Each dictionary should have keys: \n' \
           f'{fields_str} \n' \
           '(your reply should be in json format)' \
           f'To fill this list please use the following list of {from_lang} words: \n'




message2 = 'To fill this CSV file use a list of Spanish words required for level A1, ' \
           'I know there are different standards and criteria used by different organizations and countries, ' \
           'so I leave it to you to choose'



# https://www.spanishdict.com/lists/categories/47/big-lists
def make_csv(words, start, end):
    # new_file = Path(f'new_{start}-{end}.csv')
    # new_file.write_text(csv_content, encoding="utf-8")
    message = message1 + '\n'.join(words[start:end])
    res = send_question(message, beautify=False)
    csv_content = (res['data']['choices'][0]['message']['content'])
    return csv_content, res