#!/usr/bin/env python3
r"""
exam_crop.py — 수능/모의고사 수학 시험지(텍스트 PDF)에서 문제·해설을 문항별 PNG(600dpi)로 잘라내는 코어 라이브러리 + CLI

CLI
  python exam_crop.py 시험지_문제.pdf 시험지_해설.pdf ...   [--out crops] [--exam 이름] [--margin 3] [--dpi 600] [--split] [--debug]
                                                          [--pdf | --pdf-only]

  파일명에 `_문제`(또는 `_문`) 가 있으면 문제지, `_해설`(또는 `_해`) 이 있으면 해설지.   [패치 10: _문/_해 축약형 추가]
  둘 다 없거나 둘 다 있으면 합본으로 보고 **처리하지 않는다** — 문제지·해설지를 따로 나눠 넣어야 한다. [패치 14]
  --exam 을 주지 않으면 파일명에서 확장자와 _문제/_해설(_문/_해) 을 뗀 이름을 시험지명으로 쓴다.

출력
  <out>/<시험지명>_문제_1공통07.png,  <out>/<시험지명>_해설_4미적28.png
  해설이 여러 단(조각)에 걸치면  <시험지명>_해설_4미적28_c1.png, _c2.png … 로 조각별 저장.   [패치 7]
  --pdf 를 주면 같은 이름의 .pdf 도 함께 저장 (--pdf-only 는 PDF만).
  PDF 는 원본 페이지의 해당 영역을 벡터 그대로 옮긴 파일로, 조각이 여럿이면 조각당 1쪽인
  다중 페이지 PDF 가 된다.   [패치 7]

[패치 7 · 2026-08-31 — 해설 이어붙이기 제거]
  Mathpix OCR 은 여러 단을 세로로 이어붙인 초장신 이미지(세로 1만px 이상)에서
  반복 루프·환각 문자·적분 위끝 누락·숫자 오인 등 인식 붕괴를 일으킨다.
  따라서 해설을 한 장으로 stitch 하지 않고:
    - PNG: 조각별로 _c1, _c2 … 저장  → GAS(Mathpix 범위 자동변환.gs 패치 7)가 조각별로
      OCR 한 뒤 순서대로 이어붙여 Data_Latex 한 행에 기록한다.
    - PDF: 조각당 1쪽인 다중 페이지 PDF 로 저장 → Mathpix v3/pdf 가 쪽 단위로 인식한다.
  --split 옵션은 이제 기본 동작과 같아 의미가 없다 (호환을 위해 인자만 유지).

[패치 8 · 2026-09-01 — 외곽선(아웃라인) PDF 감지 모드]
  PDF 프린터(PScript5/Distiller 등)로 재출력된 PDF 는 글자가 모두 벡터 외곽선으로
  변환되어 텍스트가 전혀 없다 (폰트 0개, get_text() 빈 문자열).
  이런 파일은 문항 번호를 텍스트로 찾을 수 없으므로, 벡터 글리프의 모양을 직접 분석한다:
    1) 단(column) 왼쪽 가장자리에서 「숫자 글리프 1~2개 + 마침표」 꼴의 토큰을 찾는다.
       (숫자는 폭/높이 비율로 한글과 구분, 마침표는 숫자 높이의 10~30% 크기)
    2) 읽기 순서상 처음 9개의 한 자리 토큰이 1.~9. 임을 이용해 숫자 1~9의 외곽선
       모양을 학습하고, 첫 두 자리 토큰(10.)에서 0 을 학습한다.
       ('10.' 의 첫 글리프가 학습된 '1' 과 일치하는지로 검증)
    3) 학습된 모양으로 모든 토큰의 번호를 판독한다. 같은 글자는 같은 외곽선을 가지므로
       OCR 없이 정확히 읽힌다.
  문제(≈13pt)/해설(≈18pt) 번호는 글리프 높이로 구분한다. 흰색 글리프로 숨겨진
  문항 끝 표시(N.)도 위치 기반으로 인식해 문제 영역을 자르는 데 그대로 쓴다.
  텍스트가 하나라도 있는 PDF 는 기존(텍스트) 방식 그대로 처리한다.

[패치 9 · 2026-09-06 — 마침표 없는 해설 번호 양식(강대 K 모의고사 등)]
  강남대성 '정답 및 해설'은 해설 번호가 `7.` 이 아니라 마침표 없는 24pt 이탤릭 `7` 이고,
  두 자리 번호는 PDF 안에서 '1',' ','0' 세 span 으로 쪼개져 줄 텍스트가 '1 0' 이 된다.
  기존 패턴 `^(\d{1,2})\.\s*$` 은 둘 다 놓쳐 해설 문항이 0개가 됐다.
    1) 해설 번호 판정(strict): 줄 안 공백을 제거한 뒤 `N.` 또는 `N`(1~30) 을 모두 허용.
       (크기 ≥ SOL_HEADING_SIZE, 단 왼쪽 가장자리, 그 줄에 다른 글자 없음 — 기존 조건 유지)
    2) 과목 라벨('확률과 통계 해설' 등)이 이 양식에서는 텍스트로 추출되지 않고 선 2개만 남는다.
       23번 직전 선두 조각이 텍스트 없이 얇으면(<60pt) 라벨로 보고 버린다 — 패치 8의
       외곽선 전용 규칙을 텍스트 PDF 로 일반화. (안 버리면 직전 30번의 _c2 조각이 된다)
    3) 해설 페이지 어디에도 과목 텍스트가 없으면 "확통→미적→기하 순서 가정" 안내를 notes 에 남긴다.

[패치 10 · 2026-09-19 — 파일명 `_문` / `_해` 축약 표기 인식 + 문제지 0개 진단 로그]
  1) 파일명 종류 판별(KIND_RE)에 `_문`, `_해` 축약형을 추가했다.
       K25(260915)_문.pdf → 문제,  K25(260915)_해.pdf → 해설,  시험지명 = K25(260915)
     축약형은 구분자(_, -, 공백) 뒤에 오고 바로 뒤에 한글이 이어지지 않을 때만 인정한다
     (`_문항`, `_해커스` 같은 이름을 오인하지 않기 위해). 기존 `_문제`/`_해설`/`_문제지`/
     `_해설지`/`_정답및해설` 은 그대로다.
     ※ 패치 9까지는 `_문`/`_해` 파일이 둘 다 '합본'으로 분류되고 시험지명도 `…_문`, `…_해` 로
       서로 달라 한 세트로 묶이지 않았다. 합본으로 분석된 문제지에서 해설 크기 번호가 하나라도
       잡히면 그 쪽부터 해설 구간으로 넘어가 문제 문항이 0개가 될 수 있다.
  2) 문제/합본 파일에서 문제 문항을 하나도 못 찾았을 때, 원인을 가늠할 수 있는 진단문을
     notes 에 남긴다 (텍스트 있는 쪽 수, 크기 조건을 만족한 `N.` 번호 수, 해설 크기(≥17pt)
     번호 수, 해설 구간 시작 쪽). GUI 로그에 그대로 표시된다.
  3) 문제 파일(kind='문제')은 해설 구간을 나누지 않고, 해설 크기(≥17pt)로 잡힌 번호도
     문제 번호로 쓴다 — 문제지 번호가 크거나 마침표가 없는 양식에서 번호가 전부 해설로
     분류돼 문제 페이지가 통째로 해설 구간으로 넘어가 0개가 되는 일을 막는다.
     (해설 파일과 합본은 종전과 같다.)

[패치 11 · 2026-09-20 — 이미지 글자 PDF 감지 모드 (강대 K 문제지)]
  강남대성 K 모의고사 문제지는 본문 글자와 문항 번호가 전부 낱말 단위 이미지로 들어 있다
  (텍스트는 HWP 수식 폰트 글리프뿐, 번호 이미지는 소프트마스크라 내용 판독 불가).
  텍스트 번호도, 벡터 외곽선도 없어 패치 8·9 로는 문항 0개였다.
    1) 텍스트 번호를 못 찾았고 쪽당 이미지가 IMGTXT_MIN_IMAGES 개 이상이면 이 모드로 전환.
    2) 단 왼쪽 가장자리에 붙은 작은 이미지(폭 9~26pt, 높이 9~20pt, 줄의 첫 요소)를 번호로 본다.
    3) 번호는 읽기 순서로 1~22, 이후 23~30 반복으로 배정 (수능 수학 구성). 한 자리 번호 이미지가
       두 자리보다 좁은지, 개수가 22+8k 인지로 검증하고 어긋나면 notes 에 경고.
    4) 과목명을 읽을 수 없어 23번마다 확통→미적→기하 순으로 배정 (외곽선 모드와 같음).
  같은 세트의 해설지는 번호가 텍스트라 패치 9 로 정상 처리된다.

[패치 12 · 2026-09-27 — 3단 해설 양식 (SOLN 모의고사 등)]
  해설이 세로 구분선 2개로 나뉜 3단 편집이고, 해설 번호가 본문과 같은 9pt 크기의
  `N. [정답] ④` 꼴이라 기존 규칙(2단, 해설 번호 ≥17pt)으로는 해설이 0개였다.
    1) 레이아웃: 쪽 높이 40% 이상의 세로선이 x 위치가 다른 것으로 2개 이상이면 N단으로 본다.
       (Layout.dividers — 2단 PDF 는 종전과 똑같이 동작)
       같은 문서의 3단 쪽과 구분선 x 가 같은데 세로선이 1개뿐인 쪽(마지막 쪽 등)도 3단으로 맞춘다.
    2) 해설 번호: 3단 쪽에서 단 왼쪽 끝에 붙은 `N.` 뒤에 같은 줄로 `정답` 이 오면 해설 번호로 본다
       (글자 크기 무관). 한 줄로 합쳐진 `N. [정답] ④` 꼴도 인정.
    3) 과목 라벨(`[공통]`, `확률과 통계`, `미적분`, `기하` — 12pt 이상 단독 줄)과 `[해설]` 라벨이
       단 중간에 오면 그 윗선에서 해설 조각을 끊는다. 라벨 아래 빠른 정답표는 다음 번호 전까지라
       어느 문항에도 붙지 않는다. (종전 규칙은 라벨이 있는 선두 조각을 통째로 버려서, 라벨 위에
       있던 직전 문항(예: 22번)의 이어지는 해설까지 사라졌다.)
    4) 과목은 읽기 순서상 가장 최근에 지나온 과목 라벨로 정한다. 쪽 전체 텍스트에서 과목명을
       찾는 기존 방식은 한 쪽에 두 과목(확통 30번 + 미적 23번)이 섞이면 틀리기 때문.
    5) 해설 쪽 번호가 텍스트로 잡혀도, 문제 쪽이 이미지 글자(패치 11)이면 문제 쪽에만
       이미지 글자 감지를 따로 돌린다 (종전에는 번호가 하나라도 잡히면 이미지 감지를 건너뜀).

[패치 13 · 2026-09-28 — 이미지 글자 모드: 단 바닥 「※ 확인 사항」 안내 박스 제외 (강대 K28 문제지)]
  텍스트 모드는 '확인 사항' 문구(EXCLUDE_TEXT)에서 영역을 끊지만, 이미지 글자 PDF 는 그 문구도
  이미지라 22번·각 선택과목 30번처럼 단의 마지막 문항 아래에 안내 박스가 통째로 딸려 들어갔다.
    1) 단 폭의 90% 이상인 윗변·아랫변 가로선 + 양 끝 세로선으로 된 사각형이
       아랫변이 본문 바닥(단 구분선 아래끝)에 ±3pt 로 붙어 있고, 높이가 본문의 25% 이하이며,
       안에 문항 번호가 없으면 안내 박스로 본다.
    2) 그 박스의 선과 안의 글자 이미지를 항목에서 빼서 문항 영역이 박스 위에서 끝나게 한다.
    3) 이미지 글자 모드(_imgtxt_pass)에서만 동작 — 텍스트·외곽선 모드와 해설은 종전과 같다.
       (26K28: 1공통22·3확통30·4미적30·5기하30 네 문항만 바뀌고 나머지 42문항·해설 46문항은 동일)

[패치 14 · 2026-09-30 — 합본 PDF 거부]
  합본(한 파일에 문제+해설)은 번호 글자 크기로 문제/해설 구간을 갈라 왔는데, 조판 크기가 다른 양식에서는
  판단이 제각각이다. 서킷더베스트(07회) A4 합본은 해설 번호(15.4pt)가 해설 기준(17pt)에 못 미치고 문제 기준
  (12.3pt)은 넘어 해설 12개가 `_문제_` 이름으로 잘렸고, 진짜 문제(9.9pt)는 0개였다.
  → 문제지·해설지는 **언제나 별도 파일**로만 받는다. 종류는 파일명으로만 정한다.
    1) classify_filename: 이름에 문제 표기와 해설 표기가 **둘 다** 있으면('…문제및해설') 합본으로 본다.
       (한쪽만 있으면 종전과 같다. 시그니처·반환값 형식은 그대로 — 맥미니 러너가 의존한다.)
    2) 합본은 CLI·GUI·build_jobs 모두에서 COMBINED_MSG 를 내고 멈춘다 (CLI 는 아무것도 자르기 전에 종료 코드 2).
    3) CLI `--kind 합본` 선택지는 없앴다. analyze()의 합본 분기는 남겨 두지만 더 이상 타지 않는다.

[패치 15 · 2026-09-30 — 작은 조판 (A4 축소 양식, 서킷더베스트)]
  패치 14로 문제지·해설지를 나눠도, 파일 안의 번호 찾기가 고정 크기 기준이라 서킷더베스트07회는
  문제(9.9pt < 12.3)·해설(15.4pt < 17) 모두 0문항이었다. 종류는 이미 파일명이 정하므로 크기는
  '번호냐 본문이냐'만 가르면 된다 → _small_type_pass (그 종류의 번호를 하나도 못 찾았을 때만):
    1) 해설 파일에 해설 크기 번호가 없으면 문제 크기(≥12.3pt) 번호를 해설 번호로 쓴다 (패치 10의 거울).
    2) 그래도 0개면 기준을 '본문 크기(글자 수 가중 최빈) × 1.1'로 낮춰 `N.` 번호를 다시 찾는다.
  번호를 이미 찾는 파일은 그대로다 (26K28 문제·해설 46문항 자르는 영역 동일 확인).

[패치 16 · 2026-09-30 — 엔진 버전·기능 목록·결과 JSON·계획 출력]  (보완 계획 v5 0-4·0-5)
  - ENGINE_VERSION / CAPABILITIES / engine_version(): 러너·앱·corpus_check 가 엔진을 식별한다.
    SHA 는 (1) 같은 폴더의 _build_info.py(러너가 꺼낼 때 씀, import 가 아니라 파일로 읽음)
    (2) 이 폴더가 git 작업 트리의 최상위일 때만 git (3) 아니면 unknown. import 시점에는 아무것도 실행하지 않는다.
  - --json <경로>: 파일마다 file 레코드, 시험지마다 set 레코드 (JSON Lines, schema 1). §3.4
  - --plan-only: 자르지 않고 계획(문항 키·조각 영역)만 레코드로 낸다. 코퍼스 회귀 비교의 기준. §3.5
  - 합본은 sys.exit(2) 대신 rejected 레코드(combined_not_supported)로 남기고 다음 파일로 간다.
    종료 코드: 0 = failed·rejected 없음 / 1 = failed 있음 / 3 = failed 없고 rejected 있음.
  - 이 파일은 계속 **한 파일**이어야 한다 — 맥미니 러너는 커밋에서 exam_crop.py 만 꺼내 쓴다.

GUI 앱은 exam_crop_app.py 참고.
"""
from __future__ import annotations

