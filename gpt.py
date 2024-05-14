import requests
import logging
from config import logs, max_gpt_tokens, temperature, SYSTEM_PROMPT
from creds import iam_token, folder_id


logging.basicConfig(filename=logs, level=logging.WARNING,
                    format="%(asctime)s FILE: %(filename)s IN: %(funcName)s MESSAGE: %(message)s", filemode="a")


def count_gpt_tokens(messages):
    headers = {
        'Authorization': f'Bearer {iam_token}',
        'Content-Type': 'application/json'
    }
    data = {
        'modelUri': f"gpt://{folder_id}/yandexgpt-lite",
        "messages": messages
    }
    try:
        response = requests.post(url="https://llm.api.cloud.yandex.net/foundationModels/v1/tokenizeCompletion",
                                 json=data, headers=headers).json()['tokens']
        return len(response)
    except Exception as e:
        logging.error(e)
        return 0


def ask_gpt(messages):
    headers = {
        'Authorization': f'Bearer {iam_token}',
        'Content-Type': 'application/json'
    }
    data = {
        'modelUri': f"gpt://{folder_id}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": max_gpt_tokens
        },
        "messages": SYSTEM_PROMPT + messages
    }
    try:
        response = requests.post("https://llm.api.cloud.yandex.net/foundationModels/v1/completion", headers=headers, json=data)
        if response.status_code != 200:
            return False, f"Ошибка GPT. Статус-код: {response.status_code}", None
        answer = response.json()['result']['alternatives'][0]['message']['text']
        tokens_in_answer = count_gpt_tokens([{'role': 'assistant', 'text': answer}])
        return True, answer, tokens_in_answer
    except Exception as e:
        logging.error(e)
        return False, "Ошибка при обращении к GPT",  None
