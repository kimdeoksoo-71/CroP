#!/bin/bash
# CroP 실행 (더블클릭). ~/examcrop 가상환경의 Python으로 앱을 띄운다.
cd "$(dirname "$0")"
PY="$HOME/examcrop/bin/python"
if [ ! -x "$PY" ]; then
  echo "가상환경(~/examcrop)이 없습니다. 터미널에서 다음을 먼저 실행하세요:"
  echo "  brew install python-tk@3.12"
  echo "  python3.12 -m venv ~/examcrop && ~/examcrop/bin/pip install pymupdf pillow"
  read -n 1 -s -r -p "아무 키나 누르면 닫힙니다."
  exit 1
fi
exec "$PY" exam_crop_app.py
