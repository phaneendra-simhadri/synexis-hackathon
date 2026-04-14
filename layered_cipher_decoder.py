#!/usr/bin/env python3
"""
SYNEXIS Layered Cipher Decoder
A multi-decrypter CLI for common CTF and puzzle encodings.
"""

import base64
import codecs
import re
import string
import sys
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import unquote_plus


MORSE_DICT = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E",
    "..-.": "F", "--.": "G", "....": "H", "..": "I", ".---": "J",
    "-.-": "K", ".-..": "L", "--": "M", "-.": "N", "---": "O",
    ".--.": "P", "--.-": "Q", ".-.": "R", "...": "S", "-": "T",
    "..-": "U", "...-": "V", ".--": "W", "-..-": "X", "-.--": "Y",
    "--..": "Z",
    "-----": "0", ".----": "1", "..---": "2", "...--": "3", "....-": "4",
    ".....": "5", "-....": "6", "--...": "7", "---..": "8", "----.": "9",
}

COMMON_WORDS = (
    "THE", "AND", "THAT", "HAVE", "FOR", "NOT", "YOU", "WITH", "THIS", "FLAG"
)

DecoderFn = Callable[[str, Optional[str]], Optional[str]]


def clean_preview(text: str, limit: int = 120) -> str:
    text = text.replace("\n", "\\n")
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def english_score(text: str) -> int:
    upper = text.upper()
    score = sum(upper.count(word) * 5 for word in COMMON_WORDS)
    letters = sum(ch.isalpha() for ch in upper)
    printable = sum(ch in string.printable for ch in upper)
    score += letters // 8
    score += printable // 15
    return score


def mostly_printable(text: str) -> bool:
    if not text:
        return False
    printable = sum(ch in string.printable for ch in text)
    return printable / len(text) >= 0.85


def pad_for_base_n(text: str, block: int) -> str:
    t = text.strip()
    missing = len(t) % block
    if missing == 0:
        return t
    return t + ("=" * (block - missing))


def caesar_shift(text: str, shift: int = 1, decode: bool = True) -> str:
    result = []
    direction = -shift if decode else shift
    for ch in text:
        if "A" <= ch <= "Z":
            result.append(chr((ord(ch) - ord("A") + direction) % 26 + ord("A")))
        elif "a" <= ch <= "z":
            result.append(chr((ord(ch) - ord("a") + direction) % 26 + ord("a")))
        else:
            result.append(ch)
    return "".join(result)


def caesar_all_shifts(text: str) -> Dict[int, str]:
    return {shift: caesar_shift(text, shift=shift, decode=True) for shift in range(1, 26)}


def decode_caesar(text: str, param: Optional[str]) -> Optional[str]:
    if param:
        try:
            shift = int(param)
            return caesar_shift(text, shift=shift, decode=True)
        except ValueError:
            return None
    shifts = caesar_all_shifts(text)
    ranked = sorted(shifts.items(), key=lambda item: english_score(item[1]), reverse=True)
    lines = ["Caesar candidates (best first):"]
    for shift, candidate in ranked[:10]:
        lines.append(f"  shift {shift:2d}: {candidate}")
    return "\n".join(lines)


def decode_rot13(text: str, _: Optional[str]) -> Optional[str]:
    return codecs.decode(text, "rot_13")


def decode_atbash(text: str, _: Optional[str]) -> Optional[str]:
    out = []
    for ch in text:
        if "A" <= ch <= "Z":
            out.append(chr(ord("Z") - (ord(ch) - ord("A"))))
        elif "a" <= ch <= "z":
            out.append(chr(ord("z") - (ord(ch) - ord("a"))))
        else:
            out.append(ch)
    return "".join(out)


def decode_reverse(text: str, _: Optional[str]) -> Optional[str]:
    return text[::-1]


def decode_base64(text: str, _: Optional[str]) -> Optional[str]:
    try:
        return base64.b64decode(pad_for_base_n(text, 4), validate=False).decode("utf-8", errors="replace")
    except Exception:
        return None


def decode_base32(text: str, _: Optional[str]) -> Optional[str]:
    try:
        return base64.b32decode(pad_for_base_n(text.upper(), 8)).decode("utf-8", errors="replace")
    except Exception:
        return None


def decode_base85(text: str, _: Optional[str]) -> Optional[str]:
    try:
        return base64.b85decode(text.encode("utf-8")).decode("utf-8", errors="replace")
    except Exception:
        return None


def decode_hex(text: str, _: Optional[str]) -> Optional[str]:
    compact = re.sub(r"[^0-9a-fA-F]", "", text)
    if not compact or len(compact) % 2 != 0:
        return None
    try:
        return bytes.fromhex(compact).decode("utf-8", errors="replace")
    except Exception:
        return None


