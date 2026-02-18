# auto_blog

Claude AI를 활용하여 블로그 글을 자동으로 작성하고 네이버 블로그에 업로드하는 프로그램입니다.

## 기능

- Claude API로 주제 기반 블로그 글 자동 생성
- 네이버 블로그 API를 통한 자동 발행
- SEO 키워드 지정 가능
- 스케줄링을 통한 예약 발행 (매일 지정 시각)
- CLI 기반 수동 실행

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

### 수동 실행 (글 하나 작성 및 발행)

```bash
python -m auto_blog.main write "2025년 봄 여행지 추천"
```

키워드를 지정할 수도 있습니다:

```bash
python -m auto_blog.main write "건강한 식단 관리법" -k 다이어트 식단 건강식
```

### 스케줄링 모드

주제 목록 파일을 만들고 매일 자동 발행합니다:

```bash
# topics.txt 파일 (한 줄에 주제 하나)
# 2025년 트렌드 분석
# 재택근무 생산성 높이는 방법
# 초보자를 위한 투자 가이드

python -m auto_blog.main schedule topics.txt -t 09:00
```

## 프로젝트 구조

```
auto_blog/
├── auto_blog/
│   ├── __init__.py
│   ├── config.py        # 환경 변수 설정 관리
│   ├── ai_writer.py     # Claude API 연동 (글 생성)
│   ├── naver_blog.py    # 네이버 블로그 API 연동
│   ├── scheduler.py     # 스케줄링 모듈
│   └── main.py          # CLI 진입점
├── logs/                # 로그 파일 디렉토리
├── .env.example         # 환경 변수 예시
├── .gitignore
├── requirements.txt
└── README.md
```
