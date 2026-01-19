#!/usr/bin/env python3
import os
import sys
import math
import wave
import struct
import logging
import getpass
import traceback
from typing import Optional
from pydub import AudioSegment
from ghostbit import __version__
from ghostbit.audiostego.core.audio_multiformat_coder import (
    AudioMultiFormatCoder,
    AudioMultiFormatCoderException,
)
from ghostbit.helpers.format_argparse import (
    Colors as C,
    ColorHelpFormatter,
    ErrorFriendlyArgumentParser,
)
from ghostbit.audiostego.core.audio_steganography import (
    EncodeMode,
    BaseFileInfoItem,
    AudioSteganographyException,
    KeyEnterCanceledException,
    KeyRequiredEventArgs,
)
import warnings

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub.utils")

logger = logging.getLogger("ghostbit.audiostego")


class AudioStegoCLI:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        logger.info("AudioStegoCLI initialized")

    def _print_header(self, title: str, emoji: Optional[str] = None) -> None:
        """Print a formatted command header"""
        if emoji:
            print(f"\n{emoji} {C.BOLD}{C.BRIGHT_BLUE}{title}{C.RESET}")
        else:
            print(f"\n{C.BOLD}{C.BRIGHT_BLUE}{title}{C.RESET}")
        print(f"{C.WHITE}{'─' * 70}{C.RESET}\n")

    def encode_command(
        self,
        input_file: str,
        secret_files: list[str],
        output_file: str,
        audio_quality: str,
        file_password: Optional[str] = None,
        use_legacy_kdf: bool = False,
    ) -> Optional[int]:
        """Handle encode command"""
        logger.info("Starting encode command")
        logger.debug(
            f"Parameters: carrier={input_file}, secrets={secret_files}, quality={audio_quality}, output={output_file}, password={'set' if file_password else 'none'}, use_legacy_kdf={use_legacy_kdf}"
        )

        self._print_header("Encoding Files", "🔒")

        outputdir = os.path.join("output", "encoded")
        output_filepath = f"{outputdir}/{output_file}"
        logger.debug(f"Output directory: {outputdir}, full path: {output_filepath}")

        if not os.path.exists(input_file):
            logger.error(f"Carrier file not found: {input_file}")
            print(f"❌ Error: Carrier file '{input_file}' not found!")
            return 1

        logger.debug(
            f"Carrier file exists: {input_file} ({os.path.getsize(input_file)} bytes)"
        )

        missing_files = [f for f in secret_files if not os.path.exists(f)]
        if missing_files:
            logger.error(f"Missing {len(missing_files)} secret files: {missing_files}")
            print("❌ Error: Secret files not found:")
            for f in missing_files:
                print(f"  - {f}")
            return 1

        logger.debug(f"All {len(secret_files)} secret files validated")

        password = None
        if file_password:
            if file_password == "prompt":
                logger.debug("Prompting user for password")
                password = getpass.getpass("Enter password: ")
                password_confirm = getpass.getpass("Confirm password: ")
                if password != password_confirm:
                    logger.error("Password confirmation failed")
                    print("❌ Error: Passwords do not match!")
                    return 1
                logger.info("Password set via prompt")
            else:
                password = file_password
                logger.info("Password provided directly")
        else:
            logger.debug("No password specified (unencrypted)")

        quality_map = {
            "low": EncodeMode.LOW_QUALITY,
            "normal": EncodeMode.NORMAL_QUALITY,
            "high": EncodeMode.HIGH_QUALITY,
        }
        quality_mode = quality_map.get(audio_quality.lower(), EncodeMode.NORMAL_QUALITY)
        logger.info(f"Quality mode: {quality_mode.name}")

        try:
            logger.debug("Creating AudioMultiFormatCoder instance")
            coder = AudioMultiFormatCoder()

            if self.verbose:
                logger.debug("Setting up progress callback")
                progress = [0]

                def on_progress() -> None:
                    progress[0] += 1
                    if progress[0] % 100 == 0:
                        logger.debug(f"Encoding progress: {progress[0]} blocks")
                        print(f"  Processed {progress[0]} blocks...")

                coder.on_encoded_element = on_progress

            logger.info(f"Starting encode operation: {len(secret_files)} files")
            coder.encode_files_multi_format(
                carrier_file=input_file,
                secret_files=secret_files,
                output_file=output_filepath,
                password=password,
                quality_mode=quality_mode,
                use_legacy_kdf=use_legacy_kdf,
            )

            output_size = os.path.getsize(output_filepath)
            logger.info(
                f"Encoding completed successfully: {output_filepath} ({output_size} bytes)"
            )
            print(f"\n{C.WHITE}{'─' * 70}{C.RESET}\n")
            return 0

        except AudioSteganographyException as e:
            logger.error(f"Encoding failed with AudioSteganographyException: {e}")
            print(f"\n❌ Encoding failed: {e}")
            return 1
        except Exception as e:
            logger.exception("Unexpected error during encoding")
            print(f"\n❌ Unexpected error: {e}")
            if self.verbose:
                traceback.print_exc()
            return 1

    def decode_command(
        self,
        input_file: str,
        output_dir: str,
        file_password: Optional[str] = None,
        use_legacy_kdf: bool = False,
    ) -> Optional[int]:
        """Handle decode command"""
        logger.info("Starting decode command")
        logger.debug(
            f"Parameters: input={input_file}, output_dir={output_dir}, password={'set' if file_password else 'none'}, use_legacy_kdf={use_legacy_kdf}"
        )

        self._print_header("Decoding Files", "🔓")

        output_filepath = os.path.join("output", output_dir)
        logger.debug(f"Output directory: {output_filepath}")

        if not os.path.exists(input_file):
            logger.error(f"Input file not found: {input_file}")
            print(f"❌ Error: Input file '{input_file}' not found!")
            return 1

        logger.debug(
            f"Input file exists: {input_file} ({os.path.getsize(input_file)} bytes)"
        )

        password = None
        if file_password:
            if file_password == "prompt":
                logger.debug("Prompting user for password")
                password = getpass.getpass("Enter password: ")
                logger.info("Password provided via prompt")
            else:
                password = file_password
                logger.info("Password provided directly")
        else:
            logger.debug("No password specified")

        def request_key(key_args: KeyRequiredEventArgs) -> None:
            if password:
                logger.debug("Using provided password for decryption")
                key_args.key = password
            else:
                logger.info(f"File requires password (version: {key_args.h22_version})")
                print(f"\n🔒 File is encrypted (version: {key_args.h22_version})")
                key = getpass.getpass("Enter password (or Ctrl+C to cancel): ")
                if not key:
                    logger.warning("User cancelled password entry")
                    key_args.cancel = True
                else:
                    logger.debug("Password entered by user")
                    key_args.key = key

        try:
            logger.debug("Creating AudioMultiFormatCoder instance")
            coder = AudioMultiFormatCoder()
            coder.on_key_required = request_key

            if self.verbose:
                logger.debug("Setting up progress callback")
                progress = [0]

                def on_progress() -> None:
                    progress[0] += 1
                    if progress[0] % 100 == 0:
                        logger.debug(f"Decoding progress: {progress[0]} blocks")
                        print(f"  Processed {progress[0]} blocks...")

                coder.on_decoded_element = on_progress

            logger.info("Starting decode operation")
            coder.decode_files_multi_format(
                encoded_file=input_file,
                output_dir=output_filepath,
                password=password,
                use_legacy_kdf=use_legacy_kdf,
            )

            logger.info(f"Decoding completed successfully to {output_filepath}")
            print(f"\n{C.WHITE}{'─' * 70}{C.RESET}\n")
            return 0

        except KeyEnterCanceledException:
            logger.warning("Decoding cancelled by user (key entry cancelled)")
            print("\n❌ Decoding cancelled by user")
            return 1
        except AudioSteganographyException as e:
            logger.error(f"Decoding failed with AudioSteganographyException: {e}")
            print(f"\n❌ Decoding failed: {e}")
            return 1
        except Exception as e:
            logger.exception("Unexpected error during decoding")
            print(f"\n❌ Unexpected error: {e}")
            if self.verbose:
                traceback.print_exc()
            return 1

    def analyze_command(
        self,
        input_file: str,
        file_password: Optional[str] = None,
        use_legacy_kdf: bool = False,
    ) -> Optional[int]:
        """Handle analyze command"""
        logger.info("Starting analyze command")
        logger.debug(
            f"Parameters: input={input_file}, password={'set' if file_password else 'none'}, use_legacy_kdf={use_legacy_kdf}"
        )

        self._print_header("Analyzing File", "🔍")

        if not os.path.exists(input_file):
            logger.error(f"Input file not found: {input_file}")
            print(f"❌ Error: Input file '{input_file}' not found!")
            return 1

        logger.debug(
            f"Input file exists: {input_file} ({os.path.getsize(input_file)} bytes)"
        )

        password = None
        if file_password:
            if file_password == "prompt":
                logger.debug("Prompting user for optional password")
                password = getpass.getpass(
                    "Enter password (optional, press Enter to skip): "
                )
                if not password:
                    password = None
                    logger.debug("User skipped password entry")
                else:
                    logger.info("Password provided via prompt")
            else:
                password = file_password
                logger.info("Password provided directly")
        else:
            logger.debug("No password specified")

        try:
            logger.debug("Creating AudioMultiFormatCoder instance")
            coder = AudioMultiFormatCoder()

            def request_key(key_args: KeyRequiredEventArgs) -> None:
                if password:
                    logger.debug("Using provided password for analysis")
                    key_args.key = password
                else:
                    logger.info(
                        f"File requires password (version: {key_args.h22_version})"
                    )
                    print(f"\n🔒 File is encrypted (version: {key_args.h22_version})")
                    key = getpass.getpass("Enter password (or press Enter to skip): ")
                    if not key:
                        logger.warning("User skipped password entry")
                        key_args.cancel = True
                    else:
                        logger.debug("Password entered by user")
                        key_args.key = key

            coder.on_key_required = request_key

            logger.info("Starting analysis")
            found = coder.analyze_multi_format(input_file, password, use_legacy_kdf)

            if found:
                logger.info("Analysis complete: hidden data found")
            else:
                logger.info("Analysis complete: no hidden data found")
            print(f"\n{C.WHITE}{'─' * 70}{C.RESET}\n")
            return 0 if found else 1

        except KeyEnterCanceledException:
            logger.warning("Analysis cancelled by user (key entry cancelled)")
            print("\n⚠️  Analysis incomplete (password required)")
            return 1
        except AudioSteganographyException as e:
            logger.error(f"Analysis failed with AudioSteganographyException: {e}")
            print(f"\n❌ Analysis failed: {e}")
            return 1
        except Exception as e:
            logger.exception("Unexpected error during analysis")
            print(f"\n❌ Unexpected error: {e}")
            if self.verbose:
                traceback.print_exc()
            return 1

    def capacity_command(self, input_file: str, audio_quality: str) -> Optional[int]:
        """Handle capacity command"""
        if not os.path.exists(input_file):
            logger.error(f"Carrier file not found: {input_file}")
            raise AudioMultiFormatCoderException(
                f"Carrier file not found: {input_file}"
            )
        self._print_header("Calculating Capacity", "🧮")

        try:
            coder = AudioMultiFormatCoder()
            input_format = coder._get_file_extension(input_file)
            filename = os.path.basename(input_file)
            logger.debug(f"Carrier format: {input_format}")

            wav_file = coder._convert_to_wav(input_file)
            logger.debug(f"Converted {filename} to WAV format")

            quality_map = {
                "low": EncodeMode.LOW_QUALITY,
                "normal": EncodeMode.NORMAL_QUALITY,
                "high": EncodeMode.HIGH_QUALITY,
            }

            quality_mode = quality_map.get(
                audio_quality.lower(), EncodeMode.NORMAL_QUALITY
            )
            logger.info(f"Quality mode: {quality_mode.name}")

            base_file = BaseFileInfoItem(
                full_path=wav_file,
                encode_mode=quality_mode,
                wav_head_length=44,
            )

            capacity_bytes = base_file.max_inner_files_size
            logger.info(
                f"Calculated capacity for '{filename}': {capacity_bytes} bytes ({capacity_bytes / (1024 * 1024):.2f} MB)"
            )
            print(f"📁 Input File: '{filename}'")
            print(
                f"   • File Size: {os.path.getsize(input_file)/ (1024 * 1024):.2f} MB"
            )
            print(f"   • Audio Quality: {quality_mode.name}")
            print(
                f"   • Capacity: {capacity_bytes} bytes (~{capacity_bytes / (1024 * 1024):.2f} MB)\n"
            )
            print(f"{C.WHITE}{'─' * 70}{C.RESET}\n")
            return 0

        except Exception as e:
            logger.exception(f"Capacity calculation failed for {input_file}")
            raise AudioSteganographyException(f"Capacity calculation failed: {e}")

    def info_command(self) -> Optional[int]:
        """Handle info command - show library info"""
        logger.info("Displaying application info")

        self._print_header(rf"""{C.BOLD}{C.GRAY}
                     ╭━━━━━━━━━━━━╮  
                   ╭╯              ╰╮
                   |                |   ┏─━┓
                   ┃   ┏━╗    ┏━╗   ┃   ┃  ┃
                   ┃   ║║┃    ║┃┃   ┃  ●╯ ●╯
                ╔  ┃   ╚━┛    ╚━┛   ┃
                ┃  ┃                ┃
               ●╯  ┃      ━──╯      ┃  
                   ┃                ┃ 
                  ╭╯                ╰╮
                  ╰━╯╰━━━╯╰━━╯╰━━━╯╰━╯ 
                ┏━╸╻ ╻┏━┓┏━┓╺┳╸┏┓ ╺┓ ╺┳╸
                ║╺╗║━╣║┃║╚━┓ ║ ║┻┓ ║  ║ :
                ┗━┛╹ ╹┗━┛┗━╝ ╹ ┗━╝╺┻╸ ╹ 
             ┏━┓╻ ╻╺┳┓╺┓ ┏━┓┏━┓╺┳╸╔━╸┏━╸┏━┓
             ║━╣║ ║ ║║ ║ ║┃║╚━┓ ║ ┣╸ ║╺╗║┃║
             ╹ ╹┗━┛╺┻╝╺┻╸┗━┛┗━╝ ╹ ╚━╸┗━┛┗━┛ (v{__version__})                 
        {C.RESET}""")

        print(f"  {C.BOLD}{C.BLUE}Features:{C.RESET}")
        print(f"    {C.BLUE}•{C.RESET} Password protection using Argon2id encryption")
        print(f"    {C.BLUE}•{C.RESET} Multiple files in one carrier")
        print(f"    {C.BLUE}•{C.RESET} Multi-format support")

        print(f"\n  {C.BOLD}{C.BLUE}Supported Formats:{C.RESET}")
        print(f"    {C.BLUE}•{C.RESET} Carrier files:  WAV, FLAC, MP3, M4A, AIFF, AIF")
        print(f"    {C.BLUE}•{C.RESET} Secret files:   ANY file type")
        print(f"    {C.BLUE}•{C.RESET} Output files:   WAV, FLAC, M4A, AIFF, AIF")

        print(f"\n  {C.BOLD}{C.BLUE}Quality Modes:{C.RESET}")
        print(
            f"    {C.BLUE}•{C.RESET} Low Quality    (2:1) - Maximum capacity, lower audio quality"
        )
        print(f"    {C.BLUE}•{C.RESET} Normal Quality (4:1) - Balanced (recommended)")
        print(
            f"    {C.BLUE}•{C.RESET} High Quality   (8:1) - Minimum capacity, best audio quality\n"
        )

        print(f"{C.DIM}{'─' * 70}{C.RESET}\n")
        logger.debug("Info display complete")
        return 0

    def create_test_files_command(
        self, output_dir: str, create_carrier: bool
    ) -> Optional[int]:
        """Create test files for demonstration"""
        logger.info(f"Creating test files in {output_dir}, carrier={create_carrier}")

        self._print_header("Creating Test Files", "📄")

        output_dir = os.path.join("output", output_dir)

        logger.debug(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)

        try:
            logger.debug("Creating test_secret.txt")
            with open(f"{output_dir}/test_secret.txt", "w") as f:
                f.write("This is a SECRET MESSAGE! 🔒\n")
                f.write("If you can read this, the steganography worked!\n")
                f.write("=" * 50 + "\n")
            print("  ✓ Created test_secret.txt")
            logger.info("Created test_secret.txt")

            logger.debug("Creating test_document.txt")
            with open(f"{output_dir}/test_document.txt", "w") as f:
                f.write("CONFIDENTIAL DOCUMENT\n")
                f.write("Project: Phoenix\n")
                f.write("Classification: Top Secret\n")
                f.write("Date: 2026-01-05\n")
            print("  ✓ Created test_document.txt")
            logger.info("Created test_document.txt")
        except Exception as e:
            logger.exception("Failed to create text files")
            print(f"❌ Error creating text files: {e}")
            return 1

        if create_carrier:
            try:
                logger.info("Creating carrier audio files")
                print("\n🎵 Creating test carrier WAV file...")

                wav_path = f"{output_dir}/test_carrier.wav"
                logger.debug(f"Creating WAV file: {wav_path}")

                with wave.open(wav_path, "w") as wav:
                    wav.setnchannels(1)  # Mono
                    wav.setsampwidth(2)  # 16-bit
                    wav.setframerate(44100)  # 44.1kHz

                    duration = 5
                    logger.debug(f"Generating {duration} seconds of audio")
                    for i in range(44100 * duration):
                        value = int(
                            32767 * 0.3 * math.sin(2 * math.pi * 440 * i / 44100)
                        )
                        wav.writeframes(struct.pack("<h", value))

                size_mb = os.path.getsize(wav_path) / 1024 / 1024
                print(f"  ✓ Created test_carrier.wav ({size_mb:.2f} MB)")
                logger.info(f"Created test_carrier.wav ({size_mb:.2f} MB)")

                logger.info("Converting WAV to other formats")
                print("\n🎵 Converting WAV to other formats...")

                try:
                    sound = AudioSegment.from_wav(wav_path)

                    logger.debug("Exporting to MP3")
                    sound.export(f"{output_dir}/test_carrier.mp3", format="mp3")
                    print("  ✓ Created test_carrier.mp3")
                    logger.info("Created test_carrier.mp3")

                    logger.debug("Exporting to M4A")
                    sound.export(f"{output_dir}/test_carrier.m4a", format="mp4")
                    print("  ✓ Created test_carrier.m4a")
                    logger.info("Created test_carrier.m4a")

                    logger.debug("Exporting to FLAC")
                    sound.export(f"{output_dir}/test_carrier.flac", format="flac")
                    print("  ✓ Created test_carrier.flac")
                    logger.info("Created test_carrier.flac")

                    logger.debug("Exporting to AIFF")
                    sound.export(f"{output_dir}/test_carrier.aiff", format="aiff")
                    print("  ✓ Created test_carrier.aiff")
                    logger.info("Created test_carrier.aiff")

                    print("\n✅ Success!")
                except Exception as e:
                    logger.warning(f"Audio format conversion failed: {e}")
                    print(f"⚠️  Some format conversions failed: {e}")
                    print("    WAV file created successfully")

            except Exception as e:
                logger.error(f"Failed to create carrier audio files: {e}")
                print(f"⚠️  Could not create WAV file: {e}")
        else:
            logger.debug("Carrier creation skipped (not requested)")

        abs_path = os.path.abspath(output_dir)
        logger.info(f"Test files created in: {abs_path}")

        print(f"\n{C.DIM}{'─' * 70}{C.RESET}\n")
        print(f"\n📂 Test files created in '{abs_path}/'")
        print("\nYou can now try:")
        print("\n  # Encode:")
        print(
            "  ghostit audiostego encode test_carrier.wav -f test_secret.txt -o encoded.wav -p mypassword"
        )
        print("\n  # Analyze:")
        print("  ghostbit audiostego analyze encoded.wav -p prompt")
        print("\n  # Decode:")
        print("  ghostbit audiostego decode encoded.wav -o extracted -p mypassword")
        print(f"\n{C.DIM}{'─' * 70}{C.RESET}\n")

        logger.info("Test file creation complete")
        return 0


