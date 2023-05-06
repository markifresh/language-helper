from requests import get
from bs4 import BeautifulSoup
from re import compile as re_compile
from re import search as re_search
from json import loads as json_loads
from os import getenv
from dotenv import load_dotenv


load_dotenv()
url = getenv('SP_DICT')


def vocabs_get():
    res = get(f'{url}/lists/categories')
    soup = BeautifulSoup(res.text, 'html.parser')
    script_tag = soup.find('script', string=re_compile(r'window\.SD_COMPONENT_DATA'))
    data_str = re_search(r'window\.SD_COMPONENT_DATA = (.+);', script_tag.text).group(1)
    data = json_loads(data_str)
    return data.get('vocabLists')


def vocabs_filter_big(vocabs: list, min_words=500):
    return list(filter(lambda x: x['numVocabTranslations'] > min_words, vocabs))


def vocab_content_get(vocab_id, vocab_slug):
    res = get(f'{url}/lists/{vocab_id}/{vocab_slug}')
    soup = BeautifulSoup(res.text, 'html.parser')
    script_tag = soup.find('script', string=re_compile(r'window\.SD_COMPONENT_DATA'))
    data_str = re_search(r'window\.SD_COMPONENT_DATA = (.+);', script_tag.text).group(1)
    data = json_loads(data_str)
    return data.get('words')

