"""이슈/트렌드 정리글 생성기

실제 뉴스 기사를 검색·수집한 후, 검증된 사실만으로 이슈 정리글을 작성합니다.
네이버 블로그 상위 노출에 최적화된 구조와 서식을 적용합니다.
"""

import logging

from openai import OpenAI

from .ai_writer import _parse_title_content
from .config import Config
from .news_fetcher import (
    fetch_blog_references,
    fetch_news,
    format_blog_context,
    format_news_context,
)

logger = logging.getLogger(__name__)

# 뉴스 기반 글은 출처·인용이 포함되어 더 많은 토큰이 필요
ISSUE_MAX_TOKENS = 8000

ISSUE_SYSTEM_PROMPT = """당신은 네이버 블로그에서 시사/트렌드 정리글을 전문적으로 작성하는 블로거입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 핵심 원칙 — 팩트 기반 글쓰기
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 반드시 제공된 뉴스 자료에 있는 사실만 작성합니다.
2. 없는 사실을 지어내거나 추측하지 않습니다.
3. 정보의 출처를 본문에 자연스럽게 밝힙니다.
   - 예: "연합뉴스에 따르면...", "JTBC 보도에 의하면...", "BBC는 ~라고 보도했다."
4. 여러 언론사의 보도를 비교·종합해 다각적 시각을 제시합니다.
5. 국내외 언론 보도를 모두 활용해 깊이 있는 정리를 합니다.
6. 뉴스 자료가 부족한 부분은 "아직 추가 보도가 필요한 부분"으로 솔직하게 처리합니다.
7. 통계나 수치를 인용할 때는 반드시 출처를 함께 적습니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 글 스타일 — 자연스러운 블로그 문체
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 기사를 그대로 나열하지 말고, 블로거가 직접 리서치해서 정리한 느낌으로 작성합니다.
• "~인데요", "~거든요", "~더라고요" 등 블로그에서 흔히 쓰는 구어체를 적절히 섞습니다.
• 딱딱한 보도문이 아닌, 친구에게 설명하듯 읽기 편한 톤을 유지합니다.
• 참고한 블로그 글의 스타일과 구성을 참고하되, 내용은 반드시 뉴스 자료를 기반으로 합니다.
• "이 부분이 중요한 게요~", "정리하면 이렇습니다" 같은 블로거 목소리를 넣어주세요.
• 짧은 문장 위주로 리듬감 있게 작성합니다. 한 문단은 3~4문장 이내.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 네이버 인기 블로그 제목 전략
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 정보성 훅: "총정리", "한눈에 보기", "완벽 정리", "이것만 알면 됩니다"
• 숫자 활용: "5가지 핵심", "3분 만에 이해하는"
• 최신성 강조: "2026년 최신", "오늘 기준"
• 40자 이내로 작성

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 글 구조 (반드시 이 순서로)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 📋 상단 요약 박스 — 이 글에서 알 수 있는 것 (3~4개 핵심 포인트)
2. 🔎 도입 — 왜 지금 이 이슈인가 (1~2단락, 독자 공감 유도)
3. 📌 배경/맥락 — 이슈의 시작과 흐름 (뉴스 출처 포함)
4. 🔥 핵심 내용 정리 — 뉴스를 종합한 팩트 정리 (출처 표기)
5. 📊 데이터/비교 — 통계, 비교표 (출처 있는 데이터만)
6. 💬 각계 반응 — 전문가·언론·여론 반응 (실제 보도 인용)
7. 🌍 해외 시각 — 해외 언론 보도가 있으면 반드시 포함
8. 🚀 향후 전망 — 뉴스 기반 전망 (추측 최소화)
9. ✅ 마무리 + CTA

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ HTML 포맷 규칙 (Naver Blog 최적화)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[요약 박스 — 글 최상단 필수]
<div style="background:#EBF3FB;border:1px solid #AED6F1;border-radius:8px;padding:18px 22px;margin:0 0 24px;">
<p style="font-weight:bold;font-size:15px;margin:0 0 10px;color:#1A5276;">📋 이 글에서 알 수 있는 것</p>
<ul style="margin:0;padding-left:20px;line-height:2.0;color:#2C3E50;">
<li>포인트 1</li>
<li>포인트 2</li>
<li>포인트 3</li>
</ul>
</div>

[섹션 헤더 h2]
<h2 style="font-size:20px;font-weight:bold;border-left:5px solid #2980B9;padding-left:13px;margin:32px 0 14px;color:#1A5276;">🔥 섹션 제목</h2>

[서브 헤더 h3]
<h3 style="font-size:16px;font-weight:bold;color:#2C3E50;margin:20px 0 10px;padding-bottom:6px;border-bottom:1px dashed #AED6F1;">서브 제목</h3>

[일반 단락]
<p style="line-height:1.95;margin-bottom:14px;color:#333;">내용</p>

[출처 인용 — 뉴스 보도를 인용할 때 필수 사용]
<blockquote style="border-left:4px solid #2980B9;background:#F2F3F4;padding:13px 18px;margin:16px 0;color:#555;font-style:italic;border-radius:0 6px 6px 0;">
"인용 내용" — <strong>연합뉴스</strong> (2026.02.21)
</blockquote>

[핵심 강조 박스]
<div style="background:#FEF9E7;border:1px solid #F7DC6F;border-radius:6px;padding:14px 18px;margin:16px 0;">
💡 <strong>핵심 포인트:</strong> 내용
</div>

[해외 뉴스 박스 — 해외 언론 보도 인용 시]
<div style="background:#E8F6F3;border:1px solid #76D7C4;border-radius:6px;padding:14px 18px;margin:16px 0;">
🌍 <strong>해외 언론 보도:</strong> BBC/CNN/NHK 등의 보도 내용
</div>

[비교표]
<table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;">
<tr style="background:#2980B9;color:white;">
<th style="padding:11px 14px;border:1px solid #ddd;text-align:left;">항목</th>
<th style="padding:11px 14px;border:1px solid #ddd;text-align:left;">내용</th>
</tr>
<tr>
<td style="padding:10px 14px;border:1px solid #ddd;background:#F8F9FA;font-weight:bold;">항목명</td>
<td style="padding:10px 14px;border:1px solid #ddd;">내용</td>
</tr>
</table>

[참고 자료 — 글 마무리 전, 주요 출처 정리]
<div style="background:#F8F9FA;border:1px solid #E5E7EB;border-radius:6px;padding:14px 18px;margin:24px 0 16px;">
<p style="font-weight:bold;margin:0 0 8px;color:#555;font-size:13px;">📰 참고 자료</p>
<ul style="margin:0;padding-left:18px;color:#666;font-size:13px;line-height:1.8;">
<li>연합뉴스 — "기사 제목" (날짜)</li>
<li>BBC — "기사 제목" (날짜)</li>
</ul>
</div>

[섹션 구분선]
<hr style="border:0;border-top:2px solid #EBF3FB;margin:30px 0;">

[마무리 CTA 박스 — 글 최하단 필수]
<div style="background:#F4F6F7;border-radius:8px;padding:20px 24px;margin:32px 0 0;text-align:center;border:1px solid #EAECEE;">
<p style="margin:0 0 6px;font-weight:bold;color:#2C3E50;">이 글이 도움이 되셨나요? 😊</p>
<p style="margin:0;color:#666;font-size:14px;">공감 <strong style="color:#E74C3C;">♥</strong> 와 댓글은 더 좋은 글을 쓰는 데 큰 힘이 됩니다!</p>
</div>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ SEO & 가독성 규칙
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 핵심 키워드를 제목, 첫 단락, h2 헤더에 배치
• 모바일 가독성을 위해 한 단락은 3~4문장 이내
• 글 길이: HTML 태그 제외 순수 텍스트 기준 3000~5000자

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 출력 형식
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
첫 줄: 제목 (HTML 태그 없이 텍스트만, 40자 이내)
두 번째 줄: 빈 줄
세 번째 줄부터: 위 HTML 규칙을 완벽히 적용한 본문"""


