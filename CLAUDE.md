# CroP

시험지 PDF 크롭 앱. 웹 Claude로 만들어 파일로 관리해 왔고, **2026-09-30부터 수정은 맥미니 Claude Code(클루)가 맡는다.**
주 개발 clone은 맥미니 `~/CLUE/repos/CroP` 이다. 맥북 clone은 보조이며, 맥북에서 고칠 때는 **먼저 `git pull`** 한다.
수정본은 GitHub 저장소 `kimdeoksoo-71/CroP` 의 `main` 브랜치에 올린다.
이 레포는 **PUBLIC** 이다. 시험지 PDF·크롭 결과·내부 계획서·사고 기록은 올리지 않는다
(개발 문서는 비공개 레포 `kimdeoksoo-71/audit-pipeline-docs` = 맥미니 `~/CLUE/projects/문항검증자동화/`).
맥미니의 무인 파이프라인이 GitHub `main`을 자동으로 받아 가서, 시험(문법·시행 테스트)을 통과하면 사용한다.

## 푸시 전 필수 검사 (2026-09-30, 보완 계획 v5)

1. `python3 -m py_compile exam_crop.py exam_crop_app.py`
2. `~/audit_runner/venv/bin/python -m runner.corpus_check --engine <커밋 SHA 또는 작업 트리 경로>` — 코퍼스 전체의 `--plan-only` 계획이 기대값과 같아야 한다. 의도한 차이는 커밋 메시지에 파일·키 단위로 적는다.
   (corpus_check 가 아직 없으면 `~/audit_runner` 의 `engine.smoke_test` 로 대신한다.)
3. **엔진은 `exam_crop.py` 한 파일**이어야 한다. 러너는 커밋에서 이 파일만 꺼낸다. 다른 모듈 import 금지(표준 라이브러리·pymupdf·PIL 제외). `CAPABILITIES` 에는 완성된 기능만 넣는다.
4. 동작이 바뀌면 `ENGINE_VERSION` 을 올린다.

## 앱 실행 위치 (맥미니)

- **덕수님용 앱 = `~/audit_runner/crop_mirror/CroP.command`** — 러너가 채택한 커밋으로 맞춰진다. 창 제목에 `(러너와 동일)` 이 보여야 한다.
- 개발 clone(`~/CLUE/repos/CroP`)의 `CroP.command` 는 개발 확인용. 창 제목 `[DEV]`, 작업 중(dirty)이거나 main 이 아니면 시작 시 경고한다.
- 실행 환경: python.org Python 3.12 + venv `~/examcrop` (`requirements.txt`). Homebrew python-tk 는 쓰지 않는다.

## CroP 올려줘

사용자가 "CroP 올려줘"라고 하면 아래 순서대로 한다.

1. `git fetch origin` 후 GitHub `main`과 비교한다. GitHub가 로컬보다 앞서 있으면(로컬에 없는 커밋이 있으면) **멈추고 사용자에게 알린다.**
2. `python3 -m py_compile exam_crop.py exam_crop_app.py` 로 문법을 확인한다.
3. `git status` 로 무엇이 바뀌는지 확인한다. PDF·크롭 이미지·빌드 산출물(dist/·build/·*.app·*.spec)이 커밋에 섞이면 **멈추고 물어본다.** 삭제로 잡히는 파일이 있으면 따로 짚어 준다.
4. 사용자가 확인하면 커밋하고 `git push origin main` 한다.
5. 커밋 SHA 앞 7자리와 변경 요약을 알려 준다.

- **force push 는 하지 않는다.**

## 바꾸면 안 되는 것

- `exam_crop.py` 파일 이름과 그 안의 `classify_filename` 함수의 이름·동작(시그니처 포함)은 바꾸지 않는다.
  바꿔야 하면 먼저 사용자에게 알린다. **맥미니 러너가 이것에 의존한다.**

## 맥미니 러너

- 맥미니 러너는 GitHub `main`을 자동으로 받아 시험(문법·시행 테스트)을 하고, 통과하면 사용한다.
  러너는 개발 clone이 아니라 **전용 복사본 `~/audit_runner/crop_mirror`** 로 받는다. 푸시되지 않은 변경은 러너에 반영되지 않는다.
- 시험에 실패하면 이전 버전을 계속 쓰고, 텔레그램으로 알린다.

## .gitignore 로 제외되는 것

- 빌드 산출물: `dist/`, `build/`, `*.spec`, `*.app`
- 캐시/시스템: `__pycache__/`, `*.pyc`, `.DS_Store`, `*.log`, `.venv/`, `venv/`
- 결과물/비밀: `output/`, `crops/`, `secrets/`

## 올려도 되는 것 / 안 되는 것

- **올려도 됨:** `.py` 소스, README, 아이콘/앱 구성 파일(`CroP.icns`, `CroP.png`, `CroP.command`, `build_mac.sh`)
- **올리면 안 됨:** PDF·결과 이미지, `.app`·`dist`·`build` 산출물, 개인 파일
