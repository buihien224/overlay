#!/usr/bin/env python3
"""Tìm các string ROM mới thêm mà overlay chưa dịch, rồi đưa vào overlay để dịch.

    scan  : quét APK trong thư mục ROM, ghi phần còn thiếu ra missing/<overlay>/res/values-vi/
    merge : chép missing/ vào overlay/ (nằm dưới dòng đánh dấu CHƯA DỊCH ở cuối file)
"""

import argparse
import concurrent.futures
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import unescape

sys.dont_write_bytecode = True  # bin/__pycache__ đang nằm trong git
from compare import exclude_from_output

ROOT = Path(__file__).resolve().parent.parent
MARKER = "<!-- ===== CHƯA DỊCH (bin/missing.py) ===== -->"
HEADER = '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
FILE_OF = {"string": "strings.xml", "plurals": "plurals.xml", "array": "arrays.xml"}

ELEMENT_RE = re.compile(
    r'<(string|plurals|string-array|array)\b[^>]*?\bname="([^"]+)"[^>]*?(?:/>|>(.*?)</\1\s*>)',
    re.DOTALL,
)
PLURAL_ITEM_RE = re.compile(r'<item quantity="(\w+)">(.*?)</item>', re.DOTALL)
ARRAY_ITEM_RE = re.compile(r"<item>(.*?)</item>", re.DOTALL)
TARGET_RE = re.compile(r'targetPackage="([^"]+)"')
# values-zh-rCN, values-en, values-b+sr+Latn… (values-car không phải ngôn ngữ)
LOCALE_DIR_RE = re.compile(r"^values-(?!car\b)([a-z]{2,3}|b\+[a-z]{2,3})(?![a-z0-9])")
CJK_RE = re.compile("[㐀-䶿一-鿿]")
WORD_RE = re.compile(r"[^\W\d_]{2}")


# ---------------------------------------------------------------- APK -> package

def manifest_package(data: bytes) -> str | None:
    """Đọc thuộc tính package từ AndroidManifest.xml nhị phân."""
    pool = None
    off = 8
    while off + 8 <= len(data):
        typ, hsize, size = struct.unpack_from("<HHI", data, off)
        if size < 8:
            return None
        if typ == 0x0001:
            count, _, flags, start, _ = struct.unpack_from("<IIIII", data, off + 8)
            offsets = struct.unpack_from(f"<{count}I", data, off + hsize)
            pool = (off + start, offsets, bool(flags & 0x100))
        elif typ == 0x0102 and pool:
            astart, asize, acount = struct.unpack_from("<HHH", data, off + 24)
            for i in range(acount):
                _, name, raw, _, _, _, val = struct.unpack_from(
                    "<IIIHBBI", data, off + 16 + astart + i * asize
                )
                if _pool_string(data, pool, name) == "package":
                    return _pool_string(data, pool, val if raw == 0xFFFFFFFF else raw)
            return None
        off += size
    return None


def _pool_string(data: bytes, pool, idx: int) -> str | None:
    base, offsets, utf8 = pool
    if idx >= len(offsets):
        return None
    p = base + offsets[idx]
    if utf8:
        p += 2 if data[p] & 0x80 else 1
        n = data[p]
        p += 1
        if n & 0x80:
            n = ((n & 0x7F) << 8) | data[p]
            p += 1
        return data[p : p + n].decode("utf-8", "replace")
    (n,) = struct.unpack_from("<H", data, p)
    p += 2
    if n & 0x8000:
        n = ((n & 0x7FFF) << 16) | struct.unpack_from("<H", data, p)[0]
        p += 2
    return data[p : p + n * 2].decode("utf-16-le", "replace")


def apk_package(apk: Path) -> str | None:
    try:
        with zipfile.ZipFile(apk) as z:
            if "resources.arsc" not in z.namelist():
                return None
            return manifest_package(z.read("AndroidManifest.xml"))
    except Exception:
        return None