def decode_binary(text: str, _: Optional[str]) -> Optional[str]:
    cleaned = text.strip()
    if re.fullmatch(r"[01]{8,}", cleaned):
        if len(cleaned) % 8 != 0:
            return None
        chunks = [cleaned[i:i + 8] for i in range(0, len(cleaned), 8)]
    else:
        chunks = cleaned.split()
        if not chunks or not all(re.fullmatch(r"[01]{8}", c) for c in chunks):
            return None
    try:
        return "".join(chr(int(c, 2)) for c in chunks)
    except Exception:
        return None


def decode_octal(text: str, _: Optional[str]) -> Optional[str]:
    chunks = text.split()
    if not chunks:
        compact = re.sub(r"[^0-7]", "", text)
        if len(compact) % 3 != 0 or not compact:
            return None
        chunks = [compact[i:i + 3] for i in range(0, len(compact), 3)]
    if not all(re.fullmatch(r"[0-7]{1,3}", c) for c in chunks):
        return None
    try:
        return "".join(chr(int(c, 8)) for c in chunks)
    except Exception:
        return None


def decode_decimal_ascii(text: str, _: Optional[str]) -> Optional[str]:
    nums = re.findall(r"\d+", text)
    if not nums:
        return None
    values = [int(n) for n in nums]
    if not all(0 <= v <= 255 for v in values):
        return None
    try:
        return "".join(chr(v) for v in values)
    except Exception:
        return None


def decode_url(text: str, _: Optional[str]) -> Optional[str]:
    decoded = unquote_plus(text)
    return decoded if decoded != text else None


def decode_unicode_escape(text: str, _: Optional[str]) -> Optional[str]:
    if "\\x" not in text and "\\u" not in text and "\\N" not in text:
        return None
    try:
        return bytes(text, "utf-8").decode("unicode_escape")
    except Exception:
        return None


def decode_morse(text: str, _: Optional[str]) -> Optional[str]:
    if "." not in text and "-" not in text:
        return None
    words = text.strip().split(" / ")
    result_words = []
    for word in words:
        letters = word.split()
        if not letters:
            continue
        result_words.append("".join(MORSE_DICT.get(letter, "?") for letter in letters))
    if not result_words:
        return None
    return " ".join(result_words)


def decode_xor(text: str, param: Optional[str]) -> Optional[str]:
    if not param:
        return None

    try:
        key = int(param, 0)
        key_bytes = bytes([key & 0xFF])
    except ValueError:
        key_bytes = param.encode("utf-8")

    data = text.encode("utf-8", errors="replace")
    out = bytearray()
    for i, b in enumerate(data):
        out.append(b ^ key_bytes[i % len(key_bytes)])
    return out.decode("utf-8", errors="replace")


def decode_vigenere(text: str, param: Optional[str]) -> Optional[str]:
    if not param:
        return None
    key = [c.lower() for c in param if c.isalpha()]
    if not key:
        return None

    result = []
    ki = 0
    for ch in text:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            shift = ord(key[ki % len(key)]) - ord("a")
            result.append(chr((ord(ch) - base - shift) % 26 + base))
            ki += 1
        else:
            result.append(ch)
    return "".join(result)


DECODERS: Dict[str, DecoderFn] = {
    "atbash": decode_atbash,
    "base32": decode_base32,
    "base64": decode_base64,
    "base85": decode_base85,
    "binary": decode_binary,
    "caesar": decode_caesar,
    "decimal": decode_decimal_ascii,
    "hex": decode_hex,
    "morse": decode_morse,
    "octal": decode_octal,
    "reverse": decode_reverse,
    "rot13": decode_rot13,
    "unicode": decode_unicode_escape,
    "url": decode_url,
    "vigenere": decode_vigenere,
    "xor": decode_xor,
}


def parse_decoder_spec(spec: str) -> Tuple[str, Optional[str]]:
    if ":" in spec:
        name, param = spec.split(":", 1)
        return name.strip().lower(), param.strip()
    return spec.strip().lower(), None


def run_decoder(spec: str, text: str) -> Optional[str]:
    name, param = parse_decoder_spec(spec)
    fn = DECODERS.get(name)
    if not fn:
        return None
    return fn(text, param)


def auto_detect(text: str) -> Dict[str, str]:
    print("\n" + "=" * 78)
    print("AUTO DETECT: MULTI-DECRYPTER")
    print("=" * 78)
    print(f"Input: {clean_preview(text)}\n")

    results: Dict[str, str] = {}

    for name in [
        "base64", "base32", "base85", "hex", "binary", "octal", "decimal",
        "url", "unicode", "morse", "rot13", "atbash", "reverse"
    ]:
        output = run_decoder(name, text)
        if output and output != text and mostly_printable(output):
            results[name] = output

    # Caesar is special: show the best candidates using scoring.
    caesar_ranked = sorted(
        caesar_all_shifts(text).items(),
        key=lambda item: english_score(item[1]),
        reverse=True,
    )
    for shift, candidate in caesar_ranked[:5]:
        results[f"caesar:{shift}"] = candidate

    if not results:
        print("No confident decodings found.")
    else:
        print("Candidates:")
        for method, output in results.items():
            print(f"- {method:10s} -> {clean_preview(output)}")

    print("=" * 78 + "\n")
    return results


