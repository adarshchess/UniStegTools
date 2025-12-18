# Universal Steg Tool

A py cli tool for embedding and extracting payloads using steganography.  
Supports multiple file types (png,jpeg,jpg)

## 🚀 Installation
Clone the repository and set up a virtual environment:

```bash (it has the dependencies in the virtual virtual env so we need to activate tht first)
git clone https://github.com/adarshchess/UniStegTools.git
cd UniStegTools
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

To scan sus images
python main.py --scan --input imagename.png

To embed text into image
python main.py --embed --mode lsb --input image2.png --payload secret.txt --output new.png

To extract text from the image
python main.py --extract --mode lsb --input stego.png --output recovered.txt


To embed image into image 
python main.py --embed --mode image --input cover.png --payload secret.jpeg --output stego.png


To extract image from a image
python main.py --extract --mode image --input stego.png --output recovered.png

## but make srue your payload fits within the cover images capacity.
there are some sample images and text files in the main folder to try if you want.
thanks
