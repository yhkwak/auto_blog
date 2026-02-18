"""생성된 블로그 글을 로컬 파일로 저장합니다.

API 비용을 이미 사용한 뒤 발행 오류로 글이 유실되는 것을 방지합니다.
saved_posts/ 폴더에 날짜_제목.html 형식으로 저장됩니다.
"""

import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

SAVE_DIR = Path(__file__).resolve().parent.parent / "saved_posts"


def save_post(title: str, content: str) -> Path:
    """글을 로컬 파일로 저장하고 경로를 반환합니다."""
    SAVE_DIR.mkdir(exist_ok=True)

    # 파일명에 쓸 수 없는 문자 제거
    safe_title = re.sub(r'[\\/*?:"<>|]', '', title)[:50].strip()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{safe_title}.html"

    file_path = SAVE_DIR / filename

    html_doc = (
        f"<!DOCTYPE html>\n<html lang='ko'>\n<head>\n"
        f"<meta charset='utf-8'>\n<title>{title}</title>\n</head>\n"
        f"<body>\n<h1>{title}</h1>\n{content}\n</body>\n</html>"
    )
    file_path.write_text(html_doc, encoding="utf-8")

    logger.info("글 로컬 저장 완료: %s", file_path)
    return file_path