def index_apks(apks) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    with concurrent.futures.ThreadPoolExecutor() as ex:
        for apk, pkg in zip(apks, ex.map(apk_package, apks)):
            if pkg:
                index.setdefault(pkg, []).append(apk)
    return index


def extract_apex_apks(rom: Path, work: Path) -> list[Path]:
    """Bung APK nằm trong .apex/.capex (payload ext4) bằng 7z."""
    if not shutil.which("7z"):
        print("! Không có 7z, bỏ qua APK trong APEX", file=sys.stderr)
        return []

    def one(apex: Path) -> None:
        out = work / apex.name
        try:
            with zipfile.ZipFile(apex) as z:
                if "original_apex" in z.namelist():
                    z.extract("original_apex", out)
                    with zipfile.ZipFile(out / "original_apex") as inner:
                        inner.extract("apex_payload.img", out)
                elif "apex_payload.img" in z.namelist():
                    z.extract("apex_payload.img", out)
                else:
                    return
            subprocess.run(
                ["7z", "x", "-y", f"-o{out / 'payload'}", str(out / "apex_payload.img"), "*.apk", "-r"],
                capture_output=True,
            )
        except Exception as e:
            print(f"! Lỗi bung {apex.name}: {e}", file=sys.stderr)

    apexes = sorted(p for p in rom.rglob("*") if p.suffix in (".apex", ".capex"))
    with concurrent.futures.ThreadPoolExecutor() as ex:
        list(ex.map(one, apexes))
    return sorted(work.rglob("*.apk"))


# ---------------------------------------------------------------- đọc resource

def parse_elements(text: str) -> dict[tuple[str, str], tuple[str, str]]:
    """{(kind, name): (raw_element, body)} — kind: string | plurals | array."""
    out = {}
    for m in ELEMENT_RE.finditer(text):
        kind = "array" if m.group(1).endswith("array") else m.group(1)
        out.setdefault((kind, m.group(2)), (m.group(0), m.group(3) or ""))
    return out


def read_values_dir(d: Path) -> dict:
    out = {}
    for f in sorted(d.glob("*.xml")):
        for k, v in parse_elements(f.read_text(encoding="utf-8", errors="replace")).items():
            out.setdefault(k, v)
    return out


def decode_apk(apk: Path, work: Path, apktool: str) -> Path | None:
    """Chỉ giải mã resources.arsc (bỏ dex, ảnh…) nên mỗi APK mất vài giây."""
    stripped = work / "in.apk"
    with zipfile.ZipFile(apk) as src, zipfile.ZipFile(stripped, "w") as dst:
        for name in ("resources.arsc", "AndroidManifest.xml"):
            dst.writestr(name, src.read(name))
    out = work / "out"
    tool = ["java", "-jar", apktool] if apktool.endswith(".jar") else [apktool]
    r = subprocess.run(
        [*tool, "d", "-s", "-f", "-o", str(out), str(stripped)], capture_output=True, text=True
    )
    if not (out / "res").is_dir():
        print(f"! apktool lỗi với {apk}:\n{r.stdout[-500:]}{r.stderr[-500:]}", file=sys.stderr)
        return None
    return out / "res"


# ---------------------------------------------------------------- tìm phần thiếu

def translatable(name: str, text: str) -> bool:
    text = unescape(re.sub(r"<[^>]+>", "", text))
    # Phải có ít nhất một từ (bỏ "A", "#", "D T z"…)
    return bool(WORD_RE.search(text)) and not exclude_from_output(name, text)


