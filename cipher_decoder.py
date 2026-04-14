#!/usr/bin/env python3
"""
SYNEXIS Cipher Decoder Tool
Command-line utility for decoding all cipher types
"""

import sys
import base64
import re
from typing import Callable, Dict

# Morse code dictionary
MORSE_DICT = {
    '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E',
    '..-.': 'F', '--.': 'G', '....': 'H', '..': 'I', '.---': 'J',
    '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O',
    '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T',
    '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y',
    '--..': 'Z',
    '-----': '0', '.----': '1', '..---': '2', '...--': '3', '....-': '4',
    '.....': '5', '-....': '6', '--...': '7', '---..': '8', '----.': '9',
}

def caesar_decode(text: str, show_all: bool = True) -> str:
    """Decode Caesar cipher - show all 25 shifts"""
    result = "CAESAR CIPHER - All 25 Shifts:\n" + "="*60 + "\n\n"
    text = text.upper()
    for shift in range(1, 26):
        decoded = ""
        for char in text:
            if 'A' <= char <= 'Z':
                # Try all possible decode shifts; subtracting shift performs decryption.
                decoded += chr((ord(char) - ord('A') - shift) % 26 + ord('A'))
            else:
                decoded += char
        result += f"Shift {shift:2d}: {decoded}\n"
    return result

def rot13_decode(text: str) -> str:
    """Decode ROT13"""
    result = ""
    for char in text:
        if 'A' <= char <= 'Z':
            result += chr((ord(char) - ord('A') + 13) % 26 + ord('A'))
        elif 'a' <= char <= 'z':
            result += chr((ord(char) - ord('a') + 13) % 26 + ord('a'))
        else:
            result += char
    return result

def base64_decode(text: str) -> str:
    """Decode Base64"""
    try:
        cleaned = ''.join(text.strip().split())
        if not cleaned:
            return "[ERROR] Base64 input is empty"
        missing = len(cleaned) % 4
        if missing:
            cleaned += '=' * (4 - missing)
        return base64.b64decode(cleaned, validate=False).decode('utf-8', errors='replace')
    except Exception as e:
        return f"[ERROR] Base64 decode failed: {e}"

def binary_decode(text: str) -> str:
    """Decode Binary (space-separated 8-bit bytes)"""
    try:
        cleaned = text.strip()
        if not cleaned:
            return "[ERROR] Binary input is empty"

        if re.fullmatch(r"[01]+", cleaned):
            if len(cleaned) % 8 != 0:
                return "[ERROR] Binary input length must be a multiple of 8"
            bytes_list = [cleaned[i:i + 8] for i in range(0, len(cleaned), 8)]
        else:
            bytes_list = cleaned.split()

        result = ""
        for byte in bytes_list:
            normalized = byte.lower().replace('0b', '')
            if not re.fullmatch(r"[01]{8}", normalized):
                return f"[ERROR] Invalid binary byte: {byte}"
            result += chr(int(normalized, 2))
        return result
    except Exception as e:
        return f"[ERROR] Binary decode failed: {e}"

def hex_decode(text: str) -> str:
    """Decode Hexadecimal"""
    try:
        hex_str = text.strip().lower().replace('0x', '')
        hex_str = ''.join(hex_str.split())
        if len(hex_str) % 2 != 0:
            return "[ERROR] Odd number of hex characters"
        if not hex_str:
            return "[ERROR] Hex input is empty"
        if not re.fullmatch(r"[0-9a-f]+", hex_str):
            return "[ERROR] Hex input contains non-hex characters"
        return bytes.fromhex(hex_str).decode('utf-8', errors='replace')
    except Exception as e:
        return f"[ERROR] Hex decode failed: {e}"

