"""네이버 블로그 자동 발행 (Selenium + SmartEditor ONE)

핵심 구조:
  blog.naver.com/{id}/postwrite
  └── iframe#mainFrame (SmartEditor ONE 전체)
      ├── .se-documentTitle-editView  ← 제목 입력
      └── .se-section-text            ← 본문 입력

Selenium은 기본적으로 메인 문서만 탐색하므로,
에디터 조작 전에 반드시 switch_to.frame(iframe) 필요.
발행 버튼은 iframe 밖 메인 문서에 있으므로
조작 후 switch_to.default_content() 복귀.
"""
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

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


class NaverBlogClient:
    """Selenium으로 네이버 블로그에 글을 자동 발행합니다."""

    NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"

    def __init__(self):
        self.naver_id = Config.NAVER_ID
        self.naver_pw = Config.NAVER_PASSWORD

    # ── WebDriver ──────────────────────────────────────────────────────────

    def _create_driver(self) -> webdriver.Chrome:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(f"--user-agent={random.choice(_USER_AGENTS)}")
        options.add_argument("--disable-infobars")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        # 클립보드 권한 허용
        options.add_argument("--enable-clipboard")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # NOTE: --user-data-dir을 사용하면 기존 Chrome 인스턴스와 충돌할 수 있습니다.
        # 충돌 문제가 생기면 아래 두 줄을 주석 처리하세요.
        profile_dir = os.path.join(os.path.expanduser("~"), ".auto_blog_chrome_profile")
        options.add_argument(f"--user-data-dir={profile_dir}")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                    Object.defineProperty(navigator, 'languages',
                        {get: () => ['ko-KR','ko','en-US','en']});
                    window.chrome = {runtime: {}};
                """
            },
        )
        driver.implicitly_wait(0)  # explicit wait만 사용
        return driver

    # ── 로그인 ────────────────────────────────────────────────────────────

    def _login(self, driver: webdriver.Chrome) -> None:
        """네이버 로그인. 클립보드 붙여넣기로 자동화 탐지를 우회합니다."""
        import pyperclip

        driver.get(self.NAVER_LOGIN_URL)
        time.sleep(2)

        id_el = self._find_any(driver, [
            (By.ID, "id"),
            (By.CSS_SELECTOR, "input[name='id']"),
        ], timeout=10)
        if not id_el:
            raise RuntimeError("네이버 로그인: ID 입력란을 찾을 수 없습니다.")
        id_el.click()
        time.sleep(0.3)
        pyperclip.copy(self.naver_id)
        id_el.send_keys(Keys.CONTROL, "v")
        time.sleep(0.3)

        pw_el = self._find_any(driver, [
            (By.ID, "pw"),
            (By.CSS_SELECTOR, "input[name='pw']"),
        ], timeout=5)
        if not pw_el:
            raise RuntimeError("네이버 로그인: PW 입력란을 찾을 수 없습니다.")
        pw_el.click()
        time.sleep(0.2)
        pyperclip.copy(self.naver_pw)
        pw_el.send_keys(Keys.CONTROL, "v")
        time.sleep(0.3)

        login_btn = self._find_any(driver, [
            (By.ID, "log.login"),
            (By.CSS_SELECTOR, "button.btn_login"),
            (By.CSS_SELECTOR, "button[type='submit']"),
        ], timeout=5)
        if not login_btn:
            raise RuntimeError("네이버 로그인: 로그인 버튼을 찾을 수 없습니다.")
        login_btn.click()
        time.sleep(4)

        # 보안 기기 등록 팝업 자동 닫기
        try:
            WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[contains(.,'등록하지') or contains(.,'나중에') "
                    "or contains(.,'건너뛰기')]"))
            ).click()
            logger.info("보안 기기 등록 팝업 닫음")
            time.sleep(1)
        except Exception:
            pass

        if "nidlogin" in driver.current_url:
            raise RuntimeError(
                "네이버 로그인 실패: 아이디/비밀번호를 확인하고, "
                "2단계 인증이 켜져 있으면 해제해주세요."
            )
        logger.info("네이버 로그인 성공: %s", driver.current_url)

    # ── iframe 전환 ────────────────────────────────────────────────────────

    def _switch_to_editor_frame(self, driver: webdriver.Chrome) -> None:
        """스마트에디터 ONE이 로드된 iframe으로 전환합니다.

        네이버 블로그 글쓰기 페이지 구조:
          메인 문서
          └── iframe#mainFrame  ← 에디터 전체
              ├── 제목 입력란
              └── 본문 에디터
        """
        # iframe 로딩 대기 (최대 15초)
        iframe = None
        for selector in [
            (By.ID, "mainFrame"),
            (By.CSS_SELECTOR, "iframe#mainFrame"),
            (By.CSS_SELECTOR, "iframe[name='mainFrame']"),
            (By.CSS_SELECTOR, "iframe"),          # fallback: 페이지 첫 번째 iframe
        ]:
            try:
                iframe = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located(selector)
                )
                break
            except Exception:
                continue

        if not iframe:
            raise RuntimeError(
                "스마트에디터 iframe을 찾을 수 없습니다. "
                "글쓰기 페이지가 정상적으로 로드되었는지 확인하세요."
            )

        driver.switch_to.frame(iframe)
        logger.info("에디터 iframe 전환 완료")

        # 에디터 내부 로딩 대기
        time.sleep(2)

    # ── 클립보드 유틸 ─────────────────────────────────────────────────────

    @staticmethod
    def _paste_text(driver: webdriver.Chrome, text: str) -> None:
        """pyperclip → 클립보드 → Ctrl+V 붙여넣기."""
        import pyperclip
        pyperclip.copy(text)
        time.sleep(0.3)
        ActionChains(driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
        time.sleep(0.3)

    @staticmethod
    def _paste_html(driver: webdriver.Chrome, html_content: str, plain_text: str) -> bool:
        """Clipboard API로 HTML+텍스트를 클립보드에 쓴 뒤 Ctrl+V.
        성공하면 True, 실패하면 False 반환."""
        try:
            driver.execute_cdp_cmd("Browser.grantPermissions", {
                "permissions": ["clipboardReadWrite", "clipboardSanitizedWrite"],
            })
            ok = driver.execute_async_script("""
                const cb = arguments[arguments.length - 1];
                try {
                    const item = new ClipboardItem({
                        'text/html': new Blob([arguments[0]], {type:'text/html'}),
                        'text/plain': new Blob([arguments[1]], {type:'text/plain'})
                    });
                    navigator.clipboard.write([item]).then(()=>cb(true)).catch(()=>cb(false));
                } catch(e){ cb(false); }
            """, html_content, plain_text)
            if ok:
                time.sleep(0.3)
                ActionChains(driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
                time.sleep(0.5)
                return True
        except Exception as e:
            logger.debug("HTML 클립보드 붙여넣기 실패: %s", e)
        return False

    @staticmethod
    def _html_to_plain(html_content: str) -> str:
        """HTML → 일반 텍스트 변환 (단락 구조 유지)."""
        t = re.sub(r"<br\s*/?>", "\n", html_content)
        t = re.sub(r"</p>", "\n\n", t)
        t = re.sub(r"</h[1-6]>", "\n\n", t)
        t = re.sub(r"</li>", "\n", t)
        t = re.sub(r"<[^>]+>", "", t)
        t = html_lib.unescape(t)
        return re.sub(r"\n{3,}", "\n\n", t).strip()

    # ── 엘리먼트 검색 ─────────────────────────────────────────────────────

    @staticmethod
    def _find_any(driver, selectors, timeout=5):
        """여러 셀렉터를 순차 시도해 첫 번째로 보이는 엘리먼트를 반환합니다."""
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

    # ── 카테고리 선택 ─────────────────────────────────────────────────────

    def _select_category(self, driver: webdriver.Chrome, category_name: str) -> None:
        """카테고리 버튼을 찾아 선택합니다. (메인 문서에서 호출)"""
        try:
            btn = self._find_any(driver, [
                (By.CSS_SELECTOR, "button.se-publish-category-btn"),
                (By.CSS_SELECTOR, "button[class*='category']"),
                (By.XPATH, "//button[contains(.,'카테고리')]"),
            ], timeout=5)
            if not btn:
                logger.warning("카테고리 버튼 없음 → 기본 카테고리로 발행")
                return

            btn.click()
            time.sleep(1)

            for item in driver.find_elements(
                By.XPATH, f"//*[normalize-space(text())='{category_name}']"
            ):
                if item.is_displayed():
                    item.click()
                    logger.info("카테고리 선택: %s", category_name)
                    return

            logger.warning("카테고리 '%s' 없음 → 기본 카테고리로 발행", category_name)
        except Exception as e:
            logger.warning("카테고리 선택 오류 (무시): %s", e)

    # ── 스크린샷 ──────────────────────────────────────────────────────────

    @staticmethod
    def _screenshot(driver: webdriver.Chrome, prefix: str = "debug") -> None:
        from pathlib import Path
        from datetime import datetime
        base = Path(__file__).resolve().parent.parent / "logs"
        base.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = str(base / f"{prefix}_{ts}.png")
        try:
            driver.save_screenshot(path)
            logger.info("스크린샷 저장: %s", path)
        except Exception:
            pass

    # ── 메인 발행 로직 ────────────────────────────────────────────────────

    def publish(self, title: str, content: str, category_name: str = "") -> dict:
        """네이버 블로그에 글을 발행합니다.

        흐름:
          1. 로그인
          2. 글쓰기 페이지 이동
          3. [메인 문서] 팝업 처리 / 카테고리 선택
          4. [iframe 전환] 제목 입력
          5. [iframe] 본문 입력
          6. [메인 문서 복귀] 발행 버튼 클릭
          7. 발행 확인
        """
        logger.info("===== 네이버 블로그 발행 시작: %s =====", title)
        driver = self._create_driver()

        try:
            # ── Step 1: 로그인 ──────────────────────────────────────────
            logger.info("[1/7] 네이버 로그인 중...")
            self._login(driver)

            # ── Step 2: 글쓰기 페이지 이동 ──────────────────────────────
            logger.info("[2/7] 글쓰기 페이지 이동 중...")
            write_url = f"https://blog.naver.com/{self.naver_id}/postwrite"
            driver.get(write_url)
            time.sleep(5)
            logger.info("  현재 URL: %s", driver.current_url)
            self._screenshot(driver, "step2_write_page")

            # ── Step 3: 메인 문서에서 팝업/카테고리 처리 ─────────────────
            logger.info("[3/7] 팝업 처리 및 카테고리 선택 중...")
            try:
                WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH,
                        "//button[contains(.,'새로 작성') or contains(.,'새로작성')]"))
                ).click()
                logger.info("  '작성 중인 글' 팝업 닫음")
                time.sleep(1)
            except Exception:
                pass

            if category_name:
                self._select_category(driver, category_name)
                time.sleep(0.5)

            # ── Step 4: iframe 전환 → 제목 입력 ─────────────────────────
            logger.info("[4/7] 에디터 iframe 전환 및 제목 입력 중...")
            self._switch_to_editor_frame(driver)
            self._screenshot(driver, "step4_inside_iframe")

            # 제목 입력 영역 클릭
            title_el = self._find_any(driver, [
                # 플레이스홀더 (비어있을 때)
                (By.CSS_SELECTOR, ".se-documentTitle-editView .se-placeholder"),
                # 실제 편집 영역
                (By.CSS_SELECTOR, ".se-documentTitle-editView .se-text-paragraph"),
                (By.CSS_SELECTOR, ".se-documentTitle-editView"),
                # 대체 셀렉터
                (By.CSS_SELECTOR, "[class*='documentTitle'] p"),
                (By.CSS_SELECTOR, "[class*='documentTitle']"),
            ], timeout=10)

            if title_el:
                logger.info("  제목 영역 발견: %s", title_el.get_attribute("class"))
                driver.execute_script("arguments[0].click();", title_el)
                time.sleep(0.5)
            else:
                logger.warning("  제목 영역을 찾지 못함 → 좌표 클릭 fallback")
                self._screenshot(driver, "step4_title_not_found")
                # 에디터 최상단 클릭
                ActionChains(driver).move_to_element_with_offset(
                    driver.find_element(By.TAG_NAME, "body"), 0, 0
                ).click().perform()
                time.sleep(0.5)

            # 전체 선택 후 붙여넣기 (기존 내용 덮어쓰기)
            ActionChains(driver).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
            time.sleep(0.2)
            self._paste_text(driver, title)
            logger.info("  제목 입력 완료: %s", title)
            time.sleep(0.5)

            # ── Step 5: 본문 영역으로 이동 및 입력 ─────────────────────
            logger.info("[5/7] 본문 입력 중...")

            # (A) 제목에서 본문으로 전환: Enter → Tab 순서로 시도
            #     SmartEditor ONE에서 Enter는 제목→본문 이동,
            #     Tab도 다음 편집 영역으로 포커스 이동.
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            time.sleep(0.5)
            ActionChains(driver).send_keys(Keys.TAB).perform()
            time.sleep(0.5)

            # (B) 본문 영역을 직접 찾아 ActionChains 클릭 (포커스 확보)
            body_el = self._find_any(driver, [
                # 본문 첫 번째 단락
                (By.CSS_SELECTOR, ".se-section-text .se-text-paragraph"),
                (By.CSS_SELECTOR, ".se-component-content .se-text-paragraph"),
                (By.CSS_SELECTOR, ".se-documentContent .se-text-paragraph"),
                (By.CSS_SELECTOR, "[class*='sectionText'] p"),
                # 플레이스홀더
                (By.CSS_SELECTOR, ".se-section-text .se-placeholder"),
                # contenteditable 본문 전체
                (By.CSS_SELECTOR, ".se-section-text .se-component-content"),
            ], timeout=5)

            if body_el:
                logger.info("  본문 영역 발견: %s", body_el.get_attribute("class"))
                # ActionChains 클릭 (JS click이 아닌 실제 마우스 클릭으로 포커스 확보)
                try:
                    ActionChains(driver).move_to_element(body_el).click().perform()
                except Exception:
                    driver.execute_script("arguments[0].click();", body_el)
                time.sleep(0.3)
                # 혹시 선택된 내용이 있으면 해제
                ActionChains(driver).send_keys(Keys.END).perform()
            else:
                logger.warning("  본문 영역을 찾지 못함 → Enter/Tab으로 이미 이동된 상태")
                self._screenshot(driver, "step5_body_not_found")
            time.sleep(0.5)

            self._screenshot(driver, "step5_before_paste")

            plain_text = self._html_to_plain(content)
            if self._paste_html(driver, content, plain_text):
                logger.info("  HTML 본문 붙여넣기 완료 (서식 유지)")
            else:
                logger.info("  HTML 붙여넣기 불가 → 평문 텍스트로 붙여넣기")
                self._paste_text(driver, plain_text)

            time.sleep(1)
            self._screenshot(driver, "step5_after_body")

            # ── Step 6: 메인 문서로 복귀 → 발행 버튼 ─────────────────────
            logger.info("[6/7] 메인 문서로 복귀 후 발행 버튼 클릭 중...")
            driver.switch_to.default_content()
            time.sleep(0.5)

            publish_btn = self._find_any(driver, [
                (By.CSS_SELECTOR, "button.publish_btn__Y4pat"),
                (By.CSS_SELECTOR, "button[class*='publish_btn']"),
                (By.XPATH, "//button[contains(@class,'publish')]"),
                (By.XPATH, "//button[normalize-space(.)='발행']"),
                (By.XPATH, "//button[contains(.,'발행')]"),
                (By.XPATH, "//span[normalize-space(.)='발행']/parent::button"),
            ], timeout=10)

            if not publish_btn:
                self._screenshot(driver, "step6_no_publish_btn")
                raise RuntimeError(
                    "발행 버튼을 찾을 수 없습니다. "
                    "logs/ 폴더의 스크린샷을 확인해주세요."
                )

            logger.info("  발행 버튼 발견: %s", publish_btn.text)
            driver.execute_script("arguments[0].click();", publish_btn)
            time.sleep(2)

            # ── Step 7: 발행 확인 팝업 ────────────────────────────────────
            logger.info("[7/7] 발행 확인 팝업 처리 중...")
            confirm_btn = self._find_any(driver, [
                (By.CSS_SELECTOR, "button.confirm_btn__WEaBq"),
                (By.XPATH, "//button[contains(@class,'confirm')]"),
                (By.XPATH,
                 "//div[contains(@class,'layer') or contains(@class,'popup')]"
                 "//button[contains(.,'발행') or contains(.,'확인')]"),
            ], timeout=5)

            if confirm_btn:
                logger.info("  발행 확인 팝업 클릭: %s", confirm_btn.text)
                driver.execute_script("arguments[0].click();", confirm_btn)
                time.sleep(3)
            else:
                logger.info("  발행 확인 팝업 없음 → 즉시 발행된 것으로 판단")

            self._screenshot(driver, "step7_after_publish")
            logger.info("===== 발행 성공: %s =====", title)
            return {"status": "success", "title": title}

        except Exception as e:
            try:
                self._screenshot(driver, "error")
            except Exception:
                pass
            logger.error("발행 실패: %s", e)
            raise RuntimeError(f"블로그 발행 실패: {e}") from e
        finally:
            driver.quit()
