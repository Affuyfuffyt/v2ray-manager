import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

def show_main_menu(bot, chat_id):
    # إنشاء لوحة المفاتيح السفلية وتصغير حجمها ليتناسب مع الشاشة
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # 1. الأزرار الأساسية (نفسها اللي عندك)
    btn_create = KeyboardButton("➕ إنشاء مشترك")
    btn_manage = KeyboardButton("👥 إدارة المشتركين")
    btn_speed = KeyboardButton("🚀 فحص السرعة")
    
    # 2. الزر الجديد مالتنا (لازم يكون اسمه مطابق للشرط بـ run.py)
    btn_server_status = KeyboardButton("🖥️ حالة الخادم")
    
    # 3. ترتيب الأزرار بالشاشة (كل زرين بسطر)
    markup.add(btn_create, btn_manage)
    markup.add(btn_speed, btn_server_status)
    
    # 4. إرسال الرسالة الترحيبية مع الكيبورد الجديد
    welcome_text = "👋 أهلاً بك أيها المدير في لوحة تحكم V2Ray الإحترافية!\n\n👇 اختر الإجراء المطلوب من القائمة بالأسفل:"
    bot.send_message(chat_id, welcome_text, reply_markup=markup)
