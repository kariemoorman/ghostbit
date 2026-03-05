#!/usr/bin/env python3
import os
import sys
import logging
from getpass import getpass
from ghostbit import __version__
from typing import List, Optional
from ghostbit.helpers.format_argparse import (
    ErrorFriendlyArgumentParser,
    ColorHelpFormatter,
    Colors as C,
)
from ghostbit.imagestego.core.image_multiformat_coder import (
    ImageGenerator,
    ImageMultiFormatCoder,
    ImageTestCreationException,
    ImageMultiFormatCoderException,
)

logger = logging.getLogger("ghostbit.imagestego")


class ImageStegoCLI:

    PERMITTED = ["jpg", "jpeg", "webp", "bmp", "png", "svg", "tiff", "gif"]

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        logger.info("ImageStegoCLI initialized")

    def _print_header(self, title: str, emoji: Optional[str] = None) -> None:
        """Print a formatted command header"""
        if emoji:
            print(f"\n{emoji} {C.BOLD}{C.BRIGHT_BLUE}{title}{C.RESET}")
        else:
            print(f"\n{C.BOLD}{C.BRIGHT_BLUE}{title}{C.RESET}")
        print(f"{C.BRIGHT_BLUE}{'─' * 70}{C.RESET}\n")

    def encode_command(
        self,
        input_file: str,
        secret_files: List[str],
        file_password: Optional[str] = None,
        show_stats: bool = True,
    ) -> Optional[int]:
        """Handle encode command"""
        logger.info("Starting encode command")
        logger.debug(
            f"Parameters: carrier={input_file}, secrets={secret_files}, password={'set' if file_password else 'none'}"
        )

        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Cover image not found: {input_file}")

        file_format = os.path.splitext(input_file)[1].lstrip(".")

        if file_format not in self.PERMITTED:
            raise ImageMultiFormatCoderException("File format not supported")

        password = None
        if not file_password:
            pass
        elif file_password.lower() == "prompt":
            password = getpass("Enter encryption password: ")
            if password:
                confirm = getpass("Confirm password: ")
                if password != confirm:
                    print("❌ Error: Passwords do not match")
                    sys.exit(1)
        elif file_password:
            password = file_password

        outputdir = os.path.join("output", "encoded")
        logger.debug(f"Output directory: {outputdir}")

        try:
            self._print_header("Encoding Files", "🔒")
            stego = ImageMultiFormatCoder()
            stego.encode(
                cover_path=input_file,
                secret_files=secret_files,
                output_dir=outputdir,
                password=password,
                show_stats=show_stats,
            )
            print(f"{C.BRIGHT_BLUE}{'─' * 70}{C.RESET}\n")
            return 0

        except ImageMultiFormatCoderException as e:
            logger.error(
                f"Image Encoding failed with ImageMultiFormatCoderException: {e}"
            )
            print(f"\n❌ Image Encoding failed: {e}")
            return 1

    def decode_command(
        self, input_file: str, output_dir: str, file_password: Optional[str] = None
    ) -> Optional[int]:
        """Handle decode command"""
        logger.info("Starting decode command")
        logger.debug(
            f"Parameters: carrier={input_file}, output_dir={output_dir}, password={'set' if file_password else 'none'}"
        )

        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Cover image not found: {input_file}")

        file_format = os.path.splitext(input_file)[1].lstrip(".")

        if file_format not in self.PERMITTED:
            raise ImageMultiFormatCoderException("File format not supported")

        password = None
        if file_password == "prompt":
            password = getpass("Enter decryption password: ")
        elif file_password:
            password = file_password

        output_filepath = os.path.join("output", output_dir)
        logger.debug(f"Output directory: {output_filepath}")

        try:
            self._print_header("Decoding Files", "🔓")
            stego = ImageMultiFormatCoder()
            stego.decode(input_file, output_filepath, password)
            print(f"{C.BRIGHT_BLUE}{'─' * 70}{C.RESET}\n")
            return 0

        except ImageMultiFormatCoderException as e:
            logger.error(
                f"Image Decoding failed with ImageMultiFormatCoderException: {e}"
            )
            print(f"\n❌ Image Decoding failed: {e}")
            return 1

    def capacity_command(self, input_file: str) -> Optional[int]:
        """Handle capacity command"""

        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Image not found: {input_file}")

        file_format = os.path.splitext(input_file)[1].lstrip(".")

        if file_format not in self.PERMITTED:
            raise ImageMultiFormatCoderException("File format not supported")

        try:
            self._print_header("Calculating Capacity", "🧮")
            stego = ImageMultiFormatCoder()
            result = stego.calculate_capacity(input_file)

            print("\n📊 Maximum Capacity:")
            print(f"  • {result['capacity_bytes']:,} bytes")
            print(f"  • {result['capacity_kb']:.2f} KB")
            print(f"  • {result['capacity_mb']:.2f} MB")
            print(f"\n{C.BRIGHT_BLUE}{'─' * 70}{C.RESET}\n")
            return 0

        except ImageMultiFormatCoderException as e:
            logger.error(
                f"Image Capacity Analysis failed with ImageMultiFormatCoderException: {e}"
            )
            print(f"\n❌ Image Capacity Analysis failed: {e}")
            return 1

    def analyze_command(
        self,
        input_file: str,
    ) -> Optional[int]:
        """Handle analyze command"""

        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Image not found: {input_file}")

        file_format = os.path.splitext(input_file)[1].lstrip(".")

        if file_format not in self.PERMITTED:
            raise ImageMultiFormatCoderException("File format not supported")

        try:
            self._print_header("Analyzing File", "🔍")

            stego = ImageMultiFormatCoder()
            result = stego.analyze(input_file)

            print("\n🔍 Steganography Details:")
            print(
                f"   • Hidden Data: {'✓ YES' if result['has_hidden_data'] else '✗ NO'}"
            )
            if result["has_hidden_data"]:
                print(
                    f"   • Algorithm: {result['algorithm'].name if result['algorithm'] else 'Unknown'}"
                )
                print(f"   • Encrypted: {'Yes' if result['encrypted'] else 'No'}")
                print("\n💡 Next Steps:")
                if result["encrypted"]:
                    print(f"   • ghostbit image decode -i {input_file} -p")
                else:
                    print(f"   • ghostbit image decode -i {input_file}")
            print(f"\n{C.BRIGHT_BLUE}{'─' * 70}{C.RESET}\n")
            return 0

        except ImageMultiFormatCoderException as e:
            logger.error(
                f"Image Analysis failed with ImageMultiFormatCoderException: {e}"
            )
            print(f"\n  Image Analysis failed: {e}")
            return 1

    def create_test_files_command(self, output_dir: str):
        self._print_header("Creating Test Images", "📁")
        try:
            outputdir = os.path.join("output", output_dir)
            logger.debug(f"Output directory: {outputdir}")
            print(f"📁 Output Directory: '{outputdir}'\n")
            image_gen = ImageGenerator(out_dir=outputdir)
            image_gen.generate_all()
            print(f"\n{C.BRIGHT_BLUE}{'─' * 70}{C.RESET}\n")
        except ImageTestCreationException as e:
            logger.error(f"Image Test File Creation failed: {e}")
            print(f"\n  Image Test File Creation failed: {e}")
            return 1


