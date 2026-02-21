"""실제 뉴스 및 블로그 자료 수집 모듈

네이버 검색 API를 사용해 실제 뉴스 기사와 블로그 글을 검색합니다.
이슈 글 작성 시 팩트 기반 콘텐츠를 생성하기 위한 자료를 수집합니다.
"""

import html as html_lib
import logging
import re
from datetime import datetime

import requests

from .config import Config

logger = logging.getLogger(__name__)

_NAVER_API_BASE = "https://openapi.naver.com/v1/search"


def _strip_html(text: str) -> str:
    """HTML 태그와 엔티티를 제거합니다."""
    text = re.sub(r"<[^>]+>", "", text)
    return html_lib.unescape(text).strip()


def _naver_headers() -> dict:
    """네이버 검색 API 인증 헤더를 반환합니다."""
    return {
        "X-Naver-Client-Id": Config.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": Config.NAVER_CLIENT_SECRET,
    }


def _has_naver_api() -> bool:
    """네이버 검색 API 키가 설정되어 있는지 확인합니다."""
    return bool(Config.NAVER_CLIENT_ID and Config.NAVER_CLIENT_SECRET)


# ── 뉴스 검색 ─────────────────────────────────────────────────────────────


def fetch_news(topic: str, count: int = 15) -> list[dict]:
    """네이버 뉴스 검색 API로 실제 뉴스 기사를 수집합니다.

    Args:
        topic: 검색할 주제
        count: 가져올 기사 수 (최대 100)

    Returns:
        [{"title", "description", "source", "link", "date"}] 형태의 리스트
    """
    if not _has_naver_api():
        logger.warning("NAVER_CLIENT_ID/SECRET 미설정 → 뉴스 검색 건너뜀")
        return []

    try:
        resp = requests.get(
            f"{_NAVER_API_BASE}/news.json",
            headers=_naver_headers(),
            params={
                "query": topic,
                "display": min(count, 100),
                "sort": "date",  # 최신순
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("뉴스 검색 실패: %s", e)
        return []

    articles = []
    for item in data.get("items", []):
        title = _strip_html(item.get("title", ""))
        desc = _strip_html(item.get("description", ""))
        link = item.get("originallink") or item.get("link", "")

        # 언론사 추출 (originallink 도메인에서)
        source = _extract_source(link)

        # 날짜 파싱
        raw_date = item.get("pubDate", "")
        date_str = _parse_pub_date(raw_date)

        if title:
            articles.append({
                "title": title,
                "description": desc,
                "source": source,
                "link": link,
                "date": date_str,
            })

    logger.info("뉴스 검색 완료: '%s' → %d건", topic, len(articles))
    return articles


def _extract_source(url: str) -> str:
    """URL에서 언론사 이름을 추출합니다."""
    source_map = {
        "chosun.com": "조선일보",
        "joongang.co.kr": "중앙일보",
        "donga.com": "동아일보",
        "hani.co.kr": "한겨레",
        "khan.co.kr": "경향신문",
        "hankyung.com": "한국경제",
        "mk.co.kr": "매일경제",
        "sedaily.com": "서울경제",
        "yna.co.kr": "연합뉴스",
        "ytn.co.kr": "YTN",
        "sbs.co.kr": "SBS",
        "kbs.co.kr": "KBS",
        "mbc.co.kr": "MBC",
        "jtbc.co.kr": "JTBC",
        "news1.kr": "뉴스1",
        "newsis.com": "뉴시스",
        "edaily.co.kr": "이데일리",
        "mt.co.kr": "머니투데이",
        "hankookilbo.com": "한국일보",
        "munhwa.com": "문화일보",
        "bbc.com": "BBC",
        "bbc.co.uk": "BBC",
        "cnn.com": "CNN",
        "reuters.com": "Reuters",
        "apnews.com": "AP",
        "nhk.or.jp": "NHK",
        "nytimes.com": "NYT",
        "washingtonpost.com": "Washington Post",
        "bloomberg.com": "Bloomberg",
    }
    url_lower = url.lower()
    for domain, name in source_map.items():
        if domain in url_lower:
            return name
    # 도메인 추출 fallback
    m = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1) if m else "기타"


def _parse_pub_date(raw: str) -> str:
    """RFC 822 등의 날짜 형식을 'YYYY-MM-DD' 로 변환합니다."""
    try:
        # "Mon, 20 Jan 2025 09:30:00 +0900" 형식
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(raw)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return raw[:10] if len(raw) >= 10 else raw


# ── 블로그 검색 (스타일 참조용) ────────────────────────────────────────────


def fetch_blog_references(topic: str, count: int = 5) -> list[dict]:
    """네이버 블로그 검색 API로 인기 블로그 글을 수집합니다 (스타일 참조용).

    Args:
        topic: 검색할 주제
        count: 가져올 글 수

    Returns:
        [{"title", "description", "blogger", "date"}] 형태의 리스트
    """
    if not _has_naver_api():
        logger.warning("NAVER_CLIENT_ID/SECRET 미설정 → 블로그 검색 건너뜀")
        return []

    try:
        resp = requests.get(
            f"{_NAVER_API_BASE}/blog.json",
            headers=_naver_headers(),
            params={
                "query": topic,
                "display": min(count, 20),
                "sort": "sim",  # 관련도순 (인기 글이 상단)
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("블로그 검색 실패: %s", e)
        return []

    blogs = []
    for item in data.get("items", []):
        title = _strip_html(item.get("title", ""))
        desc = _strip_html(item.get("description", ""))
        blogger = item.get("bloggername", "")
        date = item.get("postdate", "")

        if title:
            blogs.append({
                "title": title,
                "description": desc,
                "blogger": blogger,
                "date": date,
            })

    logger.info("블로그 검색 완료: '%s' → %d건", topic, len(blogs))
    return blogs


# ── GPT 프롬프트용 컨텍스트 포맷 ──────────────────────────────────────────


def format_news_context(articles: list[dict]) -> str:
    """수집된 뉴스 기사를 GPT 프롬프트에 포함할 텍스트로 포맷합니다."""
    if not articles:
        return ""

    lines = [f"━━ 실제 뉴스 자료 ({len(articles)}건) ━━"]
    for i, a in enumerate(articles, 1):
        lines.append(
            f"\n[기사 {i}] ({a['source']}, {a['date']})\n"
            f"제목: {a['title']}\n"
            f"내용: {a['description']}"
        )
    return "\n".join(lines)


def format_blog_context(blogs: list[dict]) -> str:
    """수집된 블로그 글을 GPT 프롬프트에 포함할 텍스트로 포맷합니다."""
    if not blogs:
        return ""

    lines = [f"━━ 참고 블로그 글 ({len(blogs)}건) ━━"]
    for i, b in enumerate(blogs, 1):
        lines.append(
            f"\n[블로그 {i}] {b['title']}\n"
            f"내용 요약: {b['description']}"
        )
    return "\n".join(lines)
