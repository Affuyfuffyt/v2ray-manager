from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_active_users, get_radar_data
import time
from datetime import datetime

def register_radar_handlers(bot):
    @bot.callback_query_handler(func=lambda call: call.data == "radar_status")
    def show_radar(call):
        chat_id = call.message.chat.id
        
        # جلب كل المشتركين من الداتا بيس
        active_users = get_active_users()
        
        online_users = []
        today_users = []
        offline_users = []
        
        now = datetime.now()
        
        for user in active_users:
            email = user[0]
            # جلب معلومات الرادار الخاصة بالمشترك
            radar = get_radar_data(email)
            last_seen_str = radar.get("last_seen")
            total_sec = radar.get("total_seconds", 0)
            
            # تحويل الثواني الكلية إلى ساعات ودقائق للترتيب
            hours = total_sec // 3600
            minutes = (total_sec % 3600) // 60
            time_spent = f"{int(hours)}h {int(minutes)}m" if hours > 0 else f"{int(minutes)}m"
            
            if not last_seen_str:
                offline_users.append(f"👤 `{email}` - 👁️ لم يتصل أبداً")
                continue
                
            last_seen_dt = datetime.strptime(last_seen_str, "%Y-%m-%d %H:%M:%S")
            diff = (now - last_seen_dt).total_seconds()
            
            # إذا متصل آخر 120 ثانية (دقيقتين) نعتبره "متصل الآن"
            if diff <= 120:
                online_users.append(f"🟢 `{email}`\n└ ⏱️ مجموع اتصاله: {time_spent}")
            # إذا متصل خلال آخر 24 ساعة
            elif diff <= 86400:
                hours_ago = int(diff // 3600)
                mins_ago = int((diff % 3600) // 60)
                ago_str = f"قبل {hours_ago} ساعة و {mins_ago} دقيقة" if hours_ago > 0 else f"قبل {mins_ago} دقيقة"
                today_users.append(f"🟡 `{email}`\n└ 👁️ آخر ظهور: {ago_str}")
            # أكثر من 24 ساعة
            else:
                days_ago = int(diff // 86400)
                offline_users.append(f"🔴 `{email}`\n└ 👁️ آخر ظهور: قبل {days_ago} يوم")

        # ترتيب الرسالة
        text = "📡 **رادار السيرفر (المراقبة الحية)**\n━━━━━━━━━━━━━━━\n\n"
        
        if online_users:
            text += "🟢 **متصل الآن:**\n" + "\n".join(online_users) + "\n\n"
        if today_users:
            text += "🟡 **كان متصل اليوم:**\n" + "\n".join(today_users) + "\n\n"
        if offline_users:
            text += "🔴 **غير متصل (خامل):**\n" + "\n".join(offline_users) + "\n"
            
        if not online_users and not today_users and not offline_users:
            text += "📭 لا يوجد مشتركون فعالون حالياً."

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔄 تحديث الرادار", callback_data="radar_status"))
        # تعديل رجوع ليتطابق مع زر القائمة الرئيسية في البوت الخاص بك
        markup.add(InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="server_status")) 

        bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
