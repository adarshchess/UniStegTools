# core/text_stego.py
"""
Whitespace-based document steganography for plain text (.txt).

Technique:
- Encode bits in spaces between words:
  - Single space " " => bit 0
  - Double space "  " => bit 1
- Only spaces between words are modified.
- Characters, word order, punctuation, and newlines are preserved.

Public API: ye waale fns will be imported in main.py 
- embed_text_stego(input_text_path, payload_path, output_text_path)
- extract_text_stego(stego_text_path, output_payload_path)
"""

import re 
from typing import List


# ===== Helper fns =====

def _bytes_to_bits(data: bytes) -> List[int]:
    bits = []
    for b in data:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    return bits


def _bits_to_bytes(bits: List[int]) -> bytes:
    if len(bits) % 8 != 0:
        raise ValueError("Malformed stego data: bitstream length is not a multiple of 8")
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | (bits[i + j] & 1)
        out.append(byte)
    return bytes(out)


def _build_header(payload_len: int) -> bytes:
    if payload_len < 0 or payload_len > 0xFFFFFFFF:
        raise ValueError("Payload length out of bounds for 32-bit header")
    # 4 bytes, big-endian unsigned int
    return payload_len.to_bytes(4, byteorder="big", signed=False)


def _parse_header(header_bits: List[int]) -> int:
    if len(header_bits) != 32:
        raise ValueError("Malformed stego data: insufficient header bits")
    header_bytes = _bits_to_bytes(header_bits)
    return int.from_bytes(header_bytes, byteorder="big", signed=False)


def _tokenize_preserve(text: str) -> List[str]:
    """
    Split text into tokens of non-whitespace (words/punctuation) and whitespace,
    preserving exact original content. Newlines and tabs remain in whitespace tokens.
    """
    return re.findall(r'\S+|\s+', text)


def _is_space_gap(token: str) -> bool:
    """
    Returns True if the token is a candidate gap composed ONLY of spaces (no tabs, no newlines).
    """
    if not token or token.strip() != "":
        return False
    # token is purely whitespace; ensure it's spaces-only (no \n, \r, \t)
    return all(ch == ' ' for ch in token)


# ===== Public API =====

def embed_text_stego(input_text_path: str, payload_path: str, output_text_path: str) -> None:
    """
    Embed a payload into a plain text document by encoding bits into spaces between words.

    Encoding:
      - bit 0 => single space " "
      - bit 1 => double space "  "

    Constraints:
      - Do not change characters, punctuation, or newlines.
      - Only modify spaces between words (spaces-only tokens).
      - Raises if insufficient word gaps to hold header+payload bits.
    """
    # Read inputs
    with open(input_text_path, "r", encoding="utf-8") as f:
        original_text = f.read()
    with open(payload_path, "rb") as f:
        payload = f.read()

    header = _build_header(len(payload))
    bitstream = _bytes_to_bits(header + payload)

    tokens = _tokenize_preserve(original_text)
    bit_idx = 0
    total_bits = len(bitstream)

    # Traverse tokens; for each spaces-only gap, encode next bit
    for i, tok in enumerate(tokens):
        if bit_idx >= total_bits:
            break
        if _is_space_gap(tok):
            bit = bitstream[bit_idx]
            # Encode strictly as one or two spaces
            tokens[i] = ' ' if bit == 0 else '  '
            bit_idx += 1

    if bit_idx < total_bits:
        raise ValueError(
            f"Insufficient space in document: needed {total_bits} gaps, found {bit_idx}"
        )

    # Reconstruct text exactly (non-gap tokens unchanged; only selected space tokens modified)
    stego_text = ''.join(tokens)
    with open(output_text_path, "w", encoding="utf-8") as f:
        f.write(stego_text)


def extract_text_stego(stego_text_path: str, output_payload_path: str) -> None:
    """
    Extract a payload from a stego text document by decoding spaces between words.

    Decoding:
      - single space " " => bit 0
      - double space "  " => bit 1
      - any other spaces-only token length (e.g., 3+) is invalid and raises error

    Validation:
      - Requires 32 header bits (payload length, big-endian).
      - Requires payload_length * 8 bits thereafter.
      - Raises for malformed data or insufficient bits.
    """
    with open(stego_text_path, "r", encoding="utf-8") as f:
        stego_text = f.read()

    tokens = _tokenize_preserve(stego_text)

    bits = []
    for tok in tokens:
        if _is_space_gap(tok):
            if tok == ' ':
                bits.append(0)
            elif tok == '  ':
                bits.append(1)
            else:
                # spaces-only token with length != 1 or 2 is considered invalid for this scheme
                raise ValueError("Malformed stego data: unexpected space run length")

    # Need at least 32 bits for header
    if len(bits) < 32:
        raise ValueError("Malformed stego data: insufficient bits for header")

    header_bits = bits[:32]
    payload_len = _parse_header(header_bits)
    needed_payload_bits = payload_len * 8
    total_needed = 32 + needed_payload_bits

    if len(bits) < total_needed:
        raise ValueError(
            f"Corrupted or incomplete payload: expected {needed_payload_bits} payload bits, "
            f"found {len(bits) - 32}"
        )

    payload_bits = bits[32:32 + needed_payload_bits]
    payload_bytes = _bits_to_bytes(payload_bits)

    if len(payload_bytes) != payload_len:
        raise ValueError(
            f"Payload length mismatch: header says {payload_len} bytes, reconstructed {len(payload_bytes)} bytes"
        )

    with open(output_payload_path, "wb") as f:
        f.write(payload_bytes)
