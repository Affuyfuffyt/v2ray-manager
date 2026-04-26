import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def show_main_menu(bot, chat_id):
    # إنشاء لوحة المفاتيح الشفافة
    markup = InlineKeyboardMarkup(row_width=1)
    
    # الأزرار مالتك (نفسها اللي بالصورة بالضبط)
    btn_create = InlineKeyboardButton("➕ إنشاء كود جديد", callback_data="add_user")
    btn_manage = InlineKeyboardButton("👥 إدارة المشتركين", callback_data="manage_users")
    btn_speed = InlineKeyboardButton("📈 فحص الاستهلاك المباشر (Live Test)", callback_data="speed_test")
    
    # 🌟 الزر الجديد مالتنا (حالة الخادم)
    btn_server = InlineKeyboardButton("🖥️ حالة الخادم", callback_data="server_status")
    
    # إضافة الأزرار للوحة
    markup.add(btn_create)
    markup.add(btn_manage)
    markup.add(btn_speed)
    markup.add(btn_server)
    
    # إرسال الرسالة
    welcome_text = "⚙️ مرحباً بك في لوحة تحكم V2Ray (النسخة الاحترافية)\nاختر من القائمة أدناه:"
    bot.send_message(chat_id, welcome_text, reply_markup=markup)
