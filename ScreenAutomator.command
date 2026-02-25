#!/bin/bash
# Screen Automator 실행 스크립트
DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="/Users/kangheehan/.gemini/antigravity/scratch/screen_automator"

cd "$PROJECT_DIR"
source venv/bin/activate
python main.py
