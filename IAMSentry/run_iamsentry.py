#!/usr/bin/env python3
"""
Simple launcher for IAMSentry from IAMSentry directory
Usage: python run_iamsentry.py [options]
"""

import multiprocessing
import os
import sys


def main():
    # Add the parent directory to Python path so IAMSentry can be found
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, parent_dir)

    # Now import and run IAMSentry
    try:
        from IAMSentry import manager

        manager.main()
    except ImportError as e:
        print(f"Error importing IAMSentry: {e}")
        print("Make sure you're running this from the correct directory.")
        print(f"Current directory: {current_dir}")
        print(f"Parent directory: {parent_dir}")
        sys.exit(1)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