def main():
    parser = ErrorFriendlyArgumentParser(
        description=rf"""{C.BOLD}{C.GRAY}
  ┏━╸╻ ╻┏━┓┏━┓╺┳╸┏┓ ╺┓ ╺┳╸  ╺┓ ┏┳┓┏━┓┏━╸╔━╸┏━┓╺┳╸╔━╸┏━╸┏━┓
  ║╺╗║━╣║┃║╚━┓ ║ ║┻┓ ║  ║ :  ║ ║┃║║━╣║╺╗┣╸ ╚━┓ ║ ┣╸ ║╺╗║┃║
  ┗━┛╹ ╹┗━┛┗━╝ ╹ ┗━╝╺┻╸ ╹   ╺┻╸╹ ╹╹ ╹┗━┛╚━╸┗━╝ ╹ ╚━╸┗━┛┗━┛ (v{__version__})
        {C.RESET}""",
        formatter_class=ColorHelpFormatter,
        prog="ghostbit image",
        add_help=False,
        epilog=f"""
{C.BOLD}{C.BLUE}examples:{C.RESET}
  {C.BOLD}{C.BLUE}Capacity:{C.RESET}
    {C.BOLD}{C.PINK}ghostbit image{C.RESET} {C.GREEN}capacity {C.GREEN}-i{C.RESET} {C.CYAN}image.png{C.RESET}
  
  {C.BOLD}{C.BLUE}Encode:{C.RESET}
    {C.BOLD}{C.PINK}ghostbit image{C.RESET} {C.GREEN}encode{C.RESET} {C.GREEN}-i{C.RESET} {C.CYAN}cover.jpg{C.RESET} {C.GREEN}-s{C.RESET} {C.CYAN}secret.pdf{C.RESET} {C.GREEN}-p{C.RESET}
  
  {C.BOLD}{C.BLUE}Decode:{C.RESET}
    {C.BOLD}{C.PINK}ghostbit image{C.RESET} {C.GREEN}decode{C.RESET} {C.GREEN}-i{C.RESET} {C.CYAN}stego.png{C.RESET} {C.GREEN}-p{C.RESET}
  
  {C.BOLD}{C.BLUE}Analyze:{C.RESET}
    {C.BOLD}{C.PINK}ghostbit image{C.RESET} {C.GREEN}analyze{C.RESET} {C.GREEN}-i{C.RESET} {C.CYAN}suspicious.webp{C.RESET} {C.GREEN}-v{C.RESET}

  {C.BOLD}{C.BLUE}Test Image Creation:{C.RESET}
    {C.BOLD}{C.PINK}ghostbit image{C.RESET} {C.GREEN}test{C.RESET} {C.GREEN}-o{C.RESET} {C.CYAN}test_images{C.RESET}
    """,
    )

    parser.add_argument(
        "-h", "--help", action="help", help=f"{C.CYAN}Show help message{C.RESET}"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=f"{C.CYAN}Enable verbose output{C.RESET}",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"GH0STB1T: 1MAGESTEG0 v{__version__}",
        help=f"{C.CYAN}Program version{C.RESET}",
    )

    subparsers = parser.add_subparsers(dest="subparser_command")

    encode_parser = subparsers.add_parser(
        "encode",
        formatter_class=ColorHelpFormatter,
        add_help=False,
        help=f"{C.CYAN}Hide a secret file in an image{C.RESET}",
    )
    encode_parser.add_argument(
        "-h", "--help", action="help", help=f"{C.CYAN}Show help message{C.RESET}"
    )
    encode_parser.add_argument(
        "-i",
        "--input_file",
        required=True,
        help=f"{C.CYAN}Cover image (PNG|JPEG|WEBP|SVG|GIF){C.RESET}",
    )
    encode_parser.add_argument(
        "-s",
        "--secret_files",
        required=True,
        nargs="+",
        help=f"{C.CYAN}Secret file(s){C.RESET}",
    )
    encode_parser.add_argument(
        "-p",
        "--password",
        nargs="?",
        const="prompt",
        help=f"{C.CYAN}Password (prompts if no value){C.RESET}",
    )
    encode_parser.add_argument(
        "--show-stats",
        action="store_true",
        help=f"{C.CYAN}Show statistical analysis{C.RESET}",
    )
    encode_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=f"{C.CYAN}Enable verbose output{C.RESET}",
    )

    decode_parser = subparsers.add_parser(
        "decode",
        formatter_class=ColorHelpFormatter,
        add_help=False,
        help=f"{C.CYAN}Extract hidden file from an image{C.RESET}",
    )
    decode_parser.add_argument(
        "-h", "--help", action="help", help=f"{C.CYAN}Show help message{C.RESET}"
    )
    decode_parser.add_argument(
        "-i", "--input_file", required=True, help=f"{C.CYAN}Image to decode{C.RESET}"
    )
    decode_parser.add_argument(
        "-o",
        "--output_dir",
        required=False,
        default="decoded",
        help=f"{C.CYAN}(Optional) Output folder for extracted files{C.RESET}",
    )
    decode_parser.add_argument(
        "-p",
        "--password",
        nargs="?",
        const="prompt",
        help=f"{C.CYAN}Password (prompts if no value){C.RESET}",
    )
    decode_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=f"{C.CYAN}Enable verbose output{C.RESET}",
    )

    capacity_parser = subparsers.add_parser(
        "capacity",
        formatter_class=ColorHelpFormatter,
        add_help=False,
        help=f"{C.CYAN}Calculate image hiding capacity",
    )
    capacity_parser.add_argument(
        "-h", "--help", action="help", help=f"{C.CYAN}Show help message{C.RESET}"
    )
    capacity_parser.add_argument(
        "-i", "--input_file", required=True, help=f"{C.CYAN}Image filepath"
    )
    capacity_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=f"{C.CYAN}Enable verbose output{C.RESET}",
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        formatter_class=ColorHelpFormatter,
        add_help=False,
        help=f"{C.CYAN}Detect hidden data{C.RESET}",
    )
    analyze_parser.add_argument(
        "-h", "--help", action="help", help=f"{C.CYAN}Show help message{C.RESET}"
    )
    analyze_parser.add_argument(
        "-i", "--input_file", required=True, help=f"{C.CYAN}Image to analyze{C.RESET}"
    )
    analyze_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=f"{C.CYAN}Enable verbose output{C.RESET}",
    )

    test_parser = subparsers.add_parser(
        "test",
        formatter_class=ColorHelpFormatter,
        add_help=False,
        help=f"{C.CYAN}Create test image files{C.RESET}",
    )
    test_parser.add_argument(
        "-h", "--help", action="help", help=f"{C.CYAN}Show help message{C.RESET}"
    )
    test_parser.add_argument(
        "-o",
        "--output_dir",
        required=False,
        default="test_images",
        help=f"{C.CYAN}(Optional) Output folder for test files{C.RESET}",
    )
    test_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=f"{C.CYAN}Enable verbose output{C.RESET}",
    )

    args = parser.parse_args()

    if not getattr(args, "subparser_command", None):
        print(f"\n{C.RED}❌ Error: No command provided!{C.RESET}\n")
        parser.print_help()
        return 1

    cli = ImageStegoCLI(verbose=args.verbose)
    logger.debug("Main function started")

    try:
        if args.subparser_command == "encode":
            return cli.encode_command(
                args.input_file,
                args.secret_files,
                args.password,
                show_stats=getattr(args, "show_stats", False),
            )

        elif args.subparser_command == "decode":
            return cli.decode_command(args.input_file, args.output_dir, args.password)

        elif args.subparser_command == "capacity":
            return cli.capacity_command(args.input_file)

        elif args.subparser_command == "analyze":
            return cli.analyze_command(args.input_file)

        elif args.subparser_command == "test":
            return cli.create_test_files_command(args.output_dir)

        else:
            parser.print_help()
            return 1

    except ImageMultiFormatCoderException as e:
        print(f"❌ ImageMultiFormatCoder Error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled")
        return 1
    except Exception as e:
        logger.error(f"❌ Exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
