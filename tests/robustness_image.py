# tests/robustness_image.py
"""
Robustness testing for image steganography methods.

Goal:
Automatically test how well different image steganography methods survive
common image transformations (resize, blur, brightness, JPEG compression).

Note: failures are expected and indicate known limitations of spatial-domain steganography.
This script is not user-facing, not part of CLI, and not interactive.
"""

import os
import shutil
import cv2
import numpy as np
from PIL import Image

# Import stego methods directly from core
from core.image_lsb import embed_lsb_png, extract_lsb_png
from core.adaptive_rgb_stego import embed_adaptive_rgb, extract_adaptive_rgb

# ===== STEP 1: Configuration =====

ORIGINAL_IMAGE = "tests/data/cover.png"   # path to a clean test image
PAYLOAD_FILE = "tests/data/secret.txt"    # path to a small payload file
TMP_DIR = "tests/tmp_results"
TEST_KEY = "testkey"                      # centralized key for adaptive method

METHODS = {
    "lsb": (embed_lsb_png, extract_lsb_png),
    "adaptive": (embed_adaptive_rgb, extract_adaptive_rgb),
}

DISTORTION_LEVELS = [1, 2, 50] # yaha hum manually per centage change set kar rahe hain kitna chahiye

# ===== STEP 3: Define transformations with distortion scaling =====

def transform_resize(in_path, out_path, distortion_percent):
    img = Image.open(in_path)
    w, h = img.size
    scale = 1.0 - (distortion_percent / 100.0)
    img_small = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    img_back = img_small.resize((w, h), Image.LANCZOS)
    img_back.save(out_path)

def transform_blur(in_path, out_path, distortion_percent):
    img = cv2.imread(in_path)
    kernel_size = 1 + 2 * int(distortion_percent / 10)
    if kernel_size < 3:
        kernel_size = 3
    blurred = cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)
    cv2.imwrite(out_path, blurred)

def transform_brightness(in_path, out_path, distortion_percent):
    img = cv2.imread(in_path)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    multiplier = 1.0 + (distortion_percent / 100.0)
    hsv[..., 2] = np.clip(hsv[..., 2] * multiplier, 0, 255)
    bright = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    cv2.imwrite(out_path, bright)

def transform_jpeg(in_path, out_path, distortion_percent):
    tmp_jpeg = out_path.replace(".png", ".jpg")
    img = Image.open(in_path)
    quality = max(100 - distortion_percent, 10)
    img.save(tmp_jpeg, "JPEG", quality=quality)
    img2 = Image.open(tmp_jpeg)
    img2.save(out_path, "PNG")
    os.remove(tmp_jpeg)

TRANSFORMATIONS = {
    "resize": transform_resize,
    "blur": transform_blur,
    "brightness": transform_brightness,
    "jpeg": transform_jpeg,
}

# ===== STEP 2 + 4: Embed once, then transform =====

def run_tests():
    if not ORIGINAL_IMAGE.lower().endswith(".png"):
        raise ValueError("Robustness tests expect a PNG cover image")

    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR)

    with open(PAYLOAD_FILE, "rb") as f:
        payload_bytes = f.read()

    results = {}

    for method_name, (embed_fn, extract_fn) in METHODS.items():
        print(f"\n=== Testing method: {method_name} ===")
        method_dir = os.path.join(TMP_DIR, method_name)
        os.makedirs(method_dir)

        stego_path = os.path.join(method_dir, "stego.png")

        # Embed payload once
        try:
            if method_name == "adaptive":
                embed_fn(ORIGINAL_IMAGE, PAYLOAD_FILE, stego_path, key=TEST_KEY)
            else:
                embed_fn(ORIGINAL_IMAGE, PAYLOAD_FILE, stego_path)
            print(f"Embedded payload with {method_name}")
        except Exception as e:
            print(f"Embedding failed for {method_name}: {e}")
            results[method_name] = {f"{t}_{lvl}": "embed_fail" for t in TRANSFORMATIONS for lvl in DISTORTION_LEVELS}
            continue

        # ✅ Initialize results dict for this method
        results[method_name] = {}

        # Try extraction on the clean stego image first
        try:
            recovered_path = os.path.join(method_dir, "recovered_clean.txt")
            if method_name == "adaptive":
                extract_fn(stego_path, recovered_path, key=TEST_KEY)
            else:
                extract_fn(stego_path, recovered_path)

            recovered = open(recovered_path, "rb").read()
            if recovered == payload_bytes:
                print("Clean extraction success ✅")
                results[method_name]["clean"] = "success"
            else:
                print("Clean extraction corrupted ⚠️")
                results[method_name]["clean"] = "corrupted"
        except Exception as e:
            print(f"Clean extraction failed ({method_name}): {e}")
            results[method_name]["clean"] = "fail"

        # Apply transformations at different distortion levels
        for tname, tfunc in TRANSFORMATIONS.items():
            for lvl in DISTORTION_LEVELS:
                key_name = f"{tname}_{lvl}"
                t_out = os.path.join(method_dir, f"stego_{key_name}.png")
                try:
                    tfunc(stego_path, t_out, lvl)
                except Exception as e:
                    print(f"Transformation {key_name} failed: {e}")
                    results[method_name][key_name] = "transform_fail"
                    continue

                # Try extraction
                try:
                    recovered_path = os.path.join(method_dir, f"recovered_{key_name}.txt")
                    if method_name == "adaptive":
                        extract_fn(t_out, recovered_path, key=TEST_KEY)
                    else:
                        extract_fn(t_out, recovered_path)

                    recovered = open(recovered_path, "rb").read()
                    if recovered == payload_bytes:
                        results[method_name][key_name] = "success"
                    else:
                        results[method_name][key_name] = "corrupted"
                except Exception as e:
                    print(f"Extraction failed ({method_name}, {key_name}): {e}")
                    results[method_name][key_name] = "fail"

    return results

# ===== STEP 7: Output summary =====

def print_summary(results):
    print("\n=== Robustness Summary ===")
    methods = list(results.keys())
    keys = ["clean"] + [f"{t}_{lvl}" for t in TRANSFORMATIONS.keys() for lvl in DISTORTION_LEVELS]

    # Print header
    print("method".ljust(12), end="")
    for k in keys:
        print(k.ljust(14), end="")
    print()

    # Print rows
    for m in methods:
        print(m.ljust(12), end="")
        for k in keys:
            outcome = results[m].get(k, "-")
            print(outcome.ljust(14), end="")
        print()

if __name__ == "__main__":
    results = run_tests()
    print_summary(results)
