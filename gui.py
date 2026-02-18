"""Auto Blog GUI — GPT AI 자동 블로그 글 작성기"""
import os
import sys
import queue
import logging
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path


# ── 경로 설정 (.exe 실행 / 일반 실행 모두 지원) ──────────────────────────────

def get_app_dir() -> Path:
    """실행 방식에 관계없이 앱 루트 디렉토리를 반환합니다."""
    if getattr(sys, 'frozen', False):   # PyInstaller .exe
        return Path(sys.executable).parent
    return Path(__file__).parent        # 일반 python 실행


APP_DIR = get_app_dir()
LOGS_DIR = APP_DIR / 'logs'
ENV_PATH = APP_DIR / '.env'
LOGS_DIR.mkdir(exist_ok=True)

# auto_blog 모듈 import 전에 .env를 먼저 로드
if ENV_PATH.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ENV_PATH, override=True)


# ── 색상 테마 ─────────────────────────────────────────────────────────────────

C = {
    'bg':       '#1e1f2e',   # 메인 배경
    'surface':  '#272838',   # 카드/패널
    'input':    '#1a1b28',   # 입력칸
    'primary':  '#6c63ff',   # 메인 색상 (보라)
    'primary2': '#5a52d5',   # hover
    'accent':   '#ff6584',   # 강조
    'text':     '#e8e8f4',   # 본문 텍스트
    'dim':      '#8888aa',   # 보조 텍스트
    'success':  '#4ade80',   # 성공
    'error':    '#f87171',   # 오류
    'border':   '#33354a',   # 테두리
    'log_bg':   '#111120',   # 로그 배경
    'log_fg':   '#88ff88',   # 로그 텍스트
}

FONT_KR = 'Malgun Gothic'
FONT_MONO = 'Consolas'


# ── 로깅 핸들러 (GUI 로그창으로 출력) ───────────────────────────────────────

class _GuiLogHandler(logging.Handler):
    def __init__(self, q: queue.Queue):
        super().__init__()
        self._q = q

    def emit(self, record: logging.LogRecord):
        self._q.put(self.format(record))


# ── 메인 앱 ──────────────────────────────────────────────────────────────────

class AutoBlogApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auto Blog — 자동 블로그 글 작성기")
        self.geometry("960x740")
        self.minsize(860, 660)
        self.configure(bg=C['bg'])

        self._log_q: queue.Queue = queue.Queue()
        self._sched_running = False

        self._setup_logging()
        self._setup_style()
        self._build_ui()
        self._poll_log()

    # ── 로깅 설정 ──────────────────────────────────────────────────────────

    def _setup_logging(self):
        fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s',
                                datefmt='%H:%M:%S')

        gui_handler = _GuiLogHandler(self._log_q)
        gui_handler.setFormatter(fmt)

        file_handler = logging.FileHandler(
            LOGS_DIR / 'auto_blog.log', encoding='utf-8')
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))

        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(gui_handler)
        root.addHandler(file_handler)

    # ── 스타일 설정 ────────────────────────────────────────────────────────

    def _setup_style(self):
        s = ttk.Style(self)
        s.theme_use('clam')

        s.configure('.', background=C['bg'], foreground=C['text'],
                    font=(FONT_KR, 10))

        # Notebook
        s.configure('TNotebook', background=C['bg'], borderwidth=0)
        s.configure('TNotebook.Tab', background=C['surface'],
                    foreground=C['dim'], padding=[18, 9],
                    font=(FONT_KR, 10), borderwidth=0)
        s.map('TNotebook.Tab',
              background=[('selected', C['primary'])],
              foreground=[('selected', '#ffffff')])

        # Frames
        s.configure('TFrame', background=C['bg'])
        s.configure('Card.TFrame', background=C['surface'])

        # Labels
        s.configure('TLabel', background=C['bg'], foreground=C['text'])
        s.configure('Card.TLabel', background=C['surface'], foreground=C['text'])
        s.configure('Dim.TLabel', background=C['bg'], foreground=C['dim'],
                    font=(FONT_KR, 9))
        s.configure('CDim.TLabel', background=C['surface'], foreground=C['dim'],
                    font=(FONT_KR, 9))
        s.configure('Title.TLabel', background=C['bg'], foreground=C['text'],
                    font=(FONT_KR, 14, 'bold'))
        s.configure('CardTitle.TLabel', background=C['surface'],
                    foreground=C['text'], font=(FONT_KR, 11, 'bold'))
        s.configure('Success.TLabel', background=C['surface'],
                    foreground=C['success'], font=(FONT_KR, 10, 'bold'))
        s.configure('Error.TLabel', background=C['surface'],
                    foreground=C['error'], font=(FONT_KR, 10, 'bold'))

        # Buttons
        s.configure('Primary.TButton', background=C['primary'],
                    foreground='#ffffff', font=(FONT_KR, 10, 'bold'),
                    padding=[18, 9], relief='flat', borderwidth=0)
        s.map('Primary.TButton',
              background=[('active', C['primary2']), ('pressed', C['primary2'])])

        s.configure('Stop.TButton', background='#4a4a6a',
                    foreground='#cccccc', font=(FONT_KR, 10),
                    padding=[14, 9], relief='flat', borderwidth=0)
        s.map('Stop.TButton',
              background=[('active', '#5a5a7a')])

        s.configure('Trend.TButton', background='#d4380d',
                    foreground='#ffffff', font=(FONT_KR, 10, 'bold'),
                    padding=[14, 9], relief='flat', borderwidth=0)
        s.map('Trend.TButton',
              background=[('active', '#b32d0a'), ('pressed', '#b32d0a')])

        # Radiobutton
        s.configure('TRadiobutton', background=C['surface'],
                    foreground=C['text'], font=(FONT_KR, 10))

        # Separator
        s.configure('TSeparator', background=C['border'])

    # ── UI 빌드 ────────────────────────────────────────────────────────────

    def _build_ui(self):
        # 헤더
        hdr = tk.Frame(self, bg=C['surface'], pady=12, padx=24)
        hdr.pack(fill='x')
        tk.Label(hdr, text="✦ Auto Blog", bg=C['surface'],
                 fg=C['primary'], font=(FONT_KR, 15, 'bold')).pack(side='left')
        tk.Label(hdr, text="  GPT AI 자동 블로그 글 작성기",
                 bg=C['surface'], fg=C['dim'],
                 font=(FONT_KR, 10)).pack(side='left', pady=(4, 0))

        # 구분선
        tk.Frame(self, bg=C['border'], height=1).pack(fill='x')

        # 노트북 탭
        main = tk.Frame(self, bg=C['bg'], padx=20, pady=16)
        main.pack(fill='both', expand=True)

        nb = ttk.Notebook(main)
        nb.pack(fill='both', expand=True)

        self._build_issue_tab(nb)
        self._build_opinion_tab(nb)
        self._build_schedule_tab(nb)
        self._build_settings_tab(nb)

        # 로그 패널
        tk.Frame(main, bg=C['border'], height=1).pack(fill='x', pady=(12, 0))
        log_hdr = tk.Frame(main, bg=C['bg'])
        log_hdr.pack(fill='x', pady=(6, 4))
        tk.Label(log_hdr, text="실행 로그", bg=C['bg'],
                 fg=C['dim'], font=(FONT_KR, 9)).pack(side='left')
        tk.Button(log_hdr, text="로그 지우기", bg=C['surface'],
                  fg=C['dim'], font=(FONT_KR, 8), relief='flat',
                  bd=0, cursor='hand2',
                  command=self._clear_log).pack(side='right')

        self._log_box = scrolledtext.ScrolledText(
            main, height=7, state='disabled',
            bg=C['log_bg'], fg=C['log_fg'],
            insertbackground=C['text'],
            font=(FONT_MONO, 9), relief='flat',
            wrap='word', bd=0)
        self._log_box.pack(fill='x')

    # ── 공통 위젯 헬퍼 ────────────────────────────────────────────────────

    def _card(self, parent) -> tuple[tk.Frame, tk.Frame]:
        """Surface 색상 카드 프레임 (outer, inner) 반환."""
        outer = tk.Frame(parent, bg=C['border'], padx=1, pady=1)
        inner = tk.Frame(outer, bg=C['surface'], padx=24, pady=20)
        inner.pack(fill='both', expand=True)
        return outer, inner

    def _entry(self, parent, label: str, hint: str = '',
               show: str = '') -> tk.Entry:
        tk.Label(parent, text=label, bg=C['surface'],
                 fg=C['text'], font=(FONT_KR, 10)).pack(anchor='w', pady=(12, 3))
        e = tk.Entry(parent, bg=C['input'], fg=C['text'],
                     insertbackground=C['text'],
                     font=(FONT_KR, 10), relief='flat',
                     highlightthickness=1,
                     highlightbackground=C['border'],
                     highlightcolor=C['primary'], show=show)
        e.pack(fill='x', ipady=7)
        if hint:
            tk.Label(parent, text=hint, bg=C['surface'],
                     fg=C['dim'], font=(FONT_KR, 8)).pack(anchor='w', pady=(2, 0))
        return e

    def _textbox(self, parent, label: str, height: int = 5,
                 hint: str = '') -> tk.Text:
        tk.Label(parent, text=label, bg=C['surface'],
                 fg=C['text'], font=(FONT_KR, 10)).pack(anchor='w', pady=(12, 3))
        t = tk.Text(parent, height=height, bg=C['input'],
                    fg=C['text'], insertbackground=C['text'],
                    font=(FONT_KR, 10), relief='flat',
                    highlightthickness=1,
                    highlightbackground=C['border'],
                    highlightcolor=C['primary'], wrap='word')
        t.pack(fill='x')
        if hint:
            tk.Label(parent, text=hint, bg=C['surface'],
                     fg=C['dim'], font=(FONT_KR, 8)).pack(anchor='w', pady=(3, 0))
        return t

    def _status_label(self, parent) -> tk.Label:
        lbl = tk.Label(parent, text='', bg=C['surface'],
                       fg=C['dim'], font=(FONT_KR, 9))
        lbl.pack(side='left', padx=(12, 0))
        return lbl

    # ── Tab 1: 이슈 정리글 ────────────────────────────────────────────────

    def _build_issue_tab(self, nb: ttk.Notebook):
        tab = tk.Frame(nb, bg=C['bg'], padx=16, pady=16)
        nb.add(tab, text='  📰  이슈 정리글  ')

        outer, card = self._card(tab)
        outer.pack(fill='both', expand=True)

        tk.Label(card, text="이슈 / 트렌드 정리글", bg=C['surface'],
                 fg=C['text'], font=(FONT_KR, 12, 'bold')).pack(anchor='w')
        tk.Label(card,
                 text="트렌딩 이슈를 배경 · 현황 · 다양한 시각 · 전망 구조로 자동 정리합니다. "
                      "SEO와 클릭률에 최적화된 글을 생성합니다.\n"
                      "🔥 트렌드 자동 작성: X · 네이버 뉴스 · 구글 트렌드를 분석해 주제를 자동 선정하고 네이버 인기 블로그 형식으로 작성합니다.",
                 bg=C['surface'], fg=C['dim'], font=(FONT_KR, 9),
                 wraplength=700, justify='left').pack(anchor='w', pady=(4, 0))

        tk.Frame(card, bg=C['border'], height=1).pack(fill='x', pady=14)

        self._issue_topic = self._entry(
            card, '이슈 주제  *',
            '예:  딥시크 AI 논란  /  2025 부동산 정책 변화  /  유튜브 쇼츠 알고리즘')
        self._issue_kw = self._entry(
            card, 'SEO 키워드  (선택 · 쉼표 구분)',
            '예:  AI, 인공지능, 딥러닝')

        # 버튼 영역
        btn_row = tk.Frame(card, bg=C['surface'])
        btn_row.pack(fill='x', pady=(20, 0))
        ttk.Button(btn_row, text='글 작성 및 발행  →',
                   style='Primary.TButton',
                   command=self._run_issue).pack(side='right')
        ttk.Button(btn_row, text='🔥  트렌드 자동 작성  →',
                   style='Trend.TButton',
                   command=self._run_issue_auto).pack(side='right', padx=(0, 8))
        self._issue_status = self._status_label(btn_row)

    def _run_issue(self):
        topic = self._issue_topic.get().strip()
        if not topic:
            messagebox.showwarning('입력 오류', '이슈 주제를 입력해주세요.', parent=self)
            return
        kw_raw = self._issue_kw.get().strip()
        keywords = [k.strip() for k in kw_raw.split(',')] if kw_raw else None

        self._set_status(self._issue_status, '글 생성 중…', C['dim'])
        self._log_msg(f"[이슈] 생성 시작: {topic}")

        def task():
            try:
                self._reload_config()
                from auto_blog.issue_writer import IssueWriter
                from auto_blog.naver_blog import NaverBlogClient
                post = IssueWriter().generate_post(topic, keywords)
                self._log_msg(f"  ▸ 제목: {post['title']}  ({len(post['content'])}자)")

                from auto_blog.post_saver import save_post
                saved = save_post(post['title'], post['content'])
                self._log_msg(f"  ▸ 로컬 저장: {saved}")

                NaverBlogClient().publish(post['title'], post['content'])
                self._log_msg("  ▸ 발행 완료!")
                self.after(0, lambda: self._set_status(
                    self._issue_status, '✓ 발행 완료', C['success']))
                self.after(0, lambda: messagebox.showinfo(
                    '완료', f"발행이 완료되었습니다!\n\n제목: {post['title']}", parent=self))
            except Exception as e:
                self._log_msg(f"  ✗ 오류: {e}")
                self.after(0, lambda: self._set_status(
                    self._issue_status, '✗ 오류 발생', C['error']))
                self.after(0, lambda: messagebox.showerror(
                    '오류', str(e), parent=self))

        threading.Thread(target=task, daemon=True).start()

    def _run_issue_auto(self):
        """트렌드를 자동 분석해 가장 조회수 높을 주제로 이슈 정리글을 작성·발행합니다."""
        self._set_status(self._issue_status, '트렌드 분석 중…', C['dim'])
        self._log_msg("[자동 트렌드] X · 네이버 뉴스 · 구글 트렌드 분석 시작...")

        def task():
            try:
                self._reload_config()
                from auto_blog.trend_finder import TrendFinder
                from auto_blog.issue_writer import IssueWriter
                from auto_blog.naver_blog import NaverBlogClient

                # 트렌드 주제 선정
                finder = TrendFinder()
                topic, keywords, reason = finder.get_best_topic()
                self._log_msg(f"  ▸ 선정 주제: {topic}")
                self._log_msg(f"  ▸ SEO 키워드: {', '.join(keywords)}")
                if reason:
                    self._log_msg(f"  ▸ 선정 이유: {reason[:60]}...")

                # 주제 입력칸에 선정된 주제 표시
                self.after(0, lambda: (
                    self._issue_topic.delete(0, 'end'),
                    self._issue_topic.insert(0, topic),
                ))

                self.after(0, lambda: self._set_status(
                    self._issue_status, '글 생성 중…', C['dim']))

                # 글 생성
                post = IssueWriter().generate_post(topic, keywords)
                self._log_msg(f"  ▸ 제목: {post['title']}  ({len(post['content'])}자)")

                from auto_blog.post_saver import save_post
                saved = save_post(post['title'], post['content'])
                self._log_msg(f"  ▸ 로컬 저장: {saved}")

                # 발행
                NaverBlogClient().publish(post['title'], post['content'])
                self._log_msg("  ▸ 발행 완료!")

                self.after(0, lambda: self._set_status(
                    self._issue_status, '✓ 자동 발행 완료', C['success']))
                self.after(0, lambda: messagebox.showinfo(
                    '자동 트렌드 발행 완료',
                    f"트렌드 분석 후 자동 발행 완료!\n\n"
                    f"주제: {topic}\n"
                    f"제목: {post['title']}",
                    parent=self))
            except Exception as e:
                self._log_msg(f"  ✗ 오류: {e}")
                self.after(0, lambda: self._set_status(
                    self._issue_status, '✗ 오류 발생', C['error']))
                self.after(0, lambda: messagebox.showerror(
                    '오류', str(e), parent=self))

        threading.Thread(target=task, daemon=True).start()

    # ── Tab 2: 내 생각 정리글 ─────────────────────────────────────────────

    def _build_opinion_tab(self, nb: ttk.Notebook):
        tab = tk.Frame(nb, bg=C['bg'], padx=16, pady=16)
        nb.add(tab, text='  💭  내 생각 정리글  ')

        outer, card = self._card(tab)
        outer.pack(fill='both', expand=True)

        tk.Label(card, text="내 생각 / 의견 정리글", bg=C['surface'],
                 fg=C['text'], font=(FONT_KR, 12, 'bold')).pack(anchor='w')
        tk.Label(card,
                 text="내 생각·경험을 자유롭게 입력하면 나의 목소리가 살아있는 글로 다듬어 드립니다. "
                      "임의 내용 추가 없이 입력한 내용을 충실히 반영합니다.",
                 bg=C['surface'], fg=C['dim'], font=(FONT_KR, 9),
                 wraplength=700, justify='left').pack(anchor='w', pady=(4, 0))

        tk.Frame(card, bg=C['border'], height=1).pack(fill='x', pady=14)

        self._opinion_topic = self._entry(
            card, '글 주제  *', '예:  AI 시대의 직업 변화  /  재택근무를 1년 해보고 느낀 것')
        self._opinion_thoughts = self._textbox(
            card, '내 생각 · 경험 · 핵심 포인트  *', height=6,
            hint='자유롭게 적어주세요. 짧은 메모나 키워드도 괜찮습니다. '
                 'GPT가 읽기 좋은 글로 다듬어 드립니다.')
        self._opinion_kw = self._entry(
            card, 'SEO 키워드  (선택 · 쉼표 구분)', '예:  AI, 직업, 미래')

        btn_row = tk.Frame(card, bg=C['surface'])
        btn_row.pack(fill='x', pady=(20, 0))
        ttk.Button(btn_row, text='글 작성 및 발행  →',
                   style='Primary.TButton',
                   command=self._run_opinion).pack(side='right')
        self._opinion_status = self._status_label(btn_row)

    def _run_opinion(self):
        topic = self._opinion_topic.get().strip()
        thoughts = self._opinion_thoughts.get('1.0', 'end').strip()
        if not topic:
            messagebox.showwarning('입력 오류', '글 주제를 입력해주세요.', parent=self)
            return
        if not thoughts:
            messagebox.showwarning('입력 오류', '내 생각·의견을 입력해주세요.', parent=self)
            return
        kw_raw = self._opinion_kw.get().strip()
        keywords = [k.strip() for k in kw_raw.split(',')] if kw_raw else None

        self._set_status(self._opinion_status, '글 생성 중…', C['dim'])
        self._log_msg(f"[의견] 생성 시작: {topic}")

        def task():
            try:
                self._reload_config()
                from auto_blog.opinion_writer import OpinionWriter
                from auto_blog.naver_blog import NaverBlogClient
                post = OpinionWriter().generate_post(topic, thoughts, keywords)
                self._log_msg(f"  ▸ 제목: {post['title']}  ({len(post['content'])}자)")

                from auto_blog.post_saver import save_post
                saved = save_post(post['title'], post['content'])
                self._log_msg(f"  ▸ 로컬 저장: {saved}")

                NaverBlogClient().publish(post['title'], post['content'])
                self._log_msg("  ▸ 발행 완료!")
                self.after(0, lambda: self._set_status(
                    self._opinion_status, '✓ 발행 완료', C['success']))
                self.after(0, lambda: messagebox.showinfo(
                    '완료', f"발행이 완료되었습니다!\n\n제목: {post['title']}", parent=self))
            except Exception as e:
                self._log_msg(f"  ✗ 오류: {e}")
                self.after(0, lambda: self._set_status(
                    self._opinion_status, '✗ 오류 발생', C['error']))
                self.after(0, lambda: messagebox.showerror('오류', str(e), parent=self))

        threading.Thread(target=task, daemon=True).start()

    # ── Tab 3: 스케줄 ──────────────────────────────────────────────────────

    def _build_schedule_tab(self, nb: ttk.Notebook):
        tab = tk.Frame(nb, bg=C['bg'], padx=16, pady=16)
        nb.add(tab, text='  🕐  스케줄  ')

        outer, card = self._card(tab)
        outer.pack(fill='both', expand=True)

        tk.Label(card, text="예약 자동 발행", bg=C['surface'],
                 fg=C['text'], font=(FONT_KR, 12, 'bold')).pack(anchor='w')
        tk.Label(card, text="매일 지정한 시각에 자동으로 글을 작성하고 발행합니다.",
                 bg=C['surface'], fg=C['dim'],
                 font=(FONT_KR, 9)).pack(anchor='w', pady=(4, 0))

        tk.Frame(card, bg=C['border'], height=1).pack(fill='x', pady=14)

        # 모드 선택
        tk.Label(card, text='글쓰기 모드', bg=C['surface'],
                 fg=C['text'], font=(FONT_KR, 10)).pack(anchor='w')
        self._sched_mode = tk.StringVar(value='issue')
        mode_row = tk.Frame(card, bg=C['surface'])
        mode_row.pack(anchor='w', pady=(4, 0))
        for val, lbl in [('issue', '📰  이슈 정리글'), ('opinion', '💭  내 생각 정리글')]:
            tk.Radiobutton(mode_row, text=lbl, variable=self._sched_mode, value=val,
                           bg=C['surface'], fg=C['text'], selectcolor=C['input'],
                           activebackground=C['surface'], activeforeground=C['text'],
                           font=(FONT_KR, 10),
                           command=self._update_sched_hint).pack(side='left', padx=(0, 20))

        # 발행 시각
        self._sched_time = self._entry(card, '발행 시각', '24시간 형식 · 예:  09:00  /  21:30')
        self._sched_time.insert(0, '09:00')

        # 주제 목록
        tk.Label(card, text='주제 목록', bg=C['surface'],
                 fg=C['text'], font=(FONT_KR, 10)).pack(anchor='w', pady=(12, 2))
        self._sched_hint = tk.Label(
            card,
            text='이슈 모드: 한 줄에 주제 하나  ( # 으로 시작하면 주석 )',
            bg=C['surface'], fg=C['dim'], font=(FONT_KR, 8))
        self._sched_hint.pack(anchor='w', pady=(0, 4))
        self._sched_topics = tk.Text(
            card, height=6, bg=C['input'], fg=C['text'],
            insertbackground=C['text'], font=(FONT_KR, 10), relief='flat',
            highlightthickness=1, highlightbackground=C['border'],
            highlightcolor=C['primary'], wrap='word')
        self._sched_topics.pack(fill='x')

        btn_row = tk.Frame(card, bg=C['surface'])
        btn_row.pack(fill='x', pady=(18, 0))
        self._sched_start_btn = ttk.Button(
            btn_row, text='스케줄 시작  →', style='Primary.TButton',
            command=self._start_schedule)
        self._sched_start_btn.pack(side='left', padx=(0, 8))
        self._sched_stop_btn = ttk.Button(
            btn_row, text='■  중지', style='Stop.TButton',
            command=self._stop_schedule, state='disabled')
        self._sched_stop_btn.pack(side='left')
        self._sched_status = self._status_label(btn_row)

    def _update_sched_hint(self):
        if self._sched_mode.get() == 'opinion':
            self._sched_hint.config(
                text="내 생각 모드: 한 줄에  주제:::내 생각  형식으로 입력하세요.\n"
                     "예)  AI 시대의 직업:::AI가 단순 반복 업무를 대체하고 있다. 판단력이 더 중요해졌다.")
        else:
            self._sched_hint.config(
                text='이슈 모드: 한 줄에 주제 하나  ( # 으로 시작하면 주석 )')

    def _start_schedule(self):
        run_time = self._sched_time.get().strip()
        topics_raw = self._sched_topics.get('1.0', 'end').strip()
        mode = self._sched_mode.get()

        if not run_time:
            messagebox.showwarning('입력 오류', '발행 시각을 입력해주세요.', parent=self)
            return
        if not topics_raw:
            messagebox.showwarning('입력 오류', '주제 목록을 입력해주세요.', parent=self)
            return

        # 임시 파일에 주제 목록 저장
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', suffix='.txt', delete=False)
        tmp.write(topics_raw)
        tmp.close()
        self._tmp_topics = tmp.name

        self._sched_running = True
        self._sched_start_btn.config(state='disabled')
        self._sched_stop_btn.config(state='normal')
        mode_label = '이슈 정리' if mode == 'issue' else '내 생각 정리'
        self._set_status(self._sched_status,
                         f'실행 중  (매일 {run_time} · {mode_label})', C['success'])
        self._log_msg(f"[스케줄] 시작: 매일 {run_time} · 모드={mode}")

        def run():
            from auto_blog.scheduler import run_scheduler
            run_scheduler(self._tmp_topics, run_time, mode)

        threading.Thread(target=run, daemon=True).start()

    def _stop_schedule(self):
        import schedule as _sched
        _sched.clear()
        self._sched_running = False
        self._sched_start_btn.config(state='normal')
        self._sched_stop_btn.config(state='disabled')
        self._set_status(self._sched_status, '중지됨', C['dim'])
        self._log_msg("[스케줄] 중지됨")

    # ── Tab 4: 설정 ────────────────────────────────────────────────────────

    def _build_settings_tab(self, nb: ttk.Notebook):
        tab = tk.Frame(nb, bg=C['bg'], padx=16, pady=16)
        nb.add(tab, text='  ⚙  설정  ')

        # ── 하단 저장 버튼 (항상 보이도록 먼저 배치) ──
        save_bar = tk.Frame(tab, bg=C['surface'], padx=18, pady=10)
        save_bar.pack(side='bottom', fill='x', pady=(10, 0))
        ttk.Button(save_bar, text='설정 저장  →', style='Primary.TButton',
                   command=self._save_settings).pack(side='left')
        self._cfg_status = self._status_label(save_bar)
        tk.Label(save_bar, text=f'저장 위치: {ENV_PATH.name}',
                 bg=C['surface'], fg=C['dim'],
                 font=(FONT_KR, 8)).pack(side='right')

        # ── 스크롤 가능한 설정 카드 ──
        outer = tk.Frame(tab, bg=C['border'], padx=1, pady=1)
        outer.pack(fill='both', expand=True)

        canvas = tk.Canvas(outer, bg=C['surface'], highlightthickness=0, bd=0)
        card = tk.Frame(canvas, bg=C['surface'], padx=24, pady=20)

        card.bind('<Configure>',
                  lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        win_id = canvas.create_window((0, 0), window=card, anchor='nw')
        canvas.bind('<Configure>',
                    lambda e: canvas.itemconfigure(win_id, width=e.width))
        canvas.pack(side='left', fill='both', expand=True)

        # 마우스 휠 스크롤 (Linux)
        def _on_enter(e):
            canvas.bind_all('<Button-4>',
                            lambda ev: canvas.yview_scroll(-1, 'units'))
            canvas.bind_all('<Button-5>',
                            lambda ev: canvas.yview_scroll(1, 'units'))

        def _on_leave(e):
            canvas.unbind_all('<Button-4>')
            canvas.unbind_all('<Button-5>')

        canvas.bind('<Enter>', _on_enter)
        canvas.bind('<Leave>', _on_leave)

        # ── 설정 항목 ──
        tk.Label(card, text="API / 계정 설정", bg=C['surface'],
                 fg=C['text'], font=(FONT_KR, 12, 'bold')).pack(anchor='w')
        tk.Label(card,
                 text="설정은 프로그램 폴더의 .env 파일에 저장됩니다.",
                 bg=C['surface'], fg=C['dim'], font=(FONT_KR, 9)).pack(anchor='w', pady=(4, 0))

        tk.Frame(card, bg=C['border'], height=1).pack(fill='x', pady=14)

        self._cfg_openai = self._entry(
            card, 'OpenAI API Key  *',
            'platform.openai.com 에서 발급', show='*')
        self._cfg_naver_client_id = self._entry(
            card, 'Naver Client ID  (검색 API · 선택)',
            '네이버 개발자 센터 (developers.naver.com) 에서 발급')
        self._cfg_naver_client_secret = self._entry(
            card, 'Naver Client Secret  (검색 API · 선택)', '', show='*')
        self._cfg_naver_id = self._entry(
            card, '네이버 아이디  *',
            '블로그 발행용 네이버 로그인 아이디')
        self._cfg_naver_pw = self._entry(
            card, '네이버 비밀번호  *',
            'Selenium 자동 로그인에 사용됩니다.', show='*')

        self._load_settings()

    def _load_settings(self):
        pairs = [
            (self._cfg_openai,              'OPENAI_API_KEY'),
            (self._cfg_naver_client_id,     'NAVER_CLIENT_ID'),
            (self._cfg_naver_client_secret, 'NAVER_CLIENT_SECRET'),
            (self._cfg_naver_id,            'NAVER_ID'),
            (self._cfg_naver_pw,            'NAVER_PASSWORD'),
        ]
        for widget, key in pairs:
            widget.delete(0, 'end')
            widget.insert(0, os.getenv(key, ''))

    def _save_settings(self):
        lines = [
            f"OPENAI_API_KEY={self._cfg_openai.get().strip()}",
            f"NAVER_CLIENT_ID={self._cfg_naver_client_id.get().strip()}",
            f"NAVER_CLIENT_SECRET={self._cfg_naver_client_secret.get().strip()}",
            f"NAVER_ID={self._cfg_naver_id.get().strip()}",
            f"NAVER_PASSWORD={self._cfg_naver_pw.get().strip()}",
            "GPT_MODEL=gpt-5.2",
            "GPT_MAX_COMPLETION_TOKENS=4096",
            "GPT_REASONING_EFFORT=medium",
        ]
        ENV_PATH.write_text('\n'.join(lines), encoding='utf-8')
        self._reload_config()
        self._set_status(self._cfg_status, '✓ 저장 완료', C['success'])
        self._log_msg(f"[설정] .env 파일 저장 완료: {ENV_PATH}")
        messagebox.showinfo('저장 완료', '설정이 저장되었습니다.', parent=self)

    # ── 공통 유틸 ──────────────────────────────────────────────────────────

    def _reload_config(self):
        """저장된 .env를 다시 읽어 os.environ과 Config 클래스를 갱신합니다."""
        if ENV_PATH.exists():
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=ENV_PATH, override=True)
        try:
            from auto_blog.config import Config
            Config.OPENAI_API_KEY           = os.getenv('OPENAI_API_KEY', '')
            Config.NAVER_CLIENT_ID          = os.getenv('NAVER_CLIENT_ID', '')
            Config.NAVER_CLIENT_SECRET      = os.getenv('NAVER_CLIENT_SECRET', '')
            Config.NAVER_ID                 = os.getenv('NAVER_ID', '')
            Config.NAVER_PASSWORD           = os.getenv('NAVER_PASSWORD', '')
            Config.GPT_MODEL                = os.getenv('GPT_MODEL', 'gpt-5.2')
            Config.GPT_MAX_COMPLETION_TOKENS = int(os.getenv('GPT_MAX_COMPLETION_TOKENS', '4096'))
            Config.GPT_REASONING_EFFORT     = os.getenv('GPT_REASONING_EFFORT', 'medium')
        except Exception:
            pass

    def _set_status(self, label: tk.Label, text: str, color: str):
        label.config(text=text, fg=color)

    def _log_msg(self, msg: str):
        self._log_q.put(msg)

    def _poll_log(self):
        try:
            while True:
                msg = self._log_q.get_nowait()
                self._log_box.config(state='normal')
                self._log_box.insert('end', msg + '\n')
                self._log_box.see('end')
                self._log_box.config(state='disabled')
        except queue.Empty:
            pass
        self.after(150, self._poll_log)

    def _clear_log(self):
        self._log_box.config(state='normal')
        self._log_box.delete('1.0', 'end')
        self._log_box.config(state='disabled')


# ── 진입점 ────────────────────────────────────────────────────────────────────

def main():
    app = AutoBlogApp()
    app.mainloop()


if __name__ == '__main__':
    main()
