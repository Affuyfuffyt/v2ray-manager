import time
import subprocess
import json
import os
from database import load_db, update_db
from xray_core.panel_api import PanelAPI

# مسارات كاملة لتجنب مشاكل الاستضافة
SPEED_FILE = '/home/wathfor/v2ray_manager/live_speed.json'
ERROR_LOG = '/home/wathfor/v2ray_manager/monitor_error.log'
XRAY_BIN = '/home/wathfor/xray_core/xray'

# 🔥 التحديث السحري (Unix Domain Socket) 🔥
# نستخدم مسار الملف الفيزيائي بدلاً من IP والبورت لضمان تخطي حظر الاستضافة
API_SERVER = 'unix:///home/wathfor/xray_core/api.sock'

def start_quota_monitor():
    api = PanelAPI()
    print(f"⏱️ Monitor Started via UNIX SOCKET on {API_SERVER}...")
    
    while True:
        time.sleep(3) 
        
        # ==========================================
        # 1. نظام العيون: جلب الإحصائيات المباشرة
        # ==========================================
        try:
            # تنفيذ أمر جلب الإحصائيات عبر ملف السوكت
            cmd = f"{XRAY_BIN} api statsquery -server={API_SERVER} -reset=true"
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=5).decode('utf-8')
            
            current_down = 0
            current_up = 0
            
            if result.strip():
                stats = json.loads(result)
                stat_list = stats.get('stat', [])
                
                db = load_db()
                db_changed = False
                
                for stat in stat_list:
                    name = stat.get('name', '')
                    value = int(stat.get('value', 0))
                    if value == 0: continue
                    
                    if 'downlink' in name: current_down += value
                    if 'uplink' in name: current_up += value
                        
                    if 'user>>>' in name and '>>>traffic>>>' in name:
                        email = name.split('>>>')[1]
                        if email in db:
                            # تحديث استهلاك المستخدم بالبايتات الجديدة
                            db[email]['used_bytes'] = db[email].get('used_bytes', 0) + value
                            db_changed = True
                            
                if db_changed:
                    update_db(db)
                    
            # حفظ السرعة المباشرة للسيرفر ليتم عرضها في البوت
            with open(SPEED_FILE, 'w') as f:
                json.dump({'down_bps': current_down // 3, 'up_bps': current_up // 3}, f)
                
        except subprocess.CalledProcessError as e:
            # تسجيل الخطأ إذا فشل الاتصال بالسوكت
            with open(ERROR_LOG, 'a') as f:
                f.write(f"\n[Stats Error] {e.output.decode('utf-8')}")
        except Exception as e:
            pass

        # ==========================================
        # 2. العقل المدبر القاسي: فحص الوقت والحدود والطرد
        # ==========================================
        try:
            db = load_db()
            db_changed = False
            current_time = time.time()
            
            for email, user_data in list(db.items()):
                if user_data.get('is_active', True):
                    limit = user_data.get('limit_bytes', 0)
                    used = user_data.get('used_bytes', 0)
                    expiry = user_data.get('expiry_time', 0)
                    
                    expired_by_quota = (limit > 0 and used >= limit)
                    expired_by_time = (expiry > 0 and current_time >= expiry)
                    
                    if expired_by_quota or expired_by_time:
                        reason = "الوقت ⏱️" if expired_by_time else "الجيجات 📊"
                        print(f"🚫 تم القطع التلقائي عن: {email} بسبب انتهاء {reason}")
                        
                        # تعطيل الحساب في الداتابيس وفي سيرفر Xray
                        db[email]['is_active'] = False
                        api.change_client_status(email, enable=False)
                        db_changed = True
                        
            if db_changed:
                update_db(db)
                
        except Exception as e:
            pass
