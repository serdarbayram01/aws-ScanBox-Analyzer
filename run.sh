#!/usr/bin/env bash
# ScanBox - AWS FinSecOps Analyzer - macOS / Linux Launcher
# Auto-installs Python, pip, venv and dependencies

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON=""
MIN_PY_MAJOR=3
MIN_PY_MINOR=8

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

ok()   { echo -e "    ${GREEN}[OK]${NC} $1"; }
miss() { echo -e "    ${RED}[--]${NC} $1"; }
info() { echo -e "  ${CYAN}[i]${NC} $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; }

ask_yes() {
  local response
  echo -ne "  $1 (Y/n): "
  read -r response
  [[ -z "$response" || "$response" =~ ^[Yy] ]]
}

echo ""
echo -e "  ${CYAN}============================================${NC}"
echo -e "   ScanBox - AWS FinSecOps Analyzer"
echo -e "  ${CYAN}============================================${NC}"
echo ""

# -- Detect OS --
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then OS="macos"
elif [[ -f /etc/debian_version ]]; then OS="debian"
elif [[ -f /etc/redhat-release ]] || [[ -f /etc/fedora-release ]]; then OS="rhel"
elif [[ -f /etc/arch-release ]]; then OS="arch"
elif [[ -f /etc/alpine-release ]]; then OS="alpine"
elif [[ -f /etc/os-release ]]; then
  . /etc/os-release
  case "$ID" in
    ubuntu|debian|linuxmint|pop) OS="debian" ;;
    centos|rhel|fedora|rocky|alma|amzn) OS="rhel" ;;
    arch|manjaro) OS="arch" ;;
    alpine) OS="alpine" ;;
    suse|opensuse*) OS="suse" ;;
  esac
fi

# ============================================================
#  PHASE 1: CHECK ALL PREREQUISITES
# ============================================================

echo "  Checking prerequisites..."
echo "  --------------------------------------------"

HAS_PYTHON=0; HAS_PIP=0; HAS_VENV=0; HAS_DEPS=0; HAS_AWS=0
PY_VER=""

find_python() {
  for cmd in python3 python python3.13 python3.12 python3.11 python3.10; do
    if command -v "$cmd" &>/dev/null; then
      local ver major minor
      ver=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
      major=$(echo "$ver" | cut -d. -f1)
      minor=$(echo "$ver" | cut -d. -f2)
      if [[ "$major" -ge "$MIN_PY_MAJOR" && "$minor" -ge "$MIN_PY_MINOR" ]]; then
        PYTHON="$cmd"; PY_VER="$ver"; HAS_PYTHON=1
        return 0
      fi
    fi
  done
  return 1
}

find_python 2>/dev/null || true

if [[ $HAS_PYTHON -eq 1 ]]; then
  $PYTHON -m pip --version &>/dev/null 2>&1 && HAS_PIP=1 || true
  $PYTHON -c "import venv" &>/dev/null 2>&1 && HAS_VENV=1 || true
fi

if [[ -f "$VENV_DIR/bin/python" ]]; then
  "$VENV_DIR/bin/python" -c "import flask, boto3, pandas, reportlab" &>/dev/null 2>&1 && HAS_DEPS=1 || true
fi

command -v aws &>/dev/null 2>&1 && HAS_AWS=1 || true

# ============================================================
#  PHASE 2: DISPLAY STATUS
# ============================================================

echo ""
echo "  Prerequisites Status:"
echo "  --------------------------------------------"

if [[ $HAS_PYTHON -eq 1 ]]; then ok "Python         : $PY_VER ($PYTHON)"
else miss "Python         : NOT INSTALLED"; fi

if [[ $HAS_PIP -eq 1 ]]; then ok "pip            : Ready"
else miss "pip            : NOT FOUND"; fi

if [[ $HAS_VENV -eq 1 ]]; then ok "venv           : Ready"
else miss "venv           : NOT FOUND"; fi

if [[ $HAS_DEPS -eq 1 ]]; then ok "Dependencies   : Installed"
else miss "Dependencies   : Not installed"; fi

if [[ $HAS_AWS -eq 1 ]]; then ok "AWS CLI        : $(aws --version 2>&1 | head -1)"
else miss "AWS CLI        : Not installed (optional)"; fi

echo "  --------------------------------------------"

# -- If all required met, jump to server --
if [[ $HAS_PYTHON -eq 1 && $HAS_PIP -eq 1 && $HAS_DEPS -eq 1 ]]; then
  echo ""
  echo "  All prerequisites met."
  # Activate venv and start
  source "$VENV_DIR/bin/activate"
  echo ""
  echo -e "  ${CYAN}============================================${NC}"
  echo -e "  Starting ScanBox at ${GREEN}http://localhost:5100${NC}"
  echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop."
  echo -e "  ${CYAN}============================================${NC}"
  echo ""
  python "$SCRIPT_DIR/app.py"
  exit 0
fi

# ============================================================
#  PHASE 3: INSTALL MISSING COMPONENTS
# ============================================================

echo ""

