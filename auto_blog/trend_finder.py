"""트렌드 주제 자동 발굴 모듈

X(트위터), 네이버 뉴스, 구글 트렌드 등 다양한 매체의 트렌드를 분석해
지금 가장 조회수가 높게 나올 블로그 주제를 자동으로 선정합니다.
"""

import json
import logging
import re
from datetime import datetime

from anthropic import Anthropic

from .config import Config

logger = logging.getLogger(__name__)


TREND_SYSTEM_PROMPT = """당신은 한국 디지털 미디어 트렌드를 분석하는 콘텐츠 전략가입니다.
날짜·계절·사회적 맥락·반복 이벤트 패턴을 종합적으로 고려해
지금 네이버 블로그에서 가장 높은 조회수를 낼 수 있는 이슈 주제를 선정합니다.

분석 대상 채널:
- X(구 트위터) 한국 실시간 트렌드
- 네이버 뉴스 인기 검색어 / 실시간 이슈
- 구글 트렌드 코리아 급상승 검색어
- 유튜브 한국 인기 급상승
- 커뮤니티 (에펨코리아, 디시인사이드, 더쿠 등) 핫이슈

선정 기준:
1. 지금 이 시점에서 실시간 검색어 상위권에 오를 가능성
2. 정보 수요는 높지만 정리글이 아직 적은 주제 (블루오션)
3. 정치·경제·연예·스포츠·기술·사회·라이프 분야의 다양성
4. "이게 뭐지?", "왜 화제야?"라고 궁금해할 만한 시의성
5. 네이버 블로그 유입에 유리한 검색 키워드 포함 여부

반드시 JSON 형식으로만 응답하세요. 다른 설명이나 텍스트를 추가하지 마세요."""


TREND_USER_TEMPLATE = """오늘 날짜: {date}
현재 시각: {time}

위 날짜·시간을 기준으로, 지금 한국에서 가장 화제가 되고 있을 가능성이 높은
이슈/트렌드 주제 {count}개를 선정해주세요.

각 주제는 다음 정보를 포함해야 합니다:
- 구체적인 이슈 주제명 (너무 추상적이지 않게, 실제 검색어처럼)
- 지금 화제인 이유 (계절성, 최근 이벤트, 반복 트렌드 등 근거 포함)
- 카테고리 분류
- SEO 핵심 키워드 3~5개
- 예상 검색 볼륨 (high / medium)
- 클릭을 유도하는 블로그 제목 예시

반드시 아래 JSON 형식만 출력하세요 (```json 코드블록 없이 순수 JSON):
{{
  "analysis_date": "{date}",
  "topics": [
    {{
      "topic": "구체적인 이슈 주제명",
      "reason": "지금 화제인 이유 (2~3문장, 근거 포함)",
      "category": "정치/경제/연예/스포츠/기술/사회/라이프 중 하나",
      "keywords": ["키워드1", "키워드2", "키워드3"],
      "search_volume": "high 또는 medium",
      "hook_title": "클릭률 높은 제목 예시"
    }}
  ],
  "best_pick_index": 0,
  "best_pick_reason": "이 주제를 최우선 추천하는 이유"
}}"""


class TrendFinder:
    """Claude AI로 현재 트렌딩 이슈 주제를 자동 발굴합니다."""

    def __init__(self):
        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    def find_trending_topics(self, count: int = 5) -> dict:
        """현재 트렌딩 주제 목록을 분석해 반환합니다.

        Args:
            count: 분석할 주제 수 (기본값: 5)

        Returns:
            topics 목록과 best_pick_index가 담긴 딕셔너리
        """
        now = datetime.now()
        user_prompt = TREND_USER_TEMPLATE.format(
            date=now.strftime("%Y년 %m월 %d일 (%A)"),
            time=now.strftime("%H:%M"),
            count=count,
        )

        logger.info("트렌드 주제 분석 시작 (분석 대상: %d개)", count)

        message = self.client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=2000,
            system=TREND_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = message.content[0].text.strip()

        # JSON 블록 추출 (```json ... ``` 코드블록 포함 대응)
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                topics = data.get("topics", [])
                logger.info("트렌드 분석 완료: %d개 주제 발굴", len(topics))
                for i, t in enumerate(topics):
                    logger.info(
                        "  [%d] %s (%s / %s)",
                        i + 1,
                        t.get("topic", ""),
                        t.get("category", ""),
                        t.get("search_volume", ""),
                    )
                return data
            except json.JSONDecodeError as e:
                logger.warning("JSON 파싱 실패: %s\n원본: %s", e, response_text[:300])

        return {"topics": [], "best_pick_index": 0, "best_pick_reason": ""}

    def get_best_topic(self) -> tuple[str, list[str], str]:
        """조회수가 가장 높을 것으로 예상되는 주제를 선정해 반환합니다.

        Returns:
            (topic, keywords, reason) 튜플
        """
        data = self.find_trending_topics()
        topics = data.get("topics", [])
        best_idx = data.get("best_pick_index", 0)
        best_reason = data.get("best_pick_reason", "")

        if not topics:
            logger.warning("트렌드 분석 결과가 비어있습니다. 기본 주제 사용.")
            return "오늘의 주요 이슈 총정리", [], ""

        best_idx = max(0, min(best_idx, len(topics) - 1))
        best = topics[best_idx]

        topic = best.get("topic", "오늘의 이슈")
        keywords = best.get("keywords", [])
        hook_title = best.get("hook_title", "")

        logger.info("최종 선정 주제: %s", topic)
        logger.info("추천 이유: %s", best_reason)
        logger.info("SEO 키워드: %s", ", ".join(keywords))
        if hook_title:
            logger.info("제목 예시: %s", hook_title)

        return topic, keywords, best_reason

    def get_all_topics_summary(self) -> str:
        """분석된 모든 주제를 읽기 쉬운 문자열로 반환합니다 (로그/GUI 표시용)."""
        data = self.find_trending_topics()
        topics = data.get("topics", [])
        best_idx = data.get("best_pick_index", 0)

        if not topics:
            return "트렌드 분석 결과가 없습니다."

        lines = ["=== 트렌드 주제 분석 결과 ==="]
        for i, t in enumerate(topics):
            marker = "★ 추천" if i == best_idx else f"  {i + 1}위"
            lines.append(
                f"{marker}. [{t.get('category', '')}] {t.get('topic', '')} "
                f"(검색량: {t.get('search_volume', '')})"
            )
            lines.append(f"       이유: {t.get('reason', '')[:60]}...")
        lines.append(f"\n추천 이유: {data.get('best_pick_reason', '')}")
        return "\n".join(lines)
