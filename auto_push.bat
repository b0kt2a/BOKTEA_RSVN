@echo off
chcp 65001 >nul
setlocal

REM 1) 이 bat 파일이 있는 폴더로 이동
cd /d "%~dp0"

REM 2) 변경사항 없으면 종료
git status --porcelain > temp_git_status.txt
for /f %%A in ("temp_git_status.txt") do set size=%%~zA
del temp_git_status.txt
if "%size%"=="0" (
  echo 변경사항 없음. 종료!
  pause
  exit /b 0
)

REM 3) 최신 상태 한번 당기기(충돌 방지용)
git pull --rebase
if errorlevel 1 (
  echo pull 실패. 충돌/오류 확인 필요!
  pause
  exit /b 1
)

REM 4) add / commit / push
git add -A

set msg=auto update
set /p msg=커밋메세지(엔터=auto update): 
if "%msg%"=="" set msg=auto update

git commit -m "%msg%"
if errorlevel 1 (
  echo commit 할 게 없거나 오류가 있어!
  pause
  exit /b 1
)

git push
if errorlevel 1 (
  echo push 실패. 로그인/권한/네트워크 확인!
  pause
  exit /b 1
)

echo 성공! ✅
pause