def find_missing(res: Path, have: set, lang: str, include_all: bool) -> dict:
    """Các mục có ở values/ của APK, chưa có trong overlay và APK cũng chưa tự dịch."""
    base = read_values_dir(res / "values")
    localized, english = set(), {}
    for d in sorted(res.iterdir()):
        if not LOCALE_DIR_RE.match(d.name):
            continue
        items = read_values_dir(d)
        if re.match(rf"values-{lang}(-|$)", d.name):
            have = have | items.keys()
        else:
            localized |= items.keys()
        if d.name == "values-en" or d.name.startswith("values-en-r"):
            for k, v in items.items():
                english.setdefault(k, v)

    missing = {}
    for key, (raw, body) in base.items():
        kind, name = key
        if key in have:
            continue
        # String không được dịch sang ngôn ngữ nào khác thường là key/định dạng nội bộ.
        if localized and key not in localized and not include_all:
            continue
        if CJK_RE.search(body) and key in english:
            raw, body = english[key]
        if kind == "string":
            if not translatable(name, body):
                continue
        elif kind == "plurals":
            items = dict(PLURAL_ITEM_RE.findall(body))
            text = items.get("other") or next(iter(items.values()), "")
            if not translatable(name, text):
                continue
            # Tiếng Việt chỉ dùng quantity="other"
            raw = f'<plurals name="{name}">\n        <item quantity="other">{text}</item>\n    </plurals>'
        else:
            if not any(translatable(name, i) for i in ARRAY_ITEM_RE.findall(body)):
                continue
        missing[key] = raw
    return missing


def overlay_targets(overlay_dir: Path, lang: str) -> dict[str, list[Path]]:
    """{targetPackage: [overlay có res/values-<lang>]}"""
    targets: dict[str, list[Path]] = {}
    for d in sorted(overlay_dir.iterdir(), key=lambda p: (int(p.name.split("-")[0]) if p.name.split("-")[0].isdigit() else 0, p.name)):
        manifest = d / "AndroidManifest.xml"
        if not manifest.is_file() or not (d / "res" / f"values-{lang}").is_dir():
            continue
        m = TARGET_RE.search(manifest.read_text(encoding="utf-8"))
        if m:
            targets.setdefault(m.group(1), []).append(d)
    return targets


def overlay_names(dirs: list[Path], lang: str) -> set:
    have = set()
    for d in dirs:
        for v in (d / "res").glob(f"values-{lang}*"):
            have |= read_values_dir(v).keys()
    return have


def write_values(dest: Path, entries: dict) -> None:
    """entries: {(kind, name): raw} -> strings.xml / plurals.xml / arrays.xml trong dest."""
    for kind, fname in FILE_OF.items():
        raws = [raw for (k, n), raw in sorted(entries.items()) if k == kind]
        if raws:
            dest.mkdir(parents=True, exist_ok=True)
            (dest / fname).write_text(
                HEADER + "".join(f"    {r}\n" for r in raws) + "</resources>\n", encoding="utf-8"
            )


def cmd_scan(args) -> int:
    rom, out = Path(args.rom), Path(args.output)
    targets = overlay_targets(Path(args.overlay), args.lang)
    if args.only:
        targets = {
            t: ds for t, ds in targets.items()
            if any(o in (d.name, d.name.split("-")[0], t) for d in ds for o in args.only)
        }
    if not targets:
        print("Không có overlay nào khớp.", file=sys.stderr)
        return 1

    print(f"Lập chỉ mục APK trong {rom} …")
    index = index_apks(sorted(rom.rglob("*.apk")))
    tmp = tempfile.TemporaryDirectory(prefix="missing-")
    work = Path(tmp.name)
    if any(t not in index for t in targets):
        for pkg, apks in index_apks(extract_apex_apks(rom, work / "apex")).items():
            index.setdefault(pkg, []).extend(apks)

    def scan_target(job) -> dict:
        i, (target, dirs) = job
        missing = {}
        have = overlay_names(dirs, args.lang)
        for j, apk in enumerate(index[target]):
            w = work / f"{i}-{j}"
            w.mkdir()
            res = decode_apk(apk, w, args.apktool)
            if res:
                for k, v in find_missing(res, have, args.lang, args.all).items():
                    missing.setdefault(k, v)
            shutil.rmtree(w, ignore_errors=True)
        return missing

    found = {t: ds for t, ds in targets.items() if t in index}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        results = list(ex.map(scan_target, enumerate(found.items())))
    tmp.cleanup()

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    lines, total = [], 0
    for (target, dirs), missing in zip(found.items(), results):
        if not missing:
            continue
        write_values(out / dirs[0].name / "res" / f"values-{args.lang}", missing)
        n = {k: sum(1 for key in missing if key[0] == k) for k in FILE_OF}
        total += len(missing)
        lines.append(
            f"{dirs[0].name:<34} {target:<44} string {n['string']:>5}  plurals {n['plurals']:>4}  array {n['array']:>4}"
        )
    for target, dirs in targets.items():
        if target not in index:
            lines.append(f"{dirs[0].name:<34} {target:<44} KHÔNG CÓ APK TRONG ROM")
    lines.append(f"\nTổng: {total} mục chưa dịch -> {out}")
    report = "\n".join(lines)
    (out / "report.txt").write_text(report + "\n", encoding="utf-8")
    print(report)
    return 0


