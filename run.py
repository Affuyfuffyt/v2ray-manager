import telebot
import threading
import config
from xray_core.panel_api import PanelAPI
from handlers import admin_start, create_flow, manage_flow
from quota_monitor import start_quota_monitor # 👈 استدعاء عداد الجيجات

# 1. تهيئة البوت والـ API
bot = telebot.TeleBot(config.BOT_TOKEN)
api = PanelAPI()

# 2. إضافة فلتر الحماية (للأدمن فقط)
class IsAdmin(telebot.custom_filters.SimpleCustomFilter):
    key = 'is_admin'
    def check(self, message):
        return message.chat.id == config.ADMIN_ID

bot.add_custom_filter(IsAdmin())

# 3. تسجيل معالجات الأزرار والرسائل (Handlers)
create_flow.register_create_handlers(bot)
manage_flow.register_manage_handlers(bot)

@bot.message_handler(commands=['start'], is_admin=True)
def start(message):
    admin_start.show_main_menu(bot, message.chat.id)

# ---------------------------------------------------------
# 4. تشغيل البوت وعداد الجيجات
# ---------------------------------------------------------
if __name__ == "__main__":
    print(f"🚀 البوت يعمل الآن للأدمن ID: {config.ADMIN_ID}")
    
    # 👈 تشغيل مراقب الاستهلاك (الكوتا) في خيط منفصل
    monitor_thread = threading.Thread(target=start_quota_monitor, daemon=True)
    monitor_thread.start()
    print("📊 نظام حساب الجيجابايت (الكوتا) يعمل الآن بالخلفية...")
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ حدث خطأ في البوت: {e}")
