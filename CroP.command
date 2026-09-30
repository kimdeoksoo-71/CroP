#!/bin/bash
# CroP 실행 (더블클릭). ~/examcrop 가상환경의 Python으로 앱을 띄운다.
cd "$(dirname "$0")"
PY="$HOME/examcrop/bin/python"
if [ ! -x "$PY" ]; then
  echo "가상환경(~/examcrop)이 없습니다. 터미널에서 다음을 먼저 실행하세요:"
  echo "  1) python.org 공식 설치판 Python 3.12 설치 (Tk 포함, Homebrew와 별개)"
  echo "  2) /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m venv ~/examcrop"
  echo "  3) ~/examcrop/bin/pip install pymupdf pillow"
  echo "  (Homebrew python-tk 는 쓰지 않는다 — 맥미니에서 brew Python이 올라가면 러너 venv가 깨질 수 있음)"
  read -n 1 -s -r -p "아무 키나 누르면 닫힙니다."
  exit 1
fi
exec "$PY" exam_crop_app.py
