import os
import logging
from flask import Flask, request
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from dotenv import load_dotenv

# ماژول‌های داخلی
from auth import start_login, start_register, auth_message_handler
from products import show_categories, show_products, paginate_products
from cart import add_to_cart, show_cart, remove_from_cart, pay_cart
from orders import show_orders, paginate_orders, order_images
from routes import start_menu_router

load_dotenv()

# متغیرهای محیطی
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.getenv("PORT", 8443))
RENDER_NAME = os.getenv("RENDER_SERVICE_NAME")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH")

# پیکربندی لاگ
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ساخت ربات
bot_app = ApplicationBuilder().token(TOKEN).build()

# ⬇️ تعریف تمام handlerها
bot_app.add_handler(CommandHandler("start", show_categories))
bot_app.add_handler(CommandHandler("login", start_login))
bot_app.add_handler(CommandHandler("register", start_register))
bot_app.add_handler(CommandHandler("cart", show_cart))
bot_app.add_handler(CommandHandler("orders", show_orders))

bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auth_message_handler))

bot_app.add_handler(CallbackQueryHandler(start_menu_router, pattern="^menu_"))
bot_app.add_handler(CallbackQueryHandler(show_products, pattern="^category_"))
bot_app.add_handler(CallbackQueryHandler(paginate_products, pattern="^(next_page|prev_page)$"))
bot_app.add_handler(CallbackQueryHandler(add_to_cart, pattern="^addcart_"))
bot_app.add_handler(CallbackQueryHandler(remove_from_cart, pattern="^removecart_"))
bot_app.add_handler(CallbackQueryHandler(pay_cart, pattern="^pay_now$"))

bot_app.add_handler(CallbackQueryHandler(paginate_orders, pattern="^orders_(next|prev)$"))
bot_app.add_handler(CallbackQueryHandler(order_images, pattern="^orderimgs_"))

# ساخت اپ Flask برای webhook و health check
app = Flask(__name__)

@app.route('/')
def health():
    return '✅ Bot is alive on Render!', 200

@app.before_request
def log_wakeup():
    logging.info("📡 Webhook request received.")

@app.route(f"/{WEBHOOK_SECRET_PATH}", methods=['POST'])
def webhook():
    return bot_app.update_webhook(request)

# اجرای نهایی webhook
if __name__ == '__main__':
    bot_app.run_webhook(
        listen='0.0.0.0',
        port=PORT,
        url_path=WEBHOOK_SECRET_PATH,
        webhook_url=f"https://{RENDER_NAME}.onrender.com/{WEBHOOK_SECRET_PATH}",
        drop_pending_updates=True
    )