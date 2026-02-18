import argparse
import logging
import sys

from .config import Config
from .ai_writer import AIWriter
from .naver_blog import NaverBlogClient
from .scheduler import run_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/auto_blog.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def write_and_publish(topic: str, keywords: list[str] | None = None) -> None:
    """블로그 글을 생성하고 네이버 블로그에 발행합니다."""
    writer = AIWriter()
    blog_client = NaverBlogClient()

    print(f"\n글 생성 중: {topic}")
    post = writer.generate_post(topic, keywords)

    print(f"제목: {post['title']}")
    print(f"본문 길이: {len(post['content'])}자")
    print()

    result = blog_client.publish(post["title"], post["content"])
    print(f"발행 완료: {result}")


def auth_flow() -> None:
    """네이버 OAuth 인증 플로우를 안내합니다."""
    blog_client = NaverBlogClient()
    auth_url = blog_client.get_auth_url()

    print("\n=== 네이버 블로그 인증 ===")
    print("1. 아래 URL을 브라우저에서 열어 인증을 완료하세요:")
    print(f"   {auth_url}")
    print()
    print("2. 인증 후 리다이렉트된 URL에서 'code' 파라미터 값을 복사하세요.")

    code = input("\n인증 코드를 입력하세요: ").strip()
    if not code:
        print("인증 코드가 입력되지 않았습니다.")
        return

    access_token = blog_client.get_access_token(code)
    print(f"\nAccess Token: {access_token}")
    print("\n이 토큰을 .env 파일의 NAVER_ACCESS_TOKEN에 설정하세요.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="자동 블로그 글 작성 및 네이버 블로그 업로드 프로그램"
    )
    subparsers = parser.add_subparsers(dest="command", help="실행할 명령")

    # write 명령어
    write_parser = subparsers.add_parser("write", help="블로그 글 작성 및 발행")
    write_parser.add_argument("topic", help="블로그 글 주제")
    write_parser.add_argument(
        "-k", "--keywords", nargs="+", help="SEO 키워드 목록", default=None
    )

    # auth 명령어
    subparsers.add_parser("auth", help="네이버 블로그 OAuth 인증")

    # schedule 명령어
    schedule_parser = subparsers.add_parser("schedule", help="스케줄링 모드로 실행")
    schedule_parser.add_argument(
        "topics_file", help="주제 목록 파일 경로 (한 줄에 하나씩)"
    )
    schedule_parser.add_argument(
        "-t", "--time", default="09:00", help="매일 실행 시각 (기본값: 09:00)"
    )

    args = parser.parse_args()

    if args.command == "write":
        errors = Config.validate()
        if errors:
            for e in errors:
                print(f"[오류] {e}")
            sys.exit(1)
        write_and_publish(args.topic, args.keywords)

    elif args.command == "auth":
        auth_flow()

    elif args.command == "schedule":
        errors = Config.validate()
        if errors:
            for e in errors:
                print(f"[오류] {e}")
            sys.exit(1)
        run_scheduler(args.topics_file, args.time)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
