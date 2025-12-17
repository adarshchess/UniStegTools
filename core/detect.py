# core/detect.py

def detect_file_type(path):
    """
    Detects the type of a file based on its magic number (signature).
    Reads the first few bytes of the file and compares them to known patterns.
    """
    with open(path, "rb") as f:        # Open file in binary mode
        sig = f.read(8)                # Read first 8 bytes (signature)

    # PNG files start with 89 50 4E 47 ("89PNG")
    if sig.startswith(b"\x89PNG"):
        return "image"

    # JPEG files start with FF D8
    elif sig.startswith(b"\xFF\xD8"):
        return "jpeg"

    # WAV audio files start with "RIFF"
    elif sig.startswith(b"RIFF"):
        return "wav"

    # If none match, return unknown
    else:
        return "unknown"