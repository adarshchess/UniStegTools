# core/image_dct_stego.py
"""
DCT-based image steganography (transform-domain, JPEG-style), grayscale only.

Method summary:
- Convert image to grayscale and split into 8x8 blocks.
- Apply 2D DCT per block (cv2.dct), with JPEG-style pixel centering (subtract 128 before DCT).
- Choose a fixed mid-frequency coefficient (row=4, col=3).
- Embed 1 bit per block by adjusting the integer-rounded DCT coefficient's LSB.
- Inverse DCT to reconstruct stego image (add 128 after IDCT).

Header (little-endian, 12 bytes total):
- MAGIC: b"DCTG" (4 bytes)
- PAYLOAD_LENGTH: uint32 (4 bytes)
- CRC32: uint32 (4 bytes) of the payload bytes

Validation on extraction:
- Fail if MAGIC mismatch
- Fail if insufficient blocks for header/payload
- Fail if CRC mismatch
- Safety cap: payload_len must be <= capacity_bits // 8

Public API:
- embed_dct_image(input_image_path, payload_path, output_image_path)
- extract_dct_image(stego_image_path, output_payload_path)

Notes:
- 1 bit per 8x8 block, deterministic row-major traversal.
- Clear, interview-friendly implementation; no encryption, no randomness.
"""

from pathlib import Path
from typing import Iterator, Tuple, List
import numpy as np
import cv2
import zlib


# ====== Constants ======
_MAGIC = b"DCTG"
_HEADER_SIZE_BYTES = 12  # 4 + 4 + 4
_BLOCK_SIZE = 8
_COEFF_POS = (4, 3)  # mid-frequency coefficient (row=4, col=3)


# ====== Helpers: I/O and basic transforms ======

def _read_grayscale(path: Path) -> np.ndarray:
    """
    Read an image as grayscale float32 matrix.
    """
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image: {path}")
    # Convert to float32 for DCT
    return img.astype(np.float32)


def _write_grayscale(path: Path, img: np.ndarray) -> None:
    """
    Write a grayscale image (uint8).
    """
    img_u8 = np.clip(np.round(img), 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(path), img_u8):
        raise ValueError(f"Could not write image: {path}")


def _iterate_blocks(img: np.ndarray) -> Iterator[Tuple[int, int, np.ndarray]]:
    """
    Yield (row, col, block_view) for each 8x8 block in row-major order.
    The block_view is a read/write view into the original image slice.
    """
    h, w = img.shape
    for r in range(0, h - _BLOCK_SIZE + 1, _BLOCK_SIZE):
        for c in range(0, w - _BLOCK_SIZE + 1, _BLOCK_SIZE):
            yield r, c, img[r:r + _BLOCK_SIZE, c:c + _BLOCK_SIZE]


def _dct2(block: np.ndarray) -> np.ndarray:
    """
    2D DCT using cv2.dct. Input must be float32 (8x8).
    """
    return cv2.dct(block)


def _idct2(coeff: np.ndarray) -> np.ndarray:
    """
    2D inverse DCT using cv2.idct.
    """
    return cv2.idct(coeff)


# ====== Helpers: Bit/byte conversion and header ======

def _bytes_to_bits(data: bytes) -> List[int]:
    """
    Convert bytes to bits (LSB-first within each byte, little-endian bit order).
    """
    bits: List[int] = []
    for b in data:
        for i in range(8):
            bits.append((b >> i) & 1)
    return bits


def _bits_to_bytes(bits: List[int]) -> bytes:
    """
    Convert bits (LSB-first groups of 8) back to bytes.
    """
    if len(bits) % 8 != 0:
        raise ValueError("Bitstream length not multiple of 8")
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit_index in range(8):
            bit = bits[i + bit_index] & 1
            byte |= (bit << bit_index)
        out.append(byte)
    return bytes(out)


def _build_header(payload: bytes) -> bytes:
    """
    Header: MAGIC (4 bytes) + PAYLOAD_LENGTH (4 bytes LE) + CRC32 (4 bytes LE).
    """
    length = len(payload)
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    return _MAGIC + length.to_bytes(4, "little") + crc.to_bytes(4, "little")


def _parse_header(header_bytes: bytes) -> Tuple[int, int]:
    """
    Return (payload_length, crc32) from header bytes.
    """
    if len(header_bytes) != _HEADER_SIZE_BYTES:
        raise ValueError("Malformed header: size mismatch")
    magic = header_bytes[:4]
    if magic != _MAGIC:
        raise ValueError("Header MAGIC mismatch")
    length = int.from_bytes(header_bytes[4:8], "little", signed=False)
    crc = int.from_bytes(header_bytes[8:12], "little", signed=False)
    return length, crc


# ====== Helpers: Coefficient embedding/extraction ======