# -- Step 1: Install Python --
if [[ $HAS_PYTHON -eq 0 ]]; then
  echo "  Python ${MIN_PY_MAJOR}.${MIN_PY_MINOR}+ is required."
  echo ""
  if ask_yes "Install Python automatically?"; then
    echo ""
    echo "  Step 1: Installing Python..."
    echo "  ---------------------------------"
    case "$OS" in
      macos)
        if command -v brew &>/dev/null; then
          brew install python@3.12
        else
          echo "  Installing Homebrew first..."
          /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
          [[ -f /opt/homebrew/bin/brew ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
          [[ -f /usr/local/bin/brew ]] && eval "$(/usr/local/bin/brew shellenv)"
          brew install python@3.12
        fi
        ;;
      debian)
        sudo apt-get update -qq
        sudo apt-get install -y python3 python3-pip python3-venv
        ;;
      rhel)
        if command -v dnf &>/dev/null; then
          sudo dnf install -y python3 python3-pip python3-venv 2>/dev/null || sudo dnf install -y python3 python3-pip
        else
          sudo yum install -y python3 python3-pip
        fi
        ;;
      arch)
        sudo pacman -Sy --noconfirm python python-pip python-virtualenv
        ;;
      alpine)
        sudo apk add --no-cache python3 py3-pip py3-virtualenv
        ;;
      suse)
        sudo zypper install -y python3 python3-pip python3-virtualenv
        ;;
      *)
        fail "Unsupported OS. Please install Python ${MIN_PY_MAJOR}.${MIN_PY_MINOR}+ manually."
        exit 1
        ;;
    esac

    if find_python 2>/dev/null; then
      ok "Python $PY_VER installed"
    else
      fail "Python installation failed. Please install manually."
      exit 1
    fi
  else
    echo ""
    case "$OS" in
      macos)  info "Run: brew install python@3.12" ;;
      debian) info "Run: sudo apt-get install python3 python3-pip python3-venv" ;;
      rhel)   info "Run: sudo dnf install python3 python3-pip" ;;
      arch)   info "Run: sudo pacman -S python python-pip" ;;
      alpine) info "Run: sudo apk add python3 py3-pip" ;;
      *)      info "Visit: https://www.python.org/downloads/" ;;
    esac
    exit 1
  fi
fi

# -- Step 2: Install pip --
if [[ $HAS_PIP -eq 0 ]]; then
  echo ""
  echo "  Step 2: Installing pip..."
  echo "  ---------------------------------"
  $PYTHON -m ensurepip --upgrade 2>/dev/null || {
    case "$OS" in
      debian)
        sudo apt-get install -y python3-pip
        ;;
      rhel)
        sudo dnf install -y python3-pip 2>/dev/null || sudo yum install -y python3-pip 2>/dev/null || true
        ;;
      *)
        info "Installing pip via get-pip.py..."
        curl -sSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
        $PYTHON /tmp/get-pip.py
        rm -f /tmp/get-pip.py
        ;;
    esac
  }
  if $PYTHON -m pip --version &>/dev/null; then
    ok "pip installed"
  else
    fail "Could not install pip."
    exit 1
  fi
fi

# -- Step 3: Install venv --
if [[ $HAS_VENV -eq 0 ]]; then
  echo ""
  echo "  Step 3: Installing venv module..."
  echo "  ---------------------------------"
  case "$OS" in
    debian)
      sudo apt-get install -y python3-venv
      ;;
    rhel)
      sudo dnf install -y python3-venv 2>/dev/null || $PYTHON -m pip install virtualenv
      ;;
    *)
      $PYTHON -m pip install virtualenv
      ;;
  esac
  ok "venv ready"
fi

# -- Step 4: Create venv and install dependencies --
echo ""
echo "  Step 4: Setting up virtual environment..."
echo "  ---------------------------------"
if [[ ! -d "$VENV_DIR" ]]; then
  $PYTHON -m venv "$VENV_DIR" 2>/dev/null || {
    info "venv failed, trying virtualenv..."
    $PYTHON -m pip install virtualenv
    $PYTHON -m virtualenv "$VENV_DIR"
  }
fi
ok "Virtual environment ready"

source "$VENV_DIR/bin/activate"

echo ""
echo "  Step 5: Installing Python dependencies..."
echo "  ---------------------------------"
pip install -q --upgrade pip 2>/dev/null || true
pip install -q -r "$SCRIPT_DIR/requirements.txt" || {
  info "Retrying with --no-cache-dir..."
  pip install --no-cache-dir -r "$SCRIPT_DIR/requirements.txt"
}
ok "All dependencies installed"

# -- Step 6: Offer AWS CLI (optional) --
if [[ $HAS_AWS -eq 0 ]]; then
  echo ""
  info "AWS CLI is not installed (optional, needed for AWS operations)."
  if ask_yes "Install AWS CLI?"; then
    case "$OS" in
      macos)
        if command -v brew &>/dev/null; then
          brew install awscli
        else
          info "Downloading AWS CLI installer..."
          curl -sSL "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o /tmp/AWSCLIV2.pkg
          sudo installer -pkg /tmp/AWSCLIV2.pkg -target /
          rm -f /tmp/AWSCLIV2.pkg
        fi
        ;;
      *)
        info "Downloading AWS CLI..."
        curl -sSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
        unzip -qo /tmp/awscliv2.zip -d /tmp/aws-install
        sudo /tmp/aws-install/aws/install --update 2>/dev/null || sudo /tmp/aws-install/aws/install
        rm -rf /tmp/awscliv2.zip /tmp/aws-install
        ;;
    esac
    if command -v aws &>/dev/null; then
      ok "AWS CLI installed ($(aws --version 2>&1 | head -1))"
      info "Configure with: aws configure"
    else
      info "AWS CLI may require a new terminal session."
    fi
  fi
fi

# ============================================================
#  PHASE 4: START SERVER
# ============================================================

echo ""
echo -e "  ${CYAN}============================================${NC}"
echo -e "  Starting ScanBox at ${GREEN}http://localhost:5100${NC}"
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop."
echo -e "  ${CYAN}============================================${NC}"
echo ""

python "$SCRIPT_DIR/app.py"
