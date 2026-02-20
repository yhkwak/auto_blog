"""생성된 블로그 글을 로컬 파일로 저장합니다.

API 비용을 이미 사용한 뒤 발행 오류로 글이 유실되는 것을 방지합니다.
saved_posts/ 폴더에 날짜_제목.html 형식으로 저장됩니다.
"""

import logging
import re
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_save_dir() -> Path:
    """실행 방식에 관계없이 saved_posts 경로를 반환합니다."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "saved_posts"
    return Path(__file__).resolve().parent.parent / "saved_posts"


SAVE_DIR = _get_save_dir()


def save_post(title: str, content: str) -> Path:
    """글을 로컬 HTML 파일로 저장하고 경로를 반환합니다.

    저장 실패 시 RuntimeError를 발생시킵니다.
    """
    try:
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(
            f"저장 폴더를 만들 수 없습니다: {SAVE_DIR}\n"
            f"원인: {e}\n"
            "폴더 권한을 확인하세요."
        ) from e

    # 파일명에 사용할 수 없는 문자 제거
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:50].strip()
    if not safe_title:
        safe_title = "untitled"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{safe_title}.html"
    file_path = SAVE_DIR / filename

    html_doc = (
        "<!DOCTYPE html>\n<html lang='ko'>\n<head>\n"
        "<meta charset='utf-8'>\n"
        f"<title>{title}</title>\n"
        "</head>\n<body>\n"
        f"<h1>{title}</h1>\n"
        f"{content}\n"
        "</body>\n</html>"
    )

    try:
        file_path.write_text(html_doc, encoding="utf-8")
    except OSError as e:
        raise RuntimeError(
            f"파일 저장 실패: {file_path}\n원인: {e}"
        ) from e

    logger.info("글 로컬 저장 완료: %s  (%d bytes)", file_path, file_path.stat().st_size)
    return file_path
