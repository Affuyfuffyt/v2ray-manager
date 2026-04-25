import time
import subprocess
import json
import os
from database import load_db, update_db
from xray_core.panel_api import PanelAPI

# مسارات كاملة - تأكد من صحتها في سيرفرك
SPEED_FILE = '/home/wathfor/v2ray_manager/live_speed.json'
ERROR_LOG = '/home/wathfor/v2ray_manager/monitor_error.log'
XRAY_BIN = '/home/wathfor/xray_core/xray'

# استخدام Unix Socket لكسر جدار حماية Alwaysdata
API_SERVER = 'unix:///home/wathfor/xray_core/api.sock'

def start_quota_monitor():
    api = PanelAPI()
    print(f"🕵️‍♂️ نظام المراقبة الاحترافي يعمل الآن عبر: {API_SERVER}")
    
    while True:
        time.sleep(4) # مهلة بسيطة لضمان استقرار القراءة
        
        try:
            # 1. جلب البيانات الخام من المحرك
            cmd = f"{XRAY_BIN} api statsquery -server={API_SERVER} -reset=true"
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=5).decode('utf-8')
            
            current_down = 0
            current_up = 0
            
            if result.strip():
                stats = json.loads(result)
                stat_list = stats.get('stat', [])
                
                db = load_db()
                db_changed = False
                
                # طباعة البيانات للمراقبة (ستراها في سجلات الخدمة بالمنصة)
                if stat_list:
                    print(f"📊 تم رصد {len(stat_list)} سجل إحصائيات...")

                for stat in stat_list:
                    name = stat.get('name', '')
                    value = int(stat.get('value', 0))
                    
                    if value <= 0: continue
                    
                    # حساب السرعة العامة للسيرفر
                    if 'downlink' in name: current_down += value
                    if 'uplink' in name: current_up += value
                    
                    # الفرز الذكي للمستخدمين
                    if 'user>>>' in name and '>>>traffic>>>' in name:
                        # استخراج الإيميل بدقة
                        parts = name.split('>>>')
                        if len(parts) >= 2:
                            email = parts[1]
                            if email in db:
                                db[email]['used_bytes'] = db[email].get('used_bytes', 0) + value
                                db_changed = True
                                print(f"✅ تم تسجيل {value} بايت للمستخدم: {email}")
                            else:
                                # هذا السطر سينقذك إذا كان هناك اختلاف في الأسماء
                                print(f"⚠️ تنبيه: رصد استهلاك لاسم ({email}) لكنه غير موجود بالداتا بيس!")
                            
                if db_changed:
                    update_db(db)
            
            # تحديث ملف السرعة
            with open(SPEED_FILE, 'w') as f:
                json.dump({'down_bps': current_down // 4, 'up_bps': current_up // 4}, f)
                
        except Exception as e:
            with open(ERROR_LOG, 'a') as f:
                f.write(f"\n[{time.ctime()}] Monitor Logic Error: {str(e)}")
            pass

        # 2. نظام الطرد الصارم (وقت + جيجات)
        try:
            db = load_db()
            db_changed = False
            now = time.time()
            
            for email, data in list(db.items()):
                if data.get('is_active', True):
                    limit = data.get('limit_bytes', 0)
                    used = data.get('used_bytes', 0)
                    expiry = data.get('expiry_time', 0)
                    
                    # فحص الصلاحية
                    is_quota_done = (limit > 0 and used >= limit)
                    is_time_done = (expiry > 0 and now >= expiry)
                    
                    if is_quota_done or is_time_done:
                        reason = "الوقت ⏱️" if is_time_done else "البيانات 📊"
                        print(f"🚫 طرد فوري: {email} | السبب: انتهاء {reason}")
                        db[email]['is_active'] = False
                        api.change_client_status(email, enable=False)
                        db_changed = True
            
            if db_changed:
                update_db(db)
        except:
            pass
