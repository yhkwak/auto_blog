# auto_blog

Claude AI를 활용하여 블로그 글을 자동으로 작성하고 네이버 블로그에 업로드하는 프로그램입니다.

## 기능

- **이슈 정리글** (`issue`): 트렌딩 이슈를 다각도로 정리한 조회수 최적화 글 생성
- **내 생각 정리글** (`opinion`): 내 생각·경험을 입력하면 목소리가 살아있는 글로 다듬어줌
- 네이버 블로그 API를 통한 자동 발행
- SEO 키워드 지정 가능
- 스케줄링을 통한 예약 발행 (매일 지정 시각)

## 설치

```bash
pip install -r requirements.txt
```

## 설정

1. `.env.example`을 `.env`로 복사합니다:
```bash
cp .env.example .env
```

2. `.env` 파일에 API 키를 설정합니다:
```
ANTHROPIC_API_KEY=your_anthropic_api_key
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
NAVER_ACCESS_TOKEN=your_naver_access_token
```

### 네이버 API 키 발급

1. [네이버 개발자 센터](https://developers.naver.com)에서 애플리케이션을 등록합니다.
2. **사용 API**에서 `블로그`를 선택합니다.
3. **Callback URL**에 `http://localhost:8080/callback`을 입력합니다.
4. 발급된 Client ID와 Client Secret을 `.env`에 입력합니다.
5. 아래 인증 명령어로 Access Token을 발급받습니다:

```bash
python -m auto_blog.main auth
```

### Anthropic API 키 발급

[Anthropic Console](https://console.anthropic.com)에서 API 키를 발급받습니다.

## 사용법

### 이슈 정리글 (조회수용)

트렌딩 이슈를 배경·현황·다양한 시각·전망 순으로 정리한 글을 작성합니다.

```bash
python -m auto_blog.main issue "딥시크 AI 논란"
```

키워드를 지정해 SEO를 강화할 수 있습니다:

```bash
python -m auto_blog.main issue "2025 부동산 정책 변화" -k 부동산 아파트 청약
```

### 내 생각 정리글 (의견글)

내 생각·경험을 자유롭게 입력하면 나의 목소리가 살아있는 글로 다듬어줍니다.

```bash
python -m auto_blog.main opinion "AI 시대의 직업 변화" \
  "AI가 단순 반복 업무를 빠르게 대체하고 있다. 내 업무도 많이 바뀌었다. 하지만 판단력과 기획력은 아직 사람이 낫다고 생각한다. 앞으로는 AI를 잘 다루는 능력이 핵심 역량이 될 것 같다."
```

### 스케줄링 모드

매일 지정 시각에 자동으로 글을 발행합니다.

#### 이슈 정리글 스케줄링

```bash
# issue_topics.txt (한 줄에 주제 하나, #으로 주석 처리 가능)
# 딥시크 AI 논란
# 2025 최저임금 인상 영향
# 유튜브 쇼츠 알고리즘 변화

python -m auto_blog.main schedule issue_topics.txt -t 09:00 --mode issue
```

#### 내 생각 정리글 스케줄링

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
│   ├── config.py          # 환경 변수 설정 관리
│   ├── issue_writer.py    # 이슈 정리글 생성 (조회수 최적화)
│   ├── opinion_writer.py  # 내 생각 정리글 생성 (개인 의견)
│   ├── ai_writer.py       # 범용 글쓰기 (레거시)
│   ├── naver_blog.py      # 네이버 블로그 API 연동
│   ├── scheduler.py       # 스케줄링 모듈
│   └── main.py            # CLI 진입점
├── logs/                  # 로그 파일 디렉토리
├── .env.example           # 환경 변수 예시
├── .gitignore
├── requirements.txt
└── README.md
```

## 글쓰기 모드 비교

| 모드 | 명령어 | 특징 | 입력 |
|------|--------|------|------|
| 이슈 정리 | `issue` | SEO 최적화, 다각도 분석, 후킹 제목 | 이슈 주제만 입력 |
| 내 생각 정리 | `opinion` | 1인칭 개인 목소리, 친근한 문체 | 주제 + 핵심 생각 입력 |
| 범용 | `write` | 일반 정보성 블로그 글 | 주제만 입력 |
