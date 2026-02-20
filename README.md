# auto_blog

OpenAI GPT를 활용하여 블로그 글을 자동으로 작성하고, Selenium으로 네이버 블로그에 자동 발행하는 프로그램입니다.

## 기능

- **이슈 정리글** (`issue`): 트렌딩 이슈를 배경·현황·다양한 시각·전망 구조로 정리한 SEO 최적화 글 생성
- **내 생각 정리글** (`opinion`): 내 생각·경험을 입력하면 나의 목소리가 살아있는 글로 다듬어줌
- **자동 트렌드 분석** (`auto`): X, 네이버 뉴스, 구글 트렌드 등을 분석해 최적 주제를 자동 선정 후 발행
- **범용 글쓰기** (`write`): 주제만 입력하면 일반 정보성 블로그 글 생성
- **GUI 앱**: Tkinter 기반 다크 테마 GUI (미리보기, 카테고리 선택, 프로그레스 바, GPT 설정)
- **Selenium 자동 발행**: 네이버 SmartEditor ONE iframe 제어로 제목·본문 입력 및 발행
- **로컬 저장**: 발행 전 글을 `saved_posts/` 폴더에 HTML로 자동 백업
- **스케줄링**: 매일 지정 시각에 자동으로 글 작성·발행
- **SEO 키워드** 지정 가능
- **카테고리 선택**: 블로그 게시판 카테고리 지정 발행

## 설치

### 필수 요구 사항

- Python 3.10+
- Google Chrome 브라우저 (Selenium 자동 발행에 사용)

### 패키지 설치

```bash
pip install -r requirements.txt
```

주요 의존성:
- `openai` — GPT API 호출
- `selenium` + `webdriver-manager` — 네이버 블로그 자동 발행
- `schedule` — 예약 발행
- `python-dotenv` — 환경 변수 관리
- `pyperclip` — 클립보드 붙여넣기 (에디터 입력용)
- `pyinstaller` — exe 빌드 (선택)

## 설정

1. `.env.example`을 `.env`로 복사합니다:
```bash
cp .env.example .env
```

2. `.env` 파일에 API 키와 계정 정보를 설정합니다:
```
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# Naver 검색 API (선택 — developers.naver.com 에서 발급)
NAVER_CLIENT_ID=your_naver_client_id_here
NAVER_CLIENT_SECRET=your_naver_client_secret_here

# Naver 로그인 정보 (블로그 발행용 — Selenium 자동 로그인)
NAVER_ID=your_naver_id_here
NAVER_PASSWORD=your_naver_password_here

# GPT 모델 설정
GPT_MODEL=gpt-4.1
GPT_MAX_COMPLETION_TOKENS=4096
GPT_REASONING_EFFORT=medium
```

### OpenAI API 키 발급

