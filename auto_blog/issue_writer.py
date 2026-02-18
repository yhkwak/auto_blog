import logging
from anthropic import Anthropic
from .config import Config

logger = logging.getLogger(__name__)

ISSUE_SYSTEM_PROMPT = """당신은 시사/트렌드 전문 블로그 작가입니다.
주어진 이슈나 트렌드 주제에 대해 조회수를 높일 수 있는 정보성 정리글을 작성합니다.

작성 전략:
- 독자가 이 글 하나로 이슈의 전반을 이해할 수 있도록 구성합니다.
- 배경, 현황, 다양한 시각, 향후 전망 등을 균형 있게 다룹니다.
- 제목은 클릭을 유도하는 후킹한 표현을 사용합니다. (예: "정리해드립니다", "총정리", "알아야 할 것들")
- SEO에 유리하도록 핵심 키워드를 자연스럽게 반복 사용합니다.

작성 규칙:
1. 제목은 첫 줄에 작성하고, 본문과 빈 줄로 구분합니다.
2. HTML 태그로 포맷팅합니다 (<h2>, <h3>, <p>, <ul>, <li>, <strong> 등).
3. 소제목 구조: 이슈 배경 → 핵심 내용 정리 → 다양한 시각/반응 → 향후 전망 → 마무리
4. 자연스러운 한국어로 작성합니다.
5. 글의 길이는 2000~3500자 사이로 합니다.
6. 숫자, 통계, 구체적인 사례를 활용해 신뢰성을 높입니다.

출력 형식:
첫 줄: 제목 (HTML 태그 없이 텍스트만)
두 번째 줄: 빈 줄
세 번째 줄부터: HTML 본문
"""


class IssueWriter:
    """이슈/트렌드 정리글을 생성합니다. 조회수 최적화에 초점을 맞춥니다."""

    def __init__(self):
        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    def generate_post(self, topic: str, keywords: list[str] | None = None) -> dict:
        """이슈 정리글을 생성합니다.

        Args:
            topic: 이슈 주제 (예: "딥시크 AI 논란", "2025 부동산 정책 변화")
            keywords: SEO 키워드 목록 (선택사항)

        Returns:
            {"title": str, "content": str} 형태의 딕셔너리
        """
        user_prompt = f"이슈 주제: {topic}"
        if keywords:
            user_prompt += f"\n반드시 포함할 SEO 키워드: {', '.join(keywords)}"
        user_prompt += "\n\n위 이슈에 대한 정리글을 작성해주세요."

        logger.info("이슈 정리글 생성 요청: %s", topic)

        message = self.client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=Config.CLAUDE_MAX_TOKENS,
            system=ISSUE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = message.content[0].text
        lines = response_text.strip().split("\n", 1)

        title = lines[0].strip().strip("#").strip()
        content = lines[1].strip() if len(lines) > 1 else ""

        logger.info("이슈 정리글 생성 완료: %s (%d자)", title, len(content))
        return {"title": title, "content": content}
