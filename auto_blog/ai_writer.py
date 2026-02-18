import logging
from anthropic import Anthropic
from .config import Config

logger = logging.getLogger(__name__)

BLOG_SYSTEM_PROMPT = """당신은 전문 블로그 작가입니다.
주어진 주제에 대해 매력적이고 정보가 풍부한 블로그 글을 작성합니다.

작성 규칙:
1. 제목은 첫 줄에 작성하고, 본문과 빈 줄로 구분합니다.
2. 독자의 관심을 끄는 도입부로 시작합니다.
3. HTML 태그를 사용하여 포맷팅합니다 (<h2>, <h3>, <p>, <ul>, <li>, <strong>, <em> 등).
4. 소제목을 활용하여 구조화된 글을 작성합니다.
5. 자연스러운 한국어로 작성합니다.
6. 글의 길이는 1500~3000자 사이로 합니다.
7. 마지막에 간결한 마무리를 작성합니다.

출력 형식:
첫 줄: 제목 (HTML 태그 없이 텍스트만)
두 번째 줄: 빈 줄
세 번째 줄부터: HTML 본문
"""


class AIWriter:
    """Claude API를 사용하여 블로그 글을 생성합니다."""

    def __init__(self):
        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    def generate_post(self, topic: str, keywords: list[str] | None = None) -> dict:
        """주어진 주제로 블로그 글을 생성합니다.

        Args:
            topic: 블로그 글 주제
            keywords: SEO 키워드 목록 (선택사항)

        Returns:
            {"title": str, "content": str} 형태의 딕셔너리
        """
        user_prompt = f"주제: {topic}"
        if keywords:
            user_prompt += f"\n키워드: {', '.join(keywords)}"

        logger.info("Claude API로 글 생성 요청: %s", topic)

        message = self.client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=Config.CLAUDE_MAX_TOKENS,
            system=BLOG_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = message.content[0].text
        lines = response_text.strip().split("\n", 1)

        title = lines[0].strip().strip("#").strip()
        content = lines[1].strip() if len(lines) > 1 else ""

        logger.info("글 생성 완료: %s (%d자)", title, len(content))
        return {"title": title, "content": content}
