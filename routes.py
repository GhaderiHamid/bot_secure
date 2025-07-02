from telegram import Update
from telegram.ext import ContextTypes
from auth import start_login, start_register
from products import show_categories
from cart import show_cart
from orders import show_orders

async def start_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # تبدیل message به ساختار مناسب برای call تابع
    class ProxyMessage:
        def __init__(self, original):
            self.chat = original.chat
            self.from_user = original.from_user
        async def reply_text(self, *args, **kwargs):
            await query.message.reply_text(*args, **kwargs)
        async def reply_photo(self, *args, **kwargs):
            await query.message.reply_photo(*args, **kwargs)

    fake_update = Update(
        update.update_id,
        message=ProxyMessage(query.message)
    )

    if data == "menu_login":
        await start_login(fake_update, context)
    elif data == "menu_register":
        await start_register(fake_update, context)
    elif data == "menu_categories":
        await show_categories(fake_update, context)
    elif data == "menu_cart":
        await show_cart(fake_update, context)
    elif data == "menu_orders":
        await show_orders(fake_update, context)
    elif data == "menu_search":
        await query.message.reply_text("🔎 برای جستجو دستور زیر را بفرست:\n`/search مادربرد`\n(عبارت دلخواه خودت رو جایگزین کن)")