import time
import subprocess
import json
import os
from database import load_db, update_db
from xray_core.panel_api import PanelAPI

def start_quota_monitor():
    api = PanelAPI()
    print("📊 Quota Monitor Started...")
    
    # مسار تشغيل محرك xray داخل الاستضافة
    XRAY_BIN = os.path.expanduser('~/xray_core/xray')
    
    while True:
        time.sleep(60) # يفحص الاستهلاك كل 60 ثانية
        try:
            # استدعاء API الـ Xray السري لسحب الإحصائيات وتصفيرها برمجياً
            cmd = f"{XRAY_BIN} api statsquery -server=127.0.0.1:10085 -reset=true"
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode('utf-8')
            
            if not result.strip():
                continue

            stats = json.loads(result)
            stat_list = stats.get('stat', [])
            
            db = load_db()
            db_changed = False
            traffic_updates = {}
            
            # 1. جمع الاستهلاك (الرفع + التنزيل)
            for stat in stat_list:
                name = stat.get('name', '')
                value = int(stat.get('value', 0))
                
                # اسم الإحصائية يكون بصيغة: user>>>email>>>traffic>>>downlink
                if 'user>>>' in name and '>>>traffic>>>' in name:
                    email = name.split('>>>')[1]
                    if email not in traffic_updates:
                        traffic_updates[email] = 0
                    traffic_updates[email] += value
            
            # 2. تحديث الداتا بيس وفحص العقوبة
            for email, usage in traffic_updates.items():
                if email in db:
                    db[email]['used_bytes'] = db[email].get('used_bytes', 0) + usage
                    db_changed = True
                    
                    limit = db[email].get('limit_bytes', 0)
                    is_active = db[email].get('is_active', True)
                    
                    # إذا جان عنده حد، وعبر هذا الحد، وهو بعده فعال... اقطعه!
                    if limit > 0 and db[email]['used_bytes'] >= limit and is_active:
                        print(f"🚫 تم انتهاء باقة {email}! سيتم إيقاف اشتراكه.")
                        db[email]['is_active'] = False
                        api.change_client_status(email, enable=False)
                        
            if db_changed:
                update_db(db)
                
        except Exception as e:
            pass # في حال السيرفر ديطفي أو يرستر نتجاهل الخطأ
