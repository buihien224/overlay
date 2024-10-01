#!/bin/bash
dir=$(pwd)


# Kiểm tra đối số đầu vào
if [ "$#" -ne 1 ]; then
    echo "Sử dụng: $0 <đường dẫn đến file APK>"
    exit 1
fi

apktool="java -jar $dir/bin/apktool.jar"

APK_FILE=$1

OUTPUT_DIR="$dir/extracted_apk"

# Giải nén APK bằng apktool
echo "Giải nén APK..."
$apktool d "$APK_FILE" -s -o "$OUTPUT_DIR" || { echo "Giải nén APK thất bại"; exit 1; }

# Đường dẫn tới thư mục res chứa các thư mục ngôn ngữ
RES_DIR="$OUTPUT_DIR/res"

# Kiểm tra xem thư mục res có tồn tại không
if [ ! -d "$RES_DIR" ]; then
    echo "Thư mục res không tồn tại. Có thể APK không hợp lệ hoặc không chứa tài nguyên."
    exit 1
fi

# Tạo thư mục output để chứa các thư mục ngôn ngữ
LANG_DIR="$dir/language"
mkdir -p "$LANG_DIR"

# Trích xuất các thư mục ngôn ngữ không dành riêng cho màn hình
echo "Trích xuất các thư mục ngôn ngữ..."
for folder in "$RES_DIR"/values-*; do
    if [[ -d "$folder" && ! "$folder" =~ -sw && ! "$folder" =~ -hdpi && ! "$folder" =~ -xhdpi && ! "$folder" =~ -xxhdpi && ! "$folder" =~ -xxxhdpi ]]; then
        cp -r "$folder" "$LANG_DIR"
    fi
done

rm -rf "$LANG_DIR"/*dpi*
rm -rf "$LANG_DIR"/*land*
rm -rf "$LANG_DIR"/*port*
rm -rf "$LANG_DIR"/*ldltr*
rm -rf "$LANG_DIR"/*ldrtl*
rm -rf "$LANG_DIR"/*mcc*
rm -rf "$LANG_DIR"/*night*
rm -rf "$LANG_DIR"/*large*
rm -rf "$LANG_DIR"/*watch*
rm -rf "$LANG_DIR"/*feminine
rm -rf "$LANG_DIR"/*masculine
rm -rf "$LANG_DIR"/*neuter
rm -rf "$LANG_DIR"/*dp
rm -rf "$LANG_DIR"/*0*
rm -rf "$LANG_DIR"/*+*
rm -rf "$LANG_DIR"/*/styles.xml

for pattern in "@drawable" "@string" "@dimen"; do
    find "$LANG_DIR/" -type f -exec grep -l "$pattern" {} \; | xargs sed -i "s/$pattern\///g"
done

rm -rf $OUTPUT_DIR

echo "Hoàn tất! Các thư mục ngôn ngữ chuẩn đã được trích xuất vào $LANG_DIR."
