# Universal Steganography Tool

Hello  
This is my first open source project and also my first proper project in information security.  
This tool is a **command line based steganography toolkit** written in Python that supports **multiple steganography domains** and **multiple file types**.

The goal of this project was not to build a fancy frontend or enterprise software, but to deeply understand how steganography works across different domains and to implement those techniques in a clean and explainable way.

---

## What this tool does

This tool allows you to

- Embed hidden data inside different types of files  
- Extract that hidden data back  
- Work across multiple steganography domains  
- Test robustness of steganography methods under tampering  

All operations are performed using a single CLI interface.

---

## Steganography domains covered

### Spatial Domain Steganography

These methods directly modify the original data representation (pixels or audio samples)

- Image LSB steganography (text into image)
- Image into Image steganography
- Adaptive RGB steganography (custom method)
- Audio steganography using PCM WAV files

---

### Text Domain Steganography

This domain hides data inside text formatting

- Text into Text steganography using whitespace encoding

---

### Transform Domain Steganography

This domain hides data in the frequency domain instead of raw pixels

- DCT based image steganography (JPEG style transform domain)

## Project structure

core/
├── image_lsb.py
├── image_embed.py
├── adaptive_rgb_stego.py
├── audio_stego.py
├── text_stego.py
├── image_dct_stego.py
├── detect.py
├── scan.py

tests/
├── robustness_image.py
├── data/

main.py
report.txt




## 🚀 Installation

Clone the repository and set up a virtual environment.

git clone https://github.com/adarshchess/UniStegTools.git
cd UniStegTools
python -m venv venv

activate the vir env by venv\Scripts\Activate.ps1
also install dependencies by
pip install -r requirements.txt

CLI Arguments
--embed → Embed payload into cover file.

--extract → Extract payload from stego file.

--scan → Scan image for LSB patterns and metadata.

--input → Path to cover/stego file (required).

--output → Path to output file.

--payload → Path to payload file (required for embedding).

--mode → Steganography method. Options: lsb, image, audio, adaptive, dct, text.

--key → Secret key (required for adaptive RGB).

Usage Examples

Scan
python main.py --scan --input cover.png


Image LSB (Text → Image)
Embed:
python main.py --embed --input cover.png --payload secret.txt --output stego.png --mode lsb

Extract:
python main.py --extract --input stego.png --output recovered.txt --mode lsb


Image-in-Image
Embed:
python main.py --embed --input cover.png --payload hidden.png --output stego.png --mode image

Extract:
python main.py --extract --input stego.png --output extracted.png --mode image


Audio LSB (Text/File → WAV)
Embed:
python main.py --embed --input cover.wav --payload secret.txt --output stego.wav --mode audio

Extract:
python main.py --extract --input stego.wav --output recovered.txt --mode audio


Adaptive RGB (Key-Based Secure)
Embed:
python main.py --embed --input cover.png --payload secret.txt --output stego.png --mode adaptive --key mySecretKey

Extract:
python main.py --extract --input stego.png --output recovered.txt --mode adaptive --key mySecretKey


Text Steganography
Embed:
python main.py --embed --input cover.txt --payload secret.txt --output stego.txt --mode text

Extract:
python main.py --extract --input stego.txt --output recovered.txt --mode text


DCT (JPEG Frequency Domain)
Embed:
python main.py --embed --input cover.jpg --payload secret.txt --output stego.jpg --mode dct

Extract:
python main.py --extract --input stego.jpg --output recovered.txt --mode dct


## but make srue your payload fits within the cover file capacity.
there are some sample images and text files in the main folder to try if you want.

thanks

adarsh
