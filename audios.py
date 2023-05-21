from os import getenv
from dotenv import load_dotenv
import requests


load_dotenv()
speach_key = getenv("MS_SPEACH")
speach_region = getenv("MS_REGION")


class MSAudio:
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

        return result.json() if result.encoding == 'utf-8' else result.text

    def token_create(self):
        api_version = f'v{self.api_ver_major}.{self.api_ver_minor}'
        url = f'https://{self.region}.api.cognitive.microsoft.com/sts/{api_version}/issueToken'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        return self.make_request('POST', url, headers=headers)

    def languages_get(self):
        url = '/voices/list'
        return self.make_request('GET', url)

    def tts(self, text):
        url = f'https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v{self.api_ver_major}'
        headers = {
                    'X-Microsoft-OutputFormat': 'riff-24khz-16bit-mono-pcm',
                    'Content-Type': 'application/ssml+xml',
                  }

        data = "<speak version='1.0' xml:lang='en-US'>" + \
                  "<voice xml:lang='en-US' xml:gender='Male'\r\n" + \
                  "name='en-US-ChristopherNeural'>\r\n" + \
                  f"{text}\r\n" + \
                  "</voice></speak>"

        return self.make_request('POST', url, headers=headers, data=data)
        # if response.status_code == 200:
        #     with open("output.wav", "wb") as audio_file:
        #         audio_file.write(response.content)
        # else:
        #     print("Error:", response.text)

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
