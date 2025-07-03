from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from database import db, cursor, refresh_connection
from utils import format_price
import os
import requests
import logging
from datetime import datetime

PAYMENT_URL = os.getenv("PAYMENT_SERVICE_URL")

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = context.application.user_data.get(user_id, {})

    if not session.get("logged_in"):
        await query.message.reply_text("🔐 ابتدا باید وارد شوید.")
        return

    try:
        prod_id = int(query.data.replace("addcart_", ""))
        cart = session.get("cart", {})
        quantity = cart.get(prod_id, 0)

        cursor.execute("SELECT limited FROM products WHERE id = %s", (prod_id,))
        row = cursor.fetchone()
        if not row:
            await query.message.reply_text("❌ محصول یافت نشد.")
            return
        limit = row[0]

        if limit and quantity + 1 > limit:
            await query.message.reply_text(f"🚫 حداکثر تعداد مجاز: {limit}")
            return

        cart[prod_id] = quantity + 1
        session["cart"] = cart
        context.application.user_data[user_id] = session

        cursor.execute("SELECT id FROM users WHERE email = %s", (session.get("user_email"),))
        user_row = cursor.fetchone()
        if user_row:
            uid = user_row[0]
            now = datetime.now()
            cursor.execute("""
                INSERT INTO reservations (user_id, product_id, quantity, reserved_at)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE quantity = %s, reserved_at = %s
            """, (uid, prod_id, quantity + 1, now, quantity + 1, now))
            db.commit()

        await query.message.reply_text("🛒 محصول به سبد خرید افزوده شد.")

    except Exception as e:
        logging.error(f"[CART ERROR] {e}")
        refresh_connection()
        await query.message.reply_text("❌ خطا در افزودن به سبد خرید.")

async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = context.application.user_data.get(user_id, {})

    if not session.get("logged_in"):
        await update.message.reply_text("🔐 ابتدا وارد شوید.")
        return

    cart = session.get("cart", {})
    if not cart:
        await update.message.reply_text("🧺 سبد خرید خالی است.")
        return

    try:
        total = 0
        for prod_id, qty in cart.items():
            cursor.execute("SELECT name, price, discount, image_path FROM products WHERE id = %s", (prod_id,))
            row = cursor.fetchone()
            if not row:
                continue
            name, price, discount, image = row
            final = int(price * (1 - discount / 100))
            total += final * qty
            caption = f"🔸 {name}\n📦 تعداد: {qty}\n💰 واحد: {format_price(final)} تومان\n📊 جمع: {format_price(final * qty)}"

            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ حذف", callback_data=f"removecart_{prod_id}")]
            ])
            try:
                if image.startswith("http"):
                    await update.message.reply_photo(photo=image, caption=caption, reply_markup=markup)
                else:
                    with open(f"public/{image}", "rb") as f:
                        await update.message.reply_photo(photo=f, caption=caption, reply_markup=markup)
            except:
                await update.message.reply_text(caption, reply_markup=markup)

        pay_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 پرداخت", callback_data="pay_now")]
        ])
        await update.message.reply_text(f"💵 مجموع کل: {format_price(total)} تومان", reply_markup=pay_btn)

    except Exception as e:
        logging.error(f"[SHOW_CART ERROR] {e}")
        await update.message.reply_text("❌ خطا در نمایش سبد خرید.")
        refresh_connection()

async def remove_from_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = context.application.user_data.get(user_id, {})
    cart = session.get("cart", {})

    try:
        prod_id = int(query.data.replace("removecart_", ""))
        if prod_id in cart:
            del cart[prod_id]
            session["cart"] = cart
            context.application.user_data[user_id] = session
            await query.message.reply_text("🧹 محصول حذف شد.")
        else:
            await query.message.reply_text("⚠️ محصول در سبد یافت نشد.")
    except Exception as e:
        logging.error(f"[REMOVE ERROR] {e}")
        await query.message.reply_text("❌ خطا در حذف محصول.")

async def pay_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = context.application.user_data.get(user_id, {})

    if not session.get("logged_in"):
        await query.message.reply_text("🔐 ابتدا وارد شوید.")
        return

    cart = session.get("cart", {})
    if not cart:
        await query.message.reply_text("🧺 سبد خرید خالی است.")
        return

    try:
        email = session.get("user_email")
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not user:
            await query.message.reply_text("❌ کاربر یافت نشد.")
            return
        uid = user[0]
        subtotal = 0
        products = []

        for prod_id, qty in cart.items():
            cursor.execute("SELECT price, discount FROM products WHERE id = %s", (prod_id,))
            row = cursor.fetchone()
            if not row:
                continue
            price, discount = row
            subtotal += int(price * (1 - discount / 100)) * qty
            products.append({
                "product_id": prod_id,
                "price": int(price),
                "discount": int(discount),
                "quantity": int(qty)
            })

        payload = {
            "user_id": uid,
            "subtotal": subtotal,
            "products": products,
            "chat_id": query.message.chat_id
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(PAYMENT_URL, json=payload, headers=headers)
        data = response.json()

        if response.status_code == 200 and data.get("success"):
            link = data.get("payment_url")
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 رفتن به پرداخت", url=link)]
            ])
            session["cart"] = {}
            context.application.user_data[user_id] = session
            await query.message.reply_text("برای پرداخت روی دکمه کلیک کنید:", reply_markup=markup)
        else:
            await query.message.reply_text(f"❌ خطا در دریافت لینک پرداخت: {data.get('error', 'نامشخص')}")

    except Exception as e:
        logging.error(f"[PAYMENT ERROR] {e}")
        await query.message.reply_text("❌ خطا در ارسال به درگاه پرداخت.")