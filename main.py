from telegram.ext import (Updater, MessageHandler, Filters, CommandHandler,
                          ConversationHandler)
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot
import json


POST, HASHTAG, REMEMBER_HASHTAG, CANCEL_HASHTAG, DESCRIPTION, PUBLISH, CONFIRMATION = range(7)


def start(update, _):
    update.message.reply_text('Этот бот умеет выкладывать посты и добавлять описание\n'
                              'Если вы хотите сделать пост - напишите /post')
    return POST


def post(update, _):    # заправшивает источник
    update.message.reply_text('Мы ждём от вас источник, который вы хотите опубликовать')
    return HASHTAG


def remember_text(update, context):
    context.user_data['post'] = update.message.text
    context.user_data['message_type'] = 'text'
    return hashtag(update, context)


def remember_photo(update, context):
    context.user_data['post'] = update.message.photo[0].file_id     # получаю id отправленного фото
    context.user_data['message_type'] = 'photo'
    return hashtag(update, context)


def remember_video(update, context):
    context.user_data['post'] = update.message.video.file_id     # получаю id отправленного видео
    context.user_data['message_type'] = 'video'
    return hashtag(update, context)


def remember_doc(update, context):
    context.user_data['post'] = update.message.document.file_id  # получаю id отправленного видео
    context.user_data['message_type'] = 'doc'
    return hashtag(update, context)


def hashtag(update, context):   # запоминает источник в user_data и запрашивает хэштеги
    context.user_data['hashtag'] = []
    reply_markup = ReplyKeyboardMarkup(json_data['liked'], resize_keyboard=True)
    update.message.reply_text('Чем вам понравился этот ресурс?\n'
                              'Вы можете выбрать несколько вариантов\n'
                              'Если хотите закончить свой выбор - напишите /cancel', reply_markup=reply_markup)
    return REMEMBER_HASHTAG


def remember_hashtag(update, context):  # записывает хэштеги в user_data
    context.user_data['hashtag'].append('#{}'.format(update.message.text.lower()))
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

    if context.user_data['message_type'] == 'text':
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
    bot.forward_message('@fasdgdfhgdfhgfd', update.message.chat.id, context.user_data['result_message_id'])
    update.message.reply_text('До встречи!', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def stop(update, _):
    update.message.reply_text('Будет скучно - напишите', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


if __name__ == '__main__':

    with open('config.json', 'r', encoding='UTF-8') as file:
        json_data = json.load(file)

    bot = Bot(json_data['token'])
    updater = Updater(json_data['token'], use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            POST: [CommandHandler('post', post)],
            HASHTAG: [
                MessageHandler(Filters.text, remember_text),
                MessageHandler(Filters.photo, remember_photo),
                MessageHandler(Filters.video, remember_video),
                MessageHandler(Filters.document, remember_doc)
            ],
            REMEMBER_HASHTAG: [
                CommandHandler('cancel', cancel_hashtag),
                MessageHandler(Filters.text, remember_hashtag)
            ],
            DESCRIPTION: [MessageHandler(Filters.text, description)],
            CONFIRMATION: [MessageHandler(Filters.text, confirmation), ],
            PUBLISH: [MessageHandler(Filters.text, publish)],
        },
        fallbacks=[CommandHandler('stop', stop)]
    )

    dp.add_handler(conv_handler)
    #dp.add_handler(CommandHandler('post', post))

    updater.start_polling()
    updater.idle()