import argparse
import io
import os
import json
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import pymupdf  # PyMuPDF
from PIL import Image

# ------------------------------------------------------------ 엔진 식별 -----
ENGINE_VERSION = "P16"                     # 패치 번호. 동작이 바뀌는 커밋마다 올린다
CAPABILITIES = frozenset({"json", "plan_only"})   # 러너는 이 집합만 보고 새 경로를 쓴다 (완성된 기능만 넣는다)
JSON_SCHEMA = 1                            # --json 레코드 형식 번호. 필드를 빼거나 뜻을 바꾸면 올린다
MIRROR_DIR = os.path.expanduser("~/audit_runner/crop_mirror")   # 맥미니 러너 전용 복사본 (여기서 뜨는 앱 = 러너 엔진)


def engine_git_state() -> dict:
    """{"sha": str|None, "dirty": bool, "branch": str|None, "source": "build_info"|"git"|None}.
    호출될 때만 실행된다 (import 시점 부작용 없음). git 은 이 폴더가 작업 트리 최상위일 때만, 2초 제한."""
    here = os.path.dirname(os.path.abspath(__file__))
    st = {"sha": None, "dirty": False, "branch": None, "source": None}
    try:
        with open(os.path.join(here, "_build_info.py"), encoding="utf-8") as f:
            m = re.search(r"""GIT_SHA\s*=\s*["']([0-9a-fA-F]{7,40})(-dirty)?["']""", f.read())
        if m:
            st.update(sha=m.group(1)[:7], dirty=bool(m.group(2)), source="build_info")
            return st
    except OSError:
        pass

    def git(*args):
        r = subprocess.run(["git", "-C", here, *args], capture_output=True, text=True, timeout=2)
        return r.stdout.strip() if r.returncode == 0 else None
    try:
        top = git("rev-parse", "--show-toplevel")
        if top and os.path.realpath(top) == os.path.realpath(here):
            sha = git("rev-parse", "--short=7", "HEAD")
            if sha:
                st.update(sha=sha, source="git",
                          dirty=bool(git("status", "--porcelain", "--untracked-files=no")),
                          branch=git("rev-parse", "--abbrev-ref", "HEAD"))
    except (OSError, subprocess.SubprocessError):
        pass
    return st


def engine_version() -> str:
    """'P16+abc1234[-dirty]' 또는 'P16+unknown'."""
    st = engine_git_state()
    return f"{ENGINE_VERSION}+{st['sha'] or 'unknown'}{'-dirty' if st['dirty'] else ''}"


def is_dev_checkout() -> bool:
    """개발 clone 에서 실행 중인가 — git 작업 트리이면서 러너 미러(MIRROR_DIR)가 아닐 때."""
    here = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))
    return engine_git_state()["source"] == "git" and here != os.path.realpath(MIRROR_DIR)


# ---------------------------------------------------------------- 설정 -----
SUBJECT_CODES = {"공통": "1공통", "확통": "3확통", "미적": "4미적", "기하": "5기하"}
DEFAULT_ORDER = ["확통", "미적", "기하"]          # 23번이 다시 나올 때마다 이 순서로 과목이 바뀜
SUBJECT_PATTERNS = [                             # 페이지 머릿말/구분 라벨에서 과목 감지
    (re.compile(r"확률\s*과\s*통계"), "확통"),
    (re.compile(r"미적분"), "미적"),
    (re.compile(r"(?<![가-힣])기하(?![가-힣])"), "기하"),
]
EXCLUDE_TEXT = re.compile(
    r"지선다형|단답형|확인\s*사항|답안지|선택\s*과목|홀수형|짝수형|교시|수학\s*영역|"
    r"모의평가|모의고사|문제지|대학수학능력시험|학년도|^MEMO$|^정답$|^공통과목$"
)
SECTION_LABEL = re.compile(r"^\s*(공통과목|확률\s*과\s*통계|미적분|기하)(\s*해설)?\s*$")   # [패치 9] '… 해설' 꼴도 라벨
# [패치 9] 해설 번호: 'N.' 또는 마침표 없는 'N' (공백은 미리 제거).  문제 번호는 종전대로 'N.' 만.
SOL_HEAD_RE = re.compile(r"^(\d{1,2})\.?$")
PROB_HEAD_RE = re.compile(r"^(\d{1,2})\.(\s|$)")
LABEL_CHUNK_MAX_H = 60       # [패치 9] 23번 직전 선두 조각이 이보다 얇고 텍스트가 없으면 과목 라벨로 간주
# [패치 12] 3단 해설 양식
MULTICOL_MIN_GAP = 60.0      # 서로 다른 단 구분선으로 볼 세로선 x 간격 하한(pt)
MC_HEAD_RE = re.compile(r"^(\d{1,2})\.$")                      # 줄 전체가 'N.'
MC_HEAD_INLINE_RE = re.compile(r"^(\d{1,2})\.\s*\[?\s*정답")    # 한 줄로 합쳐진 'N. [정답] …'
MC_LABEL_RE = re.compile(r"^\[?\s*(공통(?:\s*과목)?|확률\s*과\s*통계|미적분|기하|해설)\s*\]?$")
MC_LABEL_MIN_SIZE = 12.0     # 과목·[해설] 라벨 글자 크기 하한 (본문 9pt 내외, 라벨 14.6pt)
MC_LABEL_SUBJ = {"공통": "공통", "공통과목": "공통", "확률과통계": "확통", "미적분": "미적", "기하": "기하"}
PROB_HEADING_SIZE = 12.3     # 문제 번호 글자 크기 하한 (본문 11pt 내외, 번호 13pt 내외)
SOL_HEADING_SIZE = 17.0      # 해설 번호 글자 크기 하한 (20pt 내외)
MM = 72 / 25.4               # 1mm → pt
STITCH_GAP_MM = 3.0          # (구버전 stitch 용, 현재 미사용)

# [패치 10] 파일명 종류 표기.
#   group(1): 기존 전체 표기 — 구분자 없이 붙어 있어도 인정 (예: '모의고사문제')
#   group(2): 축약 표기 '문' / '해' — 반드시 구분자(_ - 공백) 뒤에 오고, 바로 뒤에 한글이 없어야 함
#             (예: 'K25_문.pdf', 'K25_해(260915).pdf' ○ / 'K25_문항별.pdf', '2606_해커스.pdf' ×)
KIND_RE = re.compile(
    r"[_\-\s]?(문제지|문제|해설지|해설|정답및해설|정답\s*및\s*해설)"
    r"|[_\-\s](문|해)(?![가-힣])",
    re.I,
)

