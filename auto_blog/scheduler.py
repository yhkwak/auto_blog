import logging
import time
import schedule

logger = logging.getLogger(__name__)


def run_scheduler(topics_file: str, run_time: str, mode: str = "write") -> None:
    """주제 목록 파일에서 하나씩 읽어 매일 정해진 시간에 블로그 글을 발행합니다.

    Args:
        topics_file: 주제 목록 파일 경로 (한 줄에 주제 하나)
        run_time: 매일 실행 시각 (HH:MM 형식)
        mode: 글쓰기 모드 ("write" | "issue" | "opinion")
              - write: 범용 글쓰기
              - issue: 이슈 정리글 (조회수 최적화)
              - opinion: 내 생각 정리글 (opinion 모드에서는 파일 형식이 다름, 아래 참고)

    opinion 모드 파일 형식 (한 줄에 주제:::생각 형식):
        AI 시대의 직업 변화:::AI가 단순 반복 업무를 대체하고 있다. 판단력이 중요해졌다.
        재택근무의 장단점:::집중이 잘 되지만 협업이 어렵다. 루틴 관리가 핵심이다.
    """
    from .ai_writer import AIWriter
    from .issue_writer import IssueWriter
    from .opinion_writer import OpinionWriter
    from .naver_blog import NaverBlogClient

    with open(topics_file, encoding="utf-8") as f:
        raw_lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not raw_lines:
        print("주제 목록이 비어 있습니다.")
        return

    # opinion 모드는 "주제:::생각" 형식으로 파싱
    if mode == "opinion":
        items = []
        for line in raw_lines:
            if ":::" in line:
                topic, thoughts = line.split(":::", 1)
                items.append({"topic": topic.strip(), "thoughts": thoughts.strip()})
            else:
                print(f"[경고] opinion 모드에서는 '주제:::생각' 형식이 필요합니다. 건너뜀: {line}")
        if not items:
            print("유효한 항목이 없습니다.")
            return
    else:
        items = [{"topic": line} for line in raw_lines]

    mode_label = {"write": "범용", "issue": "이슈 정리", "opinion": "내 생각 정리"}[mode]
    state = {"index": 0}

    def job():
        if state["index"] >= len(items):
            print("모든 주제를 처리했습니다. 스케줄러를 종료합니다.")
            schedule.clear()
            return

        item = items[state["index"]]
        topic = item["topic"]
        logger.info(
            "[%s] 스케줄 실행 [%d/%d]: %s", mode_label, state["index"] + 1, len(items), topic
        )
        print(f"\n=== [{mode_label}] 스케줄 실행 [{state['index'] + 1}/{len(items)}] ===")
        print(f"주제: {topic}")

        try:
            blog_client = NaverBlogClient()

            if mode == "issue":
                writer = IssueWriter()
                post = writer.generate_post(topic)
            elif mode == "opinion":
                writer = OpinionWriter()
                post = writer.generate_post(topic, item["thoughts"])
            else:
                writer = AIWriter()
                post = writer.generate_post(topic)

            result = blog_client.publish(post["title"], post["content"])
            print(f"발행 완료: {post['title']}")
            logger.info("발행 성공: %s", result)
        except Exception:
            logger.exception("발행 실패: %s", topic)
            print(f"발행 실패: {topic}")

        state["index"] += 1

    schedule.every().day.at(run_time).do(job)

    print(f"\n스케줄러 시작: 매일 {run_time}에 실행 (모드: {mode_label})")
    print(f"총 {len(items)}개 주제 대기 중")
    print("종료하려면 Ctrl+C를 누르세요.\n")

    try:
        while schedule.jobs:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n스케줄러를 종료합니다.")
