import json
import os
import requests
from dotenv import load_dotenv
import time

CONFIG_PATH = '/home/wathfor/xray_core/config.json'

class PanelAPI:
    def __init__(self):
        # تحميل المفاتيح من ملف .env المخفي للاتصال الرسمي بالمنصة
        load_dotenv()
        self.api_key = os.getenv('AD_API_KEY')
        self.site_id = os.getenv('AD_SITE_ID')

    def create_client(self, email, uuid, protocol="vless"):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            # 🔥 تعديل حاسم: إضافة اليوزرات للـ Fallback (المنفذ الرئيسي 8100) ليتم حسابهم 🔥
            # حتى لو كان اتصالهم WS، البورت الرئيسي هو الذي يمسك الترافيك الحقيقي
            main_inbound = 0
            
            if protocol == "vless" or protocol == "vmess":
                new_client = {"id": uuid, "email": email, "level": 0}
            elif protocol == "trojan":
                new_client = {"password": uuid, "email": email, "level": 0} 
            else:
                new_client = {"id": uuid, "email": email, "level": 0}

            # إضافة المشترك للـ Fallback (البوابة الرئيسية)
            clients_main = config['inbounds'][main_inbound]['settings']['clients']
            if not any(c.get('email') == email for c in clients_main):
                clients_main.append(new_client)

            # إضافته للـ WS Inbound الخاص به لكي يعمل الاتصال (كودك الأصلي)
            if protocol == "vless":
                target_inbound = 1
            elif protocol == "vmess":
                target_inbound = 2
            elif protocol == "trojan":
                target_inbound = 3
            else:
                target_inbound = 1
            
            clients_ws = config['inbounds'][target_inbound]['settings']['clients']
            if not any(c.get('email') == email for c in clients_ws):
                clients_ws.append(new_client)
            
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            
            return self.restart_xray()
            
        except Exception as e:
            print(f"Error creating client locally: {e}")
            return False

    def restart_xray(self):
        # 1. الضربة القاضية: نقتل العملية فوراً لقطع النت عن المنتهية صلاحيتهم
        os.system("pkill -9 xray")
        time.sleep(0.5)
        
        # 2. التشغيل القانوني: نطلب من منصة Alwaysdata تشغيل الموقع رسمياً
        # بما أننا حولنا Xray لـ Service، إعادة التشغيل هنا غير ضرورية للخدمة، لكنها مهمة لقتل القديم
        # لأن الـ Service ستقوم بتشغيله تلقائياً بعد أن تقتله أنت.
        return True

    def get_client_traffic(self, email):
        return 0

    def change_client_status(self, email, inbound_id=None, uuid=None, enable=True):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            changed = False
            # البحث في جميع الـ inbounds وحذف المشترك (من الرئيسي والـ WS)
            for i in range(4): # غيرناها لـ 4 لكي تشمل الـ Fallback (0)
                try:
                    clients = config['inbounds'][i]['settings']['clients']
                    if not enable:
                        original_len = len(clients)
                        # حذف المشترك
                        config['inbounds'][i]['settings']['clients'] = [c for c in clients if c.get('email') != email]
                        if len(config['inbounds'][i]['settings']['clients']) != original_len:
                            changed = True
                except Exception:
                    continue
            
            if changed:
                with open(CONFIG_PATH, 'w') as f:
                    json.dump(config, f, indent=2)
                return self.restart_xray()
                
            return True
        except Exception as e:
            print(f"Error changing status: {e}")
            return False