# ---- 패치 8: 외곽선 PDF 감지 파라미터 -------------------------------------
OUTLINE_HEAD_MIN_H = 9.2      # 문항 번호 숫자 글리프 높이 하한(pt) — 본문 11pt 숫자(≈8.4)와 구분
OUTLINE_HEAD_MAX_H = 17.0     # 상한(pt) — 해설 번호(≈13~14)까지 포함
OUTLINE_DIGIT_RATIO = 0.78    # 숫자 글리프 폭/높이 상한 (한글 음절은 ≈0.9~1.0 이라 걸러짐)
OUTLINE_DOT_RATIO = (0.10, 0.30)   # 마침표 높이 ÷ 숫자 높이 허용 범위 (쉼표·기호는 더 큼)
OUTLINE_SOL_SPLIT = 1.18      # 합본에서 해설/문제 번호를 가르는 높이 비
OUTLINE_MARKER_H = (2.5, 8.8)  # 흰색 문항 끝 표시 글리프의 높이 범위(pt)
OUTLINE_SAME_TOL = 0.12       # 글리프 모양 비교 허용 오차 (높이로 정규화한 좌표)


# ------------------------------------------------------------ 자료구조 -----
@dataclass
class Item:
    rect: pymupdf.Rect
    kind: str                      # 'text' | 'image' | 'draw'
    text: str = ""
    size: float = 0.0
    color: int = 0


@dataclass
class Heading:
    num: int
    rect: pymupdf.Rect
    page: int
    col: int


@dataclass
class Layout:
    top: float
    bottom: float
    left: float
    right: float
    divider: float
    width: float
    height: float
    dividers: List[float] = field(default_factory=list)   # [패치 12] 단 구분선 x 목록 (N단)

    def __post_init__(self):
        if not self.dividers:
            self.dividers = [self.divider]

    @property
    def ncols(self) -> int:
        return len(self.dividers) + 1

    def col_bounds(self, col: int) -> Tuple[float, float]:
        edges = [self.left] + self.dividers + [self.right]
        col = max(0, min(col, len(edges) - 2))
        return edges[col], edges[col + 1]

    def col_of(self, rect: pymupdf.Rect) -> int:
        cx = (rect.x0 + rect.x1) / 2
        return sum(1 for d in self.dividers if cx >= d)


@dataclass
class PageInfo:
    no: int
    layout: Layout
    items: List[Item]
    hidden: List[Item]
    prob_heads: List[Heading]
    sol_heads: List[Heading]
    subject_hint: Optional[str]
    has_answer_table: bool


@dataclass
class Segment:
    page: int
    clip: pymupdf.Rect
    body_top: float = 0.0        # 이 y(머릿말 밑줄) 위쪽은 렌더링 후 흰색으로 지운다


@dataclass
class Job:
    """PNG 한 장(조각이 여럿이면 _c1, _c2 …)을 만드는 단위."""
    kind: str                  # '문제' | '해설'
    subject: str
    num: int
    exam: str
    segments: List[Segment] = field(default_factory=list)
    split: bool = False        # (패치 7 이후 미사용 — 호환용)

    @property
    def base(self) -> str:
        return f"{clean_exam_name(self.exam) or self.exam}_{self.kind}_{SUBJECT_CODES[self.subject]}{self.num:02d}"


@dataclass
class Analysis:
    path: str
    pages: List[PageInfo]
    problem_pages: List[int]
    solution_pages: List[int]
    outline: bool = False              # [패치 8] 외곽선 PDF 감지 모드로 분석했는가
    notes: List[str] = field(default_factory=list)   # [패치 8] 감지 과정의 경고·안내


# ------------------------------------------------------- 페이지 분석 -----
def analyze_layout(page: pymupdf.Page, drawings) -> Layout:
    """머릿말 밑줄(가로 긴 선)과 가운데 세로 구분선을 찾아 본문 영역과 단 경계를 정한다."""
    W, H = page.rect.width, page.rect.height
    h_rules, v_rules = [], []
    for d in drawings:
        r = d["rect"]
        if r.width > 0.6 * W and r.height < 3:
            h_rules.append(r)
        if r.height > 0.4 * H and r.width < 3:
            v_rules.append(r)
    top_rules = [r.y0 for r in h_rules if r.y0 < 0.3 * H]
    top = max(top_rules) if top_rules else 0.12 * H
    if v_rules:
        v = max(v_rules, key=lambda r: r.height)
        divider, bottom = v.x0, v.y1
    else:
        divider, bottom = W / 2, 0.93 * H
    left = min([r.x0 for r in h_rules], default=0.06 * W)
    right = max([r.x1 for r in h_rules], default=0.94 * W)
    # [패치 12] x 위치가 다른 긴 세로선이 2개 이상이면 N단 (3단 해설 등)
    xs: List[float] = []
    for r in sorted(v_rules, key=lambda r: r.x0):
        if not (0.1 * W < r.x0 < 0.9 * W):
            continue                                      # 쪽 테두리 세로선은 단 구분선이 아님
        if not xs or r.x0 - xs[-1] > MULTICOL_MIN_GAP:
            xs.append(r.x0)
    if len(xs) >= 2:
        if not top_rules:                                 # 머릿말 선이 없으면 세로선 윗끝을 본문 시작으로
            top = min(r.y0 for r in v_rules) - 4
        bottom = max(r.y1 for r in v_rules)
        return Layout(top, bottom, left, right, xs[0], W, H, xs)
    return Layout(top, bottom, left, right, divider, W, H)


def collect_items(page: pymupdf.Page, layout: Layout, drawings) -> Tuple[List[Item], List[Item]]:
    items, hidden = [], []
    W, H = layout.width, layout.height
    body = pymupdf.Rect(layout.left - 5, layout.top + 1, layout.right + 5, layout.bottom + 1)

    for b in page.get_text("dict")["blocks"]:
        if b["type"] == 1:
            r = pymupdf.Rect(b["bbox"])
            if r.intersects(body) and r.y0 >= layout.top - 2:
                items.append(Item(r, "image"))
            continue
        for line in b["lines"]:
            text = "".join(s["text"] for s in line["spans"]).strip()
            if not text:
                continue
            first = next(s for s in line["spans"] if s["text"].strip())
            r = pymupdf.Rect(line["bbox"])
            it = Item(r, "text", text, first["size"], first["color"])
            if all(s["color"] == 0xFFFFFF for s in line["spans"] if s["text"].strip()):
                hidden.append(it)
                continue
            # 큰 분수·적분 기호가 있는 줄은 글자 상자가 머릿말 선 위로 살짝 올라가므로 줄의 세로 중심으로 판정
            cy = (r.y0 + r.y1) / 2
            if cy < layout.top or r.y1 > layout.bottom + 15:
                continue
            items.append(it)

    for d in drawings:
        r = pymupdf.Rect(d["rect"])
        if r.width > 0.6 * W or (r.height > 0.4 * H and r.width < 3):
            continue                                    # 머릿말 선, 단 구분선
        if r.y1 < layout.top or r.y0 > layout.bottom:
            continue                                    # 머릿말/꼬릿말 장식
        if d.get("color") is None and d.get("fill") and min(d["fill"]) > 0.97:
            continue                                    # 흰색 배경 사각형
        if r.width < 0.5 and r.height < 0.5:
            continue
        lw = (d.get("width") or 0) / 2                  # 선 굵기 절반만큼 넓혀서 테두리가 잘리지 않게
        items.append(Item(pymupdf.Rect(r.x0 - lw, r.y0 - lw, r.x1 + lw, r.y1 + lw), "draw"))
    return items, hidden


def find_headings(items: List[Item], layout: Layout, page_no: int, min_size: float, strict: bool) -> List[Heading]:
    hs = []
    pat = SOL_HEAD_RE if strict else PROB_HEAD_RE
    for it in items:
        if it.kind != "text" or it.size < min_size:
            continue
        # [패치 9] 해설 번호는 '1 0' 처럼 span 사이 공백이 끼어 있을 수 있어 공백을 걷어내고 본다
        text = re.sub(r"\s+", "", it.text) if strict else it.text
        m = pat.match(text)
        if not m:
            continue
        num = int(m.group(1))
        if strict and not text.endswith(".") and not 1 <= num <= 30:
            continue                  # 마침표 없는 숫자는 문항 번호 범위일 때만 (쪽 번호 등 배제)
        x0, _ = layout.col_bounds(layout.col_of(it.rect))
        if it.rect.x0 - x0 > 40:      # 문항 번호는 단의 왼쪽 가장자리에 붙어 있어야 함
            continue
        hs.append(Heading(num, it.rect, page_no, layout.col_of(it.rect)))
    hs.sort(key=lambda h: (h.col, h.rect.y0))
    return hs


def page_subject(text: str) -> Optional[str]:
    for pat, subj in SUBJECT_PATTERNS:
        if pat.search(text):
            return subj
    return None


# ---------------------------------------------- 패치 12: 3단 해설 -----
def find_multicol_sol_heads(items: List[Item], layout: Layout, page_no: int) -> List[Heading]:
    """3단 이상 쪽에서 `N. [정답] ④` 꼴 해설 번호를 찾는다 (글자 크기 무관).

    조건: ① 줄 텍스트가 'N.' (또는 'N. [정답]…' 한 줄)  ② 단의 글자 중 가장 왼쪽에 붙어 있음
          ③ 'N.' 단독 줄이면 같은 높이 오른쪽 25pt 안에 '정답' 이 있음
    """
    texts = [it for it in items if it.kind == "text"]
    col_left: Dict[int, float] = {}
    for it in texts:
        c = layout.col_of(it.rect)
        col_left[c] = min(col_left.get(c, 1e9), it.rect.x0)
    hs = []
    for it in texts:
        t = it.text.strip()
        m = MC_HEAD_INLINE_RE.match(t)
        if not m:
            m = MC_HEAD_RE.match(re.sub(r"\s+", "", t))
            if not m:
                continue
            cy = (it.rect.y0 + it.rect.y1) / 2
            if not any("정답" in o.text and abs((o.rect.y0 + o.rect.y1) / 2 - cy) < 3
                       and 0 <= o.rect.x0 - it.rect.x1 < 25 for o in texts):
                continue
        num = int(m.group(1))
        if not 1 <= num <= 30:
            continue
        c = layout.col_of(it.rect)
        if it.rect.x0 - col_left.get(c, it.rect.x0) > 4:
            continue                                  # 단 왼쪽 끝에 붙어 있어야 함 (본문 속 'N.' 배제)
        hs.append(Heading(num, it.rect, page_no, c))
    hs.sort(key=lambda h: (h.col, h.rect.y0))
    return hs