def _embed_bit_in_coeff(coeff: np.ndarray, bit: int, pos: Tuple[int, int]) -> None:
    r, c = pos
    val = coeff[r, c]

    # ensure magnitude is not near zero
    mag = max(abs(val), 5.0)

    if bit == 1:
        coeff[r, c] = +mag
    else:
        coeff[r, c] = -mag



def _extract_bit_from_coeff(coeff: np.ndarray, pos: Tuple[int, int]) -> int:
    r, c = pos
    return 1 if coeff[r, c] >= 0 else 0


# ====== Public API: Embed ======

def embed_dct_image(
    input_image_path: str,
    payload_path: str,
    output_image_path: str
) -> None:
    """
    Embed payload bytes into a grayscale image using DCT-domain LSB on a mid-frequency coefficient.
    - 1 bit per 8x8 block, row-major traversal.
    - Fails fast if capacity insufficient (blocks < header_bits + payload_bits).
    - Uses JPEG-style pixel centering: subtract 128 before DCT, add 128 after IDCT.
    """
    in_path = Path(input_image_path)
    payload_path = Path(payload_path)
    out_path = Path(output_image_path)

    # Read inputs
    img = _read_grayscale(in_path)
    with payload_path.open("rb") as f:
        payload = f.read()

    # Build header and full bitstream
    header = _build_header(payload)  # 12 bytes
    bitstream = _bytes_to_bits(header + payload)
    total_bits = len(bitstream)

    # Compute capacity: number of 8x8 blocks
    h, w = img.shape
    blocks_h = h // _BLOCK_SIZE
    blocks_w = w // _BLOCK_SIZE
    capacity_bits = blocks_h * blocks_w

    if capacity_bits < total_bits:
        raise ValueError(
            f"Insufficient blocks: capacity={capacity_bits} bits, needed={total_bits} bits"
        )

    # Create working copy
    stego = img.copy()

    # Embed bits block-by-block
    bit_idx = 0
    for r, c, block in _iterate_blocks(stego):
        if bit_idx >= total_bits:
            break

        # JPEG-style centering: subtract 128 before DCT
        centered = block - 128.0
        dct_block = _dct2(centered)

        # Embed bit in chosen coefficient
        _embed_bit_in_coeff(dct_block, bitstream[bit_idx], _COEFF_POS)
        bit_idx += 1

        # Inverse DCT and write back; add 128 after IDCT
        idct_block = _idct2(dct_block) + 128.0
        stego[r:r + _BLOCK_SIZE, c:c + _BLOCK_SIZE] = idct_block

    # Save output
    _write_grayscale(out_path, stego)


# ====== Public API: Extract ======

def extract_dct_image(
    stego_image_path: str,
    output_payload_path: str
) -> None:
    """
    Extract payload bytes from a grayscale image embedded via DCT-domain LSB method.
    - Reads header first (12 bytes -> 96 bits) using a single block iterator.
    - Validates MAGIC and CRC.
    - Uses JPEG-style centering (subtract 128 before DCT).
    - Includes a sanity cap on payload length vs. capacity.
    """
    in_path = Path(stego_image_path)
    out_path = Path(output_payload_path)

    # Read stego image
    img = _read_grayscale(in_path)

    # Capacity (blocks) for sanity checks
    h, w = img.shape
    blocks_h = h // _BLOCK_SIZE
    blocks_w = w // _BLOCK_SIZE
    capacity_bits = blocks_h * blocks_w

    # Single iterator for clean, sequential block consumption
    blocks = _iterate_blocks(img)

    # --- Read header bits (96 bits) ---
    header_bits_needed = _HEADER_SIZE_BYTES * 8
    header_bits: List[int] = []
    try:
        for _ in range(header_bits_needed):
            r, c, block = next(blocks)
            centered = block - 128.0
            bit = _extract_bit_from_coeff(_dct2(centered), _COEFF_POS)
            header_bits.append(bit)
    except StopIteration:
        raise ValueError("Insufficient blocks for header")

    header_bytes = _bits_to_bytes(header_bits)
    payload_len, crc_expected = _parse_header(header_bytes)

    # --- Safety cap: prevent bogus headers from reading insane payloads ---
    if payload_len > capacity_bits // 8:
        raise ValueError("Suspicious payload length")

    # --- Read payload bits ---
    payload_bits_needed = payload_len * 8
    payload_bits: List[int] = []
    try:
        for _ in range(payload_bits_needed):
            r, c, block = next(blocks)
            centered = block - 128.0
            bit = _extract_bit_from_coeff(_dct2(centered), _COEFF_POS)
            payload_bits.append(bit)
    except StopIteration:
        raise ValueError(
            f"Insufficient blocks for payload: expected {payload_bits_needed} bits"
        )

    payload_bytes = _bits_to_bytes(payload_bits)

    # --- CRC check ---
    crc_actual = zlib.crc32(payload_bytes) & 0xFFFFFFFF
    if crc_actual != crc_expected:
        raise ValueError("CRC mismatch: payload may be corrupted")

    # Write payload
    with out_path.open("wb") as f:
        f.write(payload_bytes)
