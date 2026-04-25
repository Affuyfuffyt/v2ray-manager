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

def start_quota_monitor():
    api = PanelAPI()
    print("📊 Quota Monitor Started (Real-Time Speed Mode)...")
    
    while True:
        time.sleep(3) 
        try:
            cmd = f"{XRAY_BIN} api statsquery -server=127.0.0.1:10085 -reset=true"
            # تسجيل المخرجات لكشف الأخطاء وزيادة وقت الانتظار لـ 5 ثواني
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=5).decode('utf-8')
            
            if not result.strip():
                with open(SPEED_FILE, 'w') as f:
                    json.dump({'down_bps': 0, 'up_bps': 0}, f)
                continue

            stats = json.loads(result)
            stat_list = stats.get('stat', [])
            
            db = load_db()
            db_changed = False
            current_down = 0
            current_up = 0
            
            for stat in stat_list:
                name = stat.get('name', '')
                value = int(stat.get('value', 0))
                if value == 0: continue
                
                # حساب السرعة المباشرة للسيرفر
                if 'downlink' in name: current_down += value
                if 'uplink' in name: current_up += value
                    
                # حساب استهلاك الجيجات للمشتركين والقطع الفوري
                if 'user>>>' in name and '>>>traffic>>>' in name:
                    email = name.split('>>>')[1]
                    if email in db:
                        db[email]['used_bytes'] = db[email].get('used_bytes', 0) + value
                        db_changed = True
                        
                        limit = db[email].get('limit_bytes', 0)
                        is_active = db[email].get('is_active', True)
                        
                        # القطع الفوري
                        if limit > 0 and db[email]['used_bytes'] >= limit and is_active:
                            print(f"🚫 تم القطع الفوري عن: {email}")
                            db[email]['is_active'] = False
                            api.change_client_status(email, enable=False)
                            
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
