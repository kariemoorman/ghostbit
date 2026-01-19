#!/usr/bin/env python3
import sys
import logging
import argparse
from typing import Never

logger = logging.getLogger("ghostbit.helpers.format")


class Colors:
    """ANSI color codes for terminal output"""

    # Reset
    RESET = "\033[0m"

    # Text styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    HIDDEN = "\033[8m"
    STRIKETHROUGH = "\033[9m"

    # Regular colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    ORANGE = "\033[38;5;214m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    PINK = "\033[38;5;213m"
    WHITE = "\033[37m"
    GRAY = "\033[38;5;250m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


class ColorHelpFormatter(argparse.RawTextHelpFormatter):
    def _format_action_invocation(self, action: argparse.Action) -> str:
        logger.debug("ColorHelpFormatter initialized")
        if action.option_strings:
            opts = ", ".join(
                f"{Colors.GREEN}{opt}{Colors.RESET}" for opt in action.option_strings
            )

            if action.nargs not in [0, None]:
                metavar = self._metavar_formatter(action, action.dest)(0)
                if metavar:
                    opts += f" {metavar[0]}"
            return opts
        elif action.dest != "subparser_command":
            return f"{Colors.GREEN}{action.dest}{Colors.RESET}"
        else:
            return ""

    def _format_actions_usage(self, actions, groups):
        """Colorize option flags in the usage line"""
        usage = super()._format_actions_usage(actions, groups)

        # Colorize all option flags (--flag or -f)
        import re

        usage = re.sub(r"(--?[\w-]+)", rf"{Colors.GREEN}\1{Colors.RESET}", usage)

        return usage


class ErrorFriendlyArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        logger.debug("ErrorFriendlyArgumentParser initialized")
        C = Colors()
        print(f"\n{C.RED}❌ Error: {message}{C.RESET}\n")
        self.print_help()
        sys.exit(2)
