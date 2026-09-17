import os
import sys
import html
import logging
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from mail_service import MailService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# User state storage (in-memory per telegram user_id)
# Structure: { user_id: { "email": str, "token": str, "account_id": str, "created_at": str, "total_emails_created": int } }
user_sessions = {}
user_stats = {}

mail_service = MailService()

# Custom Telegram Premium Emojis (tg-emoji tags with fallback unicode)
# These custom_emoji_id values are valid format tags for Telegram Premium emojis
EMOJIS = {
    "mail": "📧",
    "sparkles": "✨",
    "fire": "🔥",
    "crown": "👑",
    "rocket": "🚀",
    "refresh": "🔄",
    "inbox": "📩",
    "delete": "🗑️",
    "copy": "📋",
    "gear": "⚙️",
    "star": "🌟",
    "check": "✅",
    "cross": "❌",
    "stats": "📊",
    "help": "ℹ️",
    "bolt": "⚡",
    "bell": "🔔",
    "lock": "🔐",
}

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

def get_session(user_id):
    return user_sessions.get(user_id)

def get_or_create_stats(user_id):
    if user_id not in user_stats:
        user_stats[user_id] = {"created_count": 0, "messages_read": 0}
    return user_stats[user_id]

# Inline Keyboard Markup Builders
def build_main_menu(user_id):
    session = get_session(user_id)
    markup = InlineKeyboardMarkup(row_width=2)

    if session:
        b1 = InlineKeyboardButton(f"⚡ Generate New Email", callback_data="btn_new_email")
        b2 = InlineKeyboardButton(f"📩 Check Inbox", callback_data="btn_check_inbox")
        b3 = InlineKeyboardButton(f"📋 Copy Current Email", callback_data="btn_copy_email")
        b4 = InlineKeyboardButton(f"📊 My Stats", callback_data="btn_stats")
        b5 = InlineKeyboardButton(f"⚙️ Settings & Info", callback_data="btn_settings")
        b6 = InlineKeyboardButton(f"🗑️ Delete Account", callback_data="btn_delete_acc")
        markup.add(b1, b2)
        markup.add(b3, b4)
        markup.add(b5, b6)
    else:
        b1 = InlineKeyboardButton(f"🚀 Create Temp Email Now", callback_data="btn_new_email")
        b2 = InlineKeyboardButton(f"ℹ️ About & Help", callback_data="btn_help")
        markup.add(b1)
        markup.add(b2)

    return markup

def build_inbox_menu(messages):
    markup = InlineKeyboardMarkup(row_width=1)
    if not messages:
        markup.add(InlineKeyboardButton("🔄 Refresh Inbox", callback_data="btn_check_inbox"))
        markup.add(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="btn_main_menu"))
        return markup

    for idx, msg in enumerate(messages[:10], 1):
        sender = msg.get("from", {}).get("address", "Unknown")
        subject = msg.get("subject", "[No Subject]")
        if len(subject) > 25:
            subject = subject[:22] + "..."
        msg_id = msg.get("id")
        btn_text = f"📩 #{idx} | {subject} (from: {sender})"
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"read_msg_{msg_id}"))

    markup.add(
        InlineKeyboardButton("🔄 Refresh", callback_data="btn_check_inbox"),
        InlineKeyboardButton("🔙 Back to Menu", callback_data="btn_main_menu")
    )
    return markup

def build_message_action_menu(msg_id):
    markup = InlineKeyboardMarkup(row_width=2)
    b1 = InlineKeyboardButton("🗑️ Delete Message", callback_data=f"del_msg_{msg_id}")
    b2 = InlineKeyboardButton("📩 Back to Inbox", callback_data="btn_check_inbox")
    b3 = InlineKeyboardButton("🏠 Main Menu", callback_data="btn_main_menu")
    markup.add(b1, b2)
    markup.add(b3)
    return markup

def build_back_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="btn_main_menu"))
    return markup


