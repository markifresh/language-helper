from os import getenv
from dotenv import load_dotenv
import requests

load_dotenv()
key = getenv("MS_TRANSLATE_KEY")
region = getenv("MS_TRANSLATE_REGION")


class MSTranslate:
    def __init__(self, api_key=key, region=region):
        self.api_key = api_key
        self.token = None
        self.region = region
        self.api_ver_major = '3'
        self.api_ver_minor = '0'
        self.translate_url = 'api.cognitive.microsofttranslator.com'

    def make_request(self, method: str, url: str, params=None, headers=None, raw_data=None, data=None, files=None):
        method = method.lower()
        if not params:
            params = {}
        params['api-version'] = f'{self.api_ver_major}.{self.api_ver_minor}'

        if 'https' not in url:
            api_url = f'https://{self.translate_url}'
            url = url[1:] if url.startswith('/') else url
            url = f"{api_url}/{url}"

        if not headers:
            headers = {}

        headers['Ocp-Apim-Subscription-Key'] = self.api_key
        headers['Ocp-Apim-Subscription-Region'] = self.region
        # headers['Authorization'] = f'Bearer {self.token}'

        result = getattr(requests, method)(url, headers=headers, params=params, data=raw_data, json=data, files=files)
        if result.status_code not in (200, 201):
            raise Exception(result.status_code, result.text)

        if result.encoding:
            return result.json()

        if result.apparent_encoding:
            return result.text

        return result.content

    def languages_detect(self, texts):
        url = f'/detect'
        headers = {"Content-Type": "application/json"}
        texts = [texts] if not isinstance(texts, list) else texts
        data = [{"Text": text} for text in texts]
        return self.make_request('POST', url, headers=headers, data=data)

    def languages_list(self):
        url = '/languages'
        return self.make_request('GET', url)

    def translate(self, from_lang, to_lang, texts):
        url = 'translate?api-version=3.0&from=en&to=ru'
        headers = {'Content-Type': 'application/json'}
        params = {
                    'from': from_lang,
                    'to_lang': to_lang
                 }
        texts = [texts] if not isinstance(texts, list) else texts
        data = [{'Text': text} for text in texts]
        return self.make_request('POST', url, headers=headers, data=data, params=params)