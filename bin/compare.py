#!/usr/bin/env python3
"""So sánh strings.xml: liệt kê các `name` có trong file mới nhưng không có trong file gốc."""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape


def escape_attr(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def extract_string_names(xml_content: str) -> dict[str, str | None]:
    root = ET.fromstring(xml_content)
    out: dict[str, str | None] = {}
    for el in root.findall("string"):
        name = el.get("name")
        if not name:
            continue
        out[name] = el.text
    return out


_NAME_PREFIX_SKIP = ("miuix_", "solar_", "chinese_")

_NUMERIC = re.compile(r"-?\d+$|-?\d+\.\d+$")
# Giá trị kiểu advanced_shortcuts_collapsed: chữ thường/số, các đoạn nối bằng _
_SNAKE_PHRASE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)+$")
# V1.0, V2.4.3.0
_VERSION_V = re.compile(r"^V\d+(?:\.\d+)*$", re.IGNORECASE)
# CHN-CBN
_REGION_CODE_UPPER = re.compile(r"^[A-Z]{2,}(?:-[A-Z0-9]+)+$")
# Chỉ chữ Hán/CJK (lịch âm…)
_CJK_ONLY = re.compile(
    r"^[\u3007\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+$"
)
# 192.168.1.1, 8.8.8.8
_IPV4 = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
# com.google.android.material.sidesheet.SideSheetBehavior
_FQCN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)+$")
# com.android.settings.Settings$WallpaperSettingsActivity
_FQCN_INNER = re.compile(
    r"^[a-z][a-z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)+\$[A-Za-z][a-zA-Z0-9_]*$"
)
# 368:98, 222:220 — tỷ lệ w:h (không phải IPv4)
_RATIO_W_H = re.compile(r"^\d+:\d+$")
# content://…
_CONTENT_URI = re.compile(r"^content://", re.IGNORECASE)
# cubic-bezier(0.2, 0, 0, 1)
_CUBIC_BEZIER = re.compile(r"^cubic-bezier\s*\(", re.IGNORECASE)
# path(M 0,0 C …)
_PATH_FUNC = re.compile(r"^path\s*\(", re.IGNORECASE)
# Dữ liệu path SVG/vector: M… rồi số và lệnh MLC…
_SVG_PATH_D = re.compile(
    r"^M[\d.,\-+\sLCcHhVvZzQqTtSsAaMm]+(?:\s*)$"
)
# M/d EEE, hh:mm, dd MMMM — chỉ ký tự mẫu ngày/giờ + phân tách
_DATE_FORMAT_CHARS = re.compile(
    r"^[EHhmsaDdMyYzSszLqQWwGFnNuKk/\s:\-\.\',\[\]0-9]+$"
)
_DATE_HAS_PATTERN_LETTER = re.compile(r"[EHhmsaDdMyYz]")
# google-sans-text, google-sans-text-medium
_HYPHEN_SLUG_LOWER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")
_URL = re.compile(r"^https?://", re.IGNORECASE)


def _is_android_resource_ref(raw: str) -> bool:
    if not raw.startswith("@"):
        return False
    # @string/foo, @android:string/foo, @*android:string/foo
    return "/" in raw or ":" in raw


def _looks_like_date_time_pattern(raw: str) -> bool:
    if not _DATE_FORMAT_CHARS.fullmatch(raw):
        return False
    return bool(_DATE_HAS_PATTERN_LETTER.search(raw))


def _is_color_hex_format_string(raw: str) -> bool:
    # # %1$02X %2$02X …
    return raw.startswith("#") and "%" in raw


# Cả chuỗi chỉ là một định dạng Android: %1$s, %2$d, %1$02X
_FORMAT_SPEC_ONLY = re.compile(r"^%(?:\d+\$)?[a-zA-Z0-9.+-]+$")
# Từ khóa tìm kiếm nối bằng ; (ASCII)
_SEMICOLON_SYNONYMS = re.compile(r"^[\w\s;\-]+$", re.ASCII)


def _is_semicolon_synonym_list(raw: str) -> bool:
    if ";" not in raw:
        return False
    if not raw.isascii():
        return False
    return bool(_SEMICOLON_SYNONYMS.fullmatch(raw))


def exclude_from_output(name: str, value: str | None) -> bool:
    if name.startswith(_NAME_PREFIX_SKIP):
        return True
    raw = "" if value is None else value.strip()
    if raw == "":
        return True
    if raw.casefold() == "null":
        return True
    if _is_android_resource_ref(raw):
        return True
    if _URL.match(raw):
        return True
    if _IPV4.fullmatch(raw):
        return True
    if _RATIO_W_H.fullmatch(raw):
        return True
    if _CONTENT_URI.match(raw):
        return True
    if _is_color_hex_format_string(raw):
        return True
    if _CUBIC_BEZIER.match(raw):
        return True
    if _PATH_FUNC.match(raw):
        return True
    if _SVG_PATH_D.fullmatch(raw) and len(raw) >= 12:
        return True
    if _FQCN_INNER.fullmatch(raw):
        return True
    if _FQCN.fullmatch(raw):
        return True
    if _looks_like_date_time_pattern(raw):
        return True
    if _HYPHEN_SLUG_LOWER.fullmatch(raw):
        return True
    if _NUMERIC.fullmatch(raw):
        return True
    if _SNAKE_PHRASE.fullmatch(raw):
        return True
    if _VERSION_V.fullmatch(raw):
        return True
    if _REGION_CODE_UPPER.fullmatch(raw):
        return True
    if _CJK_ONLY.fullmatch(raw):
        return True
    if _FORMAT_SPEC_ONLY.fullmatch(raw):
        return True
    if _is_semicolon_synonym_list(raw):
        return True
    return False


def main() -> int:
    p = argparse.ArgumentParser(
        description="File 1 = gốc, file 2 = mới. Ghi các <string name> chỉ có ở file 2 ra output."
    )
    p.add_argument("original", help="Đường dẫn file XML gốc (file 1)")
    p.add_argument("new", help="Đường dẫn file XML mới (file 2)")
    p.add_argument(
        "-o",
        "--output",
        default="output.xml",
        help="File ghi kết quả (mặc định: output.xml)",
    )
    args = p.parse_args()

    try:
        with open(args.original, "r", encoding="utf-8") as f:
            content1 = f.read()
        with open(args.new, "r", encoding="utf-8") as f:
            content2 = f.read()
    except OSError as e:
        print(f"Lỗi đọc file: {e}", file=sys.stderr)
        return 1

    names_original = extract_string_names(content1)
    names_new = extract_string_names(content2)

    only_in_new = {n: v for n, v in names_new.items() if n not in names_original}
    filtered = {
        n: v
        for n, v in only_in_new.items()
        if not exclude_from_output(n, v)
    }
    skipped = len(only_in_new) - len(filtered)

    print(
        "Các name có trong file mới nhưng không có trong file gốc "
        f"(sau lọc: {len(filtered)} mục; bỏ qua: {skipped}):"
    )
    for name, value in sorted(filtered.items()):
        print(f"  {name}: {value!r}")

    with open(args.output, "w", encoding="utf-8") as out:
        out.write('<?xml version="1.0" encoding="utf-8"?>\n')
        out.write("<resources>\n")
        for name in sorted(filtered):
            value = filtered[name]
            text = "" if value is None else escape(value)
            out.write(f'    <string name="{escape_attr(name)}">{text}</string>\n')
        out.write("</resources>\n")

    print(f"\nĐã ghi: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
