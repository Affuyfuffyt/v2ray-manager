import os
import time
import threading
from database import update_radar_data

active_users_cache = set()

def flush_radar_data():
    """
    مهمة هذه الدالة هي حفظ البيانات بالداتا بيس كل 60 ثانية دفعة واحدة
    حتى ما نهلك السيرفر بتحديثات مستمرة (خطة ذكية لتخفيف الضغط)
    """
    while True:
        time.sleep(60)
        if active_users_cache:
            # ناخذ نسخة من المتصلين ونفرغ القاموس
            users_to_update = list(active_users_cache)
            active_users_cache.clear()
            
            for email in users_to_update:
                try:
                    update_radar_data(email)
                except Exception as e:
                    print(f"Radar DB Error: {e}")

def start_radar_monitor():
    """
    وظيفة المراقبة الحية لملفات الـ Access Log
    """
    print("📡 رادار السيرفر بدأ بالمراقبة...")
    
    # تشغيل عملية الحفظ المجدولة
    threading.Thread(target=flush_radar_data, daemon=True).start()
    
    home_dir = os.path.expanduser("~")
    log_path = f"{home_dir}/xray_core/access.log"
    
    # إذا الملف ما موجود، البوت يصنعه
    if not os.path.exists(log_path):
        try: open(log_path, 'a').close()
        except: pass

    with open(log_path, 'r', encoding='utf-8') as f:
        # الذهاب إلى نهاية الملف حتى نقرأ بس المتصلين الجدد (تجاوز القديم)
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
            
            # Xray يكتب 'accepted' من يوافق على اتصال جديد
            if "accepted" in line:
                parts = line.strip().split()
                if parts:
                    # الإيميل (الاسم) دائماً يكون آخر كلمة بالسطر بين قوسين []
                    email = parts[-1].strip("[]")
                    if email and len(email) > 1:
                        # نضيف الاسم للرادار
                        active_users_cache.add(email)
