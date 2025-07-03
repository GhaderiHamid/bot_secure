from telegram import Update
from telegram.ext import ContextTypes
from database import db, cursor, refresh_connection
from utils import hash_password, check_password
import logging

STATES = {
    "REGISTER_FIRST_NAME": 1,
    "REGISTER_LAST_NAME": 2,
    "REGISTER_EMAIL": 3,
    "REGISTER_PASSWORD": 4,
    "REGISTER_PHONE": 5,
    "LOGIN_EMAIL": 6,
    "LOGIN_PASSWORD": 7
}

async def start_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📧 لطفاً ایمیل خود را وارد کنید:")
    context.user_data["state"] = STATES["LOGIN_EMAIL"]

async def start_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 نام خود را وارد کنید:")
    context.user_data["state"] = STATES["REGISTER_FIRST_NAME"]

async def auth_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    state = context.user_data.get("state")
    user_id = update.effective_user.id

    try:
        if state == STATES["LOGIN_EMAIL"]:
            context.user_data["email"] = text
            context.user_data["state"] = STATES["LOGIN_PASSWORD"]
            await update.message.reply_text("🔐 حالا رمز عبور را وارد کنید:")

        elif state == STATES["LOGIN_PASSWORD"]:
            email = context.user_data.get("email")
            password = text

            refresh_connection()
            cursor.execute("SELECT password FROM users WHERE email = %s", (email,))
            result = cursor.fetchone()

            if result and check_password(password, result[0]):
                context.application.user_data[user_id] = {
                    "logged_in": True,
                    "user_email": email
                }
                await update.message.reply_text("✅ ورود موفقیت‌آمیز بود!")
            else:
                await update.message.reply_text("❌ ایمیل یا رمز عبور اشتباه است.")

            context.user_data.clear()

        elif state == STATES["REGISTER_FIRST_NAME"]:
            context.user_data["first_name"] = text
            context.user_data["state"] = STATES["REGISTER_LAST_NAME"]
            await update.message.reply_text("📛 نام خانوادگی را وارد کنید:")

        elif state == STATES["REGISTER_LAST_NAME"]:
            context.user_data["last_name"] = text
            context.user_data["state"] = STATES["REGISTER_EMAIL"]
            await update.message.reply_text("📧 ایمیل را وارد کنید:")

        elif state == STATES["REGISTER_EMAIL"]:
            context.user_data["email"] = text
            context.user_data["state"] = STATES["REGISTER_PASSWORD"]
            await update.message.reply_text("🔒 رمز عبور را وارد کنید:")

        elif state == STATES["REGISTER_PASSWORD"]:
            context.user_data["password"] = text
            context.user_data["state"] = STATES["REGISTER_PHONE"]
            await update.message.reply_text("📱 شماره تلفن را وارد کنید:")

        elif state == STATES["REGISTER_PHONE"]:
            phone = text
            first = context.user_data["first_name"]
            last = context.user_data["last_name"]
            email = context.user_data["email"]
            password = hash_password(context.user_data["password"])

            refresh_connection()
            cursor.execute(
                "INSERT INTO users (first_name, last_name, email, password, phone) VALUES (%s, %s, %s, %s, %s)",
                (first, last, email, password, phone)
            )
            db.commit()

            await update.message.reply_text("✅ ثبت‌نام با موفقیت انجام شد!")
            context.user_data.clear()

    except Exception as e:
        logging.error(f"[AUTH ERROR] {e}")
        await update.message.reply_text("❌ خطا در عملیات ورود یا ثبت‌نام.")
        refresh_connection()
        context.user_data.clear()