from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from xray_core.panel_api import PanelAPI

api = PanelAPI()

def format_bytes(size):
    # تحويل البايتات إلى ميكا وكيكا بشكل مقروء
    power = 2**10
    n = 0
    power_labels = {0 : 'B', 1: 'MB', 2: 'GB', 3: 'TB'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}"

def register_manage_handlers(bot):

    # 1. زر إظهار قائمة المشتركين
    @bot.callback_query_handler(func=lambda call: call.data == "manage_users")
    def show_users_list(call):
        chat_id = call.message.chat.id
        users = db.get_all_users()
        
        if not users:
            bot.answer_callback_query(call.id, "لا يوجد مشتركين حالياً!")
            return

        markup = InlineKeyboardMarkup(row_width=2)
        for user in users:
            markup.add(InlineKeyboardButton(f"👤 {user}", callback_data=f"user_{user}"))
        
        bot.edit_message_text("👥 قائمة المشتركين:\nاختر مشترك لعرض تفاصيله:", chat_id, call.message.message_id, reply_markup=markup)

    # 2. زر تفاصيل المشترك (الاستهلاك، الحظر، التمديد)
    @bot.callback_query_handler(func=lambda call: call.data.startswith("user_"))
    def show_user_details(call):
        chat_id = call.message.chat.id
        email = call.data.split('_')[1]
        
        # جلب الاستهلاك من السيرفر
        total_used = api.get_client_traffic(email)
        used_today, used_yesterday = db.get_usage_stats(email, total_used)

        details = f"""
📊 **تفاصيل المشترك:** `{email}`
---
📉 **استهلاك البارحة:** `{format_bytes(used_yesterday)}`
📈 **استهلاك اليوم:** `{format_bytes(used_today)}`
📦 **الاستهلاك الكلي:** `{format_bytes(total_used)}`
        """
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("⛔️ حظر / إيقاف", callback_data=f"ban_{email}"),
            InlineKeyboardButton("🔄 تمديد الاشتراك", callback_data=f"extend_{email}"),
            InlineKeyboardButton("🗑️ حذف نهائي", callback_data=f"delete_{email}"),
            InlineKeyboardButton("🔙 رجوع", callback_data="manage_users")
        )
        
        bot.edit_message_text(details, chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # (هنا يمكنك إضافة دوال الحظر والتمديد بنفس طريقة @bot.callback_query_handler)
