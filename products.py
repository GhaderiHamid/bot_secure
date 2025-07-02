from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import cursor, refresh_connection
from utils import format_price
import logging

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cursor.execute("SELECT id, category_name FROM categories")
        categories = cursor.fetchall()
        if not categories:
            await update.message.reply_text("❌ هیچ دسته‌ای یافت نشد.")
            return

        buttons, row = [], []
        for i, (cat_id, name) in enumerate(categories, 1):
            row.append(InlineKeyboardButton(name, callback_data=f"category_{cat_id}"))
            if i % 3 == 0:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

        markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("📚 لطفاً یک دسته را انتخاب کنید:", reply_markup=markup)

    except Exception as e:
        logging.error(f"[CATEGORY ERROR] {e}")
        refresh_connection()
        await update.message.reply_text("❌ خطا در دریافت دسته‌بندی‌ها.")

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        cat_id = int(query.data.replace("category_", ""))
        context.user_data["category_id"] = cat_id
        context.user_data["page"] = 0
        await send_product_page(update, context, page=0)
    except Exception as e:
        logging.error(f"[SHOW_PRODUCTS ERROR] {e}")
        await query.message.reply_text("❌ خطا در بارگذاری دسته.")

async def send_product_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    try:
        cat_id = context.user_data["category_id"]
        offset = page * 4

        cursor.execute("""
            SELECT id, name, description, image_path, price, discount, quntity
            FROM products
            WHERE category_id = %s
            LIMIT 4 OFFSET %s
        """, (cat_id, offset))
        products = cursor.fetchall()

        if not products:
            await update.effective_chat.send_message("❌ محصولی در این دسته‌بندی یافت نشد.")
            return

        for prod in products:
            prod_id, name, desc, image, price, discount, stock = prod
            final_price = int(price * (1 - discount / 100))
            text = (
                f"🛍 {name}\n📄 {desc}\n"
                f"💰 قیمت: {format_price(price)} تومان\n"
                f"🎯 تخفیف: {discount}%\n"
                f"💵 نهایی: {format_price(final_price)} تومان\n"
            )
            if stock == 0:
                text += "❌ موجودی: تمام شده"
                buttons = [[InlineKeyboardButton("⭐ علاقه‌مندی", callback_data=f"bookmark_{prod_id}")]]
            else:
                buttons = [[
                    InlineKeyboardButton("⭐ علاقه‌مندی", callback_data=f"bookmark_{prod_id}"),
                    InlineKeyboardButton("🛒 سبد خرید", callback_data=f"addcart_{prod_id}")
                ]]
            markup = InlineKeyboardMarkup(buttons)

            try:
                if image.startswith("http"):
                    await update.effective_chat.send_photo(photo=image, caption=text, reply_markup=markup)
                else:
                    with open(f"public/{image}", 'rb') as f:
                        await update.effective_chat.send_photo(photo=f, caption=text, reply_markup=markup)
            except Exception as e:
                await update.effective_chat.send_message(f"{text}\n🚫 خطا در نمایش تصویر.", reply_markup=markup)

        # صفحه‌بندی
        cursor.execute("SELECT COUNT(*) FROM products WHERE category_id = %s", (cat_id,))
        total = cursor.fetchone()[0]

        nav_buttons = []
        if offset + 4 < total:
            nav_buttons.append(InlineKeyboardButton("⏭ بعدی", callback_data="next_page"))
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⏮ قبلی", callback_data="prev_page"))

        if nav_buttons:
            markup = InlineKeyboardMarkup([nav_buttons])
            await update.effective_chat.send_message("⬇️ محصولات بیشتر:", reply_markup=markup)

    except Exception as e:
        logging.error(f"[PRODUCT PAGE ERROR] {e}")
        refresh_connection()
        await update.effective_chat.send_message("❌ خطا در نمایش محصولات.")

async def paginate_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    page = context.user_data.get("page", 0)
    if query.data == "next_page":
        page += 1
    elif query.data == "prev_page" and page > 0:
        page -= 1

    context.user_data["page"] = page
    await send_product_page(update, context, page)