import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from .config import Config

logger = logging.getLogger(__name__)


class NaverBlogClient:
    """Selenium 브라우저 자동화로 네이버 블로그에 글을 발행합니다."""

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
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": (
                    "Object.defineProperty(navigator, 'webdriver', "
                    "{get: () => undefined});"
                )
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

        # ID 입력
        id_input = driver.find_element(By.ID, "id")
        id_input.click()
        time.sleep(0.2)
        pyperclip.copy(self.naver_id)
        id_input.send_keys(Keys.CONTROL, "v")
        time.sleep(0.3)

        # PW 입력
        pw_input = driver.find_element(By.ID, "pw")
        pw_input.click()
        time.sleep(0.2)
        pyperclip.copy(self.naver_pw)
        pw_input.send_keys(Keys.CONTROL, "v")
        time.sleep(0.3)

        # 로그인 버튼 클릭
        driver.find_element(By.ID, "log.login").click()
        time.sleep(3)

        # 로그인 실패 체크
        if "nidlogin" in driver.current_url:
            raise RuntimeError(
                "네이버 로그인 실패: 아이디 또는 비밀번호를 확인하세요.\n"
                "2단계 인증이 켜져 있으면 해제 후 다시 시도하세요."
            )

        logger.info("네이버 로그인 성공")

    # ── 블로그 글 발행 ────────────────────────────────────────────────────

    def _select_category(
        self, driver: webdriver.Chrome, wait: WebDriverWait, category_name: str
    ) -> None:
        """카테고리를 선택합니다."""
        try:
            # 카테고리 버튼 찾기 (여러 셀렉터 시도)
            category_btn = None
            css_selectors = [
                "button.se-publish-category-btn",
                ".se-category button",
                "button[class*='category']",
                ".category_area button",
            ]
            for sel in css_selectors:
                try:
                    category_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    break
                except Exception:
                    continue

            if not category_btn:
                try:
                    category_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//button[contains(., '카테고리')]")
                        )
                    )
                except Exception:
                    pass

            if not category_btn:
                logger.warning("카테고리 버튼을 찾을 수 없습니다. 기본 카테고리로 발행합니다.")
                return

            category_btn.click()
            time.sleep(1)

            # 카테고리 목록에서 이름으로 찾아 클릭
            items = driver.find_elements(
                By.XPATH, f"//*[normalize-space(text())='{category_name}']"
            )
            for item in items:
                if item.is_displayed():
                    item.click()
                    time.sleep(0.5)
                    logger.info("카테고리 선택: %s", category_name)
                    return

            logger.warning("카테고리 '%s'를 찾을 수 없습니다. 기본 카테고리로 발행합니다.", category_name)
        except Exception as e:
            logger.warning("카테고리 선택 중 오류 (기본 카테고리로 진행): %s", e)

    def publish(self, title: str, content: str, category_name: str = "") -> dict:
        """네이버 블로그에 글을 발행합니다 (Selenium).

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

            # ── 2-1. 카테고리 선택 ──
            if category_name:
                self._select_category(driver, wait, category_name)
                time.sleep(0.5)

            # ── 3. 제목 입력 ──
            try:
                title_placeholder = wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "span.se-placeholder.__se_placeholder")
                    )
                )
                title_placeholder.click()
            except Exception:
                title_area = driver.find_element(
                    By.CSS_SELECTOR, "div.se-documentTitle-editView"
                )
                title_area.click()

            time.sleep(0.5)
            active = driver.switch_to.active_element
            active.send_keys(title)
            time.sleep(0.5)

            # ── 4. 본문 영역으로 이동 (Tab) ──
            active.send_keys(Keys.TAB)
            time.sleep(1)

            # ── 5. HTML 본문 삽입 ──
            inserted = driver.execute_script(
                """
                try {
                    document.execCommand('insertHTML', false, arguments[0]);
                    return true;
                } catch(e) {
                    return false;
                }
                """,
                content,
            )

            if not inserted:
                driver.execute_script(
                    """
                    var el = document.querySelector('[contenteditable="true"]');
                    if (el) el.innerHTML = arguments[0];
                    """,
                    content,
                )

            time.sleep(1)

            # ── 6. 발행 버튼 클릭 ──
            publish_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@class, 'publish_btn')]")
                )
            )
            publish_btn.click()
            time.sleep(2)

            # ── 7. 발행 확인 팝업 ──
            try:
                confirm_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(@class, 'confirm_btn')]")
                    )
                )
                confirm_btn.click()
                time.sleep(3)
            except Exception:
                logger.debug("발행 확인 팝업 없음 — 즉시 발행된 것으로 판단")

            logger.info("블로그 발행 성공: %s", title)
            return {"status": "success", "title": title}

        except Exception as e:
            error_msg = f"블로그 발행 실패: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        finally:
            driver.quit()
