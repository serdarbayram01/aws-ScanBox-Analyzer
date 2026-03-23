@echo off
REM ScanBox - AWS FinSecOps Analyzer - Windows Launcher

setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo   ============================================
echo    ScanBox - AWS FinSecOps Analyzer
echo   ============================================
echo.

REM -- Add common Python install paths to PATH --
set "PY_PATHS=%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python310;%ProgramFiles%\Python312;%ProgramFiles%\Python311;C:\Python312;C:\Python311"
set "PATH=%PATH%;%PY_PATHS%"

REM ============================================================
REM  PHASE 1: CHECK ALL PREREQUISITES
REM ============================================================

echo   Checking prerequisites...
echo   --------------------------------------------

set HAS_PYTHON=0
set HAS_PIP=0
set HAS_VENV=0
set HAS_DEPS=0
set HAS_AWS=0
set PYTHON_CMD=
set PY_VER=N/A

REM -- Check Python --
where python >nul 2>&1 && (
  for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
  set "PYTHON_CMD=python"
  set HAS_PYTHON=1
)
if !HAS_PYTHON! equ 0 (
  where python3 >nul 2>&1 && (
    for /f "tokens=2 delims= " %%v in ('python3 --version 2^>^&1') do set "PY_VER=%%v"
    set "PYTHON_CMD=python3"
    set HAS_PYTHON=1
  )
)
if !HAS_PYTHON! equ 0 (
  where py >nul 2>&1 && (
    for /f "tokens=2 delims= " %%v in ('py --version 2^>^&1') do set "PY_VER=%%v"
    set "PYTHON_CMD=py"
    set HAS_PYTHON=1
  )
)

REM -- Check pip --
if !HAS_PYTHON! equ 1 (
  !PYTHON_CMD! -m pip --version >nul 2>&1 && set HAS_PIP=1
)

REM -- Check venv --
if !HAS_PYTHON! equ 1 (
  !PYTHON_CMD! -c "import venv" >nul 2>&1 && set HAS_VENV=1
)

REM -- Check dependencies --
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe -c "import flask, boto3, pandas, reportlab" >nul 2>&1 && set HAS_DEPS=1
)

REM -- Check AWS CLI --
where aws >nul 2>&1 && set HAS_AWS=1

REM ============================================================
REM  PHASE 2: DISPLAY STATUS
REM ============================================================

echo.
echo   Prerequisites Status:
echo   --------------------------------------------

if !HAS_PYTHON! equ 1 ( echo     [OK] Python         : !PY_VER! ) else ( echo     [--] Python         : NOT INSTALLED )
if !HAS_PIP! equ 1    ( echo     [OK] pip            : Ready    ) else ( echo     [--] pip            : NOT FOUND )
if !HAS_VENV! equ 1   ( echo     [OK] venv           : Ready    ) else ( echo     [--] venv           : NOT FOUND )
if !HAS_DEPS! equ 1   ( echo     [OK] Dependencies   : Installed) else ( echo     [--] Dependencies   : Not installed )
if !HAS_AWS! equ 1    ( echo     [OK] AWS CLI        : Installed) else ( echo     [--] AWS CLI        : Not installed - optional )

echo   --------------------------------------------

REM -- If all required components ready, skip to server --
if !HAS_PYTHON! equ 0 goto :install_python
if !HAS_PIP! equ 0 goto :install_pip
if !HAS_DEPS! equ 0 goto :install_deps
echo.
echo   All prerequisites met.
goto :start_server

REM ============================================================
REM  PHASE 3: INSTALL MISSING COMPONENTS
REM ============================================================

:install_python
echo.
echo   Python 3.10+ is required to run ScanBox.
echo.
set /p CONFIRM="   Install Python automatically? (Y/N): "
if /i "!CONFIRM!" neq "Y" (
  echo.
  echo   Please install Python manually from https://www.python.org/downloads/
  echo   IMPORTANT: Check "Add Python to PATH" during installation.
  pause
  exit /b 1
)
echo.
echo   Step 1: Installing Python...
echo   ---------------------------------

REM Try winget first
where winget >nul 2>&1
if not errorlevel 1 (
  echo   Using winget...
  winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  goto :python_post_install
)