# ---------------------------------------------------------------- merge

def merge_file(src: Path, dst: Path) -> int:
    """Thêm các mục của src vào cuối dst, dưới MARKER. Mục đã dịch (trên MARKER) giữ nguyên."""
    new = {k: v[0] for k, v in parse_elements(src.read_text(encoding="utf-8")).items()}
    text = HEADER + "</resources>\n"
    if dst.exists():
        # newline="" để giữ nguyên kiểu xuống dòng (CRLF/LF) của file overlay
        with open(dst, encoding="utf-8", newline="") as f:
            text = f.read()
    nl = "\r\n" if "\r\n" in text else "\n"
    end = text.rfind("</resources>")
    if end < 0:
        print(f"! Bỏ qua {dst}: không thấy </resources>", file=sys.stderr)
        return 0
    at = text.find(MARKER)
    head = text[: at if at >= 0 else end].rstrip() + nl
    pending = {k: v[0] for k, v in parse_elements(text[at:end]).items()} if at >= 0 else {}
    translated = parse_elements(head).keys()
    added = 0
    for k, raw in new.items():
        if k not in translated:
            added += k not in pending
            pending[k] = raw
    if not pending:
        return 0
    body = "".join(f"    {raw}\n" for raw in pending.values()).replace("\r\n", "\n").replace("\n", nl)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8", newline="") as f:
        f.write(f"{head}    {MARKER}{nl}{body}</resources>{nl}")
    return added


def cmd_merge(args) -> int:
    src_root, overlay = Path(args.output), Path(args.overlay)
    total = 0
    for src in sorted(src_root.glob("*/res/*/*.xml")):
        rel = src.relative_to(src_root)
        if not (overlay / rel.parts[0]).is_dir():
            print(f"! Không có overlay {rel.parts[0]}", file=sys.stderr)
            continue
        added = merge_file(src, overlay / rel)
        if added:
            print(f"+{added:<5} {rel}")
        total += added
    print(f"Đã thêm {total} mục vào {overlay}. Tìm \"CHƯA DỊCH\" trong từng file để dịch.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--overlay", default=str(ROOT / "overlay"), help="Thư mục chứa các overlay")
    common.add_argument("-o", "--output", default=str(ROOT / "missing"), help="Thư mục chứa phần còn thiếu")

    s = sub.add_parser("scan", parents=[common], help="Quét ROM, ghi string còn thiếu ra thư mục missing/")
    s.add_argument("rom", help="Thư mục ROM đã bung (chứa các .apk)")
    s.add_argument("--only", nargs="+", help="Chỉ quét các overlay này (số, tên thư mục hoặc package)")
    s.add_argument("--lang", default="vi", help="Ngôn ngữ overlay (mặc định: vi)")
    s.add_argument("--all", action="store_true", help="Lấy cả string không được dịch sang ngôn ngữ nào khác")
    s.add_argument("--apktool", default=str(ROOT / "bin" / "apktool.jar"), help="apktool (.jar hoặc lệnh) dùng để giải mã")
    s.add_argument("-j", "--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    s.set_defaults(func=cmd_scan)

    m = sub.add_parser("merge", parents=[common], help="Chép missing/ vào overlay/")
    m.set_defaults(func=cmd_merge)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
