import telebot
from telebot import types
from telebot.types import Message
import logging
from config import logs, count_last_messages, admin_ids
from creds import token
from gpt import ask_gpt
from speechkit import speech_to_text, text_to_speech
from database import add_message, create_database, select_n_last_messages
from validators import check_number_of_users, is_gpt_limit, is_stt_limit, is_tts_limit

logging.basicConfig(filename=logs, level=logging.WARNING,
                    format="%(asctime)s FILE: %(filename)s IN: %(funcName)s MESSAGE: %(message)s", filemode="a")
bot = telebot.TeleBot(token)
create_database()


@bot.message_handler(commands=['start'])
def start(message: Message):
    bot.send_message(message.from_user.id, "Привет. Напиши мне голосовое или текстовое сообщение.\n"
                                           "Напиши /help, чтобы получить помощь.")


@bot.message_handler(commands=['feedback'])
def feedback_handle(msg: Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    option1 = types.KeyboardButton("Мне не нравятся ответы.")
    option2 = types.KeyboardButton("Бот неудобен.")
    option3 = types.KeyboardButton('Мне все понравилось.')

    markup.add(option1, option2, option3)

    bot.send_message(msg.chat.id, 'Пожалуйста, напишите отзыв.', reply_markup=markup)
    bot.register_next_step_handler(msg, feedback)


def feedback(msg: Message):
    with open('feedback.txt', 'a', encoding='utf-8') as f:
        f.write(f'{msg.from_user.first_name}({msg.from_user.id}) оставил отзыв - "{msg.text}"\n')
        bot.send_message(msg.chat.id, 'Спасибо за отзыв!')


@bot.message_handler(commands=['help'])
def help_handle(message: Message):
    bot.send_message(message.from_user.id, "Отправь мне одну из доступных команд"
                                           " или напиши голосовое или текстовое сообщение.\n"
                                           "Напиши /feedback, чтобы оставить отзыв.")


@bot.message_handler(commands=['debug'])
def debug(message: Message):
    if str(message.from_user.id) in admin_ids:
        try:
            with open(logs, "rb") as f:
                bot.send_document(message.chat.id, f)
        except telebot.apihelper.ApiTelegramException as e:
            bot.send_message(message.chat.id, 'Не получилось отправить файл с логами. Попробуйте позже.')
            logging.error(e)
    else:
        bot.send_message(message.from_user.id, "У вас нет прав админа.")


@bot.message_handler(content_types=['voice'])
def handle_voice(message: Message):
    user_id = message.from_user.id
    try:
        status_check_users, error_message = check_number_of_users(user_id)
        if not status_check_users:
            bot.send_message(user_id, error_message)
            return

        stt_blocks, error_message = is_stt_limit(user_id, message.voice.duration)
        if error_message:
            bot.send_message(user_id, error_message)
            return

        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)
        status_stt, stt_text = speech_to_text(file)
        if not status_stt:
            bot.send_message(user_id, stt_text)
            return

        add_message(user_id=user_id, full_message=[stt_text, 'user', 0, 0, stt_blocks])

        last_messages, total_spent_tokens = select_n_last_messages(user_id, count_last_messages)

        total_gpt_tokens, error_message = is_gpt_limit(last_messages, total_spent_tokens)
        if error_message:
            bot.send_message(user_id, error_message)
            return

        status_gpt, answer_gpt, tokens_in_answer = ask_gpt(last_messages)
        if not status_gpt:
            bot.send_message(user_id, answer_gpt)
            return
        total_gpt_tokens += tokens_in_answer

        tts_symbols, error_message = is_tts_limit(user_id, answer_gpt)

        add_message(user_id=user_id, full_message=[answer_gpt, 'assistant', total_gpt_tokens, tts_symbols, 0])

        if error_message:
            bot.send_message(user_id, error_message)
            return

        status_tts, voice_response = text_to_speech(answer_gpt)

        if status_tts:
            bot.send_voice(user_id, voice_response, reply_to_message_id=message.id)

        else:
            bot.send_message(user_id, answer_gpt, reply_to_message_id=message.id)

    except Exception as e:
        logging.error(e)
        bot.send_message(user_id, "Произошла ошибка, попробуйте еще раз.")


@bot.message_handler(commands=['stt', 'start'])
def stt_handler(message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Отправь голосовое сообщение, чтобы я его распознал!')
    bot.register_next_step_handler(message, stt)


def stt(message: Message):
    user_id = message.from_user.id

    if not message.voice:
        return

    success, stt_blocks = is_stt_limit(user_id, message.voice.duration)

    if not success:
        bot.send_message(user_id, stt_blocks)
        return

    file_id = message.voice.file_id
    file_info = bot.get_file(file_id)
    file = bot.download_file(file_info.file_path)

    status, text = speech_to_text(file)

    add_message(user_id, [text, 'assistant', 0, 0, stt_blocks])

    if status:
        bot.send_message(user_id, text, reply_to_message_id=message.id)

    else:
        bot.send_message(user_id, text)


@bot.message_handler(commands=['tts'])
def tts_handler(message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Отправь текст, чтобы я его озвучил.')
    bot.register_next_step_handler(message, tts)


def tts(message: Message):
    user_id = message.from_user.id
    text = message.text

    if message.content_type != 'text':
        bot.send_message(user_id, 'Отправь текстовое сообщение')
        return

    tts_symbol, error_message = is_tts_limit(user_id, text)

    if error_message and user_id not in admin_ids:
        bot.send_message(user_id, error_message)
        return

    status, content = text_to_speech(text)

    add_message(user_id, [text, 'user', 0, tts_symbol, 0])

    if status:
        bot.send_voice(user_id, content)
    else:
        bot.send_message(user_id, content)


@bot.message_handler(content_types=['text'])
def handle_text(message: Message):
    user_id = message.from_user.id

    try:
        status_check_users, error_message = check_number_of_users(user_id)
        if not status_check_users:
            bot.send_message(user_id, error_message)
            return

        full_user_message = [message.text, 'user', 0, 0, 0]
        add_message(user_id=user_id, full_message=full_user_message)

        last_messages, total_spent_tokens = select_n_last_messages(user_id, count_last_messages)

        total_gpt_tokens, error_message = is_gpt_limit(last_messages, total_spent_tokens)
        if error_message:
            bot.send_message(user_id, error_message)
            return

        status_gpt, answer_gpt, tokens_in_answer = ask_gpt(last_messages)
        if not status_gpt:
            bot.send_message(user_id, answer_gpt)
            return
        total_gpt_tokens += tokens_in_answer

        full_gpt_message = [answer_gpt, 'assistant', total_gpt_tokens, 0, 0]
        add_message(user_id=user_id, full_message=full_gpt_message)

        bot.send_message(user_id, answer_gpt, reply_to_message_id=message.id)

    except Exception as e:
        logging.error(e)
        bot.send_message(user_id, "Не получилось ответить. Попробуй написать другое сообщение")


bot.polling()