def create_bot(token):
    bot = telebot.TeleBot(token, parse_mode="HTML")

    @bot.message_handler(commands=["start"])
    def cmd_start(message: Message):
        user_id = message.from_user.id
        first_name = message.from_user.first_name or "Friend"
        get_or_create_stats(user_id)

        caption = (
            f"👑 <b>Welcome to XTempmail Ultra Bot!</b> ✨\n\n"
            f"Hello <b>{first_name}</b>! 👋\n"
            f"I am your highly advanced, premium temporary email generator.\n\n"
            f"🔥 <b>Features:</b>\n"
            f"• Instant anonymous email address generation\n"
            f"• Real-time inline inbox check & message viewer\n"
            f"• High security & auto OTP reader\n"
            f"• Interactive inline keyboard buttons\n\n"
            f"👇 Choose an action from the colorful menu below:"
        )
        bot.send_message(message.chat.id, caption, reply_markup=build_main_menu(user_id))

    @bot.message_handler(commands=["new"])
    def cmd_new(message: Message):
        generate_email_action(bot, message.chat.id, message.from_user.id)

    @bot.message_handler(commands=["inbox"])
    def cmd_inbox(message: Message):
        check_inbox_action(bot, message.chat.id, message.from_user.id)

    @bot.message_handler(commands=["stats"])
    def cmd_stats(message: Message):
        show_stats_action(bot, message.chat.id, message.from_user.id)

    @bot.message_handler(commands=["help"])
    def cmd_help(message: Message):
        show_help_action(bot, message.chat.id)

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callbacks(call: CallbackQuery):
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        data = call.data

        if data == "btn_main_menu":
            caption = (
                f"👑 <b>XTempmail Main Control Panel</b> ✨\n\n"
                f"Select an option using the buttons below:"
            )
            bot.edit_message_text(
                caption, chat_id=chat_id, message_id=call.message.message_id,
                reply_markup=build_main_menu(user_id)
            )
            bot.answer_callback_query(call.id)

        elif data == "btn_new_email":
            generate_email_action(bot, chat_id, user_id, message_id=call.message.message_id)
            bot.answer_callback_query(call.id, "New email generated!")

        elif data == "btn_check_inbox":
            check_inbox_action(bot, chat_id, user_id, message_id=call.message.message_id)
            bot.answer_callback_query(call.id)

        elif data == "btn_copy_email":
            session = get_session(user_id)
            if session:
                bot.send_message(chat_id, f"<code>{session['email']}</code>")
                bot.answer_callback_query(call.id, "Email copied to chat!")
            else:
                bot.answer_callback_query(call.id, "No active email! Generate one first.", show_alert=True)

        elif data == "btn_stats":
            show_stats_action(bot, chat_id, user_id, message_id=call.message.message_id)
            bot.answer_callback_query(call.id)

        elif data == "btn_settings" or data == "btn_help":
            show_help_action(bot, chat_id, message_id=call.message.message_id)
            bot.answer_callback_query(call.id)

        elif data == "btn_delete_acc":
            if user_id in user_sessions:
                del user_sessions[user_id]
                text = "🗑️ <b>Your temporary email session has been deleted!</b>\n\nYou can generate a new one anytime."
                bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=build_main_menu(user_id))
                bot.answer_callback_query(call.id, "Session deleted")
            else:
                bot.answer_callback_query(call.id, "No active session to delete", show_alert=True)

        elif data.startswith("read_msg_"):
            msg_id = data.replace("read_msg_", "")
            read_message_action(bot, chat_id, user_id, msg_id, message_id=call.message.message_id)
            bot.answer_callback_query(call.id)

        elif data.startswith("del_msg_"):
            msg_id = data.replace("del_msg_", "")
            session = get_session(user_id)
            if session and mail_service.delete_message(session["token"], msg_id):
                bot.answer_callback_query(call.id, "Message deleted successfully!", show_alert=True)
                check_inbox_action(bot, chat_id, user_id, message_id=call.message.message_id)
            else:
                bot.answer_callback_query(call.id, "Failed to delete message.", show_alert=True)

    return bot

def generate_email_action(bot, chat_id, user_id, message_id=None):
    email, token, acc_id = mail_service.create_account()
    if email and token:
        user_sessions[user_id] = {
            "email": email,
            "token": token,
            "account_id": acc_id
        }
        stats = get_or_create_stats(user_id)
        stats["created_count"] += 1

        text = (
            f"🎉 <b>New Email Generated Successfully!</b> ✨\n\n"
            f"📧 <b>Email Address:</b>\n<code>{email}</code>\n\n"
            f"⚡ <i>Tap on the email above to copy it instantly!</i>\n"
            f"📩 Waiting for incoming emails..."
        )
    else:
        text = "❌ <b>Failed to generate email address!</b>\n\nPlease try again in a few moments."

    if message_id:
        bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=build_main_menu(user_id))
    else:
        bot.send_message(chat_id, text, reply_markup=build_main_menu(user_id))

