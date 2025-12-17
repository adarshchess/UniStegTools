import struct
import numpy as np
from PIL import Image

# Header format:
# MAGIC (4 bytes) + width (uint32) + height (uint32) + channels (uint32) + payload_len (uint32)
# Total header size: 4 + 4*4 = 20 bytes
MAGIC = b'IMSG'  # "Image SteG" signature
HEADER_FMT = "<4sIIII"  # little-endian: 4s, 4x uint32
HEADER_SIZE = struct.calcsize(HEADER_FMT)

def _bytes_to_bits(data: bytes):
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits

def _bits_to_bytes(bits):
    b = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bits):
                byte = (byte << 1) | bits[i + j]
        b.append(byte)
    return bytes(b)

def embed_image_into_image(cover_path: str, payload_path: str, output_path: str, preserve_exif: bool = True):
    # Open cover and payload images
    cover_img = Image.open(cover_path).convert("RGB")
    payload_img = Image.open(payload_path).convert("RGB")

    # Optional: preserve EXIF if present and save to JPEG
    exif_bytes = cover_img.info.get("exif") if preserve_exif else None

    cover_arr = np.array(cover_img)  # shape: (H, W, 3), dtype=uint8
    payload_arr = np.array(payload_img)  # shape: (h, w, 3), dtype=uint8

    # Payload bytes
    payload_bytes = payload_arr.tobytes()
    payload_len = len(payload_bytes)

    # Build header
    width, height = payload_img.width, payload_img.height
    channels = payload_arr.shape[2] if payload_arr.ndim == 3 else 1
    if channels != 3:
        raise ValueError("Only RGB payloads (3 channels) are supported for now.")
    header = struct.pack(HEADER_FMT, MAGIC, width, height, channels, payload_len)

    # Combine header + payload
    data = header + payload_bytes
    bits = _bytes_to_bits(data)

    # Capacity check
    capacity_bits = cover_arr.size  # total number of channels across image; one LSB per channel
    if len(bits) > capacity_bits:
        raise ValueError(f"Payload too large. Need {len(bits)} bits, cover has {capacity_bits} bits.")

    # Embed bits into LSBs
    flat = cover_arr.flatten()
    for i, bit in enumerate(bits):
        flat[i] = np.uint8((int(flat[i]) & ~1) | bit)
    stego_arr = flat.reshape(cover_arr.shape)

    # Save stego image
    stego_img = Image.fromarray(stego_arr, mode="RGB")
    # If saving JPEG and you want to keep EXIF, pass exif=exif_bytes
    if exif_bytes and output_path.lower().endswith((".jpg", ".jpeg")):
        stego_img.save(output_path, exif=exif_bytes)
    else:
        stego_img.save(output_path)

    return f"Embedded payload image ({payload_path}) into {output_path}"

def extract_image_from_image(stego_path: str, output_path: str):
    stego_img = Image.open(stego_path).convert("RGB")
    stego_arr = np.array(stego_img)

    # Extract all LSBs
    bits = (stego_arr.flatten() & 1).tolist()

    # First, try to reconstruct at least the header
    header_bits = bits[:HEADER_SIZE * 8]
    header_bytes = _bits_to_bytes(header_bits)
    try:
        magic, width, height, channels, payload_len = struct.unpack(HEADER_FMT, header_bytes)
    except struct.error:
        raise ValueError("Could not parse header: malformed or insufficient bits.")

    if magic != MAGIC:
        raise ValueError("Magic header not found. This image likely does not contain an embedded payload image.")

    # Compute total bits needed: header + payload
    total_bits_needed = (HEADER_SIZE + payload_len) * 8
    if total_bits_needed > len(bits):
        raise ValueError("Insufficient bits in stego image for declared payload length.")

    # Extract payload bytes after header
    payload_bits = bits[HEADER_SIZE * 8 : HEADER_SIZE * 8 + payload_len * 8]
    payload_bytes = _bits_to_bytes(payload_bits)

    # Rebuild payload image
    if channels != 3:
        raise ValueError("Only RGB payloads (3 channels) are supported for now.")
    payload_arr = np.frombuffer(payload_bytes, dtype=np.uint8).reshape((height, width, channels))
    payload_img = Image.fromarray(payload_arr, mode="RGB")
    payload_img.save(output_path)

    return f"Extracted embedded payload image into {output_path}"
