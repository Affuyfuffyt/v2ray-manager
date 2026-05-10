#!/bin/bash
clear
echo "=================================================="
echo "  🚀 أداة إدارة V2Ray (النسخة الاحترافية بـ API) "
echo "=================================================="

# 1. تنظيف وإيقاف العمليات السابقة
echo "[+] جاري إيقاف العمليات السابقة..."
pkill -9 xray
pkill -9 -f run.py

# 2. أخذ البيانات المطلوبة
read -p "🔑 أدخل توكن البوت: " BOT_TOKEN
read -p "👑 أدخل الآيدي الخاص بك: " ADMIN_ID
read -p "🛠️ أدخل Alwaysdata API Key: " AD_API_KEY
read -p "🆔 أدخل Site ID الخاص بك: " AD_SITE_ID
read -p "🌐 أدخل الدومين الخاص بك (مثال: google.com): " AD_DOMAIN
read -p "📂 أدخل اسم المجلد الجديد للبوت (مثلاً bot1 أو v2ray_manager): " APP_DIR_NAME

# إذا المستخدم ضغط إنتر بدون ما يكتب اسم، نخليه افتراضي
APP_DIR_NAME=${APP_DIR_NAME:-v2ray_manager}

# 3. تجهيز المجلدات وحذف المجلد القديم إن وجد
WORK_DIR="$HOME/$APP_DIR_NAME"
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

# 🔥 السحر البرمجي: تغيير اسم المجلد داخل كل ملفات البايثون تلقائياً حتى لا تتعطل قواعد البيانات 🔥
find $WORK_DIR -type f -name "*.py" -exec sed -i "s/v2ray_manager/$APP_DIR_NAME/g" {} +

# 6. نقل ملف config.json للمكان الصحيح
cp xray_core/config.json $XRAY_DIR/config.json

# 7. تخزين كل المفاتيح في ملف البيئة المخفي
echo "BOT_TOKEN=$BOT_TOKEN" > .env
echo "ADMIN_ID=$ADMIN_ID" >> .env
echo "AD_API_KEY=$AD_API_KEY" >> .env
echo "AD_SITE_ID=$AD_SITE_ID" >> .env
echo "AD_DOMAIN=$AD_DOMAIN" >> .env

# تجهيز ملف الريستارت التلقائي والدومين العالمي
echo "$AD_SITE_ID" > $HOME/alwaysdata_keys.txt
echo "$AD_API_KEY" >> $HOME/alwaysdata_keys.txt
echo "$AD_DOMAIN" >> $HOME/alwaysdata_keys.txt

# 8. تثبيت المكاتب
echo "[+] جاري تثبيت المتطلبات..."
pip install -r requirements.txt

# 🔥 9. إنشاء ملف المراقب الأبدي بالاسم الجديد للمجلد 🔥
cat << EOF > $HOME/keep_alive.sh
#!/bin/bash
if ! pgrep -f "run.py" > /dev/null
then
    echo "البوت كان متوقف... جاري إعادة تشغيله."
    cd $HOME/$APP_DIR_NAME
    nohup python3 run.py > system.log 2>&1 &
fi
EOF
chmod +x $HOME/keep_alive.sh

# تشغيل البوت لأول مرة
nohup python3 run.py > system.log 2>&1 &

echo "=================================================="
echo "✅ تم التثبيت والربط بـ API المنصة بنجاح!"
echo "⚠️ تم تثبيت البوت في مجلد: $APP_DIR_NAME"
echo "⚠️ خطوة أخيرة مهمة: قم بإضافة $HOME/keep_alive.sh إلى Scheduled Tasks في لوحة Alwaysdata ليعمل كل 5 دقائق."
echo "=================================================="
