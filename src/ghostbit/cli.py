#!/usr/bin/env python3
import sys
import argparse
from typing import NoReturn
from ghostbit import __version__
from ghostbit.helpers.format_argparse import (
    Colors as C,
    ColorHelpFormatter,
    ErrorFriendlyArgumentParser,
)


def main() -> NoReturn:
    """Main entry point for universal GH0STB1T CLI"""
    parser = ErrorFriendlyArgumentParser(
        description=f"""{C.BOLD}{C.GRAY}
                  ╭━━━━━━━━━━━━╮
                ╭╯              ╰╮  
                |                |  
                ┃   ┏━╗    ┏━╗   ┃ 
                ┃   ║║┃    ║┃┃   ┃         
                ┃   ╚━┛    ╚━┛   ┃ 
                ┃                ┃ 
                ┃      ━──╯      ┃ 
                ┃                ┃  
               ╭╯                ╰╮
               ╰━╯╰━━━╯╰━━╯╰━━━╯╰━╯ 
             ┏━╸╻ ╻┏━┓┏━┓╺┳╸┏┓ ╺┓ ╺┳╸
             ║╺╗║━╣║┃║╚━┓ ║ ║┻┓ ║  ║ 
             ┗━┛╹ ╹┗━┛┗━╝ ╹ ┗━╝╺┻╸ ╹ (v{__version__})

        A Mᴜʟᴛɪ-Fᴏʀᴍᴀᴛ Sᴛᴇɢᴀɴᴏɢʀᴀᴘʜʏ Tᴏᴏʟᴋɪᴛ{C.RESET}
        """,
        formatter_class=ColorHelpFormatter,
        prog="ghostbit",
        add_help=False,
        epilog=f"""{C.ORANGE}
{C.BOLD}{C.BLUE}examples:{C.RESET}
    {C.BOLD}{C.BLUE}Encode:{C.RESET}
    {C.BOLD}{C.PINK}ghostbit audio{C.RESET} {C.GREEN}encode{C.RESET} {C.GREEN}-i{C.RESET} {C.CYAN}input.wav{C.RESET} {C.GREEN}-s{C.RESET} {C.CYAN}secret.txt{C.RESET} {C.GREEN}-o{C.RESET} {C.CYAN}output.wav{C.RESET} {C.GREEN}-p{C.RESET}

    {C.BOLD}{C.BLUE}Decode:{C.RESET}
    {C.BOLD}{C.PINK}ghostbit audio{C.RESET} {C.GREEN}decode{C.RESET} {C.GREEN}-i{C.RESET} {C.CYAN}input.wav{C.RESET} {C.GREEN}-p{C.RESET}

    {C.BOLD}{C.BLUE}Help (Module-Specific):{C.RESET}
    {C.BOLD}{C.PINK}ghostbit audio{C.RESET} {C.GREEN}--help{C.RESET}
  {C.RESET}
""",
    )

    parser.add_argument(
        "-h", "--help", action="help", help=f"{C.CYAN}Show help message{C.RESET}"
    )

    parser.add_argument(
        "module",
        choices=["audio"],
        metavar="module",
        help=f"{C.CYAN}Steganography module to use (e.g., audio){C.RESET}",
    )

    parser.add_argument(
        "module_args",
        nargs=argparse.REMAINDER,
        metavar="module_args",
        help=f"{C.CYAN}Arguments to pass to the specific module (e.g., encode, decode, analyze, capacity){C.RESET}",
    )

    args = parser.parse_args()

    if args.module == "audio":
        from ghostbit.audiostego.cli.audiostego_cli import main as audio_main

        sys.argv = sys.argv[:1]
        sys.argv = ["ghostbit audio"] + args.module_args
        audio_main()
    else:
        parser.print_help()

    sys.exit(0)


if __name__ == "__main__":
    main()
