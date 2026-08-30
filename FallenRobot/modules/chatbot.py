import html
import json
import os
import re
from typing import Optional

import requests
from telegram import (
    CallbackQuery,
    Chat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    Update,
    User,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    run_async,
)
from telegram.utils.helpers import mention_html

import FallenRobot.modules.sql.chatbot_sql as sql
from FallenRobot import BOT_ID, BOT_NAME, BOT_USERNAME, dispatcher
from FallenRobot.modules.helper_funcs.chat_status import user_admin, user_admin_no_reply
from FallenRobot.modules.log_channel import gloggable


@run_async
@user_admin_no_reply
@gloggable
def fallenrm(update: Update, context: CallbackContext) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user: Optional[User] = update.effective_user
    match = re.match(r"rm_chat\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat: Optional[Chat] = update.effective_chat
        is_fallen = sql.set_fallen(chat.id)
        if is_fallen:
            is_fallen = sql.set_fallen(user_id)
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"AI_DISABLED\n"
                f"<b>Admin :</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            )
        else:
            update.effective_message.edit_text(
                "{} ᴄʜᴀᴛʙᴏᴛ ᴅɪsᴀʙʟᴇᴅ ʙʏ {}.".format(
                    dispatcher.bot.first_name, mention_html(user.id, user.first_name)
                ),
                parse_mode=ParseMode.HTML,
            )

    return ""


@run_async
@user_admin_no_reply
@gloggable
def fallenadd(update: Update, context: CallbackContext) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user: Optional[User] = update.effective_user
    match = re.match(r"add_chat\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat: Optional[Chat] = update.effective_chat
        is_fallen = sql.rem_fallen(chat.id)
        if is_fallen:
            is_fallen = sql.rem_fallen(user_id)
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"AI_ENABLE\n"
                f"<b>Admin :</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            )
        else:
            update.effective_message.edit_text(
                "{} ᴄʜᴀᴛʙᴏᴛ ᴇɴᴀʙʟᴇᴅ ʙʏ {}.".format(
                    dispatcher.bot.first_name, mention_html(user.id, user.first_name)
                ),
                parse_mode=ParseMode.HTML,
            )

    return ""


@run_async
@user_admin
@gloggable
def fallen(update: Update, context: CallbackContext):
    message = update.effective_message
    msg = "• ᴄʜᴏᴏsᴇ ᴀɴ ᴏᴩᴛɪᴏɴ ᴛᴏ ᴇɴᴀʙʟᴇ/ᴅɪsᴀʙʟᴇ ᴄʜᴀᴛʙᴏᴛ"
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="ᴇɴᴀʙʟᴇ", callback_data="add_chat({})"),
                InlineKeyboardButton(text="ᴅɪsᴀʙʟᴇ", callback_data="rm_chat({})"),
            ],
        ]
    )
    message.reply_text(
        text=msg,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )


def fallen_message(context: CallbackContext, message):
    reply_message = message.reply_to_message
    if message.text.lower() == "fallen":
        return True
    elif BOT_USERNAME in message.text.upper():
        return True
    elif reply_message:
        if reply_message.from_user.id == BOT_ID:
            return True
    else:
        return False


def chatbot(update: Update, context: CallbackContext):
    message = update.effective_message
    chat_id = update.effective_chat.id
    bot = context.bot
    is_fallen = sql.is_fallen(chat_id)
    if is_fallen:
        return

    if message.text and not message.document:
        if not fallen_message(context, message):
            return
        bot.send_chat_action(chat_id, action="typing")
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            message.reply_text("Chatbot is not configured yet. Add OPENAI_API_KEY in Render.")
            return
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are {}. Reply briefly and helpfully.".format(
                        BOT_NAME
                    ),
                },
                {"role": "user", "content": message.text},
            ],
            "max_tokens": 300,
        }
        try:
            request = requests.post(
                url,
                headers={
                    "Authorization": "Bearer " + api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            request.raise_for_status()
            results = request.json()
            reply = None
            if isinstance(results, dict):
                choices = results.get("choices", [])
                if choices:
                    reply = choices[0].get("message", {}).get("content")
            if not reply or not isinstance(reply, str):
                raise ValueError("invalid chatbot response")

            message.reply_text(reply)
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 0
            error_body = exc.response.text[:500] if exc.response is not None else ""
            LOGGER.warning("OpenAI chatbot HTTP %s: %s", status_code, error_body)
            if status_code in (401, 403):
                message.reply_text("OpenAI API key is invalid or not active in Render.")
            elif status_code == 429:
                message.reply_text("OpenAI quota or rate limit reached. Check billing and try again later.")
            elif status_code == 400:
                message.reply_text("OpenAI rejected the chatbot request. Check the model and API key project settings.")
            else:
                message.reply_text("OpenAI chatbot is temporarily unavailable. Please try again later.")
        except (requests.RequestException, ValueError, TypeError, KeyError):
            message.reply_text("OpenAI chatbot is temporarily unavailable. Please try again later.")


__help__ = f"""
*{BOT_NAME} has an chatbot whic provides you a seemingless chatting experience :*

 »  /chatbot *:* Shows chatbot control panel
"""

__mod_name__ = "Cʜᴀᴛʙᴏᴛ"


CHATBOTK_HANDLER = CommandHandler("chatbot", fallen)
ADD_CHAT_HANDLER = CallbackQueryHandler(fallenadd, pattern=r"add_chat")
RM_CHAT_HANDLER = CallbackQueryHandler(fallenrm, pattern=r"rm_chat")
CHATBOT_HANDLER = MessageHandler(
    Filters.text
    & (~Filters.regex(r"^#[^\s]+") & ~Filters.regex(r"^!") & ~Filters.regex(r"^\/")),
    chatbot,
)

dispatcher.add_handler(ADD_CHAT_HANDLER)
dispatcher.add_handler(CHATBOTK_HANDLER)
dispatcher.add_handler(RM_CHAT_HANDLER)
dispatcher.add_handler(CHATBOT_HANDLER)

__handlers__ = [
    ADD_CHAT_HANDLER,
    CHATBOTK_HANDLER,
    RM_CHAT_HANDLER,
    CHATBOT_HANDLER,
]
