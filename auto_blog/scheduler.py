import logging
import time
import schedule

logger = logging.getLogger(__name__)


def run_scheduler(topics_file: str, run_time: str) -> None:
    """주제 목록 파일에서 하나씩 읽어 매일 정해진 시간에 블로그 글을 발행합니다.

    Args:
        topics_file: 주제 목록 파일 경로 (한 줄에 주제 하나)
        run_time: 매일 실행 시각 (HH:MM 형식)
    """
    from .ai_writer import AIWriter
    from .naver_blog import NaverBlogClient

    with open(topics_file, encoding="utf-8") as f:
        topics = [line.strip() for line in f if line.strip()]

    if not topics:
        print("주제 목록이 비어 있습니다.")
        return

    state = {"index": 0}

    def job():
        if state["index"] >= len(topics):
            print("모든 주제를 처리했습니다. 스케줄러를 종료합니다.")
            schedule.clear()
            return

        topic = topics[state["index"]]
        logger.info("스케줄 실행 [%d/%d]: %s", state["index"] + 1, len(topics), topic)
        print(f"\n=== 스케줄 실행 [{state['index'] + 1}/{len(topics)}] ===")
        print(f"주제: {topic}")

        try:
            writer = AIWriter()
            blog_client = NaverBlogClient()

            post = writer.generate_post(topic)
            result = blog_client.publish(post["title"], post["content"])

            print(f"발행 완료: {post['title']}")
            logger.info("발행 성공: %s", result)
        except Exception:
            logger.exception("발행 실패: %s", topic)
            print(f"발행 실패: {topic}")

        state["index"] += 1

    schedule.every().day.at(run_time).do(job)

    print(f"\n스케줄러 시작: 매일 {run_time}에 실행")
    print(f"총 {len(topics)}개 주제 대기 중")
    print("종료하려면 Ctrl+C를 누르세요.\n")

    try:
        while schedule.jobs:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n스케줄러를 종료합니다.")