def multicol_labels(items: List[Item]) -> List[Tuple[Item, Optional[str]]]:
    """과목 라벨·[해설] 라벨 목록 → (항목, 과목코드 또는 None('해설' 라벨))."""
    out = []
    for it in items:
        if it.kind != "text" or it.size < MC_LABEL_MIN_SIZE:
            continue
        m = MC_LABEL_RE.match(it.text.strip())
        if not m:
            continue
        key = re.sub(r"\s+", "", m.group(1))
        out.append((it, MC_LABEL_SUBJ.get(key)))
    return out


def _unify_multicol(layouts: List[Layout]):
    """[패치 12] 같은 문서에서 3단 쪽의 구분선과 x 가 같은 세로선 1개짜리 쪽(마지막 쪽 등)을 3단으로 맞춘다."""
    multi = [l for l in layouts if l.ncols >= 3]
    if not multi:
        return
    ref = multi[0]
    for l in layouts:
        if l.ncols == 2 and any(abs(l.divider - d) < 3 for d in ref.dividers):
            l.dividers = list(ref.dividers)
            l.divider = ref.dividers[0]
            if ref.top < l.top:
                l.top = ref.top


# ------------------------------------------- 패치 8: 외곽선 PDF 감지 -----
def _outline_pts(dr) -> list:
    """글리프 경로의 좌표를 (상자 원점 기준, 높이로 나눠) 정규화한 목록.
    같은 글자는 같은 폰트 프로그램에서 나오므로 정규화 좌표가 사실상 동일하다."""
    r = dr["rect"]
    s = max(r.height, 0.01)
    return [((p.x - r.x0) / s, (p.y - r.y0) / s)
            for it in dr["items"] for p in it[1:] if isinstance(p, pymupdf.Point)]


def _outline_same(a: list, b: list) -> bool:
    if len(a) != len(b):
        return False
    return max(abs(x1 - x2) + abs(y1 - y2) for (x1, y1), (x2, y2) in zip(a, b)) < OUTLINE_SAME_TOL


def _outline_tokens(pno: int, layout: Layout, drawings) -> List[dict]:
    """한 페이지에서 「숫자 글리프 1~2개 + 마침표」 꼴의 문항 번호 후보 토큰을 찾는다."""
    fills = [d for d in drawings
             if d["type"] == "f" and d.get("fill") and max(d["fill"]) < 0.15]
    tokens, seen = [], set()
    dots = [d for d in fills
            if 1 < d["rect"].height < OUTLINE_DOT_RATIO[1] * OUTLINE_HEAD_MAX_H
            and d["rect"].width < 0.45 * OUTLINE_HEAD_MAX_H]
    for dot in dots:
        rd = dot["rect"]
        digits, cur_x = [], rd.x0
        for _ in range(2):                                     # 마침표 왼쪽의 숫자 1~2개
            cand = [g for g in fills
                    if OUTLINE_HEAD_MIN_H <= g["rect"].height <= OUTLINE_HEAD_MAX_H
                    and g["rect"].width < OUTLINE_DIGIT_RATIO * g["rect"].height
                    and abs(g["rect"].y1 - rd.y1) < 3           # 밑선 정렬
                    and 0 <= cur_x - g["rect"].x1 < 4.5]
            if not cand:
                break
            g = max(cand, key=lambda g: g["rect"].x1)
            digits.insert(0, g)
            cur_x = g["rect"].x0
        if not digits:
            continue
        hmax = max(g["rect"].height for g in digits)
        if not (OUTLINE_DOT_RATIO[0] * hmax <= rd.height <= OUTLINE_DOT_RATIO[1] * hmax):
            continue                                            # 마침표 크기 검증 (쉼표·기호 배제)
        t0 = digits[0]["rect"]
        rect = pymupdf.Rect(t0.x0, min(g["rect"].y0 for g in digits), rd.x1, rd.y1)
        col = layout.col_of(rect)
        colx, _ = layout.col_bounds(col)
        if t0.x0 - colx > 40:                                   # 번호는 단 왼쪽 가장자리
            continue
        cy = (t0.y0 + t0.y1) / 2
        if not (layout.top < cy < layout.bottom):
            continue
        if any(g["rect"].x1 < t0.x0 - 1 and g["rect"].y0 < cy < g["rect"].y1
               and g["rect"].x0 > colx - 6 for g in fills):
            continue                                            # 줄 왼쪽에 다른 글자가 있으면 본문
        key = (col, round(rect.x0, 1), round(rect.y0, 1))
        if key in seen:
            continue
        seen.add(key)
        tokens.append({"page": pno, "col": col, "y0": t0.y0, "rect": rect,
                       "digits": digits, "h": hmax})
    tokens.sort(key=lambda t: (t["col"], t["y0"]))
    return tokens


def _outline_markers(layout: Layout, drawings) -> List[Item]:
    """흰색 글리프로 숨겨진 문항 끝 표시(N.)를 위치·크기로 찾는다 (번호 판독은 불필요)."""
    out = []
    for d in drawings:
        if d["type"] != "f" or not d.get("fill") or min(d["fill"]) <= 0.97:
            continue
        r = d["rect"]
        if not (OUTLINE_MARKER_H[0] < r.height < OUTLINE_MARKER_H[1]):
            continue
        if r.width > r.height:                       # 흰 배경 사각형 등 배제
            continue
        col = layout.col_of(r)
        colx, _ = layout.col_bounds(col)
        if r.x0 - colx > 15:                         # 끝 표시는 단 왼쪽 가장자리에 있다
            continue
        cy = (r.y0 + r.y1) / 2
        if not (layout.top < cy < layout.bottom):
            continue
        out.append(Item(pymupdf.Rect(r), "text", "", 0.0, 0xFFFFFF))
    return out


def _outline_decode(tokens: List[dict], label: str, notes: List[str]) -> List[dict]:
    """읽기 순서의 토큰 목록에서 숫자 모양을 학습해 각 토큰에 번호(num)를 매긴다."""
    singles = [t for t in tokens if len(t["digits"]) == 1]
    doubles = [t for t in tokens if len(t["digits"]) == 2]
    if len(singles) < 9 or not doubles:
        notes.append(f"{label}: 한 자리 번호 {len(singles)}개·두 자리 {len(doubles)}개 — "
                     f"1~9 학습에 부족해 번호를 판독하지 못함")
        return []
    shapes = {i + 1: _outline_pts(t["digits"][0]) for i, t in enumerate(singles[:9])}
    for i in range(1, 10):                            # 1~9 는 서로 다른 모양이어야 한다
        for j in range(i + 1, 10):
            if _outline_same(shapes[i], shapes[j]):
                notes.append(f"{label}: 번호 {i}와 {j}의 글리프가 같음 — 오탐 의심, 판독 중단")
                return []
    first10 = doubles[0]
    if not _outline_same(_outline_pts(first10["digits"][0]), shapes[1]):
        notes.append(f"{label}: 첫 두 자리 번호가 '10.'이 아님 — 오탐 의심, 판독 중단")
        return []
    shapes[0] = _outline_pts(first10["digits"][1])

    def read(g) -> Optional[int]:
        pts = _outline_pts(g)
        for v, rep in shapes.items():
            if _outline_same(pts, rep):
                return v
        return None

    out = []
    for t in tokens:
        ds = [read(g) for g in t["digits"]]
        if None in ds:
            notes.append(f"{label}: {t['page'] + 1}쪽의 번호 글리프 판독 실패 — 해당 후보 건너뜀")
            continue
        num = ds[0] if len(ds) == 1 else ds[0] * 10 + ds[1]
        if not 1 <= num <= 30:
            continue
        t["num"] = num
        out.append(t)
    return out


