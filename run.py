import telebot
import os
from dotenv import load_dotenv
from handlers import create_flow, manage_flow
from database import db

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

bot = telebot.TeleBot(TOKEN)
db.init_db() # تشغيل قاعدة البيانات

# 🛡️ فلتر حماية: يمنع أي شخص غيرك من استخدام البوت
class IsAdmin(telebot.custom_filters.SimpleCustomFilter):
    key='is_admin'
    def check(self, message):
        return message.chat.id == ADMIN_ID

bot.add_custom_filter(IsAdmin())

@bot.message_handler(commands=['start'], is_admin=True)
def main_menu(message):
    # هنا يتم استدعاء الأزرار من ملفات الـ handlers
    create_flow.show_main_menu(bot, message.chat.id)

# تشغيل البوت
if __name__ == "__main__":
    print("Bot is running securely...")
    bot.infinity_polling()
