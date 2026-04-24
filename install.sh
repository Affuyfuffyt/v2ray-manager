#!/bin/bash
clear
echo "=================================================="
echo "  🚀 أداة إدارة V2Ray (النسخة الاحترافية بـ API) "
echo "=================================================="

# 1. تنظيف وإيقاف العمليات
pkill -9 xray
pkill -9 -f run.py

# 2. أخذ البيانات المطلوبة
read -p "🔑 أدخل توكن البوت: " BOT_TOKEN
read -p "👑 أدخل الآيدي الخاص بك: " ADMIN_ID
read -p "🛠️ أدخل Alwaysdata API Key: " AD_API_KEY
read -p "🆔 أدخل Site ID الخاص بك: " AD_SITE_ID

# 3. تجهيز المجلدات
WORK_DIR="$HOME/v2ray_manager"
XRAY_DIR="$HOME/xray_core"
mkdir -p $XRAY_DIR
rm -rf $WORK_DIR
mkdir -p $WORK_DIR

# 4. تحميل المحرك Xray (إذا لم يكن موجوداً)
if [ ! -f "$XRAY_DIR/xray" ]; then
    echo "[+] جاري تحميل محرك Xray..."
    cd $XRAY_DIR
    wget -q https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip
    unzip -q Xray-linux-64.zip
    rm Xray-linux-64.zip
    chmod +x xray
fi

# 5. سحب ملفات البوت من كيت هب
echo "[+] جاري سحب ملفات البوت..."
git clone https://github.com/Affuyfuffyt/v2ray-manager.git $WORK_DIR
cd $WORK_DIR

# 6. نقل ملف config.json للمكان الصحيح
cp xray_core/config.json $XRAY_DIR/config.json

# 7. تخزين كل المفاتيح في ملف البيئة المخفي
echo "BOT_TOKEN=$BOT_TOKEN" > .env
echo "ADMIN_ID=$ADMIN_ID" >> .env
echo "AD_API_KEY=$AD_API_KEY" >> .env
echo "AD_SITE_ID=$AD_SITE_ID" >> .env

# 8. تثبيت المكاتب وتشغيل البوت
echo "[+] جاري تثبيت المتطلبات وتشغيل البوت..."
pip install -r requirements.txt
nohup python3 run.py > system.log 2>&1 &

echo "=================================================="
echo "✅ تم التثبيت والربط بـ API المنصة بنجاح!"
echo "=================================================="
