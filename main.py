#!/usr/bin/env python3
"""
Screen Automator — 화면 자동화 도구
화면에서 반복적으로 나타나는 버튼이나 텍스트를 자동으로 감지하여 클릭합니다.
"""
import sys
import os

VERSION = "2.1.0"
GITHUB_REPO = "whitesnowsea-max/screen-automator"

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app import run


if __name__ == "__main__":
    run()