[OpenAI Platform](https://platform.openai.com)에서 API 키를 발급받습니다.

### 네이버 검색 API (선택)

트렌드 분석 기능(`auto` 명령) 사용 시 필요합니다.
1. [네이버 개발자 센터](https://developers.naver.com)에서 애플리케이션을 등록합니다.
2. **사용 API**에서 `검색`을 선택합니다.
3. 발급된 Client ID와 Client Secret을 `.env`에 입력합니다.

### 네이버 블로그 발행

블로그 발행은 Selenium을 통한 자동 로그인 + SmartEditor ONE 제어 방식으로 동작합니다.
- `.env`에 `NAVER_ID`와 `NAVER_PASSWORD`를 설정하면 자동으로 로그인됩니다.
- Chrome 프로필이 `~/.auto_blog_chrome_profile`에 저장되어 세션이 유지됩니다.
- 디버깅용 스크린샷이 `logs/` 폴더에 자동 저장됩니다.

## 사용법

### GUI 모드 (권장)

```bash
python gui.py
```

GUI에서 제공하는 기능:
- **이슈 정리글 탭**: 주제 입력 → 미리보기 → 발행
- **내 생각 정리글 탭**: 주제 + 내 생각 입력 → 미리보기 → 발행
- **트렌드 자동 작성**: 버튼 한 번으로 트렌드 분석 → 글 생성 → 발행
- **스케줄 탭**: 예약 발행 설정
- **설정 탭**: API 키, 네이버 계정, GPT 모델 설정을 GUI에서 직접 관리
- **미리보기 팝업**: 발행 전 생성된 글 확인
- **카테고리 선택**: 드롭다운으로 게시판 선택
- **프로그레스 바**: 작업 진행 상태 표시
- **실행 로그**: 실시간 로그 확인 / 복사

### CLI 모드

#### 이슈 정리글 (조회수용)

트렌딩 이슈를 배경·현황·다양한 시각·전망 순으로 정리한 글을 작성합니다.

```bash
python -m auto_blog.main issue "딥시크 AI 논란"
```

키워드와 카테고리를 지정할 수 있습니다:

```bash
python -m auto_blog.main issue "2025 부동산 정책 변화" -k 부동산 아파트 청약 -c "경제"
```

#### 자동 트렌드 분석 + 발행

주제 입력 없이 트렌드를 자동 분석해 최적 주제를 선정하고 글을 작성·발행합니다.

```bash
python -m auto_blog.main auto
```

#### 내 생각 정리글 (의견글)

내 생각·경험을 자유롭게 입력하면 나의 목소리가 살아있는 글로 다듬어줍니다.

```bash
python -m auto_blog.main opinion "AI 시대의 직업 변화" \
  "AI가 단순 반복 업무를 빠르게 대체하고 있다. 내 업무도 많이 바뀌었다. 하지만 판단력과 기획력은 아직 사람이 낫다고 생각한다."
```

#### 범용 글쓰기

```bash
python -m auto_blog.main write "파이썬 기초 문법 정리" -k 파이썬 프로그래밍 코딩
```

#### 스케줄링 모드

매일 지정 시각에 자동으로 글을 발행합니다.

**이슈 정리글 스케줄링:**

```bash
# issue_topics.txt (한 줄에 주제 하나, #으로 주석 처리 가능)
# 딥시크 AI 논란
# 2025 최저임금 인상 영향

python -m auto_blog.main schedule issue_topics.txt -t 09:00 --mode issue
```

**내 생각 정리글 스케줄링:**

opinion 모드는 `주제:::생각` 형식으로 파일을 작성합니다:

```bash
# opinion_topics.txt
AI 시대의 직업 변화:::AI가 단순 반복 업무를 대체하고 있다. 판단력이 더 중요해졌다.
재택근무의 장단점:::집중이 잘 되지만 협업이 어렵다. 루틴 관리가 핵심이다.

python -m auto_blog.main schedule opinion_topics.txt -t 20:00 --mode opinion
```

## 프로젝트 구조

```
auto_blog/
├── auto_blog/
│   ├── __init__.py
│   ├── config.py          # 환경 변수 설정 관리 (GPT 모델 설정 포함)
│   ├── main.py            # CLI 진입점
│   ├── issue_writer.py    # 이슈 정리글 생성 (SEO 최적화)
│   ├── opinion_writer.py  # 내 생각 정리글 생성 (개인 의견)
│   ├── ai_writer.py       # 범용 글쓰기 + 공용 제목 파서
│   ├── trend_finder.py    # 트렌드 자동 분석 및 주제 선정
│   ├── naver_blog.py      # Selenium 네이버 블로그 자동 발행
│   ├── post_saver.py      # 생성된 글 로컬 HTML 저장
│   └── scheduler.py       # 예약 발행 스케줄러
├── gui.py                 # Tkinter GUI 앱 (다크 테마)
├── saved_posts/           # 생성된 글 로컬 백업 (자동 생성)
├── logs/                  # 로그 파일 + 디버깅 스크린샷
├── .env.example           # 환경 변수 예시
├── .gitignore
├── requirements.txt
└── README.md
```

## 글쓰기 모드 비교

| 모드 | 명령어 | 특징 | 입력 |
|------|--------|------|------|
| 이슈 정리 | `issue` | SEO 최적화, 다각도 분석, 후킹 제목 | 이슈 주제 |
| 자동 트렌드 | `auto` | 트렌드 자동 분석 → 주제 선정 → 발행 | 입력 불필요 |
| 내 생각 정리 | `opinion` | 1인칭 개인 목소리, 친근한 문체 | 주제 + 핵심 생각 |
| 범용 | `write` | 일반 정보성 블로그 글 | 주제 |

## GPT 모델 설정

`.env` 파일 또는 GUI 설정 탭에서 GPT 모델을 변경할 수 있습니다:

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `GPT_MODEL` | `gpt-4.1` | 사용할 GPT 모델 (gpt-4.1, gpt-4.1-mini 등) |
| `GPT_MAX_COMPLETION_TOKENS` | `4096` | 최대 생성 토큰 수 |
| `GPT_REASONING_EFFORT` | `medium` | 추론 강도 (low / medium / high) |

## 블로그 카테고리

다음 카테고리를 지정할 수 있습니다 (CLI `-c` 옵션 또는 GUI 드롭다운):

- **관측일지**: 일상, 사진, 음악
- **탐구실**: 로봇, 경제, 기타
- **노트**: 영어 공부, 일본어 공부, 끄적, AI글
