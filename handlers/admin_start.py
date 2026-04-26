import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def show_main_menu(bot, chat_id):
    # إنشاء لوحة المفاتيح الشفافة (Inline)
    markup = InlineKeyboardMarkup(row_width=1)
    
    # 1. الأزرار الشفافة مالتك (مثل ما ظاهرة بالصورة)
    # ملاحظة: إذا الأزرار القديمة ما اشتغلت، معناها الـ callback_data يختلف بكودك الأصلي
    btn_create = InlineKeyboardButton("➕ إنشاء كود جديد", callback_data="add_user") 
    btn_manage = InlineKeyboardButton("👥 إدارة المشتركين", callback_data="manage_users") 
    btn_speed = InlineKeyboardButton("📈 فحص الاستهلاك المباشر (Live Test)", callback_data="speed_test") 
    
    # 2. الزر الجديد مالتنا
    btn_server_status = InlineKeyboardButton("🖥️ حالة الخادم", callback_data="server_status")
    
    # 3. ترتيب الأزرار بالشاشة (كل زر بسطر)
    markup.add(btn_create)
    markup.add(btn_manage)
    markup.add(btn_speed)
    markup.add(btn_server_status)
    
    # 4. إرسال الرسالة
    welcome_text = "⚙️ مرحباً بك في لوحة تحكم V2Ray (النسخة الاحترافية)\nاختر من القائمة أدناه:"
    bot.send_message(chat_id, welcome_text, reply_markup=markup)
