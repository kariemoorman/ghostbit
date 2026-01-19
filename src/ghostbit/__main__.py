#!/usr/bin/env python3
import argparse
from ghostbit.cli import main
from ghostbit import setup_logging

if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", "--verbose", action="store_true")
    args, _ = parser.parse_known_args()

    setup_logging(verbose=args.verbose)
    raise SystemExit(main())