def main() -> Optional[int]:
    parser = ErrorFriendlyArgumentParser(
        description=rf"""{C.BOLD}{C.GRAY}
                     ╭━━━━━━━━━━━━╮  
                   ╭╯              ╰╮
                   |                |   ┏─━┓
                   ┃   ┏━╗    ┏━╗   ┃   ┃  ┃
                   ┃   ║║┃    ║┃┃   ┃  ●╯ ●╯
                ╔  ┃   ╚━┛    ╚━┛   ┃
                ┃  ┃                ┃
               ●╯  ┃      ━──╯      ┃  
                   ┃                ┃ 
                  ╭╯                ╰╮
                  ╰━╯╰━━━╯╰━━╯╰━━━╯╰━╯ 
                ┏━╸╻ ╻┏━┓┏━┓╺┳╸┏┓ ╺┓ ╺┳╸
                ║╺╗║━╣║┃║╚━┓ ║ ║┻┓ ║  ║ :
                ┗━┛╹ ╹┗━┛┗━╝ ╹ ┗━╝╺┻╸ ╹ 
             ┏━┓╻ ╻╺┳┓╺┓ ┏━┓┏━┓╺┳╸╔━╸┏━╸┏━┓
             ║━╣║ ║ ║║ ║ ║┃║╚━┓ ║ ┣╸ ║╺╗║┃║
             ╹ ╹┗━┛╺┻╝╺┻╸┗━┛┗━╝ ╹ ╚━╸┗━┛┗━┛ (v{__version__})    
        {C.RESET}""",
        formatter_class=ColorHelpFormatter,
        prog="ghostbit audio",
        add_help=False,
        epilog=f"""
{C.BOLD}{C.BLUE}examples:{C.RESET}
  {C.BOLD}{C.BLUE}Capacity:{C.RESET}
    {C.BOLD}{C.PINK}ghostbit audio{C.RESET} {C.GREEN}capacity {C.GREEN}-i{C.RESET} {C.CYAN}audio.wav{C.RESET}
  
  {C.BOLD}{C.BLUE}Encode:{C.RESET}
    {C.BOLD}{C.PINK}ghostbit audio{C.RESET} {C.GREEN}encode{C.RESET} {C.GREEN}-i{C.RESET} {C.CYAN}audio.wav{C.RESET} {C.GREEN}-s{C.RESET} {C.CYAN}secret.pdf{C.RESET} {C.GREEN}-o{C.RESET} {C.CYAN}audio_encoded.flac{C.RESET} {C.GREEN}-p{C.RESET}
  
  {C.BOLD}{C.BLUE}Decode:{C.RESET}
    {C.BOLD}{C.PINK}ghostbit audio{C.RESET} {C.GREEN}decode{C.RESET} {C.GREEN}-i{C.RESET} {C.CYAN}audio_encoded.flac{C.RESET} {C.GREEN}-p{C.RESET}
  
  {C.BOLD}{C.BLUE}Analyze:{C.RESET}
    {C.BOLD}{C.PINK}ghostbit audio{C.RESET} {C.GREEN}analyze{C.RESET} {C.GREEN}-i{C.RESET} {C.CYAN}audio.wav{C.RESET} {C.GREEN}-v{C.RESET}
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
        version=f"GH0STB1T: AUD10STEG0 v{__version__}",
        help=f"{C.CYAN}Program version{C.RESET}",
    )

    subparsers = parser.add_subparsers(dest="subparser_command")

    encode_parser = subparsers.add_parser(
        "encode",
        formatter_class=ColorHelpFormatter,
        add_help=False,
        help=f"{C.CYAN}Encode secret files into audio{C.RESET}",
    )
    encode_parser.add_argument(
        "-h", "--help", action="help", help=f"{C.CYAN}Show help message{C.RESET}"
    )
    encode_parser.add_argument(
        "-i",
        "--input_file",
        required=True,
        help=f"{C.CYAN}Carrier audio file (WAV|FLAC|MP3|M4A|AIFF|AIF){C.RESET}",
    )
    encode_parser.add_argument(
        "-s",
        "--secret-files",
        nargs="+",
        required=True,
        help=f"{C.CYAN}Secret files to hide (any file type){C.RESET}",
    )
    encode_parser.add_argument(
        "-o",
        "--output_file",
        required=True,
        help=f"{C.CYAN}Output filename with desired format (WAV|FLAC|M4A|AIFF|AIF){C.RESET}",
    )
    encode_parser.add_argument(
        "-p",
        "--password",
        nargs="?",
        const="prompt",
        help=f"{C.CYAN}Password for encryption (prompts if no value){C.RESET}",
    )
    encode_parser.add_argument(
        "-q",
        "--quality",
        default="normal",
        choices=["low", "normal", "high"],
        help=f"{C.CYAN}Quality mode (default: normal){C.RESET}",
    )
    encode_parser.add_argument(
        "--legacy-kdf",
        action="store_true",
        help=f"{C.CYAN}Use legacy key derivation (less secure, for backwards compatibility){C.RESET}",
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
        help=f"{C.CYAN}Decode secret files from audio{C.RESET}",
    )
    decode_parser.add_argument(
        "-h", "--help", action="help", help=f"{C.CYAN}Show help message{C.RESET}"
    )
    decode_parser.add_argument(
        "-i", "--input_file", required=True, help=f"{C.CYAN}Encoded audio file{C.RESET}"
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
        help=f"{C.CYAN}Password for decryption (prompts if no value){C.RESET}",
    )
    decode_parser.add_argument(
        "--legacy-kdf",
        action="store_true",
        help=f"{C.CYAN}Use legacy key derivation (for files encoded with older versions){C.RESET}",
    )
    decode_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=f"{C.CYAN}Enable verbose output{C.RESET}",
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        formatter_class=ColorHelpFormatter,
        add_help=False,
        help=f"{C.CYAN}Analyze file for hidden data{C.RESET}",
    )
    analyze_parser.add_argument(
        "-h", "--help", action="help", help=f"{C.CYAN}Show help message{C.RESET}"
    )
    analyze_parser.add_argument(
        "-i",
        "--input_file",
        required=True,
        help=f"{C.CYAN}Audio file to analyze (WAV|FLAC|M4A|AIFF|AIF){C.RESET}",
    )
    analyze_parser.add_argument(
        "-p",
        "--password",
        nargs="?",
        const="prompt",
        help=f"{C.CYAN}Password if file is encrypted (prompts if no value){C.RESET}",
    )
    analyze_parser.add_argument(
        "--legacy-kdf",
        action="store_true",
        help=f"{C.CYAN}Use legacy key derivation (for files encoded with older versions){C.RESET}",
    )
    analyze_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=f"{C.CYAN}Enable verbose output{C.RESET}",
    )

    capacity_parser = subparsers.add_parser(
        "capacity",
        formatter_class=ColorHelpFormatter,
        add_help=False,
        help=f"{C.CYAN}Analyze file for capacity{C.RESET}",
    )
    capacity_parser.add_argument(
        "-h", "--help", action="help", help=f"{C.CYAN}Show help message{C.RESET}"
    )
    capacity_parser.add_argument(
        "-i",
        "--input_file",
        required=True,
        help=f"{C.CYAN}Audio file to analyze (WAV|FLAC|M4A|AIFF|AIF){C.RESET}",
    )
    capacity_parser.add_argument(
        "-q",
        "--quality",
        default="normal",
        choices=["low", "normal", "high"],
        help=f"{C.CYAN}Quality mode (default: normal){C.RESET}",
    )

    capacity_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=f"{C.CYAN}Enable verbose output{C.RESET}",
    )

    info_parser = subparsers.add_parser(
        "info",
        formatter_class=ColorHelpFormatter,
        add_help=False,
        help=f"{C.CYAN}Show library information{C.RESET}",
    )
    info_parser.add_argument(
        "-h", "--help", action="help", help=f"{C.CYAN}Show help message{C.RESET}"
    )
    info_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=f"{C.CYAN}Enable verbose output{C.RESET}",
    )

    test_parser = subparsers.add_parser(
        "test",
        formatter_class=ColorHelpFormatter,
        add_help=False,
        help=f"{C.CYAN}Create test secret files{C.RESET}",
    )
    test_parser.add_argument(
        "-h", "--help", action="help", help=f"{C.CYAN}Show help message{C.RESET}"
    )
    test_parser.add_argument(
        "-o",
        "--output_dir",
        required=False,
        default="testcases",
        help=f"{C.CYAN}Output folder for test files{C.RESET}",
    )
    test_parser.add_argument(
        "--create-carrier",
        action="store_true",
        help=f"{C.CYAN}Create a test carrier audio files (AIFF|WAV|MP3|FLAC|M4A){C.RESET}",
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
        sys.exit(1)

    cli = AudioStegoCLI(verbose=args.verbose)
    logger.debug("Main function initialized")

    if args.subparser_command == "encode":
        return cli.encode_command(
            args.input_file,
            args.secret_files,
            args.output_file,
            args.quality,
            args.password,
            use_legacy_kdf=getattr(args, "legacy_kdf", False),
        )
    elif args.subparser_command == "decode":
        return cli.decode_command(
            args.input_file,
            args.output_dir,
            args.password,
            use_legacy_kdf=getattr(args, "legacy_kdf", False),
        )
    elif args.subparser_command == "analyze":
        return cli.analyze_command(
            args.input_file,
            args.password,
            use_legacy_kdf=getattr(args, "legacy_kdf", False),
        )
    elif args.subparser_command == "capacity":
        return cli.capacity_command(args.input_file, args.quality)
    elif args.subparser_command == "info":
        return cli.info_command()
    elif args.subparser_command == "test":
        return cli.create_test_files_command(
            args.output_dir, create_carrier=args.create_carrier
        )
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
