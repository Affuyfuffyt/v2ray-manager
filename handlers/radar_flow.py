from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
# استدعاء الدوال الجديدة من ملف db اللي حدثناه
from db import get_active_users, get_full_radar_stats
import time
from datetime import datetime

# دالة ذكية لتحويل الثواني إلى (ساعات، دقائق، ثواني) بشكل مرتب
def format_duration(seconds):
    seconds = int(seconds)
    if seconds == 0:
        return "0 ثانية"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h > 0: parts.append(f"{h} ساعة")
    if m > 0: parts.append(f"{m} دقيقة")
    if s > 0 or not parts: parts.append(f"{s} ثانية")
    return " و ".join(parts)

def register_radar_handlers(bot):
    
    # ==========================================
    # 1️⃣ اللوحة الرئيسية للرادار (عرض الأزرار)
    # ==========================================
    @bot.callback_query_handler(func=lambda call: call.data == "radar_status")
    def show_radar(call):
        chat_id = call.message.chat.id
        
        # جلب كل المشتركين من الداتا بيس
        active_users = get_active_users()
        markup = InlineKeyboardMarkup(row_width=1)
        now = datetime.now()
        
        online_count = 0
        today_count = 0
        offline_count = 0
        
        # نجمع الأزرار في قوائم حتى نرتبهم: المتصلين أولاً، ثم اليوم، ثم الخاملين
        online_btns = []
        today_btns = []
        offline_btns = []
        
        for user in active_users:
            email = user[0]
            # جلب اللوحة الشاملة للمشترك
            stats = get_full_radar_stats(email)
            
            # إذا ماكو بيانات (مشترك جديد لم يتصل بعد)
            if not stats or not stats.get("last_seen"):
                offline_btns.append(InlineKeyboardButton(f"🔴 {email} (خامل)", callback_data=f"ruser_{email}"))
                offline_count += 1
                continue
                
            last_seen_str = stats["last_seen"]
            last_seen_dt = datetime.strptime(last_seen_str, "%Y-%m-%d %H:%M:%S")
            diff = (now - last_seen_dt).total_seconds()
            
            # إذا متصل آخر دقيقتين
            if diff <= 120:
                online_btns.append(InlineKeyboardButton(f"🟢 {email} (متصل الآن)", callback_data=f"ruser_{email}"))
                online_count += 1
            # إذا متصل آخر 24 ساعة
            elif diff <= 86400:
                today_btns.append(InlineKeyboardButton(f"🟡 {email} (نشط اليوم)", callback_data=f"ruser_{email}"))
                today_count += 1
            # أكثر من 24 ساعة
            else:
                offline_btns.append(InlineKeyboardButton(f"🔴 {email} (غير متصل)", callback_data=f"ruser_{email}"))
                offline_count += 1

        # إضافة الأزرار للوحة بالترتيب
        for btn in online_btns: markup.add(btn)
        for btn in today_btns: markup.add(btn)
        for btn in offline_btns: markup.add(btn)

        # النص التوضيحي للوحة
        text = f"📡 **رادار السيرفر المركزي**\n━━━━━━━━━━━━━━━\n"
        text += f"🟢 متصل الآن: {online_count}\n"
        text += f"🟡 نشط اليوم: {today_count}\n"
        text += f"🔴 خامل: {offline_count}\n\n"
        text += "👇 **اضغط على اسم المشترك لعرض لوحته الاستخباراتية:**"

        markup.add(InlineKeyboardButton("🔄 تحديث الرادار", callback_data="radar_status"))
        markup.add(InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="server_status")) 

        bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # ==========================================
    # 2️⃣ اللوحة الاستخباراتية (تفاصيل المشترك عند الضغط عليه)
    # ==========================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ruser_"))
    def show_user_radar_details(call):
        chat_id = call.message.chat.id
        email = call.data.split("ruser_")[1]
        
        stats = get_full_radar_stats(email)
        if not stats:
            bot.answer_callback_query(call.id, "❌ لا توجد بيانات لهذا المشترك حالياً!")
            return
        
        last_seen = stats["last_seen"] or "لم يتصل أبداً"
        
        # حساب حالة الاتصال للجمالية (Emoji)
        status_emoji = "🔴 لم يتصل"
        if stats["last_seen"]:
            now = datetime.now()
            last_seen_dt = datetime.strptime(stats["last_seen"], "%Y-%m-%d %H:%M:%S")
            diff = (now - last_seen_dt).total_seconds()
            
            if diff <= 120:
                status_emoji = "🟢 متصل الآن"
                last_seen = "الآن (نشط)"
            elif diff <= 86400:
                status_emoji = "🟡 كان متصل اليوم"
            else:
                status_emoji = "🔴 غير متصل"

        # ترتيب رسالة التفاصيل
        text = f"🕵️‍♂️ **اللوحة الاستخباراتية للمشترك:** `{email}`\n"
        text += f"━━━━━━━━━━━━━━━━━\n"
        text += f"📡 **حالة الاتصال:** {status_emoji}\n"
        text += f"👁️ **آخر ظهور:** `{last_seen}`\n\n"
        
        text += f"⏳ **إجمالي وقت الاتصال (منذ الإنشاء):**\n└ `{format_duration(stats['total_seconds'])}`\n\n"
        text += f"📅 **وقت الاتصال لليوم:**\n└ `{format_duration(stats['today_seconds'])}`\n"
        text += f"━━━━━━━━━━━━━━━━━\n"
        
        # جلب أرشيف الأيام السابقة
        if stats["history"]:
            text += "🗂️ **أرشيف الأيام السابقة:**\n"
            for record in stats["history"][:7]: # نعرض آخر 7 أيام حتى الرسالة تكون مرتبة
                text += f"▪️ `{record['date']}` ⬅️ {format_duration(record['seconds'])}\n"
        else:
            text += "📭 لا يوجد أرشيف لأيام سابقة."

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔄 تحديث بيانات المشترك", callback_data=f"ruser_{email}"))
        markup.add(InlineKeyboardButton("🔙 رجوع للرادار", callback_data="radar_status"))

        bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
