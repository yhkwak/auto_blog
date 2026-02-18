import logging
import requests
from .config import Config

logger = logging.getLogger(__name__)

NAVER_BLOG_WRITE_URL = "https://openapi.naver.com/blog/writePost.json"


class NaverBlogClient:
    """네이버 블로그 API 클라이언트입니다."""

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {Config.NAVER_ACCESS_TOKEN}",
        }

    def publish(self, title: str, content: str, category_no: int = 0) -> dict:
        """네이버 블로그에 글을 발행합니다.

        Args:
            title: 블로그 글 제목
            content: 블로그 글 본문 (HTML)
            category_no: 카테고리 번호 (0이면 기본 카테고리)

        Returns:
            API 응답 딕셔너리
        """
        data = {
            "title": title,
            "contents": content,
            "categoryNo": category_no,
        }

        logger.info("네이버 블로그에 글 발행 요청: %s", title)

        response = requests.post(
            NAVER_BLOG_WRITE_URL,
            headers=self.headers,
            data=data,
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            logger.info("블로그 발행 성공: %s", result.get("message", ""))
            return result
        else:
            error_msg = f"블로그 발행 실패 (HTTP {response.status_code}): {response.text}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def get_auth_url(self) -> str:
        """네이버 OAuth 인증 URL을 반환합니다.

        브라우저에서 이 URL로 접속하여 인증을 완료하면
        Access Token을 받을 수 있습니다.
        """
        return (
            "https://nid.naver.com/oauth2.0/authorize"
            f"?client_id={Config.NAVER_CLIENT_ID}"
            "&response_type=code"
            "&redirect_uri=http://localhost:8080/callback"
            "&state=auto_blog"
        )

    def get_access_token(self, code: str) -> str:
        """인증 코드로 Access Token을 발급받습니다.

        Args:
            code: OAuth 인증 후 받은 코드

        Returns:
            Access Token 문자열
        """
        token_url = "https://nid.naver.com/oauth2.0/token"
        params = {
            "grant_type": "authorization_code",
            "client_id": Config.NAVER_CLIENT_ID,
            "client_secret": Config.NAVER_CLIENT_SECRET,
            "code": code,
            "state": "auto_blog",
        }

        response = requests.get(token_url, params=params, timeout=30)
        result = response.json()

        if "access_token" in result:
            logger.info("Access Token 발급 성공")
            return result["access_token"]
        else:
            error_msg = f"Access Token 발급 실패: {result}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
