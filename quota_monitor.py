import time
import subprocess
import json
import os
from database import load_db, update_db
from xray_core.panel_api import PanelAPI

# ملف صغير لحفظ السرعة الحالية للسيرفر (لكي يقرأها زر التيست)
SPEED_FILE = os.path.expanduser('~/v2ray_manager/live_speed.json')

def start_quota_monitor():
    api = PanelAPI()
    print("📊 Quota Monitor Started (Real-Time Speed Mode)...")
    XRAY_BIN = os.path.expanduser('~/xray_core/xray')
    
    while True:
        # الفحص كل 3 ثواني حتى يعطيك السرعة الحالية بدقة وبدون ما يثقل السيرفر
        time.sleep(3) 
        try:
            cmd = f"{XRAY_BIN} api statsquery -server=127.0.0.1:10085 -reset=true"
            # وضعنا timeout حتى لا يعلّق الكود
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, timeout=2).decode('utf-8')
            
            if not result.strip():
                # إذا لا يوجد استهلاك، نُصفر عداد السرعة
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
                        
                        # القطع الفوري (بالملم)
                        if limit > 0 and db[email]['used_bytes'] >= limit and is_active:
                            print(f"🚫 تم القطع الفوري عن: {email}")
                            db[email]['is_active'] = False
                            api.change_client_status(email, enable=False)
                            
            if db_changed:
                update_db(db)
                
            # حفظ السرعة الحالية (قسمنا على 3 لأن الفحص كل 3 ثواني، لنحصل على بايت/ثانية)
            with open(SPEED_FILE, 'w') as f:
                json.dump({'down_bps': current_down // 3, 'up_bps': current_up // 3}, f)
                
        except Exception as e:
            pass
