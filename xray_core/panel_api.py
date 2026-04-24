import json
import os

# مسار ملف الإعدادات الخاص بمحرك Xray في Alwaysdata
CONFIG_PATH = os.path.expanduser('~/xray_core/config.json')

class PanelAPI:
    def __init__(self):
        # لم نعد بحاجة للاتصال عبر الإنترنت بلوحة خارجية
        pass

    def create_client(self, email, uuid):
        # هذه الدالة تضيف المشترك الجديد لملف الإعدادات المحلي
        try:
            # 1. قراءة الملف
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            # 2. تجهيز بيانات المشترك
            new_client = {
                "id": uuid,
                "email": email
            }
            
            # 3. إضافته لقائمة المشتركين
            clients = config['inbounds'][0]['settings']['clients']
            if not any(c.get('email') == email for c in clients):
                clients.append(new_client)
            
            # 4. حفظ الملف بعد التعديل
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            
            # 5. تطبيق التحديثات
            self.restart_xray()
            return True
            
        except Exception as e:
            print(f"Error creating client locally: {e}")
            return False

    def restart_xray(self):
        # قتل المحرك الحالي.. وموقع Alwaysdata سيقوم بإعادة تشغيله تلقائياً فوراً
        os.system("pkill -9 xray")

    def get_client_traffic(self, email):
        # بما أننا نستخدم محرك خام حالياً، سنعيد 0 
        # (مستقبلاً يمكننا تفعيل ميزة Stats API لحساب الجيجات)
        return 0

    def change_client_status(self, email, inbound_id=None, uuid=None, enable=True):
        # هذه الدالة تقوم بحظر المشترك (عن طريق حذفه من الملف) أو إعادة تفعيله
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            clients = config['inbounds'][0]['settings']['clients']
            
            if not enable:
                # حذف المشترك (حظر)
                config['inbounds'][0]['settings']['clients'] = [c for c in clients if c.get('email') != email]
            else:
                # إعادة التفعيل
                if uuid and not any(c.get('email') == email for c in clients):
                    config['inbounds'][0]['settings']['clients'].append({"id": uuid, "email": email})
            
            # حفظ التعديلات وإعادة التشغيل
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
                
            self.restart_xray()
            return True
            
        except Exception as e:
            print(f"Error changing status: {e}")
            return False
