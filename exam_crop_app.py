#!/usr/bin/env python3
"""
CroP — 수능/모의고사 수학 시험지 문항 분할 앱 (macOS, tkinter, Finder 스타일)

실행:  ~/examcrop/bin/python exam_crop_app.py   (또는 CroP.command 더블클릭)

[패치 2] 설정 > 출력 형식 에서 PNG / PDF 를 고를 수 있다 (둘 다 가능).
         PDF 는 문항별 1쪽짜리 벡터 PDF (Mathpix v3/pdf 같은 문서 입력용).
[패치 9] 도구막대 버튼을 직접 그리는 방식으로 바꿔 세로 높이를 키웠다 (기존의 약 1.5배).
         macOS 기본(aqua) ttk 버튼은 높이가 고정이라 글자에 비해 납작해 보였음.
         높이는 TB_BTN_PADY 상수로 조절한다.
[패치 10 · 2026-09-19]
  1) 상태막대 진행 표시를 「문제 12/46 · 해설 0/46 문항」 처럼 문제·해설로 나눠 센다.
     종전 「92 / 92 문항」은 문제 46 + 해설 46 을 합친 수라 파일 수처럼 보였다.
     (조각 _c1/_c2… 나 PNG+PDF 동시 출력으로 파일이 늘어나도 문항 수는 변하지 않는다.
      파일 수는 완료 시 「완료 — N개 파일」에 따로 표시된다.)
  2) 파일마다 분석 결과 한 줄을 로그에 남긴다:
     「[파일명] 종류=문제 · 문항 46 (문제 페이지 20, 해설 페이지 0)」
     문제/해설 어느 쪽이 0개인지, 종류가 뭐로 판정됐는지 바로 볼 수 있다.
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import unicodedata
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exam_crop as core  # noqa: E402

APP_TITLE = "CroP"
CONFIG_PATH = os.path.expanduser("~/.crop_app.json")
DEFAULT_CONFIG = {
    "out_dir": os.path.expanduser("~/Documents/crops"),
    "margin_mm": 3.0,
    "dpi": 600,
    "split_solutions": False,
    "overwrite": True,
    "out_png": True,          # 패치 2: 출력 형식
    "out_pdf": False,
    "last_open_dir": os.path.expanduser("~"),
}
IS_MAC = sys.platform == "darwin"

# Finder 느낌의 색상
C_SIDEBAR = "#EDEDF0"
C_SIDEBAR_SEL = "#D6D6DB"
C_TOOLBAR = "#F6F6F6"
C_ROW_ALT = "#F5F5F7"
C_BORDER = "#D9D9DE"
C_TEXT_DIM = "#6E6E73"
C_ACCENT = "#0A66E5"
# 글자 크기 — 여기 숫자만 바꾸면 앱 전체에 적용됩니다
FONT = ("SF Pro Text", 10) if IS_MAC else ("", 10)
FONT_SMALL = ("SF Pro Text", 9) if IS_MAC else ("", 9)
FONT_BOLD = ("SF Pro Text", 10, "bold") if IS_MAC else ("", 10, "bold")
FONT_MONO = ("Menlo", 9) if IS_MAC else ("monospace", 10)
ROW_HEIGHT = 28 if IS_MAC else 28          # 목록 행 높이 (행간)

# [패치 9] 도구막대 버튼 크기 — 세로 안쪽 여백(px). 글자 크기에 비례해 커진다.
#          버튼을 더 키우거나 줄이려면 배율(0.5)만 바꾸면 됩니다.
TB_BTN_PADY = max(6, int(FONT[1] * 0.5))
TB_BTN_PADX = 13
# 버튼 배경색 (기본 / 마우스 올림 / 누름)
C_BTN = "#F1F1F3"
C_BTN_HOVER = "#E7E7EA"
C_BTN_PRESS = "#DCDCE0"


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def fmt_label(cfg: dict) -> str:
    """현재 출력 형식 표시용 문자열."""
    parts = (["PNG"] if cfg.get("out_png", True) else []) + (["PDF"] if cfg.get("out_pdf") else [])
    return "+".join(parts) or "PNG"


def fmt_count(dp: int, tp: int, ds: int, ts: int) -> str:
    """[패치 10] 진행 문항 수 표시: 「문제 12/46 · 해설 0/46 문항」 (없는 종류는 생략)."""
    parts = ([f"문제 {dp}/{tp}"] if tp else []) + ([f"해설 {ds}/{ts}"] if ts else [])
    return (" · ".join(parts) + " 문항") if parts else "0 문항"


class ToolButton(tk.Label):
    """도구막대용 버튼.  [패치 9]

    macOS 기본(aqua) 테마의 ttk.Button 은 세로 높이가 시스템 고정이라 글자 크기를 키우면
    납작하고 답답해 보인다. Label 을 직접 그려 높이(TB_BTN_PADY)를 자유로 정한다.
    ttk.Button 처럼 config(state="disabled"/"normal") 로 켜고 끌 수 있다.
    """

    def __init__(self, master, text: str, command):
        # 테두리는 highlightthickness 대신 1px 테두리 프레임(_toolbar_buttons)이 그린다
        # (macOS 에서 highlight 링이 깨져 보이는 문제가 있어 쓰지 않는다).
        super().__init__(master, text=text, font=FONT, bg=C_BTN, fg="#1D1D1F",
                         padx=TB_BTN_PADX, pady=TB_BTN_PADY, borderwidth=0,
                         highlightthickness=0,
                         cursor="pointinghand" if IS_MAC else "hand2")
        self.command = command
        self.bind("<Enter>", lambda _e: self._paint(C_BTN_HOVER))
        self.bind("<Leave>", lambda _e: self._paint(C_BTN))
        self.bind("<Button-1>", lambda _e: self._paint(C_BTN_PRESS))
        self.bind("<ButtonRelease-1>", self._release)

    def _enabled(self) -> bool:
        return str(self["state"]) != "disabled"

    def _paint(self, bg: str):
        if self._enabled():
            self.config(bg=bg)

    def _release(self, e):
        if not self._enabled():
            return
        inside = 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height()
        self._paint(C_BTN_HOVER if inside else C_BTN)
        if inside and self.command:
            self.command()


class ExamSet:
    """시험지 한 세트: 문제 파일 + 해설 파일.  (combined_file 은 패치 14 이후 채워지지 않는다 — 합본 거부)"""

    def __init__(self, name: str):
        self.name = name
        self.problem_file: Optional[str] = None
        self.solution_file: Optional[str] = None
        self.combined_file: Optional[str] = None
        self.status = "대기"
        self.summary = ""
        self.warnings: List[str] = []      # 누락 문항 등 상세 경고문

    @property
    def kind_label(self) -> str:
        if self.combined_file:
            return "합본"
        if self.problem_file and self.solution_file:
            return "문제+해설"
        return "문제만" if self.problem_file else "해설만"

    def files(self) -> List[tuple]:
        out = []
        if self.combined_file:
            out.append((self.combined_file, "합본"))
        if self.problem_file:
            out.append((self.problem_file, "문제"))
        if self.solution_file:
            out.append((self.solution_file, "해설"))
        return out


class Sidebar(tk.Frame):
    """Finder 사이드바 흉내: 섹션 제목 + 선택 가능한 항목."""

    def __init__(self, master, on_select):
        super().__init__(master, bg=C_SIDEBAR, width=200)
        self.pack_propagate(False)
        self.on_select = on_select
        self.items: Dict[str, tk.Label] = {}
        self.current: Optional[str] = None

    def section(self, title: str):
        tk.Label(self, text=title, bg=C_SIDEBAR, fg=C_TEXT_DIM, font=FONT_SMALL, anchor="w").pack(
            fill="x", padx=14, pady=(14, 2))

    def item(self, key: str, text: str, action=None):
        lbl = tk.Label(self, text=text, bg=C_SIDEBAR, font=FONT, anchor="w", padx=12, pady=3)
        lbl.pack(fill="x", padx=8)
        lbl.bind("<Button-1>", lambda _e: (action() if action else self.select(key)))
        lbl.bind("<Enter>", lambda _e: lbl.config(bg=C_SIDEBAR_SEL) if key != self.current else None)
        lbl.bind("<Leave>", lambda _e: lbl.config(bg=C_SIDEBAR) if key != self.current else None)
        self.items[key] = lbl

    def select(self, key: str):
        for k, l in self.items.items():
            l.config(bg=C_SIDEBAR)
        self.items[key].config(bg=C_SIDEBAR_SEL)
        self.current = key
        self.on_select(key)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1040x700")
        self.minsize(880, 560)
        self.cfg = load_config()
        self.sets: Dict[str, ExamSet] = {}
        self.results: List[str] = []
        self.checked: Dict[str, bool] = {}
        self.worker: Optional[threading.Thread] = None
        self.stop_flag = False
        self.total = 0
        self.total_p = 0          # [패치 10] 문제 문항 수 / 해설 문항 수
        self.total_s = 0
        self.q: queue.Queue = queue.Queue()
        self._style()
        self._build_ui()
        self.sidebar.select("sets")
        self.after(100, self._poll_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------------------------------------------------- 스타일 -----
    def _style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("aqua" if IS_MAC else "clam")
        except tk.TclError:
            pass
        st.configure("Treeview", font=FONT, rowheight=ROW_HEIGHT, borderwidth=0)
        st.configure("Treeview.Heading", font=FONT_SMALL)
        st.configure("Tool.TButton", font=FONT)
        st.configure("Status.TLabel", font=FONT_SMALL, foreground=C_TEXT_DIM)

    # -------------------------------------------------------------- UI -----
    def _build_ui(self):
        # 툴바 (Finder 상단 도구막대)
        tb = tk.Frame(self, bg=C_TOOLBAR, height=46)
        tb.pack(fill="x")
        tk.Frame(self, bg=C_BORDER, height=1).pack(fill="x")
        self.tb = tb
        self.title_var = tk.StringVar(value="시험지")
        tk.Label(tb, textvariable=self.title_var, bg=C_TOOLBAR, font=FONT_BOLD).pack(side="left", padx=(14, 18), pady=10)
        self.tb_left = tk.Frame(tb, bg=C_TOOLBAR)
        self.tb_left.pack(side="left", fill="y")
        self.tb_right = tk.Frame(tb, bg=C_TOOLBAR)
        self.tb_right.pack(side="right", fill="y", padx=10)

        # 본문: 사이드바 + 내용
        body = tk.Frame(self)
        body.pack(fill="both", expand=True)
        self.sidebar = Sidebar(body, self._show_view)
        self.sidebar.pack(side="left", fill="y")
        tk.Frame(body, bg=C_BORDER, width=1).pack(side="left", fill="y")
        self.sidebar.section("작업")
        self.sidebar.item("sets", "📄  시험지")
        self.sidebar.item("results", "🖼  결과 파일")
        self.sidebar.item("settings", "⚙️  설정")
        self.sidebar.section("위치")
        self.sidebar.item("outdir", "📁  출력 폴더 (crops)", action=self.open_out)
        self.sidebar.item("log", "📝  로그")

        self.content = tk.Frame(body, bg="white")
        self.content.pack(side="left", fill="both", expand=True)
        self.views: Dict[str, tk.Frame] = {}
        self._build_sets_view()
        self._build_results_view()
        self._build_settings_view()
        self._build_log_view()

        # 하단 상태 막대 (Finder 상태 막대 + 진행 막대)
        tk.Frame(self, bg=C_BORDER, height=1).pack(fill="x")
        sb = tk.Frame(self, bg=C_TOOLBAR)
        sb.pack(fill="x")
        self.pbar = ttk.Progressbar(sb, mode="determinate", length=260)
        self.pbar.pack(side="left", padx=(14, 10), pady=6)
        self.count_var = tk.StringVar(value="")
        tk.Label(sb, textvariable=self.count_var, bg=C_TOOLBAR, font=FONT_BOLD).pack(side="left")
        self.current_var = tk.StringVar(value="")
        tk.Label(sb, textvariable=self.current_var, bg=C_TOOLBAR, font=FONT_MONO, fg=C_TEXT_DIM).pack(side="left", padx=12)
        self.status_var = tk.StringVar(value="PDF를 추가하세요")
        tk.Label(sb, textvariable=self.status_var, bg=C_TOOLBAR, font=FONT_SMALL, fg=C_TEXT_DIM).pack(side="right", padx=14)

    def _toolbar_buttons(self, specs):
        # [패치 9] aqua ttk.Button 대신 높이를 정할 수 있는 ToolButton 사용
        for w in list(self.tb_left.winfo_children()) + list(self.tb_right.winfo_children()):
            w.destroy()
        for side, text, cmd, name in specs:
            parent = self.tb_left if side == "left" else self.tb_right
            border = tk.Frame(parent, bg=C_BORDER)          # 1px 테두리
            border.pack(side="left", padx=4, pady=7)
            b = ToolButton(border, text=text, command=cmd)
            b.pack(padx=1, pady=1)
            if name:
                setattr(self, name, b)

    def _show_view(self, key: str):
        if key == "outdir":
            return
        for k, v in self.views.items():
            v.pack_forget()
        self.views[key].pack(fill="both", expand=True)
        titles = {"sets": "시험지", "results": "결과 파일", "settings": "설정", "log": "로그"}
        self.title_var.set(titles[key])
        running = self.worker is not None and self.worker.is_alive()
        if key == "sets":
            self._toolbar_buttons([
                ("left", "＋ PDF 추가…", self.add_files, None),
                ("left", "－ 제거", self.remove_selected, None),
                ("left", "목록 비우기", self.clear_sets, None),
                ("right", "▶ 문제지 분할", self.start, "run_btn"),
                ("right", "■ 중지", self.stop, "stop_btn"),
            ])
            self.run_btn.config(state="disabled" if running else "normal")
            self.stop_btn.config(state="normal" if running else "disabled")
        elif key == "results":
            self._toolbar_buttons([
                ("left", "전체 선택", lambda: self._check_all(True), None),
                ("left", "선택 해제", lambda: self._check_all(False), None),
                ("left", "체크한 파일 이동…", self.move_checked, None),
                ("left", "탐색기에서 골라 이동…", self.move_via_dialog, None),
                ("right", "Finder에서 보기", self.open_out, None),
            ])
        elif key == "settings":
            self._toolbar_buttons([("right", "기본값으로", self._reset_settings, None)])
        else:
            self._toolbar_buttons([("right", "지우기", self._log_clear, None)])

    # ---- 시험지 뷰
    def _build_sets_view(self):
        v = tk.Frame(self.content, bg="white")
        self.views["sets"] = v
        cols = ("name", "kind", "files", "status")
        self.tree = ttk.Treeview(v, columns=cols, show="headings", selectmode="extended")
        for c, t, w, stretch in (("name", "시험지명 (더블클릭해서 수정)", 260, False),
                                 ("kind", "유형", 80, False), ("files", "파일", 280, True),
                                 ("status", "상태", 200, False)):
            self.tree.heading(c, text=t, anchor="w")
            self.tree.column(c, width=w, anchor="w", stretch=stretch)
        self.tree.tag_configure("alt", background=C_ROW_ALT)
        self.tree.tag_configure("warn", foreground="#D0021B")
        self.tree.bind("<Button-1>", self._maybe_show_warning, add="+")
        ysb = ttk.Scrollbar(v, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._edit_name)
        self.tree.bind("<BackSpace>", lambda _e: self.remove_selected())
        self.tree.bind("<Delete>", lambda _e: self.remove_selected())
        self.tree.bind("<Button-1>", self._maybe_add_on_empty, add="+")

    def _maybe_show_warning(self, event):
        if self.tree.identify_column(event.x) != "#4":
            return
        iid = self.tree.identify_row(event.y)
        if iid and self.sets[iid].warnings:
            s = self.sets[iid]
            messagebox.showwarning(
                APP_TITLE,
                f"[{s.name}] 다음 문항을 찾지 못했습니다.\n\n" + "\n".join(s.warnings) +
                "\n\n원인은 대개 문항 번호의 글자 크기·위치가 다른 양식과 다를 때입니다. "
                "해당 PDF와 빠진 번호를 알려주시면 규칙을 보완할 수 있습니다.")

    def _maybe_add_on_empty(self, event):
        if not self.sets and self.tree.identify_region(event.x, event.y) != "heading":
            self.add_files()

    # ---- 결과 뷰
    def _build_results_view(self):
        v = tk.Frame(self.content, bg="white")
        self.views["results"] = v
        self.res = ttk.Treeview(v, columns=("chk", "file", "size"), show="headings", selectmode="extended")
        self.res.heading("chk", text="✓", anchor="center")
        self.res.column("chk", width=40, anchor="center", stretch=False)
        self.res.heading("file", text="이름", anchor="w")
        self.res.column("file", anchor="w", stretch=True)
        self.res.heading("size", text="크기", anchor="e")
        self.res.column("size", width=90, anchor="e", stretch=False)
        self.res.tag_configure("alt", background=C_ROW_ALT)
        ysb = ttk.Scrollbar(v, orient="vertical", command=self.res.yview)
        self.res.configure(yscrollcommand=ysb.set)
        self.res.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")
        self.res.bind("<Button-1>", self._toggle_check)
        self.res.bind("<space>", lambda _e: self._toggle_selected())
        self.res.bind("<Double-1>", lambda e: self._open_result(e))

    # ---- 설정 뷰
    def _build_settings_view(self):
        v = tk.Frame(self.content, bg="white")
        self.views["settings"] = v
        g = tk.Frame(v, bg="white")
        g.pack(anchor="nw", padx=28, pady=24)

        def row(r, label):
            tk.Label(g, text=label, bg="white", font=FONT, anchor="e", width=16).grid(row=r, column=0, sticky="e", pady=8, padx=(0, 12))

        row(0, "출력 폴더")
        self.out_var = tk.StringVar(value=self.cfg["out_dir"])
        ttk.Entry(g, textvariable=self.out_var, width=48, font=FONT).grid(row=0, column=1, sticky="w")
        ttk.Button(g, text="변경…", command=self.choose_out).grid(row=0, column=2, padx=6)
        tk.Label(g, text="문제·해설, 세트가 달라도 모두 이 폴더 하나에 저장됩니다.", bg="white", fg=C_TEXT_DIM, font=FONT_SMALL).grid(row=1, column=1, sticky="w")

        row(2, "여백 (mm)")
        self.margin_var = tk.DoubleVar(value=float(self.cfg["margin_mm"]))
        ttk.Spinbox(g, from_=0, to=15, increment=0.5, width=6, textvariable=self.margin_var, font=FONT).grid(row=2, column=1, sticky="w")
        tk.Label(g, text="본문 가장자리에서 잘라내는 여유. 기본 3mm.", bg="white", fg=C_TEXT_DIM, font=FONT_SMALL).grid(row=3, column=1, sticky="w")

        row(4, "해상도 (DPI)")
        self.dpi_var = tk.IntVar(value=int(self.cfg["dpi"]))
        ttk.Spinbox(g, from_=150, to=1200, increment=50, width=6, textvariable=self.dpi_var, font=FONT).grid(row=4, column=1, sticky="w")

        # 패치 2: 출력 형식
        row(5, "출력 형식")
        fr = tk.Frame(g, bg="white")
        fr.grid(row=5, column=1, columnspan=2, sticky="w")
        self.png_var = tk.BooleanVar(value=bool(self.cfg.get("out_png", True)))
        self.pdf_var = tk.BooleanVar(value=bool(self.cfg.get("out_pdf", False)))
        ttk.Checkbutton(fr, text="PNG (이미지, DPI 적용)", variable=self.png_var).pack(side="left")
        ttk.Checkbutton(fr, text="PDF (문항별 1쪽 벡터 PDF — Mathpix 문서 변환용)", variable=self.pdf_var).pack(side="left", padx=(16, 0))
        tk.Label(g, text="둘 다 켜면 같은 이름으로 .png 와 .pdf 를 함께 저장합니다. PDF 는 DPI 와 무관하게 글자·도형이 벡터로 유지됩니다.",
                 bg="white", fg=C_TEXT_DIM, font=FONT_SMALL).grid(row=6, column=1, columnspan=2, sticky="w")

        row(7, "해설")
        self.split_var = tk.BooleanVar(value=bool(self.cfg["split_solutions"]))
        ttk.Checkbutton(g, text="문항별로 이어붙이지 않고 단(column) 조각마다 따로 저장  (_1, _2 …)", variable=self.split_var).grid(row=7, column=1, columnspan=2, sticky="w")

        row(8, "덮어쓰기")
        self.overwrite_var = tk.BooleanVar(value=bool(self.cfg["overwrite"]))
        ttk.Checkbutton(g, text="같은 이름의 파일이 이미 있으면 덮어쓰기 (끄면 건너뜀)", variable=self.overwrite_var).grid(row=8, column=1, columnspan=2, sticky="w")

        tk.Label(g, text="설정은 자동 저장됩니다 (~/.crop_app.json).", bg="white", fg=C_TEXT_DIM, font=FONT_SMALL).grid(row=10, column=1, sticky="w", pady=(24, 0))

    def _reset_settings(self):
        self.out_var.set(DEFAULT_CONFIG["out_dir"])
        self.margin_var.set(DEFAULT_CONFIG["margin_mm"])
        self.dpi_var.set(DEFAULT_CONFIG["dpi"])
        self.split_var.set(DEFAULT_CONFIG["split_solutions"])
        self.overwrite_var.set(DEFAULT_CONFIG["overwrite"])
        self.png_var.set(DEFAULT_CONFIG["out_png"])
        self.pdf_var.set(DEFAULT_CONFIG["out_pdf"])

    # ---- 로그 뷰
    def _build_log_view(self):
        v = tk.Frame(self.content, bg="white")
        self.views["log"] = v
        self.log = tk.Text(v, wrap="word", state="disabled", font=FONT_MONO, bg="white", relief="flat", padx=12, pady=10)
        ysb = ttk.Scrollbar(v, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=ysb.set)
        self.log.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")

    # --------------------------------------------------- 파일 목록 -----
    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="시험지 PDF 선택 (여러 개 선택 가능)",
            initialdir=self.cfg.get("last_open_dir"),
            filetypes=[("PDF", "*.pdf"), ("모든 파일", "*")],
        )
        if not paths:
            return
        self.cfg["last_open_dir"] = os.path.dirname(paths[0])
        rejected = []
        for p in paths:
            name, kind = core.classify_filename(p)
            if kind not in ("문제", "해설"):          # [패치 14] 합본은 받지 않는다
                rejected.append(os.path.basename(p))
                continue
            s = self.sets.get(name)
            if s is None:
                s = self.sets[name] = ExamSet(name)
            if kind == "문제":
                s.problem_file = p
            elif kind == "해설":
                s.solution_file = p
        self._refresh_tree()
        if rejected:
            messagebox.showerror(APP_TITLE, core.COMBINED_MSG + "\n\n추가하지 않은 파일:\n" + "\n".join(rejected))

    def remove_selected(self):
        for iid in self.tree.selection():
            self.sets.pop(iid, None)
        self._refresh_tree()

    def clear_sets(self):
        self.sets.clear()
        self._refresh_tree()

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, (key, s) in enumerate(self.sets.items()):
            files = "  |  ".join(os.path.basename(p) for p, _ in s.files())
            status = s.status + ("  " + s.summary if s.summary else "")
            if s.warnings:      # 누락이 있으면 줄을 빨간색으로만 표시 (자세한 내용은 로그 또는 상태 칸 클릭)
                status += f"  ⚠{sum(w.count(',') + 1 for w in s.warnings)}"
            tags = (["alt"] if i % 2 else []) + (["warn"] if s.warnings else [])
            self.tree.insert("", "end", iid=key, values=(s.name, s.kind_label, files, status), tags=tuple(tags))
        n = len(self.sets)
        if not (self.worker and self.worker.is_alive()):
            self.status_var.set(f"{n}개 세트" if n else "PDF를 추가하세요 (빈 곳을 클릭해도 됩니다)")

    def _edit_name(self, event):
        if self.tree.identify_column(event.x) != "#1":
            return
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        x, y, w, h = self.tree.bbox(iid, "#1")
        var = tk.StringVar(value=self.sets[iid].name)
        entry = ttk.Entry(self.tree, textvariable=var, font=FONT)
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()
        entry.select_range(0, "end")

        def done(_=None):
            new = core.clean_exam_name(var.get())
            entry.destroy()
            if not new or new == self.sets[iid].name:
                return
            me = self.sets[iid]
            other = next((s for k, s in self.sets.items() if k != iid and s.name == new), None)
            if other is not None:
                # 같은 이름의 세트가 있으면 서로 겹치지 않는 파일끼리 한 세트로 합친다
                conflict = [a for a in ("problem_file", "solution_file", "combined_file")
                            if getattr(me, a) and getattr(other, a)]
                if conflict:
                    messagebox.showerror(APP_TITLE, f"'{new}' 세트에 같은 종류의 파일이 이미 있어 합칠 수 없습니다.")
                    return
                for a in ("problem_file", "solution_file", "combined_file"):
                    if getattr(me, a):
                        setattr(other, a, getattr(me, a))
                self.sets.pop(iid)
            else:
                me.name = new
            self._refresh_tree()

        entry.bind("<Return>", done)
        entry.bind("<FocusOut>", done)
        entry.bind("<Escape>", lambda _: entry.destroy())

    # -------------------------------------------------------- 설정 -----
    def choose_out(self):
        d = filedialog.askdirectory(title="출력 폴더 선택", initialdir=self.out_var.get() or os.path.expanduser("~"))
        if d:
            self.out_var.set(d)

    def open_out(self):
        d = self.out_var.get()
        os.makedirs(d, exist_ok=True)
        self._reveal(d)

    @staticmethod
    def _reveal(path: str):
        if IS_MAC:
            subprocess.Popen(["open", path])
        elif sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path])

    def _sync_cfg(self):
        try:
            margin, dpi = float(self.margin_var.get()), int(self.dpi_var.get())
        except (tk.TclError, ValueError):
            margin, dpi = DEFAULT_CONFIG["margin_mm"], DEFAULT_CONFIG["dpi"]
        png, pdf = bool(self.png_var.get()), bool(self.pdf_var.get())
        if not png and not pdf:            # 둘 다 끄면 PNG 로 되돌림
            png = True
            self.png_var.set(True)
        self.cfg.update({
            "out_dir": os.path.expanduser(self.out_var.get().strip()) or DEFAULT_CONFIG["out_dir"],
            "margin_mm": margin,
            "dpi": dpi,
            "split_solutions": bool(self.split_var.get()),
            "overwrite": bool(self.overwrite_var.get()),
            "out_png": png,
            "out_pdf": pdf,
        })
        save_config(self.cfg)

    # ------------------------------------------------------- 실행 -----
    def start(self):
        if not self.sets:
            messagebox.showinfo(APP_TITLE, "먼저 PDF 파일을 추가하세요.")
            return
        if self.worker and self.worker.is_alive():
            return
        self._sync_cfg()
        names = [s.name for s in self.sets.values()]
        if len(set(names)) != len(names):
            messagebox.showerror(APP_TITLE, "시험지명이 겹치는 세트가 있습니다. 시험지명을 다르게 바꿔 주세요.")
            return
        self.stop_flag = False
        self.results, self.checked = [], {}
        self.res.delete(*self.res.get_children())
        self.pbar.config(value=0)
        self.count_var.set("")
        self.current_var.set("문항 수 계산 중…")
        for s in self.sets.values():
            s.status, s.summary, s.warnings = "대기", "", []
        self._refresh_tree()
        self._log(f"── 분할 시작 (출력: {fmt_label(self.cfg)}) ──")
        self.worker = threading.Thread(target=self._work, daemon=True)
        self.worker.start()
        self._show_view("sets") if self.sidebar.current == "sets" else None
        if hasattr(self, "run_btn"):
            self.run_btn.config(state="disabled")
            self.stop_btn.config(state="normal")

    def stop(self):
        self.stop_flag = True
        self._log("중지 요청… 현재 문항까지 저장하고 멈춥니다.")

    def _work(self):
        cfg = self.cfg
        out_dir = cfg["out_dir"]
        os.makedirs(out_dir, exist_ok=True)
        pad_pt = cfg["margin_mm"] * core.MM
        want_png, want_pdf = bool(cfg.get("out_png", True)), bool(cfg.get("out_pdf", False))
        try:
            plans, total = [], 0
            for s in list(self.sets.values()):
                self.q.put(("status", s, "분석 중"))
                for path, kind in s.files():
                    try:
                        an, jobs = core.build_jobs(path, s.name, kind, pad_pt, cfg["split_solutions"])
                    except Exception as e:  # noqa: BLE001
                        self.q.put(("log", f"[{os.path.basename(path)}] 분석 실패: {e}"))
                        self.q.put(("summary", s, f"실패: {e}", []))
                        continue
                    # [패치 10] 파일마다 분석 결과 한 줄 — 종류 판정과 문제/해설 문항 수를 바로 볼 수 있게
                    jp = sum(1 for j in jobs if j.kind == "문제")
                    js = sum(1 for j in jobs if j.kind == "해설")
                    self.q.put(("log", f"[{os.path.basename(path)}] 종류={kind} · 문항 {len(jobs)}"
                                       f" (문제 {jp} / 해설 {js}; 문제 페이지 {len(an.problem_pages)}, 해설 페이지 {len(an.solution_pages)})"))
                    for note in getattr(an, "notes", []):      # [패치 8] 외곽선 감지 모드 등 안내
                        self.q.put(("log", f"[{os.path.basename(path)}] {note}"))
                    if not jobs:
                        self.q.put(("log", f"[{os.path.basename(path)}] 문항을 찾지 못했습니다 (텍스트 PDF가 아니거나 양식이 다름)"))
                    if not cfg["overwrite"]:
                        before = len(jobs)
                        # 이 문항이 만들 파일(PNG/PDF)이 전부 이미 있을 때만 건너뜀
                        jobs = [j for j in jobs
                                if not all(os.path.exists(p) for p in core.output_paths(j, out_dir, want_png, want_pdf))]
                        if before != len(jobs):
                            self.q.put(("log", f"[{s.name}] 이미 있는 파일 {before - len(jobs)}개 건너뜀"))
                    plans.append((s, path, kind, jobs))
                    total += len(jobs)
                n_set = sum(len(j) for ss, _, _, j in plans if ss is s)
                self.q.put(("status", s, f"대기 ({n_set}문항)"))
            total_p = sum(1 for _, _, _, jobs in plans for j in jobs if j.kind == "문제")
            total_s = sum(1 for _, _, _, jobs in plans for j in jobs if j.kind == "해설")
            self.q.put(("total", total, total_p, total_s))

            done = 0
            done_p = done_s = 0                       # [패치 10] 지금까지 끝난 문제/해설 문항 수
            done_jobs: Dict[ExamSet, List[core.Job]] = {}
            for s, path, kind, jobs in plans:
                if self.stop_flag:
                    break
                self.q.put(("status", s, "처리 중"))
                base_done, base_p, base_s = done, done_p, done_s

                def prog(i, n, name, jobs=jobs, base_done=base_done, base_p=base_p, base_s=base_s):
                    if name:
                        dp = base_p + sum(1 for j in jobs[:i] if j.kind == "문제")
                        ds = base_s + sum(1 for j in jobs[:i] if j.kind == "해설")
                        self.q.put(("progress", base_done + i, name, dp, ds))

                written = core.run_jobs(path, jobs, cfg["dpi"], out_dir, prog, lambda: self.stop_flag,
                                        png=want_png, pdf=want_pdf)
                done += len(jobs)
                done_p += sum(1 for j in jobs if j.kind == "문제")
                done_s += sum(1 for j in jobs if j.kind == "해설")
                self.q.put(("progress", done, "", done_p, done_s))
                self.q.put(("written", written))
                done_jobs.setdefault(s, []).extend(jobs)
                all_jobs = done_jobs[s]
                n_p = sum(1 for j in all_jobs if j.kind == "문제")
                n_s = sum(1 for j in all_jobs if j.kind == "해설")
                parts = ([f"문제 {n_p}"] if n_p else []) + ([f"해설 {n_s}"] if n_s else [])
                warnings = []
                for k in ("문제", "해설"):
                    kj = [j for j in all_jobs if j.kind == k]
                    if kj:
                        for subj, miss in core.expected_numbers(kj).items():
                            warnings.append(f"{k} {subj}: {', '.join(f'{n}번' for n in miss)}")
                self.q.put(("summary", s, " / ".join(parts), warnings))
                warn = ("  ⚠ 누락: " + " / ".join(warnings)) if warnings else ""
                self.q.put(("log", f"[{s.name}] {os.path.basename(path)} → {len(written)}개 저장{warn}"))
            self.q.put(("done", None))
        except Exception as e:  # noqa: BLE001
            self.q.put(("log", f"오류: {e!r}"))
            self.q.put(("done", None))

    def _poll_queue(self):
        try:
            while True:
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "total":
                    self.total, self.total_p, self.total_s = msg[1], msg[2], msg[3]
                    self.pbar.config(maximum=max(1, self.total), value=0)
                    self.count_var.set(fmt_count(0, self.total_p, 0, self.total_s))
                    self.status_var.set(f"{len(self.sets)}개 세트 처리 중")
                elif kind == "progress":
                    i, name, dp, ds = msg[1], msg[2], msg[3], msg[4]
                    self.pbar.config(value=i)
                    self.count_var.set(fmt_count(dp, self.total_p, ds, self.total_s))
                    self.current_var.set(name)
                elif kind == "status":
                    msg[1].status = msg[2]
                    self._refresh_tree()
                elif kind == "summary":
                    msg[1].status, msg[1].summary = ("실패" if msg[2].startswith("실패") else "완료"), msg[2]
                    msg[1].warnings = list(msg[3])
                    self._refresh_tree()
                elif kind == "written":
                    for p in msg[1]:
                        self._add_result(p)
                elif kind == "log":
                    self._log(msg[1])
                elif kind == "done":
                    if hasattr(self, "run_btn"):
                        self.run_btn.config(state="normal")
                        self.stop_btn.config(state="disabled")
                    self.current_var.set("중지됨" if self.stop_flag else "완료")
                    for s in self.sets.values():
                        if s.status in ("분석 중", "처리 중"):
                            s.status = "중지됨"
                    self._refresh_tree()
                    self.status_var.set(f"완료 — {len(self.results)}개 파일 → {self.cfg['out_dir']}")
                    self._log(f"완료: 총 {len(self.results)}개 파일({fmt_label(self.cfg)}) → {self.cfg['out_dir']}")
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    # ------------------------------------------------------- 로그 -----
    def _log(self, text: str):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _log_clear(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    # ------------------------------------------------- 결과 파일 이동 -----
    def _add_result(self, p: str):
        self.results.append(p)
        self.checked[p] = False
        try:
            size = f"{os.path.getsize(p) / 1024:,.0f} KB"
        except OSError:
            size = ""
        self.res.insert("", "end", iid=p, values=("☐", os.path.basename(p), size),
                        tags=("alt",) if len(self.results) % 2 == 0 else ())

    def _toggle_check(self, event):
        if self.res.identify_region(event.x, event.y) != "cell":
            return
        iid = self.res.identify_row(event.y)
        if not iid:
            return
        if self.res.identify_column(event.x) == "#1":
            self.checked[iid] = not self.checked.get(iid, False)
            self.res.set(iid, "chk", "☑" if self.checked[iid] else "☐")
            return "break"

    def _toggle_selected(self):
        for iid in self.res.selection():
            self.checked[iid] = not self.checked.get(iid, False)
            self.res.set(iid, "chk", "☑" if self.checked[iid] else "☐")

    def _open_result(self, event):
        iid = self.res.identify_row(event.y)
        if iid and os.path.exists(iid):
            self._reveal(iid)

    def _check_all(self, value: bool):
        for iid in self.res.get_children():
            self.checked[iid] = value
            self.res.set(iid, "chk", "☑" if value else "☐")

    def move_checked(self):
        files = [p for p in self.results if self.checked.get(p)]
        if not files:
            sel = list(self.res.selection())
            if sel:
                files = sel
        if not files:
            messagebox.showinfo(APP_TITLE, "이동할 파일을 체크(또는 선택)하세요.")
            return
        self._move_files(files)

    def move_via_dialog(self):
        files = filedialog.askopenfilenames(
            title="이동할 파일 선택 (여러 개 선택 가능) — 선택 후 '열기'",
            initialdir=self.out_var.get(),
            filetypes=[("PNG / PDF", "*.png *.pdf"), ("PNG", "*.png"), ("PDF", "*.pdf"), ("모든 파일", "*")],
        )
        if files:
            self._move_files(list(files))

    def _move_files(self, files: List[str]):
        dest = filedialog.askdirectory(title=f"{len(files)}개 파일을 옮길 목적지 폴더 선택",
                                       initialdir=os.path.dirname(self.out_var.get()))
        if not dest:
            return
        moved, skipped = 0, []
        for p in files:
            target = os.path.join(dest, os.path.basename(p))
            if os.path.abspath(target) == os.path.abspath(p):
                continue
            if os.path.exists(target):
                skipped.append(os.path.basename(p))
                continue
            try:
                shutil.move(p, target)
                moved += 1
                if self.res.exists(p):
                    self.res.delete(p)
                if p in self.results:
                    self.results.remove(p)
                self.checked.pop(p, None)
            except Exception as e:  # noqa: BLE001
                skipped.append(f"{os.path.basename(p)} ({e})")
        msg = f"{moved}개 파일을 옮겼습니다.\n→ {dest}"
        if skipped:
            msg += f"\n\n같은 이름이 이미 있어 건너뜀 {len(skipped)}개:\n" + "\n".join(skipped[:10])
            if len(skipped) > 10:
                msg += f"\n… 외 {len(skipped) - 10}개"
        self._log(msg.replace("\n", " "))
        self.status_var.set(f"{moved}개 이동 → {dest}")
        messagebox.showinfo(APP_TITLE, msg)

    # ------------------------------------------------------- 종료 -----
    def _on_close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno(APP_TITLE, "작업이 진행 중입니다. 종료할까요?"):
                return
            self.stop_flag = True
        self._sync_cfg()
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
