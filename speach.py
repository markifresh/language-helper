from os import getenv
from dotenv import load_dotenv
import requests
from pathlib import Path

load_dotenv()
speach_key = getenv("MS_SPEACH")
speach_region = getenv("MS_REGION")


class MSSpeach:
    def __init__(self, api_key=speach_key, region=speach_region):
        self.api_key = api_key
        self.token = None
        self.region = region
        self.api_ver_major = '1'
        self.api_ver_minor = '0'

    def make_request(self, method: str, url: str, params=None, headers=None, data=None, json=None):
        method = method.lower()

        if 'https' not in url:
            api_url = f'https://{self.region}.tts.speech.microsoft.com/cognitiveservices'
            url = url[1:] if url.startswith('/') else url
            url = f"{api_url}/{url}"

        if not headers:
            headers = {}

        headers['Ocp-Apim-Subscription-Key'] = self.api_key
        headers['Authorization'] = f'Bearer {self.token}'

        result = getattr(requests, method)(url, headers=headers, params=params, data=data, json=json)
        if result.status_code not in (200, ):
            raise Exception(result.status_code, result.text)

        if result.encoding:
            return result.json()

        if result.apparent_encoding:
            return result.text

        return result.content

    def token_create(self):
        api_version = f'v{self.api_ver_major}.{self.api_ver_minor}'
        url = f'https://{self.region}.api.cognitive.microsoft.com/sts/{api_version}/issueToken'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        return self.make_request('POST', url, headers=headers)

    def languages_get(self):
        url = '/voices/list'
        return self.make_request('GET', url)

    def tts(self, text, format='audio-24khz-96kbitrate-mono-mp3', file_location=''):
        extension = format.split('-')[-1]
        url = f'https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v{self.api_ver_major}'
        headers = {
                    'X-Microsoft-OutputFormat': format,
                    'Content-Type': 'application/ssml+xml',
                  }

        data = "<speak version='1.0' xml:lang='en-US'>" + \
                  "<voice xml:lang='en-US' xml:gender='Male'\r\n" + \
                  "name='en-US-ChristopherNeural'>\r\n" + \
                  f"{text}\r\n" + \
                  "</voice></speak>"

        file_content = self.make_request('POST', url, headers=headers, data=data)

        if not file_content:
            raise Exception('Failed to get audio content')

        file = Path(file_location)
        file = file.joinpath(f"{text}.{extension}")
        file.write_bytes(file_content)
        return file

    def language_define(self):
        pass

    def stt(self):
        pass

    def synthesis_submit(self):
        pass

    def synthesis_wait(self):
        pass

    def synthesis_download(self):
        pass

    def syntheses_get(self):
        pass

    def synthesis_get(self):
        pass

    def get_str_from_file(self):
        pass
