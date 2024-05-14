import logging
import math
from config import logs, max_users, max_gpt_tokens_per_user, max_stt_blocks_per_user, max_tts_symbols_per_user, admin_ids
from database import count_users, count_all_limits
from gpt import count_gpt_tokens

logging.basicConfig(filename=logs, level=logging.DEBUG,
                    format="%(asctime)s FILE: %(filename)s IN: %(funcName)s MESSAGE: %(message)s", filemode="a")


def check_number_of_users(user_id):
    count = count_users(user_id)
    if count is None:
        return None, "Ошибка при работе с БД"
    if count > max_users:
        return None, "Превышено максимальное количество пользователей"
    return True, ""


def is_gpt_limit(messages, total_spent_tokens):
    all_tokens = count_gpt_tokens(messages) + total_spent_tokens
    if all_tokens > max_gpt_tokens_per_user:
        return None, "Превышен общий лимит GPT-токенов."
    return all_tokens, ""


def is_tts_limit(user_id, text):
    text_symbols = len(text)

    all_symbols = count_all_limits(user_id, 'tts_symbols') + text_symbols

    if all_symbols >= max_tts_symbols_per_user and str(user_id) not in admin_ids:
        msg = "Превышен лимит SpeechKit TTS, возвращайтесь позже"
        return None, msg

    return text_symbols, None


def is_stt_limit(user_id, duration):
    audio_blocks = math.ceil(duration / 15)
    all_blocks = count_all_limits(user_id, 'stt_blocks') + audio_blocks

    if duration >= 30:
        response = "Превышена максимальная длительность голосового сообщения."
        return None, response

    if all_blocks >= max_stt_blocks_per_user and str(user_id) not in admin_ids:
        response = "Превышен лимит SpeechKit STT, возвращайтесь позже"
        return None, response

    return audio_blocks, None
