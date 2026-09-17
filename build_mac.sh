#!/bin/bash
# CroP.app 빌드 (Mac에서 한 번 실행). 결과: dist/CroP.app
set -e
cd "$(dirname "$0")"
PY="$HOME/examcrop/bin/python"
"$PY" -m PyInstaller --noconfirm --windowed --name CroP \
  --icon CroP.icns \
  --add-data "exam_crop.py:." \
  exam_crop_app.py
echo
echo "완료: $(pwd)/dist/CroP.app  →  응용 프로그램 폴더로 옮겨 쓰세요."
echo "처음 실행 시 '확인되지 않은 개발자' 경고가 뜨면: 앱을 우클릭 → 열기 → 열기"
