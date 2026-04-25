from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def show_main_menu(bot, chat_id):
    # إنشاء الأزرار الرئيسية (خلينا العرض 1 حتى تترتب الأزرار بشكل عمودي وأنيق)
    markup = InlineKeyboardMarkup(row_width=1)
    
    btn_create = InlineKeyboardButton("➕ إنشاء كود جديد", callback_data="create_code")
    btn_users = InlineKeyboardButton("👥 إدارة المشتركين", callback_data="manage_users")
    btn_test = InlineKeyboardButton("📈 فحص الاستهلاك المباشر (Live Test)", callback_data="live_speed_test") # 👈 الزر الجديد
    
    markup.add(btn_create, btn_users, btn_test)
    
    # إرسال الرسالة
    bot.send_message(
        chat_id, 
        "مرحباً بك في لوحة تحكم V2Ray (النسخة الاحترافية) ⚙️\nاختر من القائمة أدناه:", 
        reply_markup=markup
    )
