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
API_SERVER = '127.0.0.1:10085'

def start_quota_monitor():
    api = PanelAPI()
    print(f"⏱️ Monitor Started (Time & Quota) on {API_SERVER}...")
    
    while True:
        time.sleep(3) 
        try:
            # 1. جلب الإحصائيات المباشرة
            cmd = f"{XRAY_BIN} api statsquery -server={API_SERVER} -reset=true"
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=5).decode('utf-8')
            
            db = load_db()
            db_changed = False
            current_down = 0
            current_up = 0
            
            # 2. تحديث استهلاك البيانات وحساب السرعة
            if result.strip():
                stats = json.loads(result)
                stat_list = stats.get('stat', [])
                for stat in stat_list:
                    name = stat.get('name', '')
                    value = int(stat.get('value', 0))
                    if value == 0: continue
                    
                    if 'downlink' in name: current_down += value
                    if 'uplink' in name: current_up += value
                        
                    if 'user>>>' in name and '>>>traffic>>>' in name:
                        email = name.split('>>>')[1]
                        if email in db:
                            db[email]['used_bytes'] = db[email].get('used_bytes', 0) + value
                            db_changed = True

            # 3. 🚨 العقل المدبر (فحص الوقت والجيجات لجميع المشتركين)
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
                        print(f"🚫 تم القطع عن: {email} بسبب انتهاء {reason}")
                        db[email]['is_active'] = False
                        api.change_client_status(email, enable=False)
                        db_changed = True
                        
            if db_changed:
                update_db(db)
                
            # حفظ السرعة الحالية
            with open(SPEED_FILE, 'w') as f:
                json.dump({'down_bps': current_down // 3, 'up_bps': current_up // 3}, f)
                
        except Exception as e:
            # إذا صار إيرور راح ينحفظ بملف حتى نعرف الخلل وين بالضبط
            error_msg = str(e)
            if hasattr(e, 'output'):
                error_msg += f"\nOutput: {e.output.decode('utf-8')}"
            with open(ERROR_LOG, 'w') as f:
                f.write(error_msg)
            pass