def _outline_pass(pages: List[PageInfo], per_page: List[tuple], kind: str) -> List[str]:
    """텍스트가 전혀 없는(외곽선) PDF 에서 문항 번호·끝 표시를 찾아 pages 에 채워 넣는다."""
    notes: List[str] = ["외곽선 PDF 감지 모드 (텍스트 없음 — 벡터 글리프로 번호 판독)"]
    tokens: List[dict] = []
    for p, (layout, drawings) in zip(pages, per_page):
        tokens += _outline_tokens(p.no, layout, drawings)
        p.hidden.extend(_outline_markers(layout, drawings))
    tokens.sort(key=lambda t: (t["page"], t["col"], t["y0"]))
    if not tokens:
        notes.append("문항 번호 후보를 찾지 못함 — 양식이 다르거나 스캔(이미지) PDF")
        return notes

    heights = sorted(t["h"] for t in tokens)
    med = heights[len(heights) // 2]
    if kind == "문제":
        prob_t = [t for t in tokens if 0.86 * med <= t["h"] <= 1.14 * med]
        sol_t: List[dict] = []
    elif kind == "해설":
        sol_t = [t for t in tokens if 0.86 * med <= t["h"] <= 1.14 * med]
        prob_t = []
    else:                                             # 합본: 번호 높이가 두 무리로 나뉜다
        if heights[-1] / heights[0] >= OUTLINE_SOL_SPLIT:
            thr = (heights[0] + heights[-1]) / 2
            prob_t = [t for t in tokens if t["h"] < thr]
            sol_t = [t for t in tokens if t["h"] >= thr]
        else:
            notes.append("합본인데 번호 크기가 한 무리뿐 — 전부 문제 번호로 간주")
            prob_t, sol_t = list(tokens), []

    for name, ts, attr in (("문제", prob_t, "prob_heads"), ("해설", sol_t, "sol_heads")):
        if not ts:
            continue
        decoded = _outline_decode(ts, name, notes)
        for t in decoded:
            getattr(pages[t["page"]], attr).append(
                Heading(t["num"], t["rect"], t["page"], t["col"]))
    for p in pages:
        p.prob_heads.sort(key=lambda h: (h.col, h.rect.y0))
        p.sol_heads.sort(key=lambda h: (h.col, h.rect.y0))
    return notes


# ------------------------------------- 패치 11: 이미지 글자 PDF 감지 -----
IMGTXT_TOKEN_W = (9.0, 26.0)     # 번호 이미지("N.") 폭 범위(pt) — 한 자리 ≈14, 두 자리 ≈19
IMGTXT_TOKEN_H = (9.0, 20.0)     # 번호 이미지 높이 범위(pt) — 문제 ≈12.6
IMGTXT_LEFT_TOL = 15.0           # 단 왼쪽 가장자리에서 허용 오프셋(pt)
IMGTXT_MIN_IMAGES = 12           # 쪽당 이미지 수가 이 이상이면 '글자가 이미지인 PDF' 로 본다
IMGTXT_HEAD_RATIO = 1.08         # 번호 이미지 높이 ÷ 본문 낱말 이미지 높이(중앙값) 하한 — 13pt/11pt ≈ 1.15


def _imgtxt_tokens(pno: int, layout: Layout, items: List[Item]) -> List[dict]:
    """단 왼쪽 가장자리에 붙은 작은 이미지(문항 번호 'N.' 이미지) 후보를 찾는다."""
    out = []
    for it in items:
        if it.kind != "image":
            continue
        r = it.rect
        if not (IMGTXT_TOKEN_W[0] < r.width < IMGTXT_TOKEN_W[1] and IMGTXT_TOKEN_H[0] < r.height < IMGTXT_TOKEN_H[1]):
            continue
        col = layout.col_of(r)
        x0, _ = layout.col_bounds(col)
        if r.x0 - x0 > IMGTXT_LEFT_TOL or r.x0 < x0 - 6:
            continue
        if not (layout.top < (r.y0 + r.y1) / 2 < layout.bottom):
            continue
        # 같은 줄 왼쪽에 다른 이미지가 있으면 본문 (번호는 줄의 첫 요소)
        cy = (r.y0 + r.y1) / 2
        if any(o.kind == "image" and o.rect.x1 <= r.x0 + 0.5 and o.rect.y0 < cy < o.rect.y1
               and o.rect.x0 > x0 - 6 for o in items):
            continue
        out.append({"page": pno, "col": col, "y0": r.y0, "rect": pymupdf.Rect(r), "h": r.height, "w": r.width})
    out.sort(key=lambda t: (t["col"], t["y0"]))
    return out


IMGTXT_NOTICE_SPAN = 0.90        # [패치 13] 안내 박스 가로선 길이 ÷ 단 폭 하한
IMGTXT_NOTICE_BOTTOM_TOL = 3.0   # [패치 13] 박스 아랫변과 본문 바닥(단 구분선 아래끝)의 허용 차(pt)
IMGTXT_NOTICE_MAX_H = 0.25       # [패치 13] 박스 높이 ÷ 본문 높이 상한


def _imgtxt_notice_boxes(p: PageInfo) -> List[pymupdf.Rect]:
    """[패치 13] 단 바닥에 붙은 「※ 확인 사항」 안내 박스를 선 모양으로 찾는다.

    이미지 글자 PDF 에서는 '확인 사항' 문구도 이미지라 EXCLUDE_TEXT 로 걸러지지 않는다.
    단 폭 전체(≥90%)에 걸친 윗변·아랫변 가로선 + 양 끝 세로선으로 된 사각형이고,
    아랫변이 본문 바닥에 붙어 있으며(±3pt), 높이가 본문의 25% 이하이고, 안에 문항 번호가 없으면
    안내 박스로 본다. (문항 안의 조건·보기 박스는 들여쓰기돼 단 폭 전체가 아니고 바닥에 붙지 않는다)
    """
    L = p.layout
    draws = [it.rect for it in p.items if it.kind == "draw"]
    heads = p.prob_heads + p.sol_heads
    out: List[pymupdf.Rect] = []
    for col in range(L.ncols):
        x0, x1 = L.col_bounds(col)
        cw = x1 - x0
        hl = [r for r in draws if r.height < 2.5 and r.width >= IMGTXT_NOTICE_SPAN * cw
              and x0 - 8 <= r.x0 and r.x1 <= x1 + 8]
        bottoms = [r for r in hl if abs(r.y1 - L.bottom) <= IMGTXT_NOTICE_BOTTOM_TOL]
        if not bottoms:
            continue
        bot = max(bottoms, key=lambda r: r.y1)
        for top in sorted((r for r in hl if r.y1 < bot.y0 - 10), key=lambda r: -r.y0):
            h = bot.y1 - top.y0
            if h > IMGTXT_NOTICE_MAX_H * (L.bottom - L.top):
                break
            vl = [r for r in draws if r.width < 2.5 and r.y0 <= top.y1 + 2 and r.y1 >= bot.y0 - 2]
            left_ok = any(abs(r.x0 - top.x0) <= 3 for r in vl)
            right_ok = any(abs(r.x1 - top.x1) <= 3 for r in vl)
            if not (left_ok and right_ok):
                continue
            box = pymupdf.Rect(min(top.x0, bot.x0) - 1, top.y0 - 1, max(top.x1, bot.x1) + 1, bot.y1 + 1)
            if any(box.contains(hd.rect) for hd in heads):
                continue
            out.append(box)
            break
    return out


def _imgtxt_drop_notices(pages: List[PageInfo], notes: List[str]):
    """[패치 13] 안내 박스와 그 안의 글자 이미지를 항목에서 뺀다 (문항 영역에 딸려 들어가지 않게)."""
    n = 0
    for p in pages:
        boxes = _imgtxt_notice_boxes(p)
        if not boxes:
            continue
        def inside(r: pymupdf.Rect) -> bool:
            c = pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
            return any(b.contains(c) for b in boxes)
        p.items = [it for it in p.items if not inside(it.rect)]
        n += len(boxes)
    if n:
        notes.append(f"단 바닥의 안내 박스(※ 확인 사항 등) {n}개를 문항 영역에서 제외함")


def _imgtxt_number(tokens: List[dict], label: str, notes: List[str]) -> List[dict]:
    """읽기 순서대로 1~22, 그 뒤 23~30 반복으로 번호를 매긴다 (수능 수학 구성).

    이미지 글자는 판독할 수 없으므로 순서로 정한다. 한 자리(1~9) 이미지는 두 자리보다 좁아야
    한다는 점으로 순서 가정이 맞는지 검증하고, 개수가 22+8k 가 아니면 경고를 남긴다.
    """
    n = len(tokens)
    if n == 0:
        return []
    for i, t in enumerate(tokens):
        t["num"] = i + 1 if i < 22 else 23 + (i - 22) % 8
    if n < 22 or (n - 22) % 8 != 0:
        notes.append(f"{label}: 번호 이미지 {n}개 — 22+8k 가 아니어서 번호가 어긋났을 수 있음 (누락·오탐 확인)")
    single = [t["w"] for t in tokens[:9]]
    double = [t["w"] for t in tokens[9:]]
    if single and double and not (max(single) < min(double) * 0.9):
        notes.append(f"{label}: 한 자리/두 자리 번호 이미지 폭이 구분되지 않음 — 순서 배정이 틀렸을 수 있음")
    return tokens


def _imgtxt_pass(pages: List[PageInfo], kind: str) -> List[str]:
    """글자가 전부 이미지로 들어간 PDF(강대 K 문제지 등)에서 번호 이미지를 문항 제목으로 삼는다."""
    notes: List[str] = ["이미지 글자 PDF 감지 모드 (본문·번호가 텍스트가 아닌 이미지 — 번호는 읽기 순서로 배정)"]
    tokens: List[dict] = []
    for p in pages:
        tokens += _imgtxt_tokens(p.no, p.layout, p.items)
    tokens.sort(key=lambda t: (t["page"], t["col"], t["y0"]))
    # 본문 낱말 이미지(≈11pt)와 번호 이미지(≈13pt)를 높이로 가른다: 전체 이미지 높이의 중앙값이 본문 크기
    body_h = sorted(it.rect.height for p in pages for it in p.items if it.kind == "image")
    if body_h:
        med = body_h[len(body_h) // 2]
        tokens = [t for t in tokens if t["h"] >= IMGTXT_HEAD_RATIO * med]
    if not tokens:
        notes.append("번호 이미지 후보를 찾지 못함 — 양식이 다르거나 스캔(통이미지) PDF")
        return notes
    heights = sorted(t["h"] for t in tokens)
    if kind == "문제":
        prob_t, sol_t = tokens, []
    elif kind == "해설":
        prob_t, sol_t = [], tokens
    else:
        if heights[-1] / heights[0] >= OUTLINE_SOL_SPLIT:
            thr = (heights[0] + heights[-1]) / 2
            prob_t = [t for t in tokens if t["h"] < thr]
            sol_t = [t for t in tokens if t["h"] >= thr]
        else:
            notes.append("합본인데 번호 이미지 크기가 한 무리뿐 — 전부 문제 번호로 간주")
            prob_t, sol_t = tokens, []
    for name, ts, attr in (("문제", prob_t, "prob_heads"), ("해설", sol_t, "sol_heads")):
        for t in _imgtxt_number(ts, name, notes):
            getattr(pages[t["page"]], attr).append(Heading(t["num"], t["rect"], t["page"], t["col"]))
    for p in pages:
        p.prob_heads.sort(key=lambda h: (h.col, h.rect.y0))
        p.sol_heads.sort(key=lambda h: (h.col, h.rect.y0))
    _imgtxt_drop_notices(pages, notes)          # [패치 13]
    notes.append("페이지 머릿말의 과목명을 읽을 수 없어 23번이 나올 때마다 "
                 f"{'→'.join(DEFAULT_ORDER)} 순서로 과목을 배정함")
    return notes


# ---------------------------------------------- 패치 15: 작은 조판 -----
SMALL_TYPE_HEAD_RATIO = 1.1   # 번호 크기 하한 = 본문 글자 크기 × 이 비 (본문 8.4pt → 9.24pt)


def _body_size(pages: List[PageInfo]) -> float:
    """문서 본문 글자 크기 — 글자 수로 가중한 최빈 크기."""
    cnt: Dict[float, int] = {}
    for p in pages:
        for it in p.items:
            if it.kind == "text":
                k = round(it.size, 1)
                cnt[k] = cnt.get(k, 0) + len(it.text)
    return max(cnt, key=cnt.get) if cnt else 0.0


def _small_type_pass(pages: List[PageInfo], kind: str) -> List[str]:
    """[패치 15] 파일 종류(파일명)가 정해졌는데 그 종류의 번호를 하나도 못 찾았을 때만 동작한다.

    패치 14로 종류는 파일명이 정하므로, 번호 크기는 '번호냐 본문이냐'만 가르면 된다.
    A4로 축소 조판된 양식(서킷더베스트)은 번호가 고정 기준(문제 12.3pt·해설 17pt)에 못 미친다
    (문제 9.9pt·해설 15.4pt, 본문 8.4pt).
      1) 해설 파일: 해설 크기 번호가 0개이고 문제 크기 번호가 있으면 그것을 해설 번호로 쓴다 (패치 10의 거울).
      2) 그래도 0개면 기준을 '본문 크기 × SMALL_TYPE_HEAD_RATIO'로 낮춰 `N.` 번호를 다시 찾는다.
    번호를 이미 찾은 파일은 건드리지 않는다 — 종전 양식의 결과는 바뀌지 않는다.
    """
    attr = "prob_heads" if kind == "문제" else "sol_heads"
    if any(getattr(p, attr) for p in pages):
        return []
    if kind == "해설" and any(p.prob_heads for p in pages):
        n = 0
        for p in pages:
            p.sol_heads, p.prob_heads = sorted(p.prob_heads, key=lambda h: (h.col, h.rect.y0)), []
            n += len(p.sol_heads)
        return [f"해설 파일: 해설 크기(≥{SOL_HEADING_SIZE}pt) 번호가 없어 {PROB_HEADING_SIZE}pt 이상 번호 {n}개를 해설 번호로 사용"]
    body = _body_size(pages)
    min_size = round(body * SMALL_TYPE_HEAD_RATIO, 2)
    if not body or min_size >= PROB_HEADING_SIZE:
        return []
    n = 0
    for p in pages:
        hs = find_headings(p.items, p.layout, p.no, min_size, strict=False)
        setattr(p, attr, hs)
        n += len(hs)
    return [f"작은 조판: 본문 {body}pt → 번호 기준 {min_size}pt로 낮춰 {kind} 번호 {n}개 찾음"] if n else []


def analyze(path: str, kind: str = "합본") -> Analysis:
    """PDF 전체를 한 번 훑어 페이지별 레이아웃·항목·문항 제목을 찾고, 문제/해설 구간을 나눈다.

    [패치 8] 텍스트가 전혀 없으면 외곽선 감지 모드로 전환한다. kind('문제'|'해설'|'합본')는
    외곽선 모드에서 번호 크기 무리를 나누는 데 쓰인다.
    [패치 10] kind='문제' 이면 해설 구간을 나누지 않는다 (전 페이지가 문제 구간).
    """
    doc = pymupdf.open(path)
    pages: List[PageInfo] = []
    per_page: List[tuple] = []
    # [패치 12] 레이아웃을 먼저 모두 구해 3단 구분선을 문서 단위로 맞춘다
    all_drawings = [page.get_drawings() for page in doc]
    layouts = [analyze_layout(page, dr) for page, dr in zip(doc, all_drawings)]
    _unify_multicol(layouts)
    for pno, page in enumerate(doc):
        drawings, layout = all_drawings[pno], layouts[pno]
        items, hidden = collect_items(page, layout, drawings)
        sol = find_headings(items, layout, pno, SOL_HEADING_SIZE, strict=True)
        if layout.ncols >= 3 and kind != "문제":
            # [패치 12] 3단 쪽: `N. [정답]` 꼴 해설 번호 (크기 무관)
            sol += [h for h in find_multicol_sol_heads(items, layout, pno)
                    if not any(s.rect == h.rect for s in sol)]
            sol.sort(key=lambda h: (h.col, h.rect.y0))
        prob = [h for h in find_headings(items, layout, pno, PROB_HEADING_SIZE, strict=False)
                if not any(s.rect == h.rect for s in sol)]
        text = page.get_text("text")
        table = bool(re.search(r"정답\s*(및\s*해설|표)?", text)) and len(re.findall(r"[①②③④⑤]", text)) >= 15
        pages.append(PageInfo(pno, layout, items, hidden, prob, sol, page_subject(text), table))
        per_page.append((layout, drawings))
    doc.close()

    # [패치 8] 텍스트로 문항 번호를 하나도 못 찾았고 본문 텍스트가 있는 페이지가 소수이면
    # (MEMO·안내 페이지만 텍스트로 남은 외곽선 PDF 가 흔함) 외곽선 감지 모드로 전환한다.
    text_pages = sum(1 for p in pages if any(it.kind == "text" for it in p.items))
    outline = (not any(p.prob_heads or p.sol_heads for p in pages)
               and text_pages <= max(1, len(pages) // 3))
    notes: List[str] = []
    if outline:
        notes = _outline_pass(pages, per_page, kind)
    elif not any(p.prob_heads or p.sol_heads for p in pages):
        # [패치 11] 텍스트는 있지만(수식 폰트 등) 번호를 못 찾았고, 쪽마다 이미지가 많으면
        # 글자가 이미지로 들어간 PDF (강대 K 문제지) — 번호 이미지를 문항 제목으로 쓴다.
        n_img = sum(1 for p in pages for it in p.items if it.kind == "image")
        if pages and n_img / len(pages) >= IMGTXT_MIN_IMAGES:
            notes = _imgtxt_pass(pages, kind)
    elif kind == "합본" and not any(p.prob_heads for p in pages):
        # [패치 12] 해설 번호는 텍스트로 잡혔지만 문제 번호가 없는 합본 — 해설 번호가 처음 나오는 쪽
        # 앞의 쪽들이 이미지 글자 문제지면 그 쪽들에만 이미지 글자 감지를 돌린다.
        first_sol = min((p.no for p in pages if p.sol_heads), default=len(pages))
        front = [p for p in pages if p.no < first_sol]
        n_img = sum(1 for p in front for it in p.items if it.kind == "image")
        if front and n_img / len(front) >= IMGTXT_MIN_IMAGES:
            notes = _imgtxt_pass(front, "문제")

    if not outline and kind in ("문제", "해설"):
        notes += _small_type_pass(pages, kind)            # [패치 15]

    n_sol_raw = sum(len(p.sol_heads) for p in pages)      # 진단용 (병합 전 해설 크기 번호 수)
    if kind == "문제":
        # [패치 10] 문제 파일에는 해설이 없다. 해설 크기(≥17pt)로 잡힌 번호도 문제 번호로 쓰고,
        # 해설 구간을 나누지 않는다 — 번호가 크거나 마침표 없는 문제지 양식에서 문제 페이지가
        # 통째로 해설 구간으로 넘어가 0개가 되는 일을 막는다.
        for p in pages:
            for s in p.sol_heads:
                if not any(h.rect == s.rect for h in p.prob_heads):
                    p.prob_heads.append(s)
            p.sol_heads = []
            p.prob_heads.sort(key=lambda h: (h.col, h.rect.y0))
        if n_sol_raw and not outline:
            notes.append(f"문제 파일: 해설 크기(≥{SOL_HEADING_SIZE}pt) 번호 {n_sol_raw}개를 문제 번호로 사용함")
        sol_start = len(pages)
    else:
        sol_pages = [p.no for p in pages if p.sol_heads]
        sol_start = sol_pages[0] if sol_pages else len(pages)
        # 정답표 페이지가 해설 첫 제목보다 앞에 있으면 거기부터 해설 구간
        for p in pages:
            if p.has_answer_table and not p.prob_heads and p.no < sol_start:
                sol_start = p.no
                break
    problem_pages = [p.no for p in pages if p.no < sol_start and p.prob_heads]
    solution_pages = [p.no for p in pages if p.no >= sol_start]

    # [패치 10] 문제/합본인데 문제 문항이 0개면 원인을 가늠할 진단문을 남긴다
    if kind in ("문제", "합본") and not problem_pages:
        n_prob = sum(len(p.prob_heads) for p in pages)
        n_sol = n_sol_raw
        n_big = sum(1 for p in pages for it in p.items
                    if it.kind == "text" and it.size >= PROB_HEADING_SIZE and re.match(r"^\d{1,2}", it.text))
        notes.append(
            f"문제 문항 0개 진단 — 전체 {len(pages)}쪽 중 텍스트 있는 쪽 {text_pages}, "
            f"문제 번호(≥{PROB_HEADING_SIZE}pt 'N.') {n_prob}개, 해설 크기(≥{SOL_HEADING_SIZE}pt) 번호 {n_sol}개, "
            f"숫자로 시작하는 큰 글자 줄 {n_big}개, 해설 구간 시작 쪽 {sol_start + 1 if sol_start < len(pages) else '없음'}"
            + (" — 번호가 전부 해설 크기로 잡힘: 문제지 번호가 크거나 마침표가 없는 양식일 수 있음" if n_sol and not n_prob else "")
            + (" — 번호가 있는데 해설 구간 뒤로 밀림: 파일명 종류 표기(_문제/_문)를 확인" if n_prob and kind == "합본" else "")
            + (" — 큰 글자 숫자 줄은 있는데 'N.' 꼴이 아님: 마침표 없는 문제 번호 양식 의심" if n_big and not n_prob and not n_sol else ""))

    # [패치 9] 해설에 23번 이상이 있는데 과목 텍스트(확률과 통계/미적분/기하)를 한 쪽도 못 읽었으면
    # 23번이 다시 나올 때마다 확통→미적→기하 순으로 배정된다는 것을 로그로 알린다.
    sel = [h.num for pno in solution_pages for h in pages[pno].sol_heads if h.num >= 23]
    if sel and not any(pages[pno].subject_hint for pno in solution_pages):
        notes.append("해설에서 과목 라벨을 텍스트로 읽지 못함 — 23번이 나올 때마다 "
                     f"{'→'.join(DEFAULT_ORDER)} 순서로 과목을 배정함 (빠른 정답표 순서와 같은지 확인)")
    return Analysis(path, pages, problem_pages, solution_pages, outline, notes)


# ------------------------------------------------------- 영역 계산 -----
def union(rects: List[pymupdf.Rect]) -> Optional[pymupdf.Rect]:
    if not rects:
        return None
    r = pymupdf.Rect(rects[0])
    for x in rects[1:]:
        r |= x
    return r


def region_items(items: List[Item], layout: Layout, col: int, y0: float, y1: float) -> List[Item]:
    x0, x1 = layout.col_bounds(col)
    # 영역 안(문항 제목 아래)에 안내 문구('확인 사항' 등)가 있으면 그 문구의 윗선에서 영역을 자른다.
    cut = y1
    for it in items:
        cx = (it.rect.x0 + it.rect.x1) / 2
        if it.kind == "text" and EXCLUDE_TEXT.search(it.text) and x0 - 6 <= cx <= x1 + 6 \
                and y0 + 15 <= it.rect.y0 < y1:
            cut = min(cut, it.rect.y0)
    out = []
    for it in items:
        r = it.rect
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        if not (x0 - 6 <= cx <= x1 + 6) or not (y0 <= cy < y1):
            continue
        if it.kind == "text" and EXCLUDE_TEXT.search(it.text):
            continue
        if cut < y1:
            if it.kind == "draw" and r.y1 > cut - 20:
                continue
            if it.kind != "draw" and cy > cut:
                continue
        out.append(it)
    return out


def make_clip(bbox: pymupdf.Rect, layout: Layout, col: int, pad: float, full_width: bool) -> pymupdf.Rect:
    """본문 사각형에 여백을 두르되, 가운데 구분선과 페이지 밖으로는 나가지 않게 한다."""
    x0, x1 = layout.col_bounds(col)
    if full_width:
        cx0, cx1 = x0 - pad, x1 + pad
    else:
        cx0, cx1 = bbox.x0 - pad, bbox.x1 + pad
    # [패치 12] N단: 왼쪽·오른쪽 구분선 밖으로 나가지 않게
    if col > 0:
        cx0 = max(cx0, layout.dividers[col - 1] + 1.5)
    if col < len(layout.dividers):
        cx1 = min(cx1, layout.dividers[col] - 1.5)
    cx0, cx1 = max(cx0, 0), min(cx1, layout.width)
    cy0, cy1 = max(bbox.y0 - pad, 0), min(bbox.y1 + pad, layout.height)
    return pymupdf.Rect(cx0, cy0, cx1, cy1)


class SubjectTracker:
    """문항 번호 흐름과 페이지 머릿말로 과목을 결정한다."""

    def __init__(self, order: List[str]):
        self.order, self.idx, self.prev = order, -1, 0
        self.page_hint: Optional[str] = None

    def set_page_hint(self, subj: Optional[str]):
        if subj:
            self.page_hint = subj

    def subject_for(self, num: int) -> str:
        if num <= 22:
            self.prev = num
            return "공통"
        if num < self.prev or self.prev <= 22:
            self.idx += 1
        self.prev = num
        if self.page_hint:
            return self.page_hint
        if 0 <= self.idx < len(self.order):
            return self.order[self.idx]
        return self.order[-1]


# ------------------------------------------------------------- 계획 -----
def plan_problems(an: Analysis, exam: str, pad: float, order=DEFAULT_ORDER) -> List[Job]:
    tracker = SubjectTracker(list(order))
    jobs: List[Job] = []
    for pno in an.problem_pages:
        p = an.pages[pno]
        tracker.set_page_hint(p.subject_hint)
        for col in range(p.layout.ncols):
            heads = [h for h in p.prob_heads if h.col == col]
            for i, h in enumerate(heads):
                y0 = h.rect.y0 - 2
                y1 = heads[i + 1].rect.y0 - 2 if i + 1 < len(heads) else p.layout.bottom
                for hd in p.hidden:      # 숨은(흰색) 끝 표시 'N.'  [패치 8: 외곽선 표시는 위치로 판정]
                    if p.layout.col_of(hd.rect) == col and y0 < hd.rect.y0 < y1 \
                            and (re.fullmatch(rf"{h.num}\.", hd.text) if hd.text else True):
                        y1 = min(y1, hd.rect.y0)
                bbox = union([it.rect for it in region_items(p.items, p.layout, col, y0, y1)])
                if bbox is None:
                    continue
                subj = tracker.subject_for(h.num)
                jobs.append(Job("문제", subj, h.num, exam,
                                [Segment(pno, make_clip(bbox, p.layout, col, pad, False), p.layout.top + 1.5)]))
    return jobs


def plan_solutions(an: Analysis, exam: str, pad: float, split: bool, order=DEFAULT_ORDER) -> List[Job]:
    tracker = SubjectTracker(list(order))
    jobs: List[Job] = []
    current: Optional[Job] = None
    # [패치 12] 3단 해설: 과목은 읽기 순서상 가장 최근의 과목 라벨로 정한다
    label_subj: Optional[str] = None
    for pno in an.solution_pages:
        p = an.pages[pno]
        tracker.set_page_hint(p.subject_hint)
        multicol = p.layout.ncols >= 3
        for col in range(p.layout.ncols):
            heads = [h for h in p.sol_heads if h.col == col]
            bounds = [p.layout.top] + [h.rect.y0 - 3 for h in heads] + [p.layout.bottom + 3]
            for i in range(len(bounds) - 1):
                its = region_items(p.items, p.layout, col, bounds[i], bounds[i + 1])
                labels = []
                if multicol:
                    # [패치 12] 라벨이 조각 중간에 있으면 그 윗선에서 끊는다 (라벨·정답표는 버림)
                    labels = sorted(multicol_labels(its), key=lambda lb: lb[0].rect.y0)
                    if labels:
                        cut = labels[0][0].rect.y0 - 2
                        its = [it for it in its
                               if ((it.rect.y0 + it.rect.y1) / 2 < cut) and not (it.kind == "draw" and it.rect.y1 > cut)]
                elif i == 0 and any(it.kind == "text" and SECTION_LABEL.match(it.text) for it in its):
                    its = []              # 과목 구분 라벨이 있는 선두 조각은 버림
                if i == 0 and its and heads and heads[0].num == 23 \
                        and not any(it.kind == "text" for it in its):
                    # [패치 8] 외곽선 모드: 선택과목 시작 단의 선두 조각이 과목 라벨(알약)뿐이면 버림
                    # [패치 9] 텍스트 PDF 로 일반화: 라벨 글자가 텍스트로 안 뽑히고 선·그림만 남는
                    #          양식(강대)에서도, 23번 직전의 얇은 텍스트 없는 조각은 과목 라벨로 본다
                    b = union([it.rect for it in its])
                    if b is not None and b.height < LABEL_CHUNK_MAX_H:
                        its = []
                if i > 0:
                    h = heads[i - 1]
                    subj = tracker.subject_for(h.num)
                    if multicol and label_subj and ((label_subj == "공통") == (h.num <= 22)):
                        subj = label_subj     # [패치 12] 라벨 과목 우선 (번호 범위와 맞을 때만)
                    current = Job("해설", subj, h.num, exam, [], split)
                    jobs.append(current)
                for _lb, s in labels:     # [패치 12] 이 조각 뒤에 오는 문항부터 라벨 과목 적용
                    if s:
                        label_subj = s
                if current is None:       # 첫 문항 이전(정답표 등)
                    continue
                bbox = union([it.rect for it in its])
                if bbox is None:
                    continue
                current.segments.append(Segment(pno, make_clip(bbox, p.layout, col, pad, True), p.layout.top + 1.5))
    return [j for j in jobs if j.segments]


# -------------------------------------------------------------- 렌더 -----
def render(page: pymupdf.Page, clip: pymupdf.Rect, dpi: int, body_top: float = 0.0) -> Image.Image:
    pix = page.get_pixmap(clip=clip, dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False)
    im = Image.open(io.BytesIO(pix.tobytes("png")))
    if body_top > clip.y0 + 0.5:                       # 머릿말 선이 들어왔으면 그 위를 흰색으로
        cut = int(round((body_top - clip.y0) * dpi / 72)) + 1
        im.paste(255, (0, 0, im.width, min(cut, im.height)))
    return im


def stitch(images: List[Image.Image], dpi: int, gap_mm: float = STITCH_GAP_MM) -> Image.Image:
    """(구버전) 조각을 세로로 이어붙인다. 패치 7 이후 기본 흐름에서는 쓰지 않는다."""
    gap = int(dpi * gap_mm / 25.4)
    w = max(i.width for i in images)
    h = sum(i.height for i in images) + gap * (len(images) - 1)
    out = Image.new("L", (w, h), 255)
    y = 0
    for i in images:
        out.paste(i, (0, y))
        y += i.height + gap
    return out


def render_job(doc: pymupdf.Document, job: Job, dpi: int, outdir: str) -> List[str]:
    """PNG 출력.  [패치 7] 조각이 여럿이면 <base>_c1.png, _c2.png … 로 조각별 저장한다.

    (Mathpix OCR 이 세로로 이어붙인 초장신 이미지에서 인식 붕괴를 일으키므로 stitch 하지 않는다.
     조각 텍스트의 병합은 GAS 'Mathpix 범위 자동변환.gs' 패치 7 이 담당한다.)
    """
    imgs = [render(doc[s.page], s.clip, dpi, s.body_top) for s in job.segments]
    paths = []
    if len(imgs) == 1:
        path = os.path.join(outdir, job.base + ".png")
        imgs[0].save(path, dpi=(dpi, dpi), optimize=True)
        paths.append(path)
    else:
        for k, im in enumerate(imgs, 1):
            path = os.path.join(outdir, f"{job.base}_c{k}.png")
            im.save(path, dpi=(dpi, dpi), optimize=True)
            paths.append(path)
    return paths


# ---- 패치 2 → 패치 7: 벡터 PDF 출력 (조각당 1쪽 다중 페이지) ---------------
def _segments_to_pdf(src: pymupdf.Document, segments: List[Segment], path: str,
                     gap_mm: float = STITCH_GAP_MM):
    """조각들을 조각당 1쪽인 다중 페이지 벡터 PDF 로 저장.  [패치 7]

    (구버전은 조각을 세로로 이어붙인 1쪽짜리 초장신 페이지를 만들었는데, Mathpix v3/pdf 가
     이런 페이지에서 인식 붕괴를 일으킨다. 쪽으로 나누면 v3/pdf 가 쪽 단위로 인식한 뒤
     순서대로 이어 붙여 주므로 결과 mmd 는 이전과 같은 한 덩어리가 된다.)
    원본 페이지의 clip 영역을 그대로 옮기므로 글자·수식·도형이 벡터로 유지되고,
    머릿말 밑줄(body_top) 위쪽은 흰색 사각형으로 덮어 PNG 와 같은 모양으로 만든다.
    """
    out = pymupdf.open()
    for s in segments:
        page = out.new_page(width=s.clip.width, height=s.clip.height)
        page.show_pdf_page(pymupdf.Rect(0, 0, s.clip.width, s.clip.height), src, s.page, clip=s.clip)
        if s.body_top > s.clip.y0 + 0.5:
            cut = (s.body_top - s.clip.y0) + 0.5      # PNG 의 +1px 에 해당하는 여유
            shape = page.new_shape()
            shape.draw_rect(pymupdf.Rect(0, 0, s.clip.width, cut))
            shape.finish(color=None, fill=(1, 1, 1))
            shape.commit(overlay=True)
    out.save(path, garbage=4, deflate=True)
    out.close()


def render_job_pdf(doc: pymupdf.Document, job: Job, outdir: str) -> List[str]:
    """PDF 출력. 항상 <base>.pdf 하나 (조각이 여럿이면 다중 페이지).  [패치 7]"""
    path = os.path.join(outdir, job.base + ".pdf")
    _segments_to_pdf(doc, job.segments, path)
    return [path]


# ------------------------------------------------------- 파일 단위 처리 -----
def clean_exam_name(name: str) -> str:
    """시험지명에서 _문제/_해설(_문/_해) 표시를 모두 떼어낸다 (출력 파일명에는 종류가 따로 붙으므로)."""
    name = unicodedata.normalize("NFC", name.strip())
    while True:
        m = KIND_RE.search(name)
        if not m:
            break
        name = (name[:m.start()] + name[m.end():])
    return re.sub(r"[_\-\s]{2,}", "_", name).strip("_- ")


def kind_of_match(m: "re.Match") -> str:
    """KIND_RE 일치 결과 → '문제' | '해설'.  [패치 10] 축약형(group 2)도 함께 판정."""
    g = m.group(1) or m.group(2) or ""
    return "해설" if "해" in g else "문제"


def classify_filename(path: str) -> Tuple[str, str]:
    """파일명 → (시험지명, 종류). 종류는 '문제' | '해설' | '합본'.

    [패치 10] `_문제`/`_해설` 외에 `_문`/`_해` 축약 표기도 인식한다.
      K25(260915)_문.pdf → ('K25(260915)', '문제'),  K25(260915)_해.pdf → ('K25(260915)', '해설')
    [패치 14] 표기가 없거나 문제·해설 표기가 둘 다 있으면 '합본' — 합본은 처리하지 않는다 (COMBINED_MSG).
    """
    # macOS 파일명은 한글이 자모 분리형(NFD)으로 저장되므로 완성형(NFC)으로 맞춘 뒤 판별한다.
    stem = unicodedata.normalize("NFC", os.path.splitext(os.path.basename(path))[0])
    kinds = {kind_of_match(m) for m in KIND_RE.finditer(stem)}
    kind = kinds.pop() if len(kinds) == 1 else "합본"
    return clean_exam_name(stem) or stem, kind


# [패치 14] 합본 거부 안내 — CLI·GUI·맥미니 러너가 같은 문구를 쓴다
COMBINED_MSG = ("문제지와 해설지가 한 파일(합본)이거나 파일명에 '문제'/'해설' 표기가 없습니다. "
                "문제지와 해설지를 별도의 PDF로 나누고, 파일명에 각각 '문제', '해설'을 넣어 주세요 "
                "(예: 시험지명_문제.pdf, 시험지명_해설.pdf).")


def expected_numbers(jobs: List[Job]) -> Dict[str, List[int]]:
    """과목별로 빠진 번호 목록."""
    got: Dict[str, set] = {}
    for j in jobs:
        got.setdefault(j.subject, set()).add(j.num)
    missing = {}
    for subj, nums in got.items():
        rng = range(1, 23) if subj == "공통" else range(23, 31)
        miss = [n for n in rng if n not in nums]
        if miss:
            missing[subj] = miss
    return missing


def build_jobs(path: str, exam: str, kind: str, pad_pt: float, split: bool) -> Tuple[Analysis, List[Job]]:
    if kind not in ("문제", "해설"):          # [패치 14] 합본은 자르지 않는다
        raise ValueError(f"{os.path.basename(path)}: {COMBINED_MSG}")
    an = analyze(path, kind)
    jobs: List[Job] = []
    if kind in ("문제", "합본"):
        jobs += plan_problems(an, exam, pad_pt)
    if kind in ("해설", "합본"):
        jobs += plan_solutions(an, exam, pad_pt, split)
    return an, jobs


def output_paths(job: Job, outdir: str, png: bool = True, pdf: bool = False) -> List[str]:
    """이 job 이 만들 파일 경로 목록 (덮어쓰기 검사용).  [패치 7 명명 규칙]"""
    paths: List[str] = []
    if png:
        if len(job.segments) > 1:
            paths += [os.path.join(outdir, f"{job.base}_c{k}.png") for k in range(1, len(job.segments) + 1)]
        else:
            paths.append(os.path.join(outdir, job.base + ".png"))
    if pdf:
        paths.append(os.path.join(outdir, job.base + ".pdf"))
    return paths


def run_jobs(path: str, jobs: List[Job], dpi: int, outdir: str,
             progress: Optional[Callable[[int, int, str], None]] = None,
             should_stop: Optional[Callable[[], bool]] = None,
             png: bool = True, pdf: bool = False) -> List[str]:
    """jobs 를 outdir 에 저장. png/pdf 로 출력 형식을 고른다 (둘 다 True 면 둘 다 저장)."""
    os.makedirs(outdir, exist_ok=True)
    doc = pymupdf.open(path)
    written: List[str] = []
    try:
        for i, job in enumerate(jobs):
            if should_stop and should_stop():
                break
            if progress:
                progress(i, len(jobs), job.base)
            if png:
                written += render_job(doc, job, dpi, outdir)
            if pdf:
                written += render_job_pdf(doc, job, outdir)
        if progress:
            progress(len(jobs), len(jobs), "")
    finally:
        doc.close()
    return written


def write_debug_pdf(path: str, jobs: List[Job], out_path: str):
    doc = pymupdf.open(path)
    for j in jobs:
        for s in j.segments:
            doc[s.page].draw_rect(s.clip, color=(1, 0, 0) if j.kind == "문제" else (0, 0, 1), width=1)
    doc.save(out_path)
    doc.close()


# ------------------------------------------------------- 결과 레코드 -----
def job_key(job: Job) -> str:
    return f"{SUBJECT_CODES[job.subject]}{job.num:02d}"


def _side_record(jobs: List[Job], kind: str, plan: bool) -> Optional[dict]:
    """file 레코드의 problem / solution 부분. plan=True 면 조각 영역(쪽, 좌표 소수 둘째 자리)까지."""
    js = [j for j in jobs if j.kind == kind]
    if not js:
        return None
    rec = {"n": len(js), "template": None, "keys": [job_key(j) for j in js]}
    if plan:
        rec["segments"] = {job_key(j): [[s.page, *[round(v, 2) for v in (s.clip.x0, s.clip.y0, s.clip.x1, s.clip.y1)]]
                                        for s in j.segments] for j in js}
    return rec


def file_record(path: str, exam: str, input_kind: str, kind: Optional[str], status: str, reason: Optional[str],
                jobs: Optional[List[Job]] = None, notes: Optional[List[str]] = None,
                plan: bool = False, split_page: Optional[int] = None) -> dict:
    """--json 의 file 레코드 (schema 1). 거부·실패 파일도 한 줄 남긴다."""
    return {"schema": JSON_SCHEMA, "type": "file", "engine": engine_version(), "pymupdf": pymupdf.VersionBind,
            "file": os.path.basename(path), "exam": exam, "input_kind": input_kind, "kind": kind,
            "split_page": split_page, "status": status, "reason": reason,
            "problem": _side_record(jobs or [], "문제", plan), "solution": _side_record(jobs or [], "해설", plan),
            "notes": list(notes or [])}


def set_record(exam: str, files: List[dict]) -> dict:
    """같은 시험지의 file 레코드들 → set 레코드. exclude_reasons 가 비어 있지 않으면 러너는 그 세트를 뺀다."""
    reasons: List[str] = []
    notes: List[str] = []
    prob = [k for f in files if f["problem"] for k in f["problem"]["keys"]]
    sol = [k for f in files if f["solution"] for k in f["solution"]["keys"]]
    for f in files:
        if f["status"] == "rejected":
            reasons.append("rejected")
        elif f["status"] == "failed":
            reasons.append("zero_items" if f["reason"] == "zero_items" else "failed_file")
    pair_match: Optional[bool] = None
    diff = {"only_problem": [], "only_solution": []}
    if prob and sol:
        ps, ss = set(prob), set(sol)
        pair_match = ps == ss
        diff = {"only_problem": sorted(ps - ss), "only_solution": sorted(ss - ps)}
        if not pair_match:
            reasons.append("pair_mismatch")
    for side, keys in (("problem", prob), ("solution", sol)):
        dups = sorted({k for k in keys if keys.count(k) > 1})
        if dups:
            reasons.append("duplicate_key")
            notes.append(f"duplicate_key({side}): {dups}")
    reasons = list(dict.fromkeys(reasons))
    order = ["rejected", "failed", "partial", "ok"]
    status = min((f["status"] for f in files), key=order.index) if files else "failed"
    if status == "ok" and reasons:
        status = "partial"
    return {"schema": JSON_SCHEMA, "type": "set", "engine": engine_version(), "exam": exam,
            "files": [f["file"] for f in files], "status": status, "pair_match": pair_match, "diff": diff,
            "exclude_reasons": reasons, "notes": notes}


def exit_code(records: List[dict]) -> int:
    """0 = failed·rejected 없음 / 1 = failed 있음 / 3 = failed 없고 rejected 있음."""
    st = {r["status"] for r in records if r["type"] == "file"}
    return 1 if "failed" in st else (3 if "rejected" in st else 0)


# --------------------------------------------------------------- CLI -----
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--out", default="crops", help="출력 폴더 (기본: ./crops)")
    ap.add_argument("--exam", default=None, help="시험지명 (기본: 파일명에서 _문제/_해설(_문/_해) 을 뗀 이름)")
    ap.add_argument("--kind", choices=["auto", "문제", "해설"], default="auto")   # [패치 14] 합본 없음
    ap.add_argument("--margin", type=float, default=3.0, help="본문 주변 여백(mm)")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--split", action="store_true", help="(패치 7 이후 기본 동작과 동일 — 호환용)")
    ap.add_argument("--pdf", action="store_true", help="PNG 와 함께 문항별 벡터 PDF 도 저장")
    ap.add_argument("--pdf-only", action="store_true", help="PNG 없이 문항별 벡터 PDF 만 저장")
    ap.add_argument("--debug", action="store_true", help="영역 표시 PDF를 함께 저장")
    ap.add_argument("--json", metavar="경로", default=None,
                    help="[패치 16] 파일·세트 결과를 JSON Lines 로 기록 (--plan-only 에서 생략하면 표준 출력)")
    ap.add_argument("--plan-only", action="store_true",
                    help="[패치 16] 자르지 않고 계획(문항 키·조각 영역)만 레코드로 낸다")
    ap.add_argument("--version", action="store_true", help="엔진 버전만 출력")
    args = ap.parse_args(argv)
    if args.version:
        print(engine_version())
        return
    want_pdf = args.pdf or args.pdf_only
    want_png = not args.pdf_only
    quiet = args.plan_only and not args.json          # 계획을 표준 출력으로 낼 때는 사람용 줄을 숨긴다
    say = (lambda *a, **k: None) if quiet else print
    say(f"CroP 엔진 {engine_version()} (pymupdf {pymupdf.VersionBind})")

    total = 0
    records: List[dict] = []
    by_exam: Dict[str, List[dict]] = {}
    for path in args.pdfs:
        exam, input_kind = classify_filename(path)
        exam = args.exam or exam
        kind = input_kind if args.kind == "auto" else args.kind
        if kind not in ("문제", "해설"):
            # [패치 14→16] 합본은 자르지 않는다. 멈추지 않고 rejected 레코드로 남긴 뒤 다음 파일로 간다.
            say(f"[{os.path.basename(path)}] 거부: {COMBINED_MSG}")
            rec = file_record(path, exam, input_kind, None, "rejected", "combined_not_supported",
                              notes=[COMBINED_MSG])
            records.append(rec); by_exam.setdefault(exam, []).append(rec)
            continue
        an, jobs = build_jobs(path, exam, kind, args.margin * MM, args.split)
        say(f"[{os.path.basename(path)}] 시험지명={exam} 종류={kind} "
            f"문제페이지={len(an.problem_pages)} 해설페이지={len(an.solution_pages)} 문항={len(jobs)}")
        for note in an.notes:
            say(f"  * {note}")
        for subj, miss in expected_numbers(jobs).items():
            say(f"  ! {subj} 누락 번호: {miss}")
        status, reason = ("failed", "zero_items") if not jobs else ("ok", None)
        rec = file_record(path, exam, input_kind, kind, status, reason, jobs, an.notes, plan=args.plan_only)
        records.append(rec); by_exam.setdefault(exam, []).append(rec)
        if args.plan_only:
            continue

        def prog(i, n, name):
            if name:
                say(f"  {i + 1:>3}/{n}  {name}")

        written = run_jobs(path, jobs, args.dpi, args.out, prog, png=want_png, pdf=want_pdf)
        total += len(written)
        if args.debug:
            dp = os.path.join(args.out, f"{exam}_{kind}_debug.pdf")
            write_debug_pdf(path, jobs, dp)
            say(f"  [debug] {dp}")
    for exam, files in by_exam.items():
        records.append(set_record(exam, files))
    if args.json or args.plan_only:
        lines = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
        if args.json:
            os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
            with open(args.json, "w", encoding="utf-8") as f:
                f.write(lines)
        else:
            sys.stdout.write(lines)
    if not args.plan_only:
        fmt = "PNG+PDF" if (want_png and want_pdf) else ("PDF" if want_pdf else "PNG")
        say(f"완료: {total}개 {fmt} → {args.out}")
    code = exit_code(records)
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
