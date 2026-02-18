"""이슈/트렌드 정리글 생성기

네이버 블로그 조회수 상위 1% 인기 글의 형식과 구조를 적용해
SEO와 클릭률에 최적화된 이슈 정리글을 자동 작성합니다.
"""

import logging

from openai import OpenAI

from .config import Config

logger = logging.getLogger(__name__)

# 인기 이슈 글은 HTML 풍부도가 높아 더 많은 토큰이 필요
ISSUE_MAX_TOKENS = 6000

ISSUE_SYSTEM_PROMPT = """당신은 네이버 블로그에서 월 100만 뷰를 달성하는 시사/트렌드 전문 블로거입니다.
조회수 상위 1% 글의 형식·구조·전략을 완벽히 구현해야 합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 네이버 인기 블로그 제목 전략
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 정보성 훅: "총정리", "한눈에 보기", "완벽 정리", "이것만 알면 됩니다", "알아야 할 것들"
• 숫자 활용: "5가지 핵심", "3분 만에 이해하는", "TOP 3 포인트"
• 궁금증 유발: "진짜 이유", "충격적 사실", "아무도 말 안 해주는"
• 최신성 강조: "2026년 최신", "지금 바로 확인", "오늘 기준"
• 40자 이내로 작성

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 글 구조 (반드시 이 순서로)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 📋 상단 요약 박스 (이탈 방지 핵심 장치)
2. 🔎 도입 — 왜 지금 이 이슈인가 (1~2단락, 독자 공감 유도)
3. 📌 배경/맥락 — 이슈의 시작과 흐름
4. 🔥 핵심 내용 정리 — 번호 매긴 단계별 설명
5. 📊 통계/데이터 또는 비교표 (표 필수 1개 이상)
6. 💬 다양한 시각/반응 — 찬반, 전문가 의견, 커뮤니티 반응
7. 🚀 향후 전망 — 앞으로 어떻게 될까
8. ✅ 마무리 + 공감 유도 CTA

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

[핵심 강조 박스 — 노란색, 중요 포인트마다]
<div style="background:#FEF9E7;border:1px solid #F7DC6F;border-radius:6px;padding:14px 18px;margin:16px 0;">
💡 <strong>핵심 포인트:</strong> 중요한 내용을 여기에
</div>

[정보 박스 — 초록색, 유용한 팁]
<div style="background:#EAFAF1;border:1px solid #A9DFBF;border-radius:6px;padding:14px 18px;margin:16px 0;">
✅ <strong>알아두면 좋은 점:</strong> 유용한 정보
</div>

[주의/경고 박스 — 빨간색]
<div style="background:#FDEDEC;border:1px solid #F1948A;border-radius:6px;padding:14px 18px;margin:16px 0;">
⚠️ <strong>주의:</strong> 주의사항 내용
</div>

[인용구 — 전문가 의견, 발언 인용]
<blockquote style="border-left:4px solid #2980B9;background:#F2F3F4;padding:13px 18px;margin:16px 0;color:#555;font-style:italic;border-radius:0 6px 6px 0;">
인용 내용 또는 핵심 발언
</blockquote>

[비교표 — 섹션당 1개 이상 필수]
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
• 핵심 키워드를 제목, 첫 단락, h2 헤더에 자연스럽게 배치
• 롱테일 키워드를 본문에 3~5회 자연스럽게 포함
• 숫자, 통계, 날짜를 활용해 신뢰성 강화
• 모바일 가독성을 위해 한 단락은 3~4문장 이내
• 글 길이: HTML 태그 제외 순수 텍스트 기준 3000~5000자

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 출력 형식
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
첫 줄: 제목 (HTML 태그 없이 텍스트만, 40자 이내)
두 번째 줄: 빈 줄
세 번째 줄부터: 위 HTML 규칙을 완벽히 적용한 본문"""


class IssueWriter:
    """네이버 블로그 인기 형식으로 이슈/트렌드 정리글을 생성합니다."""

    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

    def generate_post(self, topic: str, keywords: list[str] | None = None) -> dict:
        """이슈 정리글을 생성합니다.

        Args:
            topic: 이슈 주제 (예: "딥시크 AI 논란", "2026 부동산 정책 변화")
            keywords: SEO 키워드 목록 (선택사항)

        Returns:
            {"title": str, "content": str} 형태의 딕셔너리
        """
        user_prompt = f"이슈 주제: {topic}"
        if keywords:
            user_prompt += f"\n반드시 포함할 SEO 키워드: {', '.join(keywords)}"
        user_prompt += (
            "\n\n위 이슈에 대해 네이버 블로그 조회수 상위 1% 형식으로 정리글을 작성해주세요."
            "\n요약 박스, 이모지 헤더, 강조 박스, 비교표, CTA 박스를 모두 포함해야 합니다."
        )

        logger.info("이슈 정리글 생성 요청: %s", topic)

        response = self.client.chat.completions.create(
            model=Config.GPT_MODEL,
            max_completion_tokens=ISSUE_MAX_TOKENS,
            reasoning_effort=Config.GPT_REASONING_EFFORT,
            messages=[
                {"role": "system", "content": ISSUE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        response_text = response.choices[0].message.content
        lines = response_text.strip().split("\n", 1)

        title = lines[0].strip().strip("#").strip()
        content = lines[1].strip() if len(lines) > 1 else ""

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
