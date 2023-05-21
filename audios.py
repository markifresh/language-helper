from os import getenv
from dotenv import load_dotenv
import requests


load_dotenv()
speach_key = getenv("MS_SPEACH")
speach_region = getenv("MS_REGION")
SERVICE_HOST = "customvoice.api.speech.microsoft.com"


NAME = 'test_name'
DESCRIPTION = 'test_DESCRIPTION'


class MSAudio():
    def __init__(self, api_key=speach_key, region=speach_region):
        self.api_key = api_key
        self.token = None
        self.region = region
        self.api_version = 'v1.0'


    def make_request(self, method: str, url: str, params=None, headers=None):
        method = method.lower()
        api_url = f"https://{speach_region}.api.cognitive.microsoft.com/sts/{self.api_version}"
        url = url[1:] if url.startswith('/') else url
        url = f"{api_url}/{url}"
        if not headers:
            headers = {}

        headers['Ocp-Apim-Subscription-Key'] = self.api_key
        headers['Authorization'] = f'Bearer {self.token}'

        result = getattr(requests, method)(url, headers=headers, params=params)
        if result.status_code not in (200, ):
            raise Exception(result.status_code, result.text)

        return result


    def token_set(self):
        url = '/issueToken'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        return self.make_request('POST', url, headers=headers)


    def languages_get(self):
        url = 'https://.tts.speech.microsoft.com/cognitiveservices/voices/list'
        # "https://.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            'Ocp-Apim-Subscription-Key': speach_key
        }
        return requests.get(url, headers=headers)

    def tts(self, text):
        url = f"https://{speach_region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            'Authorization': 'Bearer xxxx',
            'X-Microsoft-OutputFormat': 'riff-24khz-16bit-mono-pcm',
            'Content-Type': 'application/ssml+xml',
            'Ocp-Apim-Subscription-Key': 'xxxxx'
        }

        payload = "<speak version='1.0' xml:lang='en-US'>" + \
                  "<voice xml:lang='en-US' xml:gender='Male'\r\n" + \
                  "name='en-US-ChristopherNeural'>\r\n" + \
                  f"{text}\r\n" + \
                  "</voice></speak>"

        return requests.post(url, headers=headers, data=payload)


    def synthesis_submit(self):
        # url = f'https://{speach_region}.{SERVICE_HOST}/api/texttospeech/3.1-preview1/batchsynthesis'
        url = f'https://{speach_region}.tts.speech.microsoft.com/cognitiveservices/v1'
        header = {
            'Ocp-Apim-Subscription-Key': speach_key,
            'Content-Type': 'application/json'
        }

        payload = {
            'displayName': NAME,
            'description': DESCRIPTION,
            "textType": "PlainText",
            'synthesisConfig': {
                "voice": "en-US-JennyNeural",
            },
            # Replace with your custom voice name and deployment ID if you want to use custom voice.
            # Multiple voices are supported, the mixture of custom voices and platform voices is allowed.
            # Invalid voice name or deployment ID will be rejected.
            'customVoices': {
                # "YOUR_CUSTOM_VOICE_NAME": "YOUR_CUSTOM_VOICE_ID"
            },
            "inputs": [
                {
                    "text": "here is my test"
                },
            ],
            "properties": {
                "outputFormat": "audio-24khz-160kbitrate-mono-mp3",
                # "destinationContainerUrl": "<blob container url with SAS token>"
            },
        }

        return requests.post(url, json=payload, headers=header)

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
