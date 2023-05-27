from os import getenv
from dotenv import load_dotenv
import requests
from pathlib import Path
import xml.etree.ElementTree as xml_tree
from subprocess import run as subprocess_run


load_dotenv()
key = getenv("MS_SPEACH_KEY")
region = getenv("MS_SPEACH_REGION")


# todo: think on flow, probably need to make a project for each language so no need to make tts if it already exists
# get tanscriptions
# https://eastus.dev.cognitive.microsoft.com/docs/services/speech-to-text-api-v3-1/operations/Transcriptions_List

class MSSpeach:
    def __init__(self, api_key=key, region=region):
        self.api_key = api_key
        self.token = None
        self.region = region
        self.api_ver_major = '1'
        self.api_ver_minor = '0'
        self.tts_url = 'tts.speech.microsoft.com/cognitiveservices'
        self.stt_url = 'stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices'
        self.token_url = 'api.cognitive.microsoft.com/sts'

    def make_request(self, method: str, url: str, params=None, headers=None, raw_data=None, data=None, files=None):
        method = method.lower()

        if 'https' not in url:
            api_url = f'https://{self.region}.tts.speech.microsoft.com/cognitiveservices'
            url = url[1:] if url.startswith('/') else url
            url = f"{api_url}/{url}"

        if not headers:
            headers = {}

        headers['Ocp-Apim-Subscription-Key'] = self.api_key
        headers['Authorization'] = f'Bearer {self.token}'

        result = getattr(requests, method)(url, headers=headers, params=params, data=raw_data, json=data, files=files)
        if result.status_code not in (200, 201):
            raise Exception(result.status_code, result.text)

        if result.encoding:
            return result.json()

        if result.apparent_encoding:
            return result.text

        return result.content

    def token_create(self):
        api_version = f'v{self.api_ver_major}.{self.api_ver_minor}'
        url = f'https://{self.region}.{self.token_url}/{api_version}/issueToken'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        return self.make_request('POST', url, headers=headers)

    def languages_get(self):
        url = f'https://{self.region}.{self.tts_url}/voices/list'
        return self.make_request('GET', url)

    def text_to_speach(self, text, audio_format='ogg-48khz-16bit-mono-opus', file_location=''):
        extension = audio_format.split('-')[-1]
        url = f'https://{self.region}.{self.tts_url}/v{self.api_ver_major}'
        headers = {
                    'X-Microsoft-OutputFormat': audio_format,
                    'Content-Type': 'application/ssml+xml',
                  }

        speak = xml_tree.Element('speak')
        speak.set('version', '1.0')
        speak.set('xml:lang', 'en-US')

        voice = xml_tree.SubElement(speak, 'voice')
        voice.set('xml:lang', 'en-US')
        voice.set('xml:gender', 'Male')
        voice.set('name', 'en-US-ChristopherNeural')
        voice.text = text

        # todo: check with parameters can be added to voice (emotions, different pronunciation, speed,...)
        # https://github.com/MicrosoftDocs/azure-docs/blob/main/articles/cognitive-services/Speech-Service/speech-synthesis-markup.md
        # https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/

        data = xml_tree.tostring(speak, encoding='utf-8').decode()

        file_content = self.make_request('POST', url, headers=headers, raw_data=data)

        if not file_content:
            raise Exception('Failed to get audio content')

        file = Path(file_location, f"{text}.{extension}")
        file.write_bytes(file_content)

        return file

    def speach_to_text(self, file, file_location='', language='en-US'):
        url = f'https://{self.region}.{self.stt_url}/v{self.api_ver_major}'
        headers = {'Content-Type': 'audio/ogg'}
        params = {'language': language}
        file = Path(file_location, file) if not isinstance(file, Path) else file
        data = file.read_bytes()

        return self.make_request('POST', url, headers=headers, raw_data=data, params=params)

    @staticmethod
    def play_sound(file, file_location='', app_path='vlc', args=None):
        """
        make sure app has inline interface, so you can use it in cli way or you may use it this way:
            file_path = "path/to/sound_file.mp3"
            subprocess.run(["mpc-hc64.exe", "/play", file_path], shell=True)
        """
        file = Path(file_location, file) if not isinstance(file, Path) else file
        path = str(file)

        match app_path.lower():
            case 'vlc':
                app_path = 'C:\\Program Files\\VideoLAN\\VLC\\vlc.exe'
                args = ['--intf', 'dummy', '--play-and-exit'] if not args else args

        if args:
            command = [app_path] + args + [path]
            subprocess_run(command)

        else:
            command = [app_path, '/play', path]
            subprocess_run(command, shell=True)