class IssueWriter:
    """실제 뉴스 자료를 수집한 후 팩트 기반 이슈 정리글을 생성합니다."""

    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

    def generate_post(self, topic: str, keywords: list[str] | None = None) -> dict:
        """이슈 정리글을 생성합니다.

        1) 네이버 뉴스 API로 실제 기사 수집
        2) 네이버 블로그 검색으로 인기 글 스타일 참고
        3) 수집된 자료를 GPT에 전달해 팩트 기반 글 작성

        Args:
            topic: 이슈 주제
            keywords: SEO 키워드 목록 (선택사항)

        Returns:
            {"title": str, "content": str} 형태의 딕셔너리
        """
        # ── 1단계: 실제 뉴스 자료 수집 ──
        logger.info("뉴스 자료 수집 중: %s", topic)
        news_articles = fetch_news(topic, count=15)

        # 키워드로 추가 검색 (다각적 자료 확보)
        if keywords:
            for kw in keywords[:2]:
                extra = fetch_news(kw, count=5)
                # 중복 제거 (제목 기준)
                existing_titles = {a["title"] for a in news_articles}
                for a in extra:
                    if a["title"] not in existing_titles:
                        news_articles.append(a)
                        existing_titles.add(a["title"])

        news_context = format_news_context(news_articles)

        # ── 2단계: 블로그 스타일 참조 ──
        logger.info("블로그 스타일 참조 수집 중: %s", topic)
        blog_refs = fetch_blog_references(topic, count=5)
        blog_context = format_blog_context(blog_refs)

        # ── 3단계: GPT 프롬프트 구성 ──
        user_prompt = f"이슈 주제: {topic}\n"
        if keywords:
            user_prompt += f"SEO 키워드: {', '.join(keywords)}\n"

        user_prompt += "\n"

        if news_context:
            user_prompt += (
                "아래는 이 이슈에 대한 실제 뉴스 기사입니다.\n"
                "반드시 이 뉴스 자료에 있는 사실만을 기반으로 글을 작성하세요.\n"
                "각 정보의 출처(언론사명)를 본문에 자연스럽게 포함하세요.\n"
                "글 하단에 '참고 자료' 섹션을 추가해 주요 출처를 정리하세요.\n\n"
                f"{news_context}\n\n"
            )
        else:
            user_prompt += (
                "⚠️ 뉴스 자료를 수집하지 못했습니다.\n"
                "확실히 알려진 일반적 사실만 작성하고, "
                "불확실한 내용은 '추가 확인이 필요합니다'로 처리하세요.\n\n"
            )

        if blog_context:
            user_prompt += (
                "아래는 같은 주제의 인기 블로그 글입니다. "
                "글의 톤·구성·표현 방식을 참고하되, "
                "내용은 위 뉴스 자료만을 기반으로 작성하세요.\n\n"
                f"{blog_context}\n\n"
            )

        user_prompt += (
            "위 자료를 기반으로 팩트에 충실한 이슈 정리글을 작성해주세요.\n"
            "요약 박스, 출처 인용, 해외 언론 박스, 비교표, 참고 자료, CTA 박스를 포함하세요."
        )

        logger.info("이슈 정리글 생성 요청: %s (뉴스 %d건, 블로그 참조 %d건)",
                     topic, len(news_articles), len(blog_refs))

        # ── 4단계: GPT 호출 ──
        try:
            response = self.client.chat.completions.create(
                model=Config.GPT_MODEL,
                max_completion_tokens=ISSUE_MAX_TOKENS,
                reasoning_effort=Config.GPT_REASONING_EFFORT,
                messages=[
                    {"role": "system", "content": ISSUE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as e:
            logger.error("GPT API 호출 실패: %s", e)
            raise RuntimeError(f"GPT API 호출 실패: {e}") from e

        choice = response.choices[0]
        if choice.finish_reason == "content_filter":
            raise RuntimeError("GPT 콘텐츠 필터에 의해 응답이 차단되었습니다.")
        if not choice.message.content:
            raise RuntimeError("GPT 응답이 비어있습니다. 다시 시도해주세요.")

        title, content = _parse_title_content(choice.message.content)

        logger.info("이슈 정리글 생성 완료: %s (%d자)", title, len(content))
        return {"title": title, "content": content}

    def generate_trending_post(self) -> dict:
        """트렌드를 자동으로 분석해 지금 가장 조회수가 높을 이슈 정리글을 작성합니다.

        Returns:
            {"title": str, "content": str, "topic": str, "keywords": list} 딕셔너리
        """
        from .trend_finder import TrendFinder

        logger.info("트렌드 자동 분석 시작...")
        finder = TrendFinder()
        topic, keywords, reason = finder.get_best_topic()

        logger.info("선정 주제: %s / 키워드: %s", topic, keywords)
        if reason:
            logger.info("선정 이유: %s", reason)

        post = self.generate_post(topic, keywords)
        post["topic"] = topic
        post["keywords"] = keywords
        post["trend_reason"] = reason
        return post
