# core/adaptive_rgb_stego.py

from __future__ import annotations
from pathlib import Path
import hashlib, zlib, random
from typing import List, Tuple
import numpy as np
from PIL import Image

MAGIC = b"ARSG"
HEADER_SIZE_BYTES = 16  # MAGIC(4) + LEN(4) + LEN_INV(4) + CRC32(4)
HEADER_SIZE_BITS = HEADER_SIZE_BYTES * 8

class AdaptiveConfig:
    def __init__(self, min_noise: int = 12, mid_noise: int = 24, max_capacity_ratio: float = 0.7, stego_guard: bool = False):
        self.min_noise = min_noise
        self.mid_noise = mid_noise
        self.max_capacity_ratio = max_capacity_ratio
        self.stego_guard = stego_guard  # optional, default OFF

def embed_adaptive_rgb(input_image_path: str, payload_path: str, output_image_path: str, key: str, config: AdaptiveConfig = AdaptiveConfig()):
    img = Image.open(input_image_path).convert("RGB")
    arr = np.array(img, dtype=np.uint8)
    H, W, C = arr.shape

    payload = Path(payload_path).read_bytes()
    header_plain = _build_header(payload)

    noise = _compute_noise_scores(arr)
    rng = _rng_from_key(key)
    positions = _eligible_positions(arr.shape, noise, config, rng)

    total_needed_bits = len(payload) * 8 + HEADER_SIZE_BITS
    hard_cap_bits = int(config.max_capacity_ratio * len(positions))
    if total_needed_bits > hard_cap_bits:
        raise ValueError(f"Payload too large: need {total_needed_bits}, cap {hard_cap_bits}")

    # Header whitening
    header_bits = list(_bytes_to_bits(header_plain))
    keystream_bits = _keystream_bits(rng, HEADER_SIZE_BITS)
    header_bits_whitened = [hb ^ kb for hb, kb in zip(header_bits, keystream_bits)]

    arr_out = arr.copy()
    # Write header
    for i in range(HEADER_SIZE_BITS):
        y, x, ch = positions[i]
        arr_out[y, x, ch] = (arr_out[y, x, ch] & 0xFE) | header_bits_whitened[i]
    # Write payload
    payload_bits_iter = _bytes_to_bits(payload)
    for j in range(len(payload) * 8):
        y, x, ch = positions[HEADER_SIZE_BITS + j]
        arr_out[y, x, ch] = (arr_out[y, x, ch] & 0xFE) | next(payload_bits_iter)

    Image.fromarray(arr_out, "RGB").save(output_image_path)

def extract_adaptive_rgb(stego_image_path: str, output_payload_path: str, key: str, config: AdaptiveConfig = AdaptiveConfig()):
    img = Image.open(stego_image_path).convert("RGB")
    arr = np.array(img, dtype=np.uint8)

    noise = _compute_noise_scores(arr)
    rng = _rng_from_key(key)
    positions = _eligible_positions(arr.shape, noise, config, rng)

    header_bits_whitened = _read_bits(arr, positions[:HEADER_SIZE_BITS])
    keystream_bits = _keystream_bits(rng, HEADER_SIZE_BITS)
    header_bits = [hb ^ kb for hb, kb in zip(header_bits_whitened, keystream_bits)]
    header_bytes = _bits_to_bytes(header_bits)

    magic, payload_len, payload_len_inv, payload_crc = _parse_header(header_bytes)
    if magic != MAGIC: raise ValueError("Invalid header magic")
    if payload_len_inv != (~payload_len & 0xFFFFFFFF): raise ValueError("Header LEN redundancy failed")

    total_payload_bits = payload_len * 8
    payload_bits = positions[HEADER_SIZE_BITS:HEADER_SIZE_BITS + total_payload_bits]
    payload_bytes = _bits_to_bytes(_read_bits(arr, payload_bits))

    crc = zlib.crc32(payload_bytes) & 0xFFFFFFFF
    if crc != payload_crc: raise ValueError("CRC mismatch")

    Path(output_payload_path).write_bytes(payload_bytes)

# ===== Helpers =====
def _build_header(payload: bytes) -> bytes:
    length = len(payload)
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    length_inv = (~length) & 0xFFFFFFFF
    return MAGIC + length.to_bytes(4,"little") + length_inv.to_bytes(4,"little") + crc.to_bytes(4,"little")

def _parse_header(b: bytes) -> Tuple[bytes,int,int,int]:
    return b[:4], int.from_bytes(b[4:8],"little"), int.from_bytes(b[8:12],"little"), int.from_bytes(b[12:16],"little")

def _rng_from_key(key: str) -> random.Random:
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest(),"big")
    return random.Random(seed)

def _keystream_bits(rng: random.Random, n_bits: int) -> List[int]:
    out = []
    for _ in range((n_bits+7)//8):
        byte = rng.getrandbits(8)
        for i in range(8): out.append((byte>>i)&1)
    return out[:n_bits]

def _compute_noise_scores(arr: np.ndarray) -> np.ndarray:
    # Ignore LSBs so embedding does not affect noise estimation
    arr_clean = arr & 0xFE

    R = arr_clean[..., 0].astype(np.float32)
    G = arr_clean[..., 1].astype(np.float32)
    B = arr_clean[..., 2].astype(np.float32)

    Y = 0.299*R+0.587*G+0.114*B
    H,W = Y.shape
    Yp = np.pad(Y,((1,1),(1,1)),mode="edge")
    neighbors = [Yp[0:H,0:W],Yp[0:H,1:W+1],Yp[0:H,2:W+2],Yp[1:H+1,0:W],Yp[1:H+1,2:W+2],Yp[2:H+2,0:W],Yp[2:H+2,1:W+1],Yp[2:H+2,2:W+2]]
    diffs = [np.abs(Y-n) for n in neighbors]
    return np.mean(diffs,axis=0).astype(np.uint16)

def _eligible_positions(shape: Tuple[int,int,int], noise: np.ndarray, config: AdaptiveConfig, rng: random.Random) -> List[Tuple[int,int,int]]:
    H,W,C = shape
    pixels=[]
    for y in range(H):
        for x in range(W):
            n=int(noise[y,x])
            if n>=config.min_noise:
                bits_here=2 if n>=config.mid_noise else 1
                pixels.append((y,x,bits_here))
    rng.shuffle(pixels)
    positions=[]
    for (y,x,bits_here) in pixels:
        for _ in range(bits_here):
            # fixed bias: Blue most likely, then Green, then Red
            r=rng.random()
            if r<0.1: ch=0
            elif r<0.4: ch=1
            else: ch=2
            positions.append((y,x,ch))
    rng.shuffle(positions)
    return positions

def _bytes_to_bits(b: bytes):
    for byte in b:
        for i in range(8): yield (byte>>i)&1

def _bits_to_bytes(bits: List[int]) -> bytes:
    out=bytearray()
    for i in range(0,len(bits),8):
        chunk=bits[i:i+8]; byte=0
        for j,bit in enumerate(chunk): byte|=(bit&1)<<j
        out.append(byte)
    return bytes(out)

def _read_bits(arr: np.ndarray, positions: List[Tuple[int,int,int]]) -> List[int]:
    return [(arr[y,x,ch]&1) for (y,x,ch) in positions]
