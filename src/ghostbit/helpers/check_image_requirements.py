#!/usr/bin/env python3
import sys
import logging
import importlib.util
from typing import Dict
from ghostbit.helpers.format_argparse import Colors as C

logger = logging.getLogger("ghostbit.helpers.image_requirements")


class RequirementsChecker:
    """Check software requirements"""

    def __init__(self) -> None:
        logger.info("RequirementsChecker initialized")
        self.PIL = False
        self.NUMPY = False
        self.CRYPTOGRAPHY = False
        self.SCIPY = False
        self.PYWAVELETS = False
        self.JPEGIO = False

    def check_requirements(self, print_results: bool = False) -> None:
        self.PIL = importlib.util.find_spec("PIL") is not None
        logger.debug(f"PIL: {'Available' if self.PIL else 'Not available'}")
        self.NUMPY = importlib.util.find_spec("numpy") is not None
        logger.debug(f"NUMPY: {'Available' if self.NUMPY else 'Not available'}")
        self.CRYPTOGRAPHY = importlib.util.find_spec("cryptography") is not None
        logger.debug(
            f"CRYPTOGRAPHY: {'Available' if self.CRYPTOGRAPHY else 'Not available'}"
        )
        self.SCIPY = importlib.util.find_spec("scipy") is not None
        logger.debug(f"SCIPY: {'Available' if self.SCIPY else 'Not available'}")
        self.PYWAVELETS = importlib.util.find_spec("pywt") is not None
        logger.debug(
            f"PYWAVELETS: {'Available' if self.PYWAVELETS else 'Not available'}"
        )
        self.JPEGIO = importlib.util.find_spec("jpegio") is not None
        logger.debug(f"JPEGIO: {'Available' if self.JPEGIO else 'Not available'}")
        status: Dict[str, bool] = {
            "Pillow": self.PIL,
            "numpy": self.NUMPY,
            "cryptography": self.CRYPTOGRAPHY,
            "scipy": self.SCIPY,
            "PyWavelets": self.PYWAVELETS,
            "jpegio": self.JPEGIO,
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
