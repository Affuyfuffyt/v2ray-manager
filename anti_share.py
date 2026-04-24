import time
import os
from database import load_db, update_db
from xray_core.panel_api import PanelAPI

LOG_PATH = os.path.expanduser('~/xray_core/access.log')

def start_monitor():
    api = PanelAPI()
    print("🛡️ Anti-Share Monitor Started...")
    
    while True:
        # 1. السكربت يرتاح 10 ثواني حتى ما يثقل السيرفر (طلبك الأول)
        time.sleep(10)
        
        if not os.path.exists(LOG_PATH):
            # إنشاء الملف إذا ما موجود
            open(LOG_PATH, 'w').close()
            continue
            
        # 2. قراءة منو متصل هسه
        with open(LOG_PATH, 'r') as f:
            lines = f.readlines()
            
        # 3. تفرغ الملف فوراً حتى ما ينترس السيرفر وينحظر
        open(LOG_PATH, 'w').close()
        
        db = load_db()
        active_ips = {}
        
        # 4. فرز الـ IP لكل مشترك
        for line in lines:
            if 'accepted' in line and 'email:' in line:
                try:
                    parts = line.split()
                    email_idx = parts.index('email:') + 1
                    email = parts[email_idx]
                    ip = parts[2].split(':')[0] # استخراج الـ IP
                    
                    if email not in active_ips:
                        active_ips[email] = set()
                    active_ips[email].add(ip)
                except:
                    continue
                    
        # 5. الطرد وتطبيق العقوبة (20 ثانية)
        db_changed = False
        for email, ips in active_ips.items():
            if email in db:
                limit = db[email].get('limit', 0)
                # إذا مسجل أكثر من جهاز وعدد الـ IPs الفعلي أكبر من المسموح
                if limit > 0 and len(ips) > limit:
                    print(f"🚨 طرد {email}! أجهزة: {len(ips)}، المسموح: {limit}")
                    api.change_client_status(email, enable=False)
                    # معاقبة المشترك بإيقاف النت لمدة 20 ثانية (طلبك الثاني)
                    db[email]['banned_until'] = time.time() + 20
                    db_changed = True
                    
        # 6. فك الحظر عن اللي خلصت فترة طردهم (20 ثانية)
        for email, data in db.items():
            if data.get('banned_until', 0) > 0 and time.time() > data['banned_until']:
                print(f"✅ فك الحظر عن {email}")
                api.change_client_status(email, uuid=data['uuid'], enable=True)
                data['banned_until'] = 0
                db_changed = True
                
        if db_changed:
            update_db(db)
