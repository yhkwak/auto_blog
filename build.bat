@echo off
chcp 65001 > nul
echo.
echo ============================================================
echo   Auto Blog .exe 빌드 스크립트
echo ============================================================
echo.

REM ── Python 설치 확인 ────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo        https://www.python.org/downloads/ 에서 설치 후 다시 실행하세요.
    echo        설치 시 "Add Python to PATH" 에 반드시 체크하세요!
    pause
    exit /b 1
)

echo [1/4] Python 확인 완료
python --version

echo.
echo [2/4] 필요한 패키지 설치 중...
pip install -r requirements.txt
pip install pyinstaller
if %errorlevel% neq 0 (
    echo [오류] 패키지 설치 실패. 인터넷 연결을 확인하세요.
    pause
    exit /b 1
)

echo.
echo [3/4] .exe 파일 빌드 중... (1~3분 소요)
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "AutoBlog" ^
    --hidden-import "anthropic" ^
    --hidden-import "auto_blog.config" ^
    --hidden-import "auto_blog.issue_writer" ^
    --hidden-import "auto_blog.opinion_writer" ^
    --hidden-import "auto_blog.naver_blog" ^
    --hidden-import "auto_blog.scheduler" ^
    --hidden-import "auto_blog.ai_writer" ^
    --hidden-import "schedule" ^
    --hidden-import "dotenv" ^
    --collect-all "anthropic" ^
    gui.py

if %errorlevel% neq 0 (
    echo [오류] 빌드 실패. 위 오류 메시지를 확인하세요.
    pause
    exit /b 1
)

echo.
echo [4/4] 완료!
echo.
echo ============================================================
echo   dist\AutoBlog.exe 파일이 생성되었습니다.
echo.
echo   사용 방법:
echo   1. dist 폴더 안의 AutoBlog.exe 를 원하는 곳에 복사합니다.
echo   2. AutoBlog.exe 를 실행합니다.
echo   3. [설정] 탭에서 API 키를 입력하고 저장합니다.
echo   4. 이슈 정리글 또는 내 생각 정리글 탭에서 글을 작성합니다.
echo ============================================================
echo.
pause
