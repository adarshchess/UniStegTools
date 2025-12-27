# sabse pehle imoprted all the files from the core folder jitni working hai

import argparse                               # CLI parsing
from core.detect import detect_file_type      # File type detection
from core.image_lsb import embed_lsb_png, extract_lsb_png  # image me txt embed/extract karne ke liye
from core.scan import scan_lsb_patterns, scan_metadata #image scanning + metadeta check
from core import image_embed # image me image embed/extract karne k lie


# whenever reopen vsc pehle reactivate the virtual envr->    ..\venv\Scripts\Activate.ps1



def main():
    # Build the command-line parser and define flags/options
    parser = argparse.ArgumentParser(description="Universal Steganography Tool")
    parser.add_argument("--embed", action="store_true", help="Embed secret data into a file")
    parser.add_argument("--extract", action="store_true", help="Extract hidden data from a file")
    parser.add_argument("--scan", action="store_true", help="Scan a file for hidden data")
    parser.add_argument("--input", required=True, help="Input file path")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--payload", help="Payload file path (for embedding)")
    parser.add_argument("--mode", choices=["lsb", "image"], default="lsb",
                    help="Choose embedding mode: lsb (text-in-image) or image (image-in-image)")

    args = parser.parse_args()                 # Parse CLI args into a Namespace

    # Detect file type early for routing
    file_type = detect_file_type(args.input)   # e.g., "image", "jpeg", "wav", "unknown"
    print("Detected file type:", file_type)    # Simple visibility during tests

    # If user asked to scan, we have now connceted our scan.py which can do meta data detection and lsb pattern scan
    if args.scan:
     if file_type == "image":
        print(scan_lsb_patterns(args.input))
        print(scan_metadata(args.input))
    else:
        print("Scan not yet implemented for this file type.")


# Handle embed operation
    if args.embed:
        # Validate required arguments for embedding
        if file_type not in ("image", "jpeg"):  # Our LSB supports RGB PNG/JPEG converted to RGB
            raise ValueError("Embed currently supports PNG/JPEG images only.")
        if not args.payload:
            raise ValueError("Missing --payload for embedding.")
        if not args.output:
            raise ValueError("Missing --output for embedding.")

        # Decide which embedding mode to use
        if args.mode == "lsb":
            # Text-in-image embedding (your existing code)
            embed_lsb_png(
                input_path=args.input,
                payload_path=args.payload,
                output_path=args.output
            )
        elif args.mode == "image":
            # Image-in-image embedding (new functionality)
            image_embed.embed_image_into_image(
    cover_path=args.input,
    payload_path=args.payload,
    output_path=args.output
)

        print(f"Embedded payload into {args.output}")
        return


        # Handle extract operation
    if args.extract:
        # Validate required arguments for extraction
        if file_type not in ("image", "jpeg"):
            raise ValueError("Extract currently supports PNG/JPEG images only.")
        if not args.output:
            raise ValueError("Missing --output for extraction (payload destination).")

        # Decide which extraction mode to use
        if args.mode == "lsb":
            # Text-in-image extraction (your existing code)
            extract_lsb_png(
                stego_path=args.input,             # Stego image containing hidden data
                output_payload_path=args.output    # File to write recovered payload
            )
        elif args.mode == "image":
            # Image-in-image extraction (new functionality)
            image_embed.extract_image_from_image(
    stego_path=args.input,
    output_path=args.output
)

        print(f"Extracted payload to {args.output}")
        return

    # If no operation flag was provided, show parsed args to confirm CLI is working
    print("Arguments received:", args)


if __name__ == "__main__": 
    main() # ye tab hi chalega if we are in main 
