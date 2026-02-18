import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """환경 변수에서 설정을 로드합니다."""

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID", "")
    NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET", "")
    NAVER_ID: str = os.getenv("NAVER_ID", "")
    NAVER_PASSWORD: str = os.getenv("NAVER_PASSWORD", "")

    # GPT 모델 설정
    GPT_MODEL: str = os.getenv("GPT_MODEL", "gpt-4o-mini")
    GPT_MAX_TOKENS: int = int(os.getenv("GPT_MAX_TOKENS", "4096"))

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
