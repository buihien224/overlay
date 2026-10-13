# VS OVERLAY
VS Overlay for MIUI is an initiative aimed at providing comprehensive and accurate translations for MIUI versions, a user interface for Android devices developed by Xiaomi.

Our project focuses on translating text strings from Chinese into various languages such as English, Vietnamese, French, German, and many others. We use translation methods along with translation tools to ensure that our translations are accurate and easily understandable.

If you would like to contribute to our project, you can do so by translating text strings from Chinese into a language you know or editing existing translations to enhance their quality.

We hope that this project will help MIUI users have a better experience when using their interface on Android devices.

Thank you for joining our project, and if you have any questions or contributions, please feel free to contact us.

## Tìm string chưa dịch khi ROM cập nhật

`bin/missing.py` so sánh APK của ROM mới với overlay và lấy ra các string / plurals / array chưa có bản dịch.

```bash
# 1. Quét ROM đã bung -> missing/<overlay>/res/values-vi/*.xml + missing/report.txt
python3 bin/missing.py scan /đường/dẫn/rom

# 2. Chép vào overlay (nằm cuối mỗi file, dưới dòng "CHƯA DỊCH")
python3 bin/missing.py merge
```

- Dùng `bin/apktool.jar` để giải mã; cần `7z` trong `PATH` để đọc APK nằm trong APEX.
- `scan --only 42 34` chỉ quét vài overlay; `scan --all` lấy cả string mà APK không dịch sang ngôn ngữ nào khác (thường là key nội bộ).
- Có thể dịch ngay trong `missing/` rồi chạy `merge` lại: mục còn nằm dưới dòng "CHƯA DỊCH" sẽ được cập nhật, mục đã dịch phía trên giữ nguyên.

## Build

```bash
./build.sh all          # build song song tất cả overlay -> output/
JOBS=4 ./build.sh all   # giới hạn số overlay build cùng lúc
./build.sh 42           # build một overlay theo số thứ tự
```

`bin/apktool.jar` là bản 3.x (chỉ dùng aapt2). Overlay phải build qua `bin/aapt2-overlay` (build.sh đã tự truyền `--aapt`), nếu không aapt2 sẽ xoá hết string chỉ có trong `values-vi`.
