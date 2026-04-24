from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def show_main_menu(bot, chat_id):
    # إنشاء الأزرار الرئيسية
    markup = InlineKeyboardMarkup(row_width=2)
    btn_users = InlineKeyboardButton("👥 إدارة المشتركين", callback_data="manage_users")
    btn_create = InlineKeyboardButton("➕ إنشاء كود جديد", callback_data="create_code")
    markup.add(btn_users, btn_create)
    
    # إرسال الرسالة
    bot.send_message(
        chat_id, 
        "مرحباً بك في لوحة تحكم V2Ray (النسخة الاحترافية) ⚙️\nاختر من القائمة أدناه:", 
        reply_markup=markup
    )
