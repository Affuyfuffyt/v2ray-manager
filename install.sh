#!/bin/bash
clear
echo "=================================================="
echo "  🚀 تثبيت عقدة (Node) V2Ray للسيرفر الفرعي "
echo "=================================================="

# 1. تنظيف وإيقاف العمليات القديمة
pkill -9 xray
pkill -9 -f run.py

# 2. أخذ البيانات المطلوبة فقط للسيرفر الفرعي
read -p "🛠️ أدخل Alwaysdata API Key: " AD_API_KEY
read -p "🆔 أدخل Site ID الخاص بك: " AD_SITE_ID
read -p "🌐 أدخل الدومين الخاص بك (مثال: google.com): " AD_DOMAIN
read -p "👤 أدخل FTP User (اسم حسابك): " FTP_USER

# 3. تجهيز المجلدات
WORK_DIR="$HOME/v2ray_manager"
XRAY_DIR="$HOME/xray_core"
mkdir -p $XRAY_DIR
rm -rf $WORK_DIR
mkdir -p $WORK_DIR

# 4. تحميل المحرك Xray
if [ ! -f "$XRAY_DIR/xray" ]; then
    echo "[+] جاري تحميل محرك Xray..."
    cd $XRAY_DIR
    wget -q https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip
    unzip -q Xray-linux-64.zip
    rm Xray-linux-64.zip
    chmod +x xray
fi

# 5. سحب ملفات الإعداد من كيت هب
echo "[+] جاري سحب ملفات الإعداد..."
git clone https://github.com/Affuyfuffyt/v2ray-manager.git $WORK_DIR
cd $WORK_DIR
cp xray_core/config.json $XRAY_DIR/config.json

echo "[+] جاري تصحيح مسارات السيرفر..."
sed -i 's|"access":.*|"access": "/home/'"$FTP_USER"'/xray_core/access.log",|g' $XRAY_DIR/config.json
sed -i 's|"error":.*|"error": "/home/'"$FTP_USER"'/xray_core/error.log",|g' $XRAY_DIR/config.json

# 6. تخزين المفاتيح
echo "AD_API_KEY=$AD_API_KEY" > .env
echo "AD_SITE_ID=$AD_SITE_ID" >> .env
echo "AD_DOMAIN=$AD_DOMAIN" >> .env
echo "FTP_USER=$FTP_USER" >> .env

echo "$AD_SITE_ID" > $HOME/alwaysdata_keys.txt
echo "$AD_API_KEY" >> $HOME/alwaysdata_keys.txt
echo "$AD_DOMAIN" >> $HOME/alwaysdata_keys.txt

# 7. إنشاء ملف المراقب الأبدي للـ Xray فقط
cat << 'EOF' > $HOME/keep_alive.sh
#!/bin/bash
if ! pgrep -f "xray" > /dev/null
then
    echo "جاري إعادة تشغيل المحرك..."
    cd $HOME/xray_core
    nohup ./xray run -c config.json > system.log 2>&1 &
fi
EOF
chmod +x $HOME/keep_alive.sh

# 8. تشغيل محرك Xray
echo "[+] جاري تشغيل المحرك..."
nohup $HOME/xray_core/xray run -c $HOME/xray_core/config.json > $HOME/xray_core/system.log 2>&1 &

echo "=================================================="
echo "✅ تم تثبيت السيرفر الفرعي بنجاح!"
echo "=================================================="
