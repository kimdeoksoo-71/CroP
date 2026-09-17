#!/usr/bin/env python3
"""
exam_crop.py — 수능/모의고사 수학 시험지(텍스트 PDF)에서 문제·해설을 문항별 PNG(600dpi)로 잘라내는 코어 라이브러리 + CLI

CLI
  python exam_crop.py 시험지_문제.pdf 시험지_해설.pdf ...   [--out crops] [--exam 이름] [--margin 3] [--dpi 600] [--split] [--debug]
                                                          [--pdf | --pdf-only]

  파일명에 `_문제` 가 있으면 문제지, `_해설` 이 있으면 해설지, 둘 다 없으면 합본(문제 뒤에 해설)으로 보고 자동 감지한다.
  --exam 을 주지 않으면 파일명에서 확장자와 _문제/_해설 을 뗀 이름을 시험지명으로 쓴다.

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

GUI 앱은 exam_crop_app.py 참고.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import pymupdf  # PyMuPDF
from PIL import Image

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
PROB_HEADING_SIZE = 12.3     # 문제 번호 글자 크기 하한 (본문 11pt 내외, 번호 13pt 내외)
SOL_HEADING_SIZE = 17.0      # 해설 번호 글자 크기 하한 (20pt 내외)
MM = 72 / 25.4               # 1mm → pt
STITCH_GAP_MM = 3.0          # (구버전 stitch 용, 현재 미사용)

KIND_RE = re.compile(r"[_\-\s]?(문제지|문제|해설지|해설|정답및해설|정답\s*및\s*해설)", re.I)

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

    def col_bounds(self, col: int) -> Tuple[float, float]:
        return (self.left, self.divider) if col == 0 else (self.divider, self.right)

    def col_of(self, rect: pymupdf.Rect) -> int:
        return 0 if (rect.x0 + rect.x1) / 2 < self.divider else 1


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


def analyze(path: str, kind: str = "합본") -> Analysis:
    """PDF 전체를 한 번 훑어 페이지별 레이아웃·항목·문항 제목을 찾고, 문제/해설 구간을 나눈다.

    [패치 8] 텍스트가 전혀 없으면 외곽선 감지 모드로 전환한다. kind('문제'|'해설'|'합본')는
    외곽선 모드에서 번호 크기 무리를 나누는 데만 쓰인다 (텍스트 PDF 에서는 영향 없음).
    """
    doc = pymupdf.open(path)
    pages: List[PageInfo] = []
    per_page: List[tuple] = []
    for pno, page in enumerate(doc):
        drawings = page.get_drawings()
        layout = analyze_layout(page, drawings)
        items, hidden = collect_items(page, layout, drawings)
        sol = find_headings(items, layout, pno, SOL_HEADING_SIZE, strict=True)
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

    sol_pages = [p.no for p in pages if p.sol_heads]
    sol_start = sol_pages[0] if sol_pages else len(pages)
    # 정답표 페이지가 해설 첫 제목보다 앞에 있으면 거기부터 해설 구간
    for p in pages:
        if p.has_answer_table and not p.prob_heads and p.no < sol_start:
            sol_start = p.no
            break
    problem_pages = [p.no for p in pages if p.no < sol_start and p.prob_heads]
    solution_pages = [p.no for p in pages if p.no >= sol_start]

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
    if col == 0:
        cx1 = min(cx1, layout.divider - 1.5)
    else:
        cx0 = max(cx0, layout.divider + 1.5)
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
        for col in (0, 1):
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
    for pno in an.solution_pages:
        p = an.pages[pno]
        tracker.set_page_hint(p.subject_hint)
        for col in (0, 1):
            heads = [h for h in p.sol_heads if h.col == col]
            bounds = [p.layout.top] + [h.rect.y0 - 3 for h in heads] + [p.layout.bottom + 3]
            for i in range(len(bounds) - 1):
                its = region_items(p.items, p.layout, col, bounds[i], bounds[i + 1])
                if i == 0 and any(it.kind == "text" and SECTION_LABEL.match(it.text) for it in its):
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
                    current = Job("해설", tracker.subject_for(h.num), h.num, exam, [], split)
                    jobs.append(current)
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
    """시험지명에서 _문제/_해설 표시를 모두 떼어낸다 (출력 파일명에는 종류가 따로 붙으므로)."""
    name = unicodedata.normalize("NFC", name.strip())
    while True:
        m = KIND_RE.search(name)
        if not m:
            break
        name = (name[:m.start()] + name[m.end():])
    return re.sub(r"[_\-\s]{2,}", "_", name).strip("_- ")


def classify_filename(path: str) -> Tuple[str, str]:
    """파일명 → (시험지명, 종류). 종류는 '문제' | '해설' | '합본'."""
    # macOS 파일명은 한글이 자모 분리형(NFD)으로 저장되므로 완성형(NFC)으로 맞춘 뒤 판별한다.
    stem = unicodedata.normalize("NFC", os.path.splitext(os.path.basename(path))[0])
    kind = "합본"
    m = KIND_RE.search(stem)
    if m:
        kind = "해설" if "해설" in m.group(1) else "문제"
    return clean_exam_name(stem) or stem, kind


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


# --------------------------------------------------------------- CLI -----
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--out", default="crops", help="출력 폴더 (기본: ./crops)")
    ap.add_argument("--exam", default=None, help="시험지명 (기본: 파일명에서 _문제/_해설 을 뗀 이름)")
    ap.add_argument("--kind", choices=["auto", "문제", "해설", "합본"], default="auto")
    ap.add_argument("--margin", type=float, default=3.0, help="본문 주변 여백(mm)")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--split", action="store_true", help="(패치 7 이후 기본 동작과 동일 — 호환용)")
    ap.add_argument("--pdf", action="store_true", help="PNG 와 함께 문항별 벡터 PDF 도 저장")
    ap.add_argument("--pdf-only", action="store_true", help="PNG 없이 문항별 벡터 PDF 만 저장")
    ap.add_argument("--debug", action="store_true", help="영역 표시 PDF를 함께 저장")
    args = ap.parse_args(argv)
    want_pdf = args.pdf or args.pdf_only
    want_png = not args.pdf_only

    total = 0
    for path in args.pdfs:
        exam, kind = classify_filename(path)
        exam = args.exam or exam
        if args.kind != "auto":
            kind = args.kind
        an, jobs = build_jobs(path, exam, kind, args.margin * MM, args.split)
        print(f"[{os.path.basename(path)}] 시험지명={exam} 종류={kind} "
              f"문제페이지={len(an.problem_pages)} 해설페이지={len(an.solution_pages)} 문항={len(jobs)}")
        for note in an.notes:
            print(f"  * {note}")
        for subj, miss in expected_numbers(jobs).items():
            print(f"  ! {subj} 누락 번호: {miss}")

        def prog(i, n, name):
            if name:
                print(f"  {i + 1:>3}/{n}  {name}")

        written = run_jobs(path, jobs, args.dpi, args.out, prog, png=want_png, pdf=want_pdf)
        total += len(written)
        if args.debug:
            dp = os.path.join(args.out, f"{exam}_{kind}_debug.pdf")
            write_debug_pdf(path, jobs, dp)
            print(f"  [debug] {dp}")
    fmt = "PNG+PDF" if (want_png and want_pdf) else ("PDF" if want_pdf else "PNG")
    print(f"완료: {total}개 {fmt} → {args.out}")


if __name__ == "__main__":
    main()
