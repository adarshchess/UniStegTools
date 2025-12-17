# core/image_lsb.py

from PIL import Image  # Pillow: image I/O and pixel access
import numpy as np     # NumPy: efficient array manipulation


def _read_payload_bytes(payload_path):
    """
    Reads the payload file (the secret) as raw bytes.
    Returns b'' if the file is empty.
    """
    with open(payload_path, "rb") as f:         # Open payload in binary mode
        data = f.read()                         # Read all bytes
    return data


def _build_header(payload_len):
    """
    Create a fixed-size header to store payload length (in bytes).
    We use 32-bit unsigned integer, big-endian.

    Header format: 4 bytes representing the payload length.
    This allows the extract function to know how many bits to read.
    """
    # Convert integer length to 4 bytes, big-endian (network order)
    return payload_len.to_bytes(4, byteorder="big")


def _image_to_bit_capacity(img_array):
    """
    Calculate how many bits we can store:
    We use 1 LSB per color channel (R, G, B).
    Capacity = total pixels * 3 bits (for RGB).
    """
    h, w, c = img_array.shape                   # Height, width, channels
    if c < 3:
        raise ValueError("Image must have at least 3 channels (RGB).")
    return h * w * 3


def _bytes_to_bits(byte_data):
    """
    Convert a bytes object into a list of bits (integers 0 or 1).
    """
    bits = []
    for byte in byte_data:                      # Iterate over each byte
        for i in range(8):                      # 8 bits per byte
            # Extract bit from most significant to least significant (big-endian within byte)
            bits.append((byte >> (7 - i)) & 1)
    return bits


def _bits_to_bytes(bits):
    """
    Convert a list of bits (0/1) back into bytes.
    Expects length to be a multiple of 8; extra bits are ignored.
    """
    out = bytearray()
    for i in range(0, len(bits) // 8):          # Process 8 bits at a time
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i * 8 + j]
        out.append(byte)
    return bytes(out)


def embed_lsb_png(input_path, payload_path, output_path):
    """
    Embed payload bytes into the least significant bits of the input PNG's RGB channels.
    Writes a new PNG at output_path containing the hidden payload.

    Data layout:
      [4-byte header: payload length] + [payload bytes]
    Each bit is stored in the LSB of R, G, or B channel sequentially.
    """
    # Open the image with Pillow; ensure RGB mode for predictable 3-channel data
    with Image.open(input_path) as img:
        img = img.convert("RGB")                # Enforce RGB (no alpha channel for simplicity)
        arr = np.array(img)                     # Convert to NumPy array: shape (H, W, 3)

    # Prepare payload
    payload = _read_payload_bytes(payload_path) # Read secret data from file as bytes
    header = _build_header(len(payload))        # 4-byte header representing payload length
    full_data = header + payload                # Concatenate header + payload

    # Convert to bits for embedding
    data_bits = _bytes_to_bits(full_data)       # List of 0/1 bits
    capacity_bits = _image_to_bit_capacity(arr) # Total bits we can store in image

    # Check capacity
    if len(data_bits) > capacity_bits:          # If payload doesn't fit, fail early
        raise ValueError(
            f"Payload too large: need {len(data_bits)} bits, but image holds {capacity_bits} bits."
        )

    # Flatten pixel channels into a 1D view: R,G,B,R,G,B,...
    flat = arr.reshape(-1, 3)                   # Shape (H*W, 3)
    # We'll walk through the channels and set each LSB to our next data bit
    bit_idx = 0
    for i in range(flat.shape[0]):              # Iterate each pixel
        for ch in range(3):                     # Iterate R, G, B channels
            if bit_idx >= len(data_bits):       # Stop once we've embedded all bits
                break
            # Cast to int for bitwise ops, then back to uint8
            flat[i, ch] = np.uint8((int(flat[i, ch]) & ~1) | data_bits[bit_idx])
            bit_idx += 1
        if bit_idx >= len(data_bits):
            break
        

    # Reshape back to original image shape
    stego_arr = flat.reshape(arr.shape)         # Same H, W, 3 as original
    stego_img = Image.fromarray(stego_arr, mode="RGB")  # Build a Pillow Image from array

    # Save as PNG to preserve exact pixel values (PNG is lossless)
    stego_img.save(output_path, format="PNG")   # Write the stego image to disk


def extract_lsb_png(stego_path, output_payload_path):
    """
    Extract payload bytes from the LSBs of an RGB PNG previously embedded with embed_lsb_png.

    Steps:
      1) Read 32 bits (4 bytes) header to get payload length.
      2) Read payload_len bytes from subsequent bits.
      3) Write recovered payload to output_payload_path.
    """
    # Open stego image and ensure RGB
    with Image.open(stego_path) as img:
        img = img.convert("RGB")
        arr = np.array(img)

    # Read bits sequentially from R, G, B channels
    flat = arr.reshape(-1, 3)
    bits = []
    for i in range(flat.shape[0]):
        for ch in range(3):
            bits.append(flat[i, ch] & 1)       # Take LSB (value 0 or 1)

    # First 32 bits (4 bytes) are the header (payload length)
    header_bits = bits[:32]                     # Slice first 32 bits
    header_bytes = _bits_to_bytes(header_bits)  # Convert bits to bytes
    if len(header_bytes) < 4:
        raise ValueError("Corrupt or insufficient data for header.")
    payload_len = int.from_bytes(header_bytes, byteorder="big")  # Recover integer length

    # Next payload_len bytes = payload
    payload_bits_needed = payload_len * 8       # Number of bits to read
    payload_bits = bits[32:32 + payload_bits_needed]
    recovered = _bits_to_bytes(payload_bits)    # Convert bits back to bytes

    # Basic integrity check: recovered length matches header
    if len(recovered) != payload_len:
        raise ValueError("Recovered payload length mismatch. Image may not contain valid embedded data.")

    # Write the recovered payload to disk
    with open(output_payload_path, "wb") as f:
        f.write(recovered)
