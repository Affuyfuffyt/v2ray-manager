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

# 4. 🔥 الكلب البوليسي (Watchdog): يراقب Xray وإذا طفى يشغله فوراً بالخفاء 🔥
def xray_watchdog():
    xray_bin = "/home/wathfor/xray_core/xray"
    config_path = "/home/wathfor/xray_core/config.json"
    
    # تنظيف مبدئي لأي نسخة معلقة من المحرك القديم
    os.system("pkill -9 xray")
    time.sleep(1)
    
    while True:
        try:
            # يفحص هل Xray يعمل حالياً؟
            subprocess.check_output(["pgrep", "-x", "xray"])
        except subprocess.CalledProcessError:
            # إذا لكاه طافي، يشغله فوراً كـ "ابن" للبوت حتى ميوكف النت
            print("⚠️ Xray Engine is DOWN! Watchdog is restarting it internally...")
            subprocess.Popen([xray_bin, 'run', '-c', config_path])
            print("✅ Xray Engine is UP and running!")
        
        # يفحص حالة المحرك كل 3 ثواني
        time.sleep(3)

# ---------------------------------------------------------
# 5. تشغيل النظام بالكامل
# ---------------------------------------------------------
if __name__ == "__main__":
    print(f"🚀 البوت يعمل الآن للأدمن ID: {config.ADMIN_ID}")
    
    # أول خطوة: تشغيل حارس المحرك (يضمن بقاء الإنترنت شغال والبورت مفتوح)
    watchdog_thread = threading.Thread(target=xray_watchdog, daemon=True)
    watchdog_thread.start()
    
    # نعطي مهلة ثانيتين للمحرك حتى يشتغل براحته قبل لا يدخل المراقب
    time.sleep(2)
    
    # ثاني خطوة: تشغيل مراقب الاستهلاك والسرعة بالخلفية
    monitor_thread = threading.Thread(target=start_quota_monitor, daemon=True)
    monitor_thread.start()
    print("📊 نظام الحارس الشخصي ومراقب الجيجابايت يعمل الآن...")
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ حدث خطأ في البوت: {e}")
