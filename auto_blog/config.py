import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """환경 변수에서 설정을 로드합니다."""

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID", "")
    NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET", "")
    NAVER_ACCESS_TOKEN: str = os.getenv("NAVER_ACCESS_TOKEN", "")

    # Claude 모델 설정
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    CLAUDE_MAX_TOKENS: int = int(os.getenv("CLAUDE_MAX_TOKENS", "4096"))

    @classmethod
    def validate(cls) -> list[str]:
        """필수 설정값이 있는지 확인합니다."""
        errors = []
        if not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        if not cls.NAVER_CLIENT_ID:
            errors.append("NAVER_CLIENT_ID가 설정되지 않았습니다.")
        if not cls.NAVER_CLIENT_SECRET:
            errors.append("NAVER_CLIENT_SECRET가 설정되지 않았습니다.")
        if not cls.NAVER_ACCESS_TOKEN:
            errors.append("NAVER_ACCESS_TOKEN이 설정되지 않았습니다.")
        return errors
