import argparse
import logging
import sys

from .config import Config
from .ai_writer import AIWriter
from .issue_writer import IssueWriter
from .opinion_writer import OpinionWriter
from .naver_blog import NaverBlogClient
from .scheduler import run_scheduler
from .trend_finder import TrendFinder

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


def write_issue_and_publish(topic: str, keywords: list[str] | None = None) -> None:
    """이슈 정리글을 생성하고 네이버 블로그에 발행합니다."""
    writer = IssueWriter()
    blog_client = NaverBlogClient()

    print(f"\n[이슈 정리글] 생성 중: {topic}")
    post = writer.generate_post(topic, keywords)

    print(f"제목: {post['title']}")
    print(f"본문 길이: {len(post['content'])}자")
    print()

    result = blog_client.publish(post["title"], post["content"])
    print(f"발행 완료: {result}")


def write_auto_trending_and_publish() -> None:
    """트렌드를 자동 분석해 가장 조회수가 높을 이슈 정리글을 생성·발행합니다."""
    print("\n[자동 트렌드 분석] X, 네이버 뉴스, 구글 트렌드 기반으로 주제 선정 중...")

    finder = TrendFinder()
    topic, keywords, reason = finder.get_best_topic()

    print(f"  ▸ 선정된 주제: {topic}")
    print(f"  ▸ SEO 키워드: {', '.join(keywords)}")
    if reason:
        print(f"  ▸ 선정 이유: {reason}")
    print()

    writer = IssueWriter()
    blog_client = NaverBlogClient()

    print(f"[이슈 정리글] 네이버 인기 형식으로 생성 중...")
    post = writer.generate_post(topic, keywords)

    print(f"제목: {post['title']}")
    print(f"본문 길이: {len(post['content'])}자")
    print()

    result = blog_client.publish(post["title"], post["content"])
    print(f"발행 완료: {result}")


def write_opinion_and_publish(
    topic: str, thoughts: str, keywords: list[str] | None = None
) -> None:
    """개인 의견 글을 생성하고 네이버 블로그에 발행합니다."""
    writer = OpinionWriter()
    blog_client = NaverBlogClient()

    print(f"\n[내 생각 정리글] 생성 중: {topic}")
    post = writer.generate_post(topic, thoughts, keywords)

    print(f"제목: {post['title']}")
    print(f"본문 길이: {len(post['content'])}자")
    print()

    result = blog_client.publish(post["title"], post["content"])
    print(f"발행 완료: {result}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="자동 블로그 글 작성 및 네이버 블로그 업로드 프로그램"
    )
    subparsers = parser.add_subparsers(dest="command", help="실행할 명령")

    # write 명령어 (기존 범용)
    write_parser = subparsers.add_parser("write", help="범용 블로그 글 작성 및 발행")
    write_parser.add_argument("topic", help="블로그 글 주제")
    write_parser.add_argument(
        "-k", "--keywords", nargs="+", help="SEO 키워드 목록", default=None
    )

    # issue 명령어 (이슈 정리글)
    issue_parser = subparsers.add_parser(
        "issue", help="이슈/트렌드 정리글 작성 및 발행 (조회수 최적화)"
    )
    issue_parser.add_argument(
        "topic", help="이슈 주제 (예: '딥시크 AI 논란', '2025 부동산 정책 변화')"
    )
    issue_parser.add_argument(
        "-k", "--keywords", nargs="+", help="SEO 키워드 목록", default=None
    )

    # opinion 명령어 (내 생각 정리글)
    opinion_parser = subparsers.add_parser(
        "opinion", help="내 생각/의견 정리글 작성 및 발행"
    )
    opinion_parser.add_argument("topic", help="글의 주제")
    opinion_parser.add_argument(
        "thoughts",
        help="핵심 생각, 경험, 의견을 자유롭게 입력 (예: '요즘 AI 때문에 업무가 많이 바뀌었다. 단순 반복은 줄었지만 판단력이 더 중요해졌다.')",
    )
    opinion_parser.add_argument(
        "-k", "--keywords", nargs="+", help="SEO 키워드 목록", default=None
    )

    # auto 명령어 (자동 트렌드 분석 + 작성 + 발행)
    subparsers.add_parser(
        "auto",
        help="트렌드 자동 분석 후 가장 조회수 높을 이슈 정리글 작성 및 발행 (주제 입력 불필요)",
    )

    # schedule 명령어
    schedule_parser = subparsers.add_parser("schedule", help="스케줄링 모드로 실행")
    schedule_parser.add_argument(
        "topics_file", help="주제 목록 파일 경로 (한 줄에 하나씩)"
    )
    schedule_parser.add_argument(
        "-t", "--time", default="09:00", help="매일 실행 시각 (기본값: 09:00)"
    )
    schedule_parser.add_argument(
        "--mode",
        choices=["issue", "opinion", "write"],
        default="write",
        help="글쓰기 모드 선택 (기본값: write)",
    )

    args = parser.parse_args()

    if args.command == "write":
        errors = Config.validate()
        if errors:
            for e in errors:
                print(f"[오류] {e}")
            sys.exit(1)
        write_and_publish(args.topic, args.keywords)

    elif args.command == "issue":
        errors = Config.validate()
        if errors:
            for e in errors:
                print(f"[오류] {e}")
            sys.exit(1)
        write_issue_and_publish(args.topic, args.keywords)

    elif args.command == "opinion":
        errors = Config.validate()
        if errors:
            for e in errors:
                print(f"[오류] {e}")
            sys.exit(1)
        write_opinion_and_publish(args.topic, args.thoughts, args.keywords)

    elif args.command == "auto":
        errors = Config.validate()
        if errors:
            for e in errors:
                print(f"[오류] {e}")
            sys.exit(1)
        write_auto_trending_and_publish()

    elif args.command == "schedule":
        errors = Config.validate()
        if errors:
            for e in errors:
                print(f"[오류] {e}")
            sys.exit(1)
        run_scheduler(args.topics_file, args.time, args.mode)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
