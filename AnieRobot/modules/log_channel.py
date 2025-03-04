﻿#Copyright (C) 2021 Free Software @noobanon @FakeMasked , Inc.[ https://t.me/noobanon https://t.me/FakeMasked ]
#Everyone is permitted to copy and distribute verbatim copies
#of this license document, but changing it is not allowed.
#The GNGeneral Public License is a free, copyleft license for
#software and other kinds of works.
#PTB13 Updated by @noobanon

from functools import wraps
from typing import Optional

from AnieRobot.modules.helper_funcs.misc import is_module_loaded

from AnieRobot.modules.translations.strings import tld

FILENAME = __name__.rsplit(".", 1)[-1]

if is_module_loaded(FILENAME):
    from telegram import Bot, Update, ParseMode, Message, Chat
    from telegram.error import BadRequest, Unauthorized
    from telegram.ext import CommandHandler, run_async
    from telegram.utils.helpers import escape_markdown

    from AnieRobot import dispatcher, LOGGER
    from AnieRobot.modules.helper_funcs.chat_status import user_admin
    from AnieRobot.modules.sql import log_channel_sql as sql


    def loggable(func):
        @wraps(func)
        def log_action(update, context, *args, **kwargs):
            result = func(update, context, *args, **kwargs)
            chat = update.effective_chat  # type: Optional[Chat]
            message = update.effective_message  # type: Optional[Message]
            if result:
                if chat.type == chat.SUPERGROUP and chat.username:
                    result += "\n<b>Link:</b> " \
                              "<a href=\"http://telegram.me/{}/{}\">click here</a>".format(chat.username,
                                                                                           message.message_id)
                log_chat = sql.get_chat_log_channel(chat.id)
                if log_chat:
                    send_log(context.bot, log_chat, chat.id, result)
            elif result == "":
                pass
            else:
                LOGGER.warning("%s was set as loggable, but had no return statement.", func)

            return result

        return log_action


    def send_log(bot: Bot, log_chat_id: str, orig_chat_id: str, result: str):
        try:
            bot.send_message(log_chat_id, result, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            if excp.message == "Chat not found":
                bot.send_message(orig_chat_id, "This log channel has been deleted - unsetting.")
                sql.stop_chat_logging(orig_chat_id)
            else:
                LOGGER.warning(excp.message)
                LOGGER.warning(result)
                LOGGER.exception("Could not parse")

                bot.send_message(log_chat_id, result + "\n\nFormatting has been disabled due to an unexpected error.")


    
    @user_admin
    def logging(update, context):
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]

        log_channel = sql.get_chat_log_channel(chat.id)
        if log_channel:
            log_channel_info = bot.get_chat(log_channel)
            message.reply_text(
                "This group has all it's logs sent to: {} (`{}`)".format(escape_markdown(log_channel_info.title),
                                                                         log_channel),
                parse_mode=ParseMode.MARKDOWN)

        else:
            message.reply_text("No log channel has been set for this group!")


   
    @user_admin
    def setlog(update, context):
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]
        bot = context.bot
        if chat.type == chat.CHANNEL:
            message.reply_text(tld(chat.id, "Now, forward the /setlog to the group you want to tie this channel to!"))

        elif message.forward_from_chat:
            sql.set_chat_log_channel(chat.id, message.forward_from_chat.id)
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("Error deleting message in log channel. Should work anyway though.")

            try:
                bot.send_message(message.forward_from_chat.id, tld(chat.id, 
                                 "This channel has been set as the log channel for {}.").format(
                                     chat.title or chat.first_name))
            except Unauthorized as excp:
                if excp.message == "Forbidden: bot is not a member of the channel chat":
                    bot.send_message(chat.id, tld(chat.id, "Successfully set log channel!"))
                else:
                    LOGGER.exception("ERROR in setting the log channel.")

            bot.send_message(chat.id, tld(chat.id, "Successfully set log channel!"))

        else:
            message.reply_text(tld(chat.id, "*The steps to set a log channel are:*\n"
                               " • add bot to the desired channel\n"
                               " • send /setlog to the channel\n"
                               " • forward the /setlog to the group\n"), ParseMode.MARKDOWN)


    
    @user_admin
    def unsetlog(update, context):
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]
        bot = context.bot

        log_channel = sql.stop_chat_logging(chat.id)
        if log_channel:
            bot.send_message(log_channel, tld(chat.id, "Channel has been unlinked from {}").format(chat.title))
            message.reply_text(tld(chat.id, "Log channel has been un-set."))

        else:
            message.reply_text(tld(chat.id, "No log channel has been set yet!"))


    def __stats__():
        return "{} log channels set.".format(sql.num_logchannels())


    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)


    def __chat_settings__(bot, update, chat, chatP, user):
        log_channel = sql.get_chat_log_channel(chat.id)
        if log_channel:
            log_channel_info = dispatcher.bot.get_chat(log_channel)
            return "This group has all it's logs sent to: {} (`{}`)".format(escape_markdown(log_channel_info.title),
                                                                            log_channel)
        return "No log channel is set for this group!"


    LOG_HANDLER = CommandHandler("logchannel", logging, run_async=True)
    SET_LOG_HANDLER = CommandHandler("setlog", setlog, run_async=True)
    UNSET_LOG_HANDLER = CommandHandler("unsetlog", unsetlog, run_async=True)

    dispatcher.add_handler(LOG_HANDLER)
    dispatcher.add_handler(SET_LOG_HANDLER)
    dispatcher.add_handler(UNSET_LOG_HANDLER)

else:
    # run anyway if module not loaded
    def loggable(func):
        return func