def morse_decode(text: str) -> str:
    """Decode Morse code (space between letters, ' / ' between words)"""
    try:
        normalized = text.strip().replace('|', ' / ')
        normalized = re.sub(r"\s+/\s+", " / ", normalized)
        words = normalized.split(' / ')
        result_words = []
        for word in words:
            letters = word.strip().split()
            word_str = ""
            for letter in letters:
                word_str += MORSE_DICT.get(letter, '?')
            result_words.append(word_str)
        return ' '.join(result_words)
    except Exception as e:
        return f"[ERROR] Morse decode failed: {e}"


DECODER_MAP: Dict[str, Callable[[str], str]] = {
    'caesar': caesar_decode,
    'rot13': rot13_decode,
    'base64': base64_decode,
    'binary': binary_decode,
    'hex': hex_decode,
    'morse': morse_decode,
}

def print_help():
    """Print help message"""
    help_text = """
╔════════════════════════════════════════════════════════════════════════╗
║               SYNEXIS Cipher Decoder - Command Line Tool               ║
╚════════════════════════════════════════════════════════════════════════╝

USAGE:
    python cipher_decoder.py <cipher_type> <input_text>

CIPHER TYPES:
    caesar          Caesar cipher (shows all 25 shifts)
    rot13           ROT13 cipher
    base64          Base64 decoder
    binary          Binary (space-separated 8-bit bytes)
    hex             Hexadecimal (space-separated or continuous)
    morse           Morse code (space between letters, ' / ' between words)

EXAMPLES:
    python cipher_decoder.py caesar "KHOOR ZRUOG"
    python cipher_decoder.py rot13 "URYYB JBEYQ"
    python cipher_decoder.py base64 "SGVsbG8gV29ybGQ="
    python cipher_decoder.py binary "01001000 01100101 01101100 01101100 01101111"
    python cipher_decoder.py hex "48 65 6C 6C 6F"
    python cipher_decoder.py morse ".... . .-.. .-.. --- / .-- --- .-. .-.. -.."

CAESAR CIPHER TIPS:
    - Scans all 25 shifts
    - Look for readable English words: THE, AND, FOR, YOU, etc.
    - Common first letter: E (12%), T (9%), A (8%)

BASE64 TIPS:
    - Ends with "=" (1 char) or "==" (2 chars)
    - Valid characters: A-Z, a-z, 0-9, +/
    - Always try first if you see "=" padding

HEX TIPS:
    - Pairs of hex digits: 48 65 6C 6C 6F = "Hello"
    - Can have spaces or be continuous
    - 41-5A = uppercase letters, 61-7A = lowercase

BINARY TIPS:
    - 8-bit bytes, space-separated
    - 65-90 = A-Z, 97-122 = a-z, 48-57 = 0-9
    - Common: 01001000=H, 01100101=e

MORSE TIPS:
    - Dot (.) = short, Dash (-) = long
    - Space between letters, " / " between words
    - A=.-, B=-..., E=., T=-

LAYERED DECODING:
    - If output looks like gibberish, decode it again with different cipher
    - Base64 → Caesar is very common
    - Hex → Binary → ASCII also common
    """
    print(help_text)

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help', 'help']:
        print_help()
        return

    cipher_type = sys.argv[1].lower()
    
    if len(sys.argv) < 3:
        print(f"[ERROR] Missing input text")
        print(f"Usage: python cipher_decoder.py {cipher_type} <input_text>")
        return

    # Join remaining args as input (in case there are spaces)
    input_text = ' '.join(sys.argv[2:])

    print(f"\n{'='*70}")
    print(f"Cipher Type: {cipher_type.upper()}")
    print(f"Input: {input_text[:100]}{'...' if len(input_text) > 100 else ''}")
    print(f"{'='*70}\n")

    try:
        decoder = DECODER_MAP.get(cipher_type)
        if decoder is None:
            print(f"[ERROR] Unknown cipher type: {cipher_type}")
            print(f"Valid types: {', '.join(DECODER_MAP.keys())}")
            return

        result = decoder(input_text)
        print(result)
        print(f"\n{'='*70}")

    except KeyboardInterrupt:
        print("\n\nExiting decoder.")
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
