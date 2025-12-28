# sabse pehle imoprted all the files from the core folder jitni working hai

import argparse                               # CLI parsing
from core.detect import detect_file_type      # File type detection
from core.image_lsb import embed_lsb_png, extract_lsb_png  # image me txt embed/extract karne ke liye
from core.scan import scan_lsb_patterns, scan_metadata #image scanning + metadeta check
from core import image_embed # image me image embed/extract karne k lie
from core.audio_stego import embed_audio_lsb, extract_audio_lsb



# whenever reopen vsc pehle reactivate the virtual envr->    ..\venv\Scripts\Activate.ps1



def main():
    parser = argparse.ArgumentParser(description="Universal Steganography Tool")
    parser.add_argument("--embed", action="store_true")
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--scan", action="store_true")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    parser.add_argument("--payload")
    parser.add_argument("--mode", choices=["lsb", "image", "audio"], default="lsb")

    args = parser.parse_args()
    file_type = detect_file_type(args.input)
    print("Detected file type:", file_type)

    # -------- SCAN --------
    if args.scan:
        if file_type == "image":
            print(scan_lsb_patterns(args.input))
            print(scan_metadata(args.input))
        else:
            print("Scan not yet implemented for this file type.")
        return

    # -------- EMBED --------
    elif args.embed:
        if not args.payload:
            raise ValueError("Missing --payload for embedding.")
        if not args.output:
            raise ValueError("Missing --output for embedding.")

        if file_type in ("image", "jpeg"):
            if args.mode == "lsb":
                embed_lsb_png(args.input, args.payload, args.output)
            elif args.mode == "image":
                image_embed.embed_image_into_image(
                    args.input, args.payload, args.output
                )
            else:
                raise ValueError("Invalid mode for image.")

        elif file_type == "wav":
            embed_audio_lsb(args.input, args.payload, args.output)

        else:
            raise ValueError("Unsupported file type for embedding.")

        print(f"Embedded payload into {args.output}")
        return

    # -------- EXTRACT --------
    elif args.extract:
        if not args.output:
            raise ValueError("Missing --output for extraction.")

        if file_type in ("image", "jpeg"):
            if args.mode == "lsb":
                extract_lsb_png(args.input, args.output)
            elif args.mode == "image":
                image_embed.extract_image_from_image(args.input, args.output)
            else:
                raise ValueError("Invalid mode for image.")

        elif file_type == "wav":
            extract_audio_lsb(args.input, args.output)

        else:
            raise ValueError("Unsupported file type for extraction.")

        print(f"Extracted payload to {args.output}")
        return

    else:
        print("No operation specified.")



if __name__ == "__main__": 
    main() # ye tab hi chalega if we are in main 