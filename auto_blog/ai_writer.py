import logging
import re

from openai import OpenAI

from .config import Config

logger = logging.getLogger(__name__)


def _parse_title_content(response_text: str) -> tuple[str, str]:
    """GPT 응답에서 제목과 본문을 분리합니다.

    다양한 형식에 대응합니다:
    - '# 제목' / '## 제목' (마크다운 헤더)
    - '제목: ...'
    - 첫 줄 텍스트 그대로
    """
    text = response_text.strip()
    lines = text.split("\n", 1)

    title_line = lines[0].strip()

    # 마크다운 헤더 제거: "### 제목" → "제목"
    title = re.sub(r'^#{1,6}\s*', '', title_line).strip()
    # 앞뒤 따옴표 제거
    title = title.strip('"').strip("'").strip()
    # "제목: ..." 형식 처리
    if title.lower().startswith("제목:") or title.lower().startswith("title:"):
        title = title.split(":", 1)[1].strip()

    content = lines[1].strip() if len(lines) > 1 else ""
    # 본문 시작이 빈 줄이면 제거
    content = content.lstrip("\n")

    if not title:
        title = "제목 없음"

    return title, content

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
    """OpenAI GPT API를 사용하여 블로그 글을 생성합니다."""

    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

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

        logger.info("GPT API로 글 생성 요청: %s", topic)

        try:
            response = self.client.chat.completions.create(
                model=Config.GPT_MODEL,
                max_completion_tokens=Config.GPT_MAX_COMPLETION_TOKENS,
                reasoning_effort=Config.GPT_REASONING_EFFORT,
                messages=[
                    {"role": "system", "content": BLOG_SYSTEM_PROMPT},
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

        logger.info("글 생성 완료: %s (%d자)", title, len(content))
        return {"title": title, "content": content}
