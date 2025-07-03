from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from database import cursor, refresh_connection
from utils import format_price
import jdatetime
import logging

async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = context.application.user_data.get(user_id, {})

    if not session.get("logged_in"):
        await update.message.reply_text("🔐 ابتدا باید وارد شوید.")
        return

    session["orders_page"] = 0
    context.application.user_data[user_id] = session
    await send_orders_page(update, context, page=0)

async def send_orders_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    try:
        user_id = update.effective_user.id
        session = context.application.user_data.get(user_id, {})

        email = session.get("user_email")
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        if not row:
            await update.message.reply_text("❌ کاربر یافت نشد.")
            return
        db_user_id = row[0]

        cursor.execute("SELECT id, status, created_at FROM orders WHERE user_id = %s ORDER BY id DESC", (db_user_id,))
        orders = cursor.fetchall()

        if not orders:
            await update.message.reply_text("📭 شما هنوز سفارشی ثبت نکرده‌اید.")
            return

        page_size = 4
        start = page * page_size
        end = start + page_size
        selected_orders = orders[start:end]

        status_map = {
            "processing": "در حال پردازش",
            "shipped": "ارسال شده",
            "delivered": "تحویل شده",
            "returned": "مرجوع شده",
            "return_requested": "درخواست مرجوعی",
            "return_rejected": "رد درخواست مرجوعی",
        }

        for order_id, status, created_at in selected_orders:
            status_fa = status_map.get(status.lower(), status)
            date_str = jdatetime.date.fromgregorian(date=created_at.date()).strftime('%Y/%m/%d')

            cursor.execute("""
                SELECT p.name, od.quantity, od.price, p.image_path
                FROM order_details od
                JOIN products p ON p.id = od.product_id
                WHERE od.order_id = %s
            """, (order_id,))
            details = cursor.fetchall()

            total = 0
            lines = []
            images = []
            for name, qty, price, img in details:
                line_total = price * qty
                total += line_total
                lines.append(f"🔸 {name} × {qty} → {format_price(line_total)} تومان")
                images.append((name, img))

            msg = (
                f"🧾 سفارش #{order_id}\n"
                f"📅 تاریخ: {date_str}\n"
                f"🚚 وضعیت: {status_fa}\n\n"
                + "\n".join(lines) +
                f"\n\n💰 جمع کل سفارش: {format_price(total)} تومان"
            )

            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("📷 تصاویر محصولات", callback_data=f"orderimgs_{order_id}")]
            ])

            await update.effective_chat.send_message(msg, reply_markup=reply_markup)
            session.setdefault("order_images", {})[str(order_id)] = images

        # صفحه‌بندی
        nav_buttons = []
        if end < len(orders):
            nav_buttons.append(InlineKeyboardButton("⏭ بعدی", callback_data="orders_next"))
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⏮ قبلی", callback_data="orders_prev"))
        if nav_buttons:
            await update.effective_chat.send_message("⬇️ پیمایش سفارش‌ها:", reply_markup=InlineKeyboardMarkup([nav_buttons]))

        session["orders_page"] = page
        context.application.user_data[user_id] = session

    except Exception as e:
        logging.error(f"[ORDERS ERROR] {e}")
        refresh_connection()
        await update.effective_chat.send_message("❌ خطا در نمایش سفارش‌ها.")

async def paginate_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    session = context.application.user_data.get(user_id, {})
    page = session.get("orders_page", 0)

    if query.data == "orders_next":
        page += 1
    elif query.data == "orders_prev" and page > 0:
        page -= 1

    session["orders_page"] = page
    context.application.user_data[user_id] = session
    await send_orders_page(update, context, page)

async def order_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    session = context.application.user_data.get(user_id, {})
    order_id = query.data.split("_")[1]
    images = session.get("order_images", {}).get(order_id)

    if not images:
        await query.message.reply_text("❌ تصویری برای این سفارش ذخیره نشده.")
        return

    for name, image_path in images:
        try:
            if image_path.startswith("http"):
                await query.message.reply_photo(photo=image_path, caption=name)
            else:
                with open(f"public/{image_path}", "rb") as f:
                    await query.message.reply_photo(photo=f, caption=name)
        except:
            await query.message.reply_text(f"{name}\n🚫 خطا در نمایش تصویر.")