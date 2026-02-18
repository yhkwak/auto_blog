import logging
from anthropic import Anthropic
from .config import Config

logger = logging.getLogger(__name__)

OPINION_SYSTEM_PROMPT = """당신은 개인 블로그 글쓰기를 도와주는 전문 에디터입니다.
사용자가 제공한 주제와 생각의 흐름(핵심 포인트, 경험, 의견)을 바탕으로
사용자의 목소리와 관점이 살아있는 진정성 있는 블로그 글을 작성합니다.

작성 방향:
- 사용자가 제공한 생각과 의견을 충실히 반영합니다. 임의로 내용을 추가하거나 왜곡하지 않습니다.
- 1인칭 시점("나는", "나의 경우", "내 생각엔")을 사용해 개인적인 목소리를 살립니다.
- 독자와 대화하듯 친근하고 자연스러운 문체로 작성합니다.
- 사용자의 핵심 생각이 글의 중심이 되도록 구성합니다.

작성 규칙:
1. 제목은 첫 줄에 작성하고, 본문과 빈 줄로 구분합니다.
2. HTML 태그로 포맷팅합니다 (<h2>, <h3>, <p>, <ul>, <li>, <strong>, <em> 등).
3. 구조: 도입(왜 이 주제인가) → 본론(생각 전개) → 결론(핵심 메시지)
4. 자연스러운 한국어 구어체로 작성합니다.
5. 글의 길이는 1500~2500자 사이로 합니다.
6. 독자가 공감하거나 생각해볼 수 있는 질문이나 여운을 남깁니다.

출력 형식:
첫 줄: 제목 (HTML 태그 없이 텍스트만)
두 번째 줄: 빈 줄
세 번째 줄부터: HTML 본문
"""


class OpinionWriter:
    """사용자의 생각을 바탕으로 개인 의견 블로그 글을 생성합니다."""

    def __init__(self):
        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    def generate_post(self, topic: str, thoughts: str, keywords: list[str] | None = None) -> dict:
        """사용자의 생각을 바탕으로 의견 글을 생성합니다.

        Args:
            topic: 글의 주제 (예: "AI 시대의 직업 변화")
            thoughts: 사용자의 핵심 생각, 경험, 의견 (자유롭게 작성)
            keywords: SEO 키워드 목록 (선택사항)

        Returns:
            {"title": str, "content": str} 형태의 딕셔너리
        """
        user_prompt = f"주제: {topic}\n\n내 생각 및 핵심 포인트:\n{thoughts}"
        if keywords:
            user_prompt += f"\n\n포함할 키워드: {', '.join(keywords)}"
        user_prompt += "\n\n위 내용을 바탕으로 내 목소리가 살아있는 블로그 글을 작성해주세요."

        logger.info("개인 의견 글 생성 요청: %s", topic)

        message = self.client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=Config.CLAUDE_MAX_TOKENS,
            system=OPINION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = message.content[0].text
        lines = response_text.strip().split("\n", 1)

        title = lines[0].strip().strip("#").strip()
        content = lines[1].strip() if len(lines) > 1 else ""

        logger.info("개인 의견 글 생성 완료: %s (%d자)", title, len(content))
        return {"title": title, "content": content}
