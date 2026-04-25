import telebot
import threading
import config
import os
import subprocess
import time
from xray_core.panel_api import PanelAPI
from handlers import admin_start, create_flow, manage_flow, speed_test
from quota_monitor import start_quota_monitor

# 1. تهيئة البوت والـ API
bot = telebot.TeleBot(config.BOT_TOKEN)
api = PanelAPI()

# 2. إضافة فلتر الحماية (للأدمن فقط)
class IsAdmin(telebot.custom_filters.SimpleCustomFilter):
    key = 'is_admin'
    def check(self, message):
        return message.chat.id == config.ADMIN_ID

bot.add_custom_filter(IsAdmin())

# 3. تسجيل المعالجات (Handlers) لجميع الأقسام
create_flow.register_create_handlers(bot)
manage_flow.register_manage_handlers(bot)
speed_test.register_speed_handlers(bot)

@bot.message_handler(commands=['start'], is_admin=True)
def start(message):
    admin_start.show_main_menu(bot, message.chat.id)

# 4. 🔥 الدالة السحرية لتشغيل Xray وجعله جزء من البوت 🔥
def start_xray_engine():
    print("🚀 Starting Xray Engine internally...")
    os.system("pkill -9 xray") # تنظيف أي نسخة معلقة
    time.sleep(1)
    # تشغيل المحرك كـ "ابن" للبوت حتى لا تقتله الاستضافة
    xray_bin = "/home/wathfor/xray_core/xray"
    config_path = "/home/wathfor/xray_core/config.json"
    subprocess.Popen([xray_bin, 'run', '-c', config_path])
    print("✅ Xray Engine is UP and running on port 10085!")

# ---------------------------------------------------------
# 5. تشغيل النظام بالكامل
# ---------------------------------------------------------
if __name__ == "__main__":
    print(f"🚀 البوت يعمل الآن للأدمن ID: {config.ADMIN_ID}")
    
    # أول خطوة: إطلاق محرك الإنترنت الداخلي حتى لا يتم حظره
    start_xray_engine()
    
    # ثاني خطوة: تشغيل مراقب الاستهلاك والسرعة بالخلفية
    monitor_thread = threading.Thread(target=start_quota_monitor, daemon=True)
    monitor_thread.start()
    print("📊 نظام حساب الجيجابايت والسرعة المباشرة يعمل الآن...")
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ حدث خطأ في البوت: {e}")
