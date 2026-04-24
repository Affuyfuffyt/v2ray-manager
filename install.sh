#!/bin/bash
clear
echo "=================================================="
echo "  🚀 أداة إدارة V2Ray الاحترافية (نسخة Alwaysdata) "
echo "=================================================="

# 1. أخذ التوكن والآيدي من المستخدم أثناء التثبيت
read -p "🔑 أدخل توكن البوت (Bot Token): " BOT_TOKEN
read -p "👑 أدخل الآيدي الخاص بك (Admin ID): " ADMIN_ID
read -p "🌐 أدخل رابط لوحة السيرفر (مثال http://1.1.1.1:2053): " PANEL_URL
read -p "👤 أدخل يوزر لوحة السيرفر: " PANEL_USER
read -p "🔒 أدخل باسورد لوحة السيرفر: " PANEL_PASS

# 2. إنشاء بيئة العمل
WORK_DIR="$HOME/v2ray_manager"
mkdir -p $WORK_DIR
cd $WORK_DIR

# 3. حفظ البيانات الحساسة في ملف مخفي
cat <<EOF > .env
BOT_TOKEN=$BOT_TOKEN
ADMIN_ID=$ADMIN_ID
PANEL_URL=$PANEL_URL
PANEL_USER=$PANEL_USER
PANEL_PASS=$PANEL_PASS
EOF

# 4. سحب الملفات من مستودعك على كيت هب (تستبدل USER و REPO باسم حسابك)
echo "[+] جاري سحب ملفات النظام..."
git clone https://github.com/USER/REPO.git .

# 5. تثبيت المكاتب (Telebot, SQLite, Requests, Schedule)
echo "[+] جاري تثبيت المتطلبات..."
pip install -r requirements.txt

# 6. تشغيل البوت كخدمة بالخلفية
pkill -f "python3 run.py" 2>/dev/null
nohup python3 run.py > system.log 2>&1 &

echo "=================================================="
echo "✅ تم التثبيت بنجاح! البوت متصل الآن بالسيرفر الفعلي."
echo "=================================================="
