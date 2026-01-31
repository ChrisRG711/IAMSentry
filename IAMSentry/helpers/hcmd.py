"""Command-line argument parsing for IAMSentry.

This module provides command-line argument parsing using argparse.
"""

import argparse
from typing import List, Optional


def parse(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Arguments:
        args: List of arguments to parse. If None, uses sys.argv.

    Returns:
        Namespace object with parsed arguments:
            - config: Path to configuration file (default: 'my_config.yaml')
            - now: Boolean flag to run immediately instead of scheduled
            - print_base_config: Boolean flag to print base configuration

    Example:
        >>> args = parse(['--config', 'custom.yaml', '--now'])
        >>> args.config
        'custom.yaml'
        >>> args.now
        True
    """
    parser = argparse.ArgumentParser(
        prog="IAMSentry",
        description="IAMSentry - GCP IAM Security Auditor and Remediation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --now                    Run audit immediately
  %(prog)s -c config.yaml --now     Use custom config and run immediately
  %(prog)s --print-base-config      Print default configuration
        """,
    )

    parser.add_argument(
        "-c",
        "--config",
        default="my_config.yaml",
        metavar="FILE",
        help="Path to configuration file (default: my_config.yaml)",
    )

    parser.add_argument(
        "-n",
        "--now",
        action="store_true",
        help="Run audit immediately instead of waiting for scheduled time",
    )

    parser.add_argument(
        "-p",
        "--print-base-config",
        action="store_true",
        dest="print_base_config",
        help="Print the base configuration and exit",
    )

    parser.add_argument(
        "-v", "--version", action="store_true", help="Print version information and exit"
    )

    parsed_args = parser.parse_args(args)

    # Handle version flag
    if parsed_args.version:
        try:
            from IAMSentry import __version__

            print(f"IAMSentry {__version__}")
        except ImportError:
            print("IAMSentry (version unknown)")
        raise SystemExit(0)

    return parsed_args
