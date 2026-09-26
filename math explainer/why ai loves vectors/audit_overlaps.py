#!/usr/bin/env python3
"""Run the current storyboard's layout audit in its configured Docker image."""
from pathlib import Path
import subprocess
import sys
if __name__ == '__main__':
    subprocess.run([sys.executable,str(Path(__file__).with_name('editor.py')),'--audit-layout'],check=True)
