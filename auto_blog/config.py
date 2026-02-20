import os
from dotenv import load_dotenv

load_dotenv()


def _safe_int(value: str, default: int) -> int:
    """환경변수 문자열을 int로 안전하게 변환합니다."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class Config:
    """환경 변수에서 설정을 로드합니다."""

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID", "")
    NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET", "")
    NAVER_ID: str = os.getenv("NAVER_ID", "")
    NAVER_PASSWORD: str = os.getenv("NAVER_PASSWORD", "")

    # GPT 모델 설정
    GPT_MODEL: str = os.getenv("GPT_MODEL", "gpt-4.1")
    GPT_MAX_COMPLETION_TOKENS: int = _safe_int(
        os.getenv("GPT_MAX_COMPLETION_TOKENS", ""), 4096
    )
    GPT_REASONING_EFFORT: str = os.getenv("GPT_REASONING_EFFORT", "medium")

    @classmethod
    def validate(cls) -> list[str]:
        """필수 설정값이 있는지 확인합니다."""
        errors = []
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY가 설정되지 않았습니다.")
        if not cls.NAVER_ID:
            errors.append("NAVER_ID(네이버 아이디)가 설정되지 않았습니다.")
        if not cls.NAVER_PASSWORD:
            errors.append("NAVER_PASSWORD(네이버 비밀번호)가 설정되지 않았습니다.")
        return errors

    @classmethod
    def reload(cls) -> None:
        """환경변수를 다시 읽어 모든 설정을 갱신합니다."""
        cls.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        cls.NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
        cls.NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
        cls.NAVER_ID = os.getenv("NAVER_ID", "")
        cls.NAVER_PASSWORD = os.getenv("NAVER_PASSWORD", "")
        cls.GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4.1")
        cls.GPT_MAX_COMPLETION_TOKENS = _safe_int(
            os.getenv("GPT_MAX_COMPLETION_TOKENS", ""), 4096
        )
        cls.GPT_REASONING_EFFORT = os.getenv("GPT_REASONING_EFFORT", "medium")
