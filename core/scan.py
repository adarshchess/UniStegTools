import numpy as np
from PIL import Image
import piexif


def scan_lsb_patterns(image_path):
    """
    Analyze the least significant bits (LSBs) of an image to check for hidden data.
    Strategy:
      - Extract LSBs from all RGB channels.
      - Look at the first 32 bits: if they decode to a plausible payload length, flag it.
      - Optionally, measure randomness of LSBs (uniform distribution vs structured).
    """
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        arr = np.array(img)

    flat = arr.reshape(-1, 3)
    bits = []
    for i in range(flat.shape[0]):
        for ch in range(3):
            bits.append(flat[i, ch] & 1)

    # First 32 bits = header candidate
    header_bits = bits[:32]
    header_bytes = _bits_to_bytes(header_bits)
    payload_len = int.from_bytes(header_bytes, byteorder="big")

    # Simple heuristic: if payload_len is >0 and less than image capacity, flag possible hidden data
    capacity_bits = arr.shape[0] * arr.shape[1] * 3
    if 0 < payload_len * 8 <= capacity_bits:
        return f"Possible hidden payload detected (length={payload_len} bytes)."
    else:
        return "No obvious LSB payload detected."


def scan_metadata(image_path):
    """
    Inspect EXIF metadata for anomalies.
    Strategy:
      - Extract EXIF tags using piexif.
      - Report unusual or suspicious fields (GPS, UserComment, etc).
    """
    try:
        exif_dict = piexif.load(image_path)
    except Exception:
        return "No EXIF metadata found."

    anomalies = []
    for ifd_name in exif_dict:
        for tag, value in exif_dict[ifd_name].items():
            if isinstance(value, bytes):
                try:
                    value = value.decode(errors="ignore")
                except Exception:
                    pass
            # Flag suspicious tags
            if tag in (piexif.ExifIFD.UserComment, piexif.GPSIFD.GPSLatitude, piexif.GPSIFD.GPSLongitude):
                anomalies.append((tag, value))

    if anomalies:
        return f"Suspicious metadata fields: {anomalies}"
    else:
        return "No suspicious metadata detected."


def _bits_to_bytes(bits):
    """
    Helper: convert list of bits back into bytes.
    """
    b = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bits):
                byte = (byte << 1) | bits[i + j]
        b.append(byte)
    return bytes(b)
