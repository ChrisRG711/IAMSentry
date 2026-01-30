#!/usr/bin/env python3
"""
Simple launcher for IAMSentry
Usage: python run_iamsentry.py [options]
"""

import os
import sys

# Add the current directory to Python path so IAMSentry can be found
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Now import and run IAMSentry
try:
    from IAMSentry import manager
    manager.main()
except ImportError as e:
    print(f"Error importing IAMSentry: {e}")
    print("Make sure you're running this from the correct directory.")
    sys.exit(1)