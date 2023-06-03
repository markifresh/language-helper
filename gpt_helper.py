# from urllib import request as url_request
# from urllib.error import HTTPError
# from json import dumps as json_dumps
# from json import loads as json_loads

from time import sleep
from datetime import datetime
import requests
from dotenv import load_dotenv
load_dotenv()
from os import getenv


token = getenv('OPENAI_TOKEN')
chat_url = getenv('CHAT_URL')
model = "gpt-3.5-turbo"


def make_request(method, url, data=None, headers=None, params=None):
    method = method.lower()
    data = {} if not data else data
    params = {} if not params else params
    headers = {'Content-Type': 'application/json'} if not headers else headers
    headers['Authorization'] = 'Bearer ' + token

    res = getattr(requests, method)(url, headers=headers, json=data, params=params)
    if res.status_code == 429:
        sleep(30)
        res = getattr(requests, method)(url, headers=headers, json=data, params=params)

    success = res.status_code == 200
    data = res.json() if success else res.text
    return {
                'success': success,
                'status_code': res.status_code,
                'data': data,
           }



# def make_request(method, url, data, headers=None):
#     method = method.upper()
#
#     if not headers:
#         headers = {'Content-Type': 'application/json'}
#     headers['Authorization'] = 'Bearer ' + token
#
#     json_data = json_dumps(data).encode('utf-8') if data else {}
#     req = url_request.Request(url, method=method, data=json_data, headers=headers)
#     try:
#         response = url_request.urlopen(req)
#         success = response.status == 200
#         if success:
#             res_text = response.read().decode('utf-8')
#             return {
#                         'success': success,
#                         'data': json_loads(res_text),
#                         'status_code': response.status
#                     }
#         else:
#             return {
#                         'success': success,
#                         'data': f"HTTP Error {response.status}: {response.reason}",
#                         'status_code': response.status
#                    }
#     except HTTPError as e:
#         return {
#                     'success': False,
#                     'data': f"HTTP Error {e.code}: {e.reason}",
#                     'status_code': 666
#                 }


def format_chat_output(output_org):
        output = output_org['data']
        output_org['data'] = {
                                'message': output['choices'][0]['message']['content'],
                                'output_length': len(output['choices'][0]['message']['content']),
                                'finish_reason': output['choices'][0]['finish_reason'],
                                'tokens_used': output['usage']['total_tokens'],
                                'chat_model': output['model'],
                                'chat_id': output['id'],
                                'timestamp': output['created'],
                                'date': datetime.fromtimestamp(output['created']),
                                }
        return output_org


def send_question(question, history=None, beautify=True):
    messages = [{"role": "user", "content": question}]

    if history:
        messages = history + messages

    data = {
                "model": model,
                "messages": messages
            }

    res = make_request('POST', chat_url, data=data)
    if beautify:
        res = format_chat_output(res) if res['success'] else res
    return res

# Text of the message to be sent, 1-4096 characters after entities parsing
# protect_content	Boolean	Optional	Protects the contents of the sent message from forwarding and saving
# reply_to_message_id	Integer	Optional	If the message is a reply, ID of the original message

# resend message, it will resend all previous mesagess? by tag?
# add tag to answer as well

# todo: when tag in message, put the same tag in output
# todo: when tag in message 1. send last 3 messages with this tag as assistant (his answers) 2. send 3 last messages as user
# so bot will have 3 last questions and 3 last answers, if use #all tag, it will use all messages with this tag

# todo: make function /create_conversation - all questions and answers will be forwarded to bot
# creates a database with id? use this in tag of message?
# todo: make function /close_conversation
# removes db when no closed
# todo: force close db when size is too big
# todo: send info about DBs

# DBs as mapped volumes
# alert, that when converation created, all data will be stored in server

  # model="gpt-3.5-turbo",
  # messages=[
  #       {"role": "system", "content": "You are a helpful assistant."},
  #       {"role": "user", "content": "Who won the world series in 2020?"},
  #       {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
  #       {"role": "user", "content": "Where was it played?"}
  #   ]

# https://platform.openai.com/account/usage

# calculate token used by user, limit it?
# still need a conversation? when it's more that 10 messages?
