import html as html_lib
import logging
import os
import random
import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from .config import Config

logger = logging.getLogger(__name__)

# 실제 Chrome 사용자와 동일한 User-Agent 목록
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


class NaverBlogClient:
    """Selenium 브라우저 자동화로 네이버 블로그에 글을 발행합니다.

    스마트에디터 ONE은 가상 커서 + 숨겨진 입력 버퍼를 사용하므로
    send_keys()가 작동하지 않습니다.  pyperclip(클립보드) + Ctrl+V
    붙여넣기 방식으로 모든 텍스트를 입력합니다.
    """

    NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"

    def __init__(self):
        self.naver_id = Config.NAVER_ID
        self.naver_pw = Config.NAVER_PASSWORD

    # ── WebDriver 생성 ────────────────────────────────────────────────────

    def _create_driver(self) -> webdriver.Chrome:
        """자동화 감지를 우회한 Chrome WebDriver를 생성합니다."""
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(f"--user-agent={random.choice(_USER_AGENTS)}")
        options.add_argument("--disable-infobars")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Chrome 프로필을 유지하면 쿠키 기반 재로그인 등에 유리
        profile_dir = os.path.join(
            os.path.expanduser("~"), ".auto_blog_chrome_profile"
        )
        options.add_argument(f"--user-data-dir={profile_dir}")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # navigator.webdriver 속성 제거 + plugins/languages 스푸핑
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['ko-KR', 'ko', 'en-US', 'en']
                    });
                    window.chrome = {runtime: {}};
                """
            },
        )
        driver.implicitly_wait(10)
        return driver

    # ── 네이버 로그인 ─────────────────────────────────────────────────────

    def _login(self, driver: webdriver.Chrome) -> None:
        """네이버에 로그인합니다 (클립보드 붙여넣기 방식으로 자동화 감지 우회)."""
        import pyperclip

        driver.get(self.NAVER_LOGIN_URL)
        time.sleep(2)

        # ID 입력 — 여러 셀렉터 시도
        id_input = self._find_element_multi(driver, [
            (By.ID, "id"),
            (By.CSS_SELECTOR, "input[name='id']"),
            (By.CSS_SELECTOR, "#id"),
        ])
        if not id_input:
            raise RuntimeError("네이버 로그인 페이지에서 ID 입력란을 찾을 수 없습니다.")

        id_input.click()
        time.sleep(0.3 + random.random() * 0.3)
        pyperclip.copy(self.naver_id)
        id_input.send_keys(Keys.CONTROL, "v")
        time.sleep(0.3 + random.random() * 0.2)

        # PW 입력
        pw_input = self._find_element_multi(driver, [
            (By.ID, "pw"),
            (By.CSS_SELECTOR, "input[name='pw']"),
            (By.CSS_SELECTOR, "#pw"),
        ])
        if not pw_input:
            raise RuntimeError("네이버 로그인 페이지에서 PW 입력란을 찾을 수 없습니다.")

        pw_input.click()
        time.sleep(0.2 + random.random() * 0.3)
        pyperclip.copy(self.naver_pw)
        pw_input.send_keys(Keys.CONTROL, "v")
        time.sleep(0.3 + random.random() * 0.2)

        # 로그인 버튼 클릭
        login_btn = self._find_element_multi(driver, [
            (By.ID, "log.login"),
            (By.CSS_SELECTOR, "button.btn_login, button.btn_global"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//button[contains(text(),'로그인')]"),
        ])
        if not login_btn:
            raise RuntimeError("로그인 버튼을 찾을 수 없습니다.")

        login_btn.click()
        time.sleep(4)

        # "새로운 기기" 보안 알림 팝업 처리
        try:
            skip_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     "//button[contains(text(),'등록하지') or "
                     "contains(text(),'나중에') or "
                     "contains(text(),'건너뛰기')]")
                )
            )
            skip_btn.click()
            time.sleep(1)
            logger.info("새로운 기기 보안 알림 건너뜀")
        except Exception:
            pass

        # 로그인 실패 체크
        if "nidlogin" in driver.current_url:
            raise RuntimeError(
                "네이버 로그인 실패: 아이디 또는 비밀번호를 확인하세요.\n"
                "2단계 인증이 켜져 있으면 해제 후 다시 시도하세요."
            )

        logger.info("네이버 로그인 성공")

    # ── 엘리먼트 검색 유틸 ─────────────────────────────────────────────────

    @staticmethod
    def _find_element_multi(driver, selectors, timeout=5):
        """여러 셀렉터를 순차 시도해 첫 번째 발견된 엘리먼트를 반환합니다."""
        for by, sel in selectors:
            try:
                el = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((by, sel))
                )
                if el.is_displayed():
                    return el
            except Exception:
                continue
        return None

    # ── 클립보드 유틸 ─────────────────────────────────────────────────────

    @staticmethod
    def _clipboard_paste(driver: webdriver.Chrome, text: str) -> None:
        """pyperclip으로 클립보드에 복사 후 Ctrl+V 붙여넣기."""
        import pyperclip

        pyperclip.copy(text)
        time.sleep(0.2)
        ActionChains(driver) \
            .key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL) \
            .perform()

    @staticmethod
    def _clipboard_paste_html(
        driver: webdriver.Chrome, html_content: str, plain_text: str
    ) -> bool:
        """Clipboard API로 HTML을 클립보드에 설정 후 Ctrl+V 붙여넣기.

        HTML 서식(제목, 굵게, 목록 등)을 유지한 채 스마트에디터에 삽입합니다.
        Clipboard API 사용이 불가능하면 False를 반환합니다.
        """
        try:
            # Chrome DevTools Protocol로 클립보드 권한 부여
            driver.execute_cdp_cmd('Browser.grantPermissions', {
                'permissions': ['clipboardReadWrite', 'clipboardSanitizedWrite'],
            })

            success = driver.execute_async_script("""
                const callback = arguments[arguments.length - 1];
                try {
                    const item = new ClipboardItem({
                        'text/html':  new Blob([arguments[0]], {type: 'text/html'}),
                        'text/plain': new Blob([arguments[1]], {type: 'text/plain'})
                    });
                    navigator.clipboard.write([item])
                        .then(() => callback(true))
                        .catch(() => callback(false));
                } catch(e) {
                    callback(false);
                }
            """, html_content, plain_text)

            if success:
                time.sleep(0.3)
                ActionChains(driver) \
                    .key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL) \
                    .perform()
                return True
        except Exception as e:
            logger.debug("Clipboard API HTML 붙여넣기 실패: %s", e)

        return False

    @staticmethod
    def _html_to_text(html_content: str) -> str:
        """HTML → 텍스트 변환 (단락 구조 유지)."""
        text = re.sub(r'<br\s*/?\s*>', '\n', html_content)
        text = re.sub(r'</p>\s*', '\n\n', text)
        text = re.sub(r'</h[1-6]>\s*', '\n\n', text)
        text = re.sub(r'</li>\s*', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = html_lib.unescape(text)
        return re.sub(r'\n{3,}', '\n\n', text).strip()

    # ── 카테고리 선택 ─────────────────────────────────────────────────────

    def _select_category(
        self, driver: webdriver.Chrome, wait: WebDriverWait, category_name: str
    ) -> None:
        """카테고리를 선택합니다."""
        try:
            category_btn = self._find_element_multi(driver, [
                (By.CSS_SELECTOR, "button.se-publish-category-btn"),
                (By.CSS_SELECTOR, ".se-category button"),
                (By.CSS_SELECTOR, "button[class*='category']"),
                (By.CSS_SELECTOR, ".category_area button"),
                (By.XPATH, "//button[contains(., '카테고리')]"),
                (By.XPATH, "//span[contains(text(),'카테고리')]/ancestor::button"),
            ], timeout=5)

            if not category_btn:
                logger.warning("카테고리 버튼을 찾을 수 없습니다. 기본 카테고리로 발행합니다.")
                return

            category_btn.click()
            time.sleep(1)

            items = driver.find_elements(
                By.XPATH, f"//*[normalize-space(text())='{category_name}']"
            )
            for item in items:
                if item.is_displayed():
                    item.click()
                    time.sleep(0.5)
                    logger.info("카테고리 선택: %s", category_name)
                    return

            logger.warning(
                "카테고리 '%s'를 찾을 수 없습니다. 기본 카테고리로 발행합니다.",
                category_name,
            )
        except Exception as e:
            logger.warning("카테고리 선택 중 오류 (기본 카테고리로 진행): %s", e)

    # ── 디버깅 스크린샷 ────────────────────────────────────────────────────

    @staticmethod
    def _save_debug_screenshot(driver: webdriver.Chrome, prefix: str = "debug") -> str:
        """디버깅용 스크린샷을 저장하고 경로를 반환합니다."""
        import sys
        from pathlib import Path
        from datetime import datetime

        if getattr(sys, 'frozen', False):
            base = Path(sys.executable).parent
        else:
            base = Path(__file__).resolve().parent.parent

        debug_dir = base / "logs"
        debug_dir.mkdir(exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = str(debug_dir / f"{prefix}_{ts}.png")
        try:
            driver.save_screenshot(path)
            logger.info("디버그 스크린샷 저장: %s", path)
        except Exception:
            path = ""
        return path

    # ── 블로그 글 발행 ────────────────────────────────────────────────────

    def publish(self, title: str, content: str, category_name: str = "") -> dict:
        """네이버 블로그에 글을 발행합니다 (Selenium).

        스마트에디터 ONE의 가상 커서에 대응하여 모든 입력을
        클립보드 붙여넣기(pyperclip + Ctrl+V) 방식으로 수행합니다.

        Args:
            title: 블로그 글 제목
            content: 블로그 글 본문 (HTML)
            category_name: 카테고리 이름 (예: "AI글", "일상"). 비어있으면 기본 카테고리.

        Returns:
            발행 결과 딕셔너리
        """
        logger.info("네이버 블로그 발행 시작 (Selenium): %s", title)

        driver = self._create_driver()
        wait = WebDriverWait(driver, 20)

        try:
            # ── 1. 로그인 ──
            self._login(driver)

            # ── 2. 블로그 글쓰기 페이지 이동 ──
            write_url = f"https://blog.naver.com/{self.naver_id}/postwrite"
            driver.get(write_url)
            time.sleep(5)

            # ── 2-1. "작성 중인 글이 있습니다" 팝업 처리 ──
            try:
                popup_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH,
                         "//button[contains(text(),'새로 작성') or "
                         "contains(text(),'확인') or "
                         "contains(text(),'새로작성')]")
                    )
                )
                popup_btn.click()
                logger.info("'작성 중인 글' 팝업 닫음")
                time.sleep(1)
            except Exception:
                pass  # 팝업 없음

            # ── 2-2. 카테고리 선택 ──
            if category_name:
                self._select_category(driver, wait, category_name)
                time.sleep(0.5)

            # ── 3. 제목 입력 (클립보드 붙여넣기) ──
            title_el = self._find_element_multi(driver, [
                (By.CSS_SELECTOR, "span.se-placeholder.__se_placeholder"),
                (By.CSS_SELECTOR, ".se-documentTitle-editView .se-text-paragraph"),
                (By.CSS_SELECTOR, ".se-documentTitle-editView"),
                (By.CSS_SELECTOR, ".se-section-title .se-text-paragraph"),
                (By.CSS_SELECTOR, ".se-section-title"),
                (By.XPATH, "//*[contains(@class,'documentTitle')]//p"),
                (By.XPATH, "//*[contains(@class,'Title')]//span[@class='se-placeholder']"),
            ], timeout=8)

            if title_el:
                title_el.click()
            else:
                logger.warning("제목 영역을 찾지 못해 페이지 상단 클릭으로 대체합니다.")
                self._save_debug_screenshot(driver, "title_not_found")
                ActionChains(driver).move_by_offset(480, 200).click().perform()

            time.sleep(0.3)
            self._clipboard_paste(driver, title)
            logger.info("제목 입력 완료")
            time.sleep(0.5)

            # ── 4. 본문 영역으로 이동 ──
            # TAB 대신 직접 본문 영역 클릭 시도 (더 안정적)
            body_el = self._find_element_multi(driver, [
                (By.CSS_SELECTOR, ".se-component-content .se-text-paragraph"),
                (By.CSS_SELECTOR, ".se-documentContent .se-text-paragraph"),
                (By.CSS_SELECTOR, ".se-section-text .se-text-paragraph"),
            ], timeout=3)

            if body_el:
                body_el.click()
            else:
                # 폴백: TAB 키로 이동
                ActionChains(driver).send_keys(Keys.TAB).perform()
            time.sleep(0.5)

            # ── 5. 본문 입력 (Clipboard API HTML → 평문 텍스트 폴백) ──
            plain_text = self._html_to_text(content)

            html_pasted = self._clipboard_paste_html(driver, content, plain_text)
            if html_pasted:
                logger.info("HTML 본문 붙여넣기 완료 (서식 유지)")
            else:
                logger.info("HTML 붙여넣기 불가 → 텍스트로 붙여넣기")
                self._clipboard_paste(driver, plain_text)

            time.sleep(1)

            # ── 6. 발행 버튼 클릭 ──
            publish_btn = self._find_element_multi(driver, [
                (By.CSS_SELECTOR, "button.publish_btn__Y4pat"),
                (By.CSS_SELECTOR, "button[class*='publish_btn']"),
                (By.XPATH, "//button[contains(@class,'publish')]"),
                (By.XPATH, "//button[contains(text(),'발행')]"),
                (By.XPATH, "//span[contains(text(),'발행')]/ancestor::button"),
            ], timeout=8)

            if not publish_btn:
                self._save_debug_screenshot(driver, "publish_btn_not_found")
                raise RuntimeError("발행 버튼을 찾을 수 없습니다.")

            publish_btn.click()
            time.sleep(2)

            # ── 7. 발행 확인 팝업 ──
            confirm_btn = self._find_element_multi(driver, [
                (By.CSS_SELECTOR, "button.confirm_btn__WEaBq"),
                (By.XPATH,
                 "//button[contains(@class,'confirm') or "
                 "contains(@class,'ok_btn')]"),
                (By.XPATH,
                 "//div[contains(@class,'layer')]//button[contains(text(),'발행')]"),
                (By.XPATH,
                 "//div[contains(@class,'popup')]//button[contains(text(),'확인')]"),
            ], timeout=5)

            if confirm_btn:
                confirm_btn.click()
                time.sleep(3)
            else:
                logger.debug("발행 확인 팝업 없음 — 즉시 발행된 것으로 판단")

            logger.info("블로그 발행 성공: %s", title)
            return {"status": "success", "title": title}

        except Exception as e:
            self._save_debug_screenshot(driver, "error")
            error_msg = f"블로그 발행 실패: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        finally:
            driver.quit()
