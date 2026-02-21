"""내 생각/의견 정리글 생성기

사용자의 생각과 경험을 바탕으로 진정성 있는 블로그 글을 작성합니다.
인기 블로그 글의 스타일을 참고해 읽기 편하고 공감되는 글을 만듭니다.
"""

import logging

from openai import OpenAI

from .ai_writer import _parse_title_content
from .config import Config
from .news_fetcher import fetch_blog_references, format_blog_context

logger = logging.getLogger(__name__)

OPINION_SYSTEM_PROMPT = """당신은 개인 블로그 글쓰기를 도와주는 전문 에디터입니다.
사용자가 제공한 주제와 생각의 흐름(핵심 포인트, 경험, 의견)을 바탕으로
사용자의 목소리와 관점이 살아있는 진정성 있는 블로그 글을 작성합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 핵심 원칙
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 사용자가 제공한 생각과 의견을 충실히 반영합니다. 임의로 내용을 추가하거나 왜곡하지 않습니다.
• 사실이 아닌 내용을 창작하지 않습니다. 사용자의 의견은 의견으로, 사실은 사실로 구분합니다.
• 참고 블로그 글의 톤·표현·구성을 참고하되, 사용자의 생각을 중심에 둡니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 글 스타일 — 자연스럽고 읽기 좋은 블로그 문체
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 1인칭 시점("나는", "내 경우엔", "내 생각엔")을 사용해 개인적인 목소리를 살립니다.
• 독자와 대화하듯 친근하고 자연스러운 문체로 작성합니다.
• "~인데요", "~거든요", "~더라고요" 등 블로그에서 흔히 쓰는 구어체를 적절히 섞습니다.
• 글 AI가 쓴 티가 나지 않도록 완벽한 문법보다 자연스러운 흐름을 중시합니다.
• 짧은 문장 위주로 리듬감 있게. 한 문단은 3~4문장 이내.
• 중간중간 독자에게 말을 거는 표현을 넣어줍니다.
  ("혹시 이런 경험 있으신가요?", "저만 그런 건 아니겠죠?")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 글 구조
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 도입 — 왜 이 주제에 대해 쓰게 됐는지 (공감 유도, 1~2단락)
2. 본론 — 사용자의 생각 전개 (소제목으로 구분, 핵심 포인트별 정리)
3. 경험/에피소드 — 개인 경험이 있으면 구체적으로 풀어서
4. 결론 — 핵심 메시지 + 독자에게 여운을 남기는 마무리

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ HTML 포맷 규칙
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[섹션 헤더]
<h2 style="font-size:20px;font-weight:bold;border-left:5px solid #8E44AD;padding-left:13px;margin:32px 0 14px;color:#4A235A;">✍️ 소제목</h2>

[일반 단락]
<p style="line-height:1.95;margin-bottom:14px;color:#333;">내용</p>

[핵심 생각 강조 박스]
<div style="background:#F5EEF8;border:1px solid #D2B4DE;border-radius:6px;padding:14px 18px;margin:16px 0;">
💭 <strong>내 생각:</strong> 핵심 의견
</div>

[경험 인용]
<blockquote style="border-left:4px solid #8E44AD;background:#F9F5FC;padding:13px 18px;margin:16px 0;color:#555;font-style:italic;border-radius:0 6px 6px 0;">
개인 경험이나 에피소드
</blockquote>

[마무리 박스]
<div style="background:#F4F6F7;border-radius:8px;padding:20px 24px;margin:32px 0 0;text-align:center;border:1px solid #EAECEE;">
<p style="margin:0 0 6px;font-weight:bold;color:#2C3E50;">여러분의 생각은 어떠신가요? 😊</p>
<p style="margin:0;color:#666;font-size:14px;">댓글로 의견 남겨주시면 감사하겠습니다!</p>
</div>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ SEO & 가독성
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 핵심 키워드를 제목, 첫 단락, h2에 자연스럽게 배치
• 글 길이: 1500~3000자
• 제목: 40자 이내, 개인적 시각이 드러나는 제목

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 출력 형식
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
첫 줄: 제목 (HTML 태그 없이 텍스트만)
두 번째 줄: 빈 줄
세 번째 줄부터: HTML 본문"""


class OpinionWriter:
    """사용자의 생각을 바탕으로 개인 의견 블로그 글을 생성합니다."""

    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

    def generate_post(self, topic: str, thoughts: str, keywords: list[str] | None = None) -> dict:
        """사용자의 생각을 바탕으로 의견 글을 생성합니다.

        1) 네이버 블로그 검색으로 인기 글 스타일 참고
        2) 사용자의 생각 + 참고 스타일을 GPT에 전달

        Args:
            topic: 글의 주제
            thoughts: 사용자의 핵심 생각, 경험, 의견
            keywords: SEO 키워드 목록 (선택사항)

        Returns:
            {"title": str, "content": str} 형태의 딕셔너리
        """
        # ── 1단계: 블로그 스타일 참조 ──
        logger.info("블로그 스타일 참조 수집 중: %s", topic)
        blog_refs = fetch_blog_references(topic, count=5)
        blog_context = format_blog_context(blog_refs)

        # ── 2단계: GPT 프롬프트 구성 ──
        user_prompt = f"주제: {topic}\n\n내 생각 및 핵심 포인트:\n{thoughts}"
        if keywords:
            user_prompt += f"\n\n포함할 키워드: {', '.join(keywords)}"

        if blog_context:
            user_prompt += (
                "\n\n아래는 같은 주제의 인기 블로그 글입니다. "
                "글의 톤·구성·표현 방식을 참고해서 작성해주세요.\n\n"
                f"{blog_context}"
            )

        user_prompt += "\n\n위 내용을 바탕으로 내 목소리가 살아있는 블로그 글을 작성해주세요."

        logger.info("개인 의견 글 생성 요청: %s (블로그 참조 %d건)",
                     topic, len(blog_refs))

        # ── 3단계: GPT 호출 ──
        try:
            response = self.client.chat.completions.create(
                model=Config.GPT_MODEL,
                max_completion_tokens=Config.GPT_MAX_COMPLETION_TOKENS,
                reasoning_effort=Config.GPT_REASONING_EFFORT,
                messages=[
                    {"role": "system", "content": OPINION_SYSTEM_PROMPT},
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

        logger.info("개인 의견 글 생성 완료: %s (%d자)", title, len(content))
        return {"title": title, "content": content}
