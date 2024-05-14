admin_ids = ["1343148733"]  # id админов в телеграмме (строкой)
max_stt_blocks_per_user = 10  # максимальное количество stt блоков на пользователя
max_tts_symbols_per_user = 5000  # максимальное количество tts символов на пользователя
max_gpt_tokens_per_user = 2500  # максимальное количество gpt токенов на одного пользователя
max_users = 3
max_gpt_tokens = 120  # максимальное количество токенов gpt на ответ
temperature = 0.7  # температура ответов нейросети
count_last_messages = 4
logs = 'logs.log'
DB_FILE = 'messages.db'
SYSTEM_PROMPT = [{'role': 'system', 'text': 'Будь вежливым'}]


