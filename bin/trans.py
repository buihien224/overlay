import argparse
import concurrent.futures
import sys
import re
import time
import threading
from typing import Dict, Tuple
from xml.sax.saxutils import escape as xml_escape
from xml.sax.saxutils import unescape as xml_unescape

import requests


STRING_TAG_RE = re.compile(
    r"(<string\b[^>]*>)(.*?)(</string>)",
    flags=re.DOTALL,
)

# Common Android placeholders like %1$s, %2$s, %1s, %s, %%.
PLACEHOLDER_RE = re.compile(r"%(?:\d+\$)?[0-9.]*[a-zA-Z]|%%")


def protect_placeholders(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Replace placeholders with stable tokens so the translator doesn't mess them up.
    """
    mapping: Dict[str, str] = {}

    def repl(m: re.Match) -> str:
        token = f"__PH{len(mapping)}__"
        mapping[token] = m.group(0)
        return token

    return PLACEHOLDER_RE.sub(repl, text), mapping


def restore_placeholders(text: str, mapping: Dict[str, str]) -> str:
    for token, original in mapping.items():
        text = text.replace(token, original)
    return text


def translate_with_mymemory(
    session: requests.Session,
    text: str,
    source_lang: str,
    target_lang: str,
    cache: Dict[Tuple[str, str, str], str],
    cache_lock: threading.Lock,
    verbose: bool,
) -> str:
    """
    Free translation service: MyMemory (https://mymemory.translated.net/).
    """
    key = (source_lang, target_lang, text)
    if cache_lock is not None:
        with cache_lock:
            if key in cache:
                return cache[key]
    else:
        if key in cache:
            return cache[key]

    url = "https://api.mymemory.translated.net/get"
    params = {"q": text, "langpair": f"{source_lang}|{target_lang}"}

    try:
        r = session.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        translated = data["responseData"]["translatedText"]
        if verbose:
            sys.stderr.write(f"TRANSLATE: {text!r} => {translated!r}\n")
    except Exception as e:
        if verbose:
            sys.stderr.write(f"TRANSLATE ERROR: {text!r}: {e}\n")
        translated = text

    # Small delay to reduce rate limiting.
    time.sleep(0.05)
    if cache_lock is not None:
        with cache_lock:
            cache[key] = translated
    else:
        cache[key] = translated
    return translated


def translate_xml_string_inner(
    raw_inner: str,
    session: requests.Session,
    source_lang: str,
    target_lang: str,
    cache: Dict[Tuple[str, str, str], str],
    cache_lock: threading.Lock,
    verbose: bool,
) -> str:
    """
    Translate ONLY the content inside <string>...</string>, preserving internal newlines
    and leading/trailing whitespace per line.
    """
    if raw_inner.strip() == "":
        return raw_inner

    # Convert XML entities to characters before translation.
    inner = xml_unescape(raw_inner)

    # Protect placeholders like %1$s.
    protected, placeholder_mapping = protect_placeholders(inner)

    # Fast path: most <string> values are single-line; translate once for speed.
    if "\n" not in protected:
        translated = translate_with_mymemory(
            session=session,
            text=protected,
            source_lang=source_lang,
            target_lang=target_lang,
            cache=cache,
            cache_lock=cache_lock,
            verbose=verbose,
        )
        translated = restore_placeholders(translated, placeholder_mapping)
        return xml_escape(translated, {"\"": "&quot;", "'": "&apos;"})

    # Preserve formatting for multiline strings: translate each line while keeping
    # its leading/trailing whitespace unchanged.
    translated_lines = []
    for line in protected.split("\n"):
        # Keep empty/whitespace-only lines as-is.
        if line.strip() == "":
            translated_lines.append(line)
            continue

        lead_len = len(line) - len(line.lstrip())
        trail_len = len(line) - len(line.rstrip())
        prefix = line[:lead_len]
        core = line[lead_len : len(line) - trail_len]
        suffix = line[len(line) - trail_len :]

        translated_core = translate_with_mymemory(
            session=session,
            text=core,
            source_lang=source_lang,
            target_lang=target_lang,
            cache=cache,
            cache_lock=cache_lock,
            verbose=verbose,
        )
        translated_lines.append(prefix + translated_core + suffix)

    translated = "\n".join(translated_lines)
    translated = restore_placeholders(translated, placeholder_mapping)

    # Escape back to valid XML.
    return xml_escape(translated, {"\"": "&quot;", "'": "&apos;"})


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Translate Android strings XML while preserving XML structure/format."
    )
    parser.add_argument("file", help="Path to input XML file (e.g., bin/output.xml)")
    parser.add_argument("target_lang", help="Target language code (e.g., vi)")
    parser.add_argument(
        "--source_lang",
        default="en",
        help="Source language code for MyMemory (default: en).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output path. Default: overwrite input file.",
    )
    parser.add_argument("--verbose", action="store_true", help="Print debug info to stderr")
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel translation workers (be careful with rate limiting).",
    )
    args = parser.parse_args()

    in_path = args.file
    out_path = args.out or in_path

    with open(in_path, "r", encoding="utf-8", newline="") as f:
        original = f.read()

    cache: Dict[Tuple[str, str, str], str] = {}
    cache_lock = threading.Lock()

    matches = list(STRING_TAG_RE.finditer(original))
    translations = ["" for _ in range(len(matches))]

    def worker(i: int, inner: str) -> str:
        # Each worker has its own HTTP session (requests.Session is not thread-safe).
        local_session = requests.Session()
        return translate_xml_string_inner(
            raw_inner=inner,
            session=local_session,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            cache=cache,
            cache_lock=cache_lock,
            verbose=args.verbose,
        )

    changed = 0
    if args.workers <= 1:
        for i, m in enumerate(matches):
            inner = m.group(2)
            translated_inner = worker(i, inner)
            translations[i] = translated_inner
            if translated_inner != inner:
                changed += 1
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            future_to_idx = {
                ex.submit(worker, i, m.group(2)): i for i, m in enumerate(matches)
            }
            for fut in concurrent.futures.as_completed(future_to_idx):
                i = future_to_idx[fut]
                m = matches[i]
                inner = m.group(2)
                translated_inner = fut.result()
                translations[i] = translated_inner
                if translated_inner != inner:
                    changed += 1

    # Reconstruct output with original tags.
    out_parts = []
    last_end = 0
    for i, m in enumerate(matches):
        out_parts.append(original[last_end : m.start()])
        out_parts.append(m.group(1))
        out_parts.append(translations[i])
        out_parts.append(m.group(3))
        last_end = m.end()
    out_parts.append(original[last_end:])
    result = "".join(out_parts)

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(result)

    if args.verbose:
        sys.stderr.write(f"Done. Translated {changed} <string> nodes.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())