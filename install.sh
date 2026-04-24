#!/bin/bash
clear
echo "=================================================="
echo "  🚀 أداة إدارة V2Ray الاحترافية (نسخة Alwaysdata) "
echo "=================================================="

# 1. أخذ البيانات
read -p "🔑 أدخل توكن البوت (Bot Token): " BOT_TOKEN
read -p "👑 أدخل الآيدي الخاص بك (Admin ID): " ADMIN_ID
read -p "🌐 أدخل رابط لوحة السيرفر (مثال http://1.1.1.1:2053): " PANEL_URL
read -p "👤 أدخل يوزر لوحة السيرفر: " PANEL_USER
read -p "🔒 أدخل باسورد لوحة السيرفر: " PANEL_PASS

# 2. إنشاء بيئة العمل وتنظيفها إذا كانت موجودة لتجنب الأخطاء
WORK_DIR="$HOME/v2ray_manager"
rm -rf $WORK_DIR
mkdir -p $WORK_DIR

# 3. سحب الملفات من كيت هب (أولاً)
echo "[+] جاري سحب ملفات النظام..."
git clone https://github.com/Affuyfuffyt/v2ray-manager.git $WORK_DIR
cd $WORK_DIR

# 4. إنشاء ملف .env (ثانياً)
cat <<EOF > .env
BOT_TOKEN=$BOT_TOKEN
ADMIN_ID=$ADMIN_ID
PANEL_URL=$PANEL_URL
PANEL_USER=$PANEL_USER
PANEL_PASS=$PANEL_PASS
EOF

# 5. تثبيت المكاتب
echo "[+] جاري تثبيت المتطلبات..."
pip install -r requirements.txt

# 6. تشغيل البوت كخدمة بالخلفية
pkill -f "python3 run.py" 2>/dev/null
nohup python3 run.py > system.log 2>&1 &

echo "=================================================="
echo "✅ تم التثبيت بنجاح! البوت متصل الآن بالسيرفر الفعلي."
echo "=================================================="
