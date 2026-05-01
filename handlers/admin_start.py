import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def show_main_menu(bot, chat_id):
    # إنشاء لوحة المفاتيح الشفافة
    markup = InlineKeyboardMarkup(row_width=1)
    
    # الأزرار الأساسية
    btn_create = InlineKeyboardButton("➕ إنشاء كود جديد", callback_data="create_code")
    btn_manage = InlineKeyboardButton("👥 إدارة المشتركين", callback_data="manage_users")
    
    # 🔥 الزر الجديد: رادار السيرفر 🔥
    btn_radar = InlineKeyboardButton("📡 رادار السيرفر (المتصلين الآن)", callback_data="radar_status")
    
    # الأزرار الباقية
    btn_speed = InlineKeyboardButton("📈 فحص الاستهلاك المباشر (Live Test)", callback_data="speed_test")
    btn_server = InlineKeyboardButton("🖥️ حالة الخادم", callback_data="server_status")
    
    # ترتيب الأزرار في اللوحة
    markup.add(btn_create)
    markup.add(btn_manage)
    markup.add(btn_radar) # إضافة الرادار بالنص حتى يكون بارز
    markup.add(btn_speed)
    markup.add(btn_server)
    
    welcome_text = "⚙️ مرحباً بك في لوحة تحكم V2Ray (النسخة الاحترافية)\nاختر من القائمة أدناه:"
    bot.send_message(chat_id, welcome_text, reply_markup=markup)