def layered_decode(text: str, steps: List[str]) -> str:
    print("\n" + "=" * 78)
    print("LAYERED DECODING PIPELINE")
    print("=" * 78)
    print(f"Step 0 input: {clean_preview(text)}")

    current = text
    for i, step in enumerate(steps, start=1):
        output = run_decoder(step, current)
        if output is None:
            print(f"Step {i}: {step} -> failed (unknown decoder or invalid parameter)")
            break
        current = output
        print(f"Step {i}: {step} -> {clean_preview(current)}")

    print("=" * 78)
    print("Final output:")
    print(current)
    print()
    return current


def print_help() -> None:
    methods = ", ".join(sorted(DECODERS.keys()))
    print(
        """
SYNEXIS LAYERED CIPHER DECODER

Usage:
  python layered_cipher_decoder.py auto <encoded_text>
  python layered_cipher_decoder.py decode <decoder> <encoded_text>
  python layered_cipher_decoder.py layer <decoder1> <decoder2> ... <encoded_text>
  python layered_cipher_decoder.py list

Decoder specs:
  - Plain decoder names: base64, rot13, hex, binary, morse, ...
  - Decoder with parameter: caesar:3, xor:42, xor:K, vigenere:LEMON

Available decoders:
  """
        + methods
        +
        """

Examples:
  python layered_cipher_decoder.py auto "SGVsbG8gV29ybGQ="
  python layered_cipher_decoder.py decode caesar:3 "KHOOR ZRUOG"
  python layered_cipher_decoder.py decode vigenere:LEMON "LXFOPV EF RNHR"
  python layered_cipher_decoder.py layer base64 reverse "PT1RZ2J5OTJW"
  python layered_cipher_decoder.py layer hex xor:7 "4f4b4c4c48"
"""
    )


def print_interactive_menu() -> None:
    options = {
        "1": "Auto detect",
        "2": "Decode one method",
        "3": "Layered decode",
        "4": "List methods",
        "5": "Help",
        "0": "Exit",
    }

    while True:
        print("\nSYNEXIS INTERACTIVE DECODER")
        for key, label in options.items():
            print(f"  {key}. {label}")
        choice = input("Choose option: ").strip()

        if choice == "0":
            return
        if choice == "1":
            text = input("Enter encoded text: ").strip()
            auto_detect(text)
            continue
        if choice == "2":
            method = input("Decoder (e.g. base64, caesar:3, xor:42): ").strip()
            text = input("Enter encoded text: ").strip()
            output = run_decoder(method, text)
            if output is None:
                print("Failed to decode. Check decoder name/parameter.")
            else:
                print("Result:")
                print(output)
            continue
        if choice == "3":
            layers = input("Enter decoders separated by space: ").strip().split()
            text = input("Enter encoded text: ").strip()
            layered_decode(text, layers)
            continue
        if choice == "4":
            print("Available methods:")
            for name in sorted(DECODERS):
                print(f"- {name}")
            continue
        if choice == "5":
            print_help()
            continue

        print("Invalid option.")


def main() -> None:
    if len(sys.argv) < 2:
        print_interactive_menu()
        return

    command = sys.argv[1].lower()

    if command in {"-h", "--help", "help"}:
        print_help()
        return

    if command == "list":
        print("Available decoders:")
        for name in sorted(DECODERS):
            print(f"- {name}")
        return

    if command == "auto":
        if len(sys.argv) < 3:
            print("Usage: python layered_cipher_decoder.py auto <encoded_text>")
            return
        text = " ".join(sys.argv[2:])
        auto_detect(text)
        return

    if command == "decode":
        if len(sys.argv) < 4:
            print("Usage: python layered_cipher_decoder.py decode <decoder> <encoded_text>")
            return
        spec = sys.argv[2]
        text = " ".join(sys.argv[3:])
        output = run_decoder(spec, text)
        if output is None:
            print(f"Decode failed for decoder: {spec}")
        else:
            print(output)
        return

    if command == "layer":
        if len(sys.argv) < 5:
            print("Usage: python layered_cipher_decoder.py layer <decoder1> <decoder2> ... <encoded_text>")
            return
        steps = sys.argv[2:-1]
        text = sys.argv[-1]
        layered_decode(text, steps)
        return

    print(f"Unknown command: {command}")
    print("Use --help for usage information.")


if __name__ == "__main__":
    main()
