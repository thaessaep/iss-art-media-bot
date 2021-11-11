import os
import json
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (Updater, MessageHandler, Filters, CommandHandler,
                          ConversationHandler, CallbackQueryHandler, PicklePersistence)
from dotenv import load_dotenv
from states import *

load_dotenv()
persistence = PicklePersistence('./persistence')


def start(update, _):
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Сделать пост', callback_data='/post')]])
    update.message.reply_text('Этот бот умеет выкладывать посты и добавлять описание', reply_markup=reply_markup)
    return POST


def post(update, _):    # заправшивает источник
    update.callback_query.message.reply_text('Мы ждём от вас источник, который вы хотите опубликовать')
    return DOC_TYPE


def remember_text(update, context):
    context.user_data['post'] = update.message.text
    context.user_data['message_type'] = 'ref'
    return doc_type(update, context.user_data['message_type'])


def remember_photo(update, context):
    context.user_data['post'] = update.message.photo[0].file_id     # получаю id отправленного фото
    context.user_data['message_type'] = 'photo'
    return doc_type(update, context.user_data['message_type'])


def remember_video(update, context):
    context.user_data['post'] = update.message.video.file_id     # получаю id отправленного видео
    context.user_data['message_type'] = 'video'
    return doc_type(update, context.user_data['message_type'])


def remember_audio(update, context):
    context.user_data['post'] = update.message.audio.file_id
    context.user_data['message_type'] = 'audio'
    return doc_type(update, context.user_data['message_type'])


def remember_doc(update, context):
    context.user_data['post'] = update.message.document.file_id  # получаю id отправленного видео
    context.user_data['message_type'] = 'doc'
    return doc_type(update, context.user_data['message_type'])


def doc_type(update, document_type):
    reply_markup = ReplyKeyboardMarkup(json_data[document_type + '_type'], resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text('Как вы охарактеризуете этот ресурс?', reply_markup=reply_markup)
    return HASHTAG


def hashtag(update, context):   # запоминает источник в user_data и запрашивает хэштеги
    context.user_data['hashtag'] = []
    context.user_data['hashtag'].append('#{}'.format(update.message.text.replace(' ', '').lower()))
    reply_markup = ReplyKeyboardMarkup(json_data[context.user_data['message_type'] + '_descriptors'],
                                       resize_keyboard=True)
    update.message.reply_text('Чем вам понравился этот ресурс?\n'
                              'Вы можете выбрать несколько вариантов\n'
                              'Если хотите закончить свой выбор - напишите /cancel', reply_markup=reply_markup)
    return REMEMBER_HASHTAG


def remember_hashtag(update, context):  # записывает хэштеги в user_data
    context.user_data['hashtag'].append('#{}'.format(update.message.text.replace(' ', '').lower()))
    return REMEMBER_HASHTAG


def cancel_hashtag(update, _):   # прекращает формирование хэштегов и запрашивает описание
    reply_markup = ReplyKeyboardMarkup([['Да', 'Нет']], resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text('Хотите ли бы вы сформировать описание?', reply_markup=reply_markup)
    return DESCRIPTION


def description(update, context):   # формирует описание в зависимости от ответа
    if update.message.text == 'Да':
        update.message.reply_text('Добавьте описание к посту')
        return CONFIRMATION
    else:
        return confirmation(update, context)


def send_message(func, chat_id, context, caption=None):     # отправка сообщения
    if caption is not None:
        context.user_data['result_message_id'] = func(chat_id, context.user_data['post'], caption=caption).message_id
    else:
        context.user_data['result_message_id'] = func(chat_id, context.user_data['post']).message_id


def confirmation(update, context):    # выдаёт заполненный пост и запрашивает подтверждение на его публикацию

    hashtag_description = '\n\n{}\n\n'.format(' '.join(context.user_data['hashtag']))
    if update.message.text != 'Нет':
        hashtag_description += update.message.text

    update.message.reply_text('Ваш пост сформирован:\n')

    if context.user_data['message_type'] == 'ref':
        context.user_data['post'] += hashtag_description
        send_message(bot.send_message, update.message.chat.id, context)
    elif context.user_data['message_type'] == 'photo':
        send_message(bot.send_photo, update.message.chat.id, context, hashtag_description)
    elif context.user_data['message_type'] == 'video':
        send_message(bot.send_video, update.message.chat.id, context, hashtag_description)
    elif context.user_data['message_type'] == 'doc':
        send_message(bot.send_document, update.message.chat.id, context, hashtag_description)

    reply_markup = ReplyKeyboardMarkup([['Да', 'Нет']], resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text('Вы хотите выложить пост в группу?', reply_markup=reply_markup)
    return PUBLISH


def publish(update, context):   # публикует пост в источник
    if update.message.text == 'Да':
        bot.forward_message(CHANNEL_NAME, update.message.chat.id, context.user_data['result_message_id'])
    update.message.reply_text('До встречи!', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def stop(update, _):
    update.message.reply_text('Будет скучно - напишите', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


if __name__ == '__main__':

    with open('config.json', 'r', encoding='UTF-8') as file:
        json_data = json.load(file)

    TOKEN = os.getenv('TOKEN')
    CHANNEL_NAME = os.getenv('CHANNEL_NAME')
    bot = Bot(TOKEN)
    updater = Updater(TOKEN, use_context=True, persistence=persistence)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            POST: [CommandHandler('post', post), CallbackQueryHandler(post)],
            DOC_TYPE: [
                MessageHandler(Filters.text, remember_text),
                MessageHandler(Filters.photo, remember_photo),
                MessageHandler(Filters.video, remember_video),
                MessageHandler(Filters.audio, remember_audio),
                MessageHandler(Filters.document, remember_doc),
            ],
            HASHTAG: [MessageHandler(Filters.text, hashtag)],
            REMEMBER_HASHTAG: [
                CommandHandler('cancel', cancel_hashtag),
                MessageHandler(Filters.text, remember_hashtag)
            ],
            DESCRIPTION: [MessageHandler(Filters.text, description)],
            CONFIRMATION: [MessageHandler(Filters.text, confirmation), ],
            PUBLISH: [MessageHandler(Filters.text, publish)],
        },
        fallbacks=[CommandHandler('stop', stop)], persistent=True, name='iss-art-media'
    )

    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()