REM Fallback: PowerShell download
echo   Downloading Python 3.12 installer...
set "PY_INSTALLER=%TEMP%\python-3.12-installer.exe"
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '!PY_INSTALLER!'"
if not exist "!PY_INSTALLER!" (
  echo   [FAIL] Download failed. Install Python manually from python.org
  pause
  exit /b 1
)
echo   Running installer (adds to PATH)...
"!PY_INSTALLER!" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1
del "!PY_INSTALLER!" 2>nul

:python_post_install
REM Refresh PATH from registry
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%b"
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%b"
set "PATH=!USER_PATH!;!SYS_PATH!;%PY_PATHS%"

REM Find Python again
set HAS_PYTHON=0
where python >nul 2>&1 && ( set "PYTHON_CMD=python" & set HAS_PYTHON=1 )
if !HAS_PYTHON! equ 0 ( where python3 >nul 2>&1 && ( set "PYTHON_CMD=python3" & set HAS_PYTHON=1 ) )
if !HAS_PYTHON! equ 0 ( where py >nul 2>&1 && ( set "PYTHON_CMD=py" & set HAS_PYTHON=1 ) )

if !HAS_PYTHON! equ 0 (
  echo.
  echo   Python installed but not found in this terminal session.
  echo   Please CLOSE this window and run run.bat again.
  pause
  exit /b 1
)
for /f "tokens=2 delims= " %%v in ('!PYTHON_CMD! --version 2^>^&1') do set "PY_VER=%%v"
echo   [OK] Python !PY_VER! installed

:install_pip
if !HAS_PIP! equ 1 goto :install_deps
echo.
echo   Step 2: Installing pip...
echo   ---------------------------------
!PYTHON_CMD! -m ensurepip --upgrade >nul 2>&1
!PYTHON_CMD! -m pip --version >nul 2>&1
if errorlevel 1 (
  echo   Downloading get-pip.py...
  powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TEMP%\get-pip.py'"
  !PYTHON_CMD! "%TEMP%\get-pip.py"
  del "%TEMP%\get-pip.py" 2>nul
)
!PYTHON_CMD! -m pip --version >nul 2>&1
if errorlevel 1 (
  echo   [FAIL] Could not install pip.
  pause
  exit /b 1
)
echo   [OK] pip installed

:install_deps
if !HAS_DEPS! equ 1 goto :check_aws
echo.
echo   Step 3: Setting up virtual environment...
echo   ---------------------------------
if not exist ".venv\" (
  !PYTHON_CMD! -m venv .venv 2>nul
  if errorlevel 1 (
    !PYTHON_CMD! -m pip install -q virtualenv
    !PYTHON_CMD! -m virtualenv .venv
  )
)
echo   [OK] Virtual environment ready

call .venv\Scripts\activate.bat

echo.
echo   Step 4: Installing Python dependencies...
echo   ---------------------------------
pip install -q --upgrade pip 2>nul
pip install -q -r requirements.txt
if errorlevel 1 (
  echo   Retrying...
  pip install --no-cache-dir -r requirements.txt
)
echo   [OK] All dependencies installed

:check_aws
if !HAS_AWS! equ 1 goto :start_server
echo.
echo   AWS CLI is not installed (optional, needed for AWS operations).
set /p INSTALL_AWS="   Install AWS CLI? (Y/N): "
if /i "!INSTALL_AWS!" neq "Y" goto :start_server

echo   Installing AWS CLI...
where winget >nul 2>&1
if not errorlevel 1 (
  winget install Amazon.AWSCLI --accept-package-agreements --accept-source-agreements >nul 2>&1
  echo   [OK] AWS CLI installed. Configure with: aws configure
  goto :start_server
)
echo   Downloading AWS CLI installer...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://awscli.amazonaws.com/AWSCLIV2.msi' -OutFile '%TEMP%\AWSCLI.msi'"
msiexec /i "%TEMP%\AWSCLI.msi" /quiet
del "%TEMP%\AWSCLI.msi" 2>nul
echo   [OK] AWS CLI installed. Configure with: aws configure

REM ============================================================
REM  PHASE 4: START SERVER
REM ============================================================

:start_server
if not exist ".venv\Scripts\activate.bat" (
  echo   [FAIL] Virtual environment not found.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat

echo.
echo   ============================================
echo   Starting ScanBox at http://localhost:5100
echo   Press Ctrl+C to stop.
echo   ============================================
echo.

python app.py
pause
