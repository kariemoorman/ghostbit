#!/usr/bin/env python3
import sys
import logging
import subprocess
import importlib.util
from typing import Dict
from ghostbit.helpers.format_argparse import Colors as C

logger = logging.getLogger("ghostbit.helpers.audio_requirements")


class RequirementsChecker:
    """Check software requirements"""

    def __init__(self) -> None:
        logger.info("RequirementsChecker initialized")
        self.PYCRYPTODOME_AVAILABLE = False
        self.PYDUB_AVAILABLE = False
        self.SOUNDFILE_AVAILABLE = False
        self.FFMPEG_AVAILABLE = False

    def check_requirements(self, print_results: bool = False) -> None:
        """Check if required libraries and ffmpeg are installed"""
        logger.info("Checking software requirements")

        self.PYCRYPTODOME_AVAILABLE = importlib.util.find_spec("Crypto") is not None
        logger.debug(
            f"PYCRYPTODOME: {'Available' if self.PYCRYPTODOME_AVAILABLE else 'Not available'}"
        )

        self.PYDUB_AVAILABLE = importlib.util.find_spec("pydub") is not None
        logger.debug(
            f"PYDUB: {'Available' if self.PYDUB_AVAILABLE else 'Not available'}"
        )

        self.SOUNDFILE_AVAILABLE = importlib.util.find_spec("soundfile") is not None
        logger.debug(
            f"SOUNDFILE: {'Available' if self.SOUNDFILE_AVAILABLE else 'Not available'}"
        )

        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            self.FFMPEG_AVAILABLE = True
            logger.debug("FFMPEG: Available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.FFMPEG_AVAILABLE = False
            logger.debug("FFMPEG: Not available")

        status: Dict[str, bool] = {
            "PYCRYPTODOME": self.PYCRYPTODOME_AVAILABLE,
            "PYDUB": self.PYDUB_AVAILABLE,
            "SOUNDFILE": self.SOUNDFILE_AVAILABLE,
            "FFMPEG": self.FFMPEG_AVAILABLE,
        }

        if print_results:
            print(f"\n  {C.BOLD}{C.PINK}Checking software requirements...{C.RESET}\n")
            for lib, available in status.items():
                status_icon = "✅" if available else "❌"
                print(
                    f"    {status_icon} {C.CYAN}{lib}{C.RESET}: {f'{C.GREEN}Available{C.RESET}' if available else f'{C.ORANGE}Not Installed{C.RESET}'}"
                )

        if not all(status.values()):
            missing = [lib for lib, available in status.items() if not available]
            missing_str = "\n  - ".join(missing)
            print(
                f"\n{C.PINK}One or more dependencies is not available:\n\n  {C.RESET}{C.CYAN}- {C.RESET}{C.ORANGE}{missing_str}{C.RESET}\n\n{C.PINK}Please install all dependencies, then retry.\n{C.RESET}"
            )
            sys.exit(1)