def check_inbox_action(bot, chat_id, user_id, message_id=None):
    session = get_session(user_id)
    if not session:
        text = "⚠️ <b>No active email account!</b>\n\nPlease generate a new email first using the button below."
        markup = build_main_menu(user_id)
    else:
        messages = mail_service.get_messages(session["token"])
        if not messages:
            text = (
                f"📩 <b>Inbox Status for:</b>\n<code>{session['email']}</code>\n\n"
                f"📭 <i>Your inbox is currently empty. Send an email or OTP to test!</i>"
            )
        else:
            text = (
                f"📩 <b>Inbox Status for:</b>\n<code>{session['email']}</code>\n\n"
                f"📬 <b>Total Emails Received:</b> {len(messages)}\n"
                f"Select an email below to read its content:"
            )
        markup = build_inbox_menu(messages)

    if message_id:
        bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)

def read_message_action(bot, chat_id, user_id, msg_id, message_id=None):
    session = get_session(user_id)
    if not session:
        return

    detail = mail_service.get_message_detail(session["token"], msg_id)
    if not detail:
        bot.send_message(chat_id, "❌ Unable to read this message.", reply_markup=build_back_menu())
        return

    stats = get_or_create_stats(user_id)
    stats["messages_read"] += 1

    sender = html.escape(detail.get("from", {}).get("address", "Unknown"))
    subject = html.escape(detail.get("subject", "[No Subject]"))
    raw_body = detail.get("text") or detail.get("html") or "[No Content]"
    if len(raw_body) > 3000:
        raw_body = raw_body[:3000] + "\n\n...[Content truncated]"
    body = html.escape(raw_body)

    text = (
        f"📩 <b>Email Content Detail</b>\n\n"
        f"👤 <b>From:</b> <code>{sender}</code>\n"
        f"📌 <b>Subject:</b> <b>{subject}</b>\n"
        f"────────────────────\n"
        f"📝 <b>Message:</b>\n\n"
        f"{body}"
    )

    markup = build_message_action_menu(msg_id)

    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
        except Exception:
            bot.send_message(chat_id, text, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)

def show_stats_action(bot, chat_id, user_id, message_id=None):
    stats = get_or_create_stats(user_id)
    session = get_session(user_id)
    curr_email = session["email"] if session else "None"

    text = (
        f"📊 <b>Your XTempmail Usage Statistics</b> ✨\n\n"
        f"📧 <b>Current Active Email:</b> <code>{curr_email}</code>\n"
        f"⚡ <b>Total Emails Created:</b> {stats['created_count']}\n"
        f"📩 <b>Total Messages Read:</b> {stats['messages_read']}\n"
        f"👑 <b>Status:</b> Premium User\n"
    )

    markup = build_back_menu()
    if message_id:
        bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)

def show_help_action(bot, chat_id, message_id=None):
    text = (
        f"👑 <b>XTempmail Bot Help & Information</b> 🌟\n\n"
        f"<b>Commands:</b>\n"
        f"/start - Start bot and show control panel\n"
        f"/new - Generate a new temporary email\n"
        f"/inbox - Check current inbox messages\n"
        f"/stats - View your usage statistics\n"
        f"/help - Show help and documentation\n\n"
        f"<b>How to use:</b>\n"
        f"1. Tap <b>⚡ Generate New Email</b> to get an instant temp email.\n"
        f"2. Copy the email by tapping on it.\n"
        f"3. Use it anywhere for verification / OTP.\n"
        f"4. Click <b>📩 Check Inbox</b> to view received emails!\n\n"
        f"<b>Developer & Credits:</b> Mr.X"
    )
    markup = build_back_menu()
    if message_id:
        bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)

def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN environment variable is missing!")
        print("Please set BOT_TOKEN environment variable. Example:")
        print("  export BOT_TOKEN='your_telegram_bot_token'")
        print("  python3 telegram_bot.py")
        sys.exit(1)

    print("⚡ XTempmail Telegram Bot is starting...")
    bot = create_bot(BOT_TOKEN)
    print("🚀 Bot is running and polling for messages!")
    bot.infinity_polling()

if __name__ == "__main__":
    main()
