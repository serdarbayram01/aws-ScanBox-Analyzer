# Contributing to ScanBox — AWS FinSecOps Analyzer

Thank you for your interest in contributing! This guide will help you get started.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Architecture Overview](#architecture-overview)
- [Adding a SecOps Inventory Module](#adding-a-secops-inventory-module)
- [Adding a MapInventory Collector](#adding-a-mapinventory-collector)
- [Frontend Guidelines](#frontend-guidelines)
- [Code Style](#code-style)
- [Commit Convention](#commit-convention)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

---

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/serdarbayram01/aws-ScanBox-Analyzer.git
   cd aws-ScanBox-Analyzer
   ```
3. **Create a branch** for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate.bat     # Windows

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py                     # With AWS credentials
SCANBOX_DEMO=1 python app.py      # Demo mode (no credentials needed)
```

The app runs at **http://localhost:5100**. Changes to Python files require a server restart. Changes to HTML/JS/CSS are reflected on browser refresh.

---

## Architecture Overview

ScanBox is built as **8 independent Flask Blueprints** registered in `app.py`. Each module is self-contained — removing a module means deleting its folder and 2 lines in `app.py`.

### Key Files

| File | Role |
|---|---|
| `app.py` | Flask entry point, registers all blueprints, middleware (logging, rate limiting, CORS, error handlers) |
| `aws_client.py` | Shared boto3 wrapper for Cost Explorer, EC2, STS, Budgets — used by all modules |
| `report_generator.py` | FinOps-specific HTML/CSV/PDF export |
| `static/js/i18n.js` | Shared translations (TR/EN), icon definitions (`ICONS`), color palette (`PALETTE`), chart helpers |
| `static/css/theme.css` | All CSS — dark/light theme variables, component styles, responsive breakpoints |
| `templates/base.html` | Shared layout with sidebar navigation |

### Module Structure

Every module follows the same pattern:

```
modules/<name>/
├── routes.py              # Flask Blueprint with API endpoints
├── cache.py               # Per-profile result caching (optional)
├── report_generator.py    # HTML/CSV/PDF export (optional)
├── templates/             # Module-specific Jinja2 templates (optional)
└── data/                  # Cached scan results (gitignored)
```

---

## Adding a SecOps Inventory Module

SecOps currently scans 24 AWS services. To add a new one:

### 1. Create the inventory module

Create `modules/secops/inventory/<service_name>.py`:

```python
from .base import make_finding, not_available

def run_checks(session, exclude_defaults=True, regions=None):
    """
    Returns a list of findings for the service.

    Args:
        session: boto3.Session with the target profile
        exclude_defaults: Whether to skip default/AWS-managed resources
        regions: List of region codes to scan

    Returns:
        list[dict]: List of findings from make_finding()
    """
    findings = []

    try:
        client = session.client('your-service', region_name='us-east-1')
        # ... your checks here ...

        findings.append(make_finding(
            id='your-service-001',
            title='Check title in English',
            title_tr='Check title in Turkish',
            description='What this check verifies',
            description_tr='Turkish description',
            severity='HIGH',           # CRITICAL | HIGH | MEDIUM | LOW | INFO
            status='FAIL',             # PASS | FAIL | WARNING | NOT_AVAILABLE | MANUAL
            service='YourService',
            resource_id='resource-id-here',
            resource_type='AWS::Service::Resource',
            resource_name='resource-name',
            region='us-east-1',
            frameworks={
                'CIS': ['1.1'],
                'HIPAA': ['164.312(a)(1)'],
                'ISO27001': ['A.9.1.1'],
                'WAFR': {
                    'pillar': 'Security',
                    'controls': ['SEC-01']
                }
            },
            remediation='How to fix this issue',
            remediation_tr='Turkish remediation',
        ))

    except Exception as e:
        findings.append(not_available(
            id='your-service-001',
            service='YourService',
            error=str(e)
        ))

    return findings
```

### 2. Register in scanner.py

```python
# Import your module
from .inventory import your_service

# Add to SERVICES_ORDER list
SERVICES_ORDER = [..., 'YourService']

# Add to modules dict in run_scan()
modules = {
    ...,
    'YourService': your_service,
}
```

### 3. Add Cost Explorer mapping (if conditional)

In `scanner.py`, add entries so the smart scan knows when to skip your service:

```python
CE_SERVICE_MAP = {
    ...,
    'Amazon YourService': 'YourService',
}

_MODULE_TO_CE_PATTERNS = {
    ...,
    'YourService': ['Amazon YourService', 'AWS YourService'],
}
```

If the service should **always** scan (like IAM, S3), skip this step — it will scan regardless of Cost Explorer data.

---

## Adding a MapInventory Collector

MapInventory has 150+ collectors in `modules/mapinventory/collectors/`. To add a new one:

### 1. Create the collector

Create `modules/mapinventory/collectors/<service_name>.py`:

```python
def collect(session, regions, progress_callback=None):
    """
    Returns a list of resource dicts.

    Args:
        session: boto3.Session
        regions: List of region codes
        progress_callback: Optional callable for progress updates

    Returns:
        list[dict]: Discovered resources
    """
    resources = []

    for region in regions:
        try:
            client = session.client('your-service', region_name=region)
            # ... enumerate resources ...

            resources.append({
                'name': 'resource-name',
                'type': 'AWS::Service::Resource',
                'region': region,
                'service': 'YourService',
                'details': {
                    # Service-specific metadata
                }
            })
        except Exception:
            pass  # Log warning, don't raise

    return resources
```

### 2. Register in collector.py

Import and add your collector to the collectors list and CE keyword mapping (`_COLLECTOR_TO_CE_KEYWORDS`).

---

## Frontend Guidelines

### Do

- Use `escapeHtml()` from `i18n.js` for all user-facing content (XSS protection)
- Use `ICONS.*` from `i18n.js` for icons — **never emoji**
- Use `getChartColors()` and `applyChartDefaults()` from `i18n.js` for Chart.js
- Use `PALETTE` from `i18n.js` for consistent colors
- Use CSS custom properties from `theme.css` — never hardcode colors
- Dispatch `themechange` event when theme changes so charts re-render
- Use `encodeURIComponent()` for filenames in `href` attributes

### Don't

- Don't duplicate shared helpers (`escapeHtml`, `getChartColors`, `PALETTE`) in module JS files
- Don't use native `<select>` in SecOps — use the custom `.cfd` component
- Don't share global JS variables between modules — each module's JS is independent
- Don't add external JS dependencies — vanilla JS + Chart.js (CDN) only

### Translations

All UI strings must support Turkish and English. Add translations to `static/js/i18n.js`:

```javascript
const LANG = {
    your_key: { tr: 'Turkish text', en: 'English text' },
};
```

---

## Code Style

- **Python**: Follow PEP 8. Use descriptive variable names. Keep functions focused.
- **JavaScript**: Vanilla JS only (no frameworks, no TypeScript). Use `const`/`let`, never `var`.
- **CSS**: Use existing CSS custom properties. Add new variables to `:root` in `theme.css` if needed.
- **HTML**: Use Jinja2 templates extending `base.html`.
- **Error handling**: Use `not_available()` for permission errors in SecOps — never raise exceptions from inventory modules. Log warnings instead of silent `pass` in collectors.

---

## Commit Convention

Use clear, descriptive commit messages:

```
<type>(<scope>): <description>

# Examples:
feat(secops): add AWS Backup inventory module
fix(finops): correct region distribution for marketplace services
docs(readme): add topology module screenshots
refactor(mapinventory): switch to queue-based result collection
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `style`, `test`, `chore`

**Scopes:** `finops`, `secops`, `mapinventory`, `topology`, `advice`, `health`, `about`, `core`, `ui`

---

## Pull Request Process

1. **Ensure your branch is up to date** with `main`
2. **Test your changes** — run the app and verify the affected module works
3. **Run in demo mode** — ensure `SCANBOX_DEMO=1` doesn't break your changes
4. **Check both themes** — verify dark and light mode look correct
5. **Check both languages** — verify TR and EN translations work
6. **Create a PR** with:
   - Clear title describing the change
   - Description of what changed and why
   - Screenshots if UI changes are involved
7. **One module per PR** — keep changes focused. Cross-module changes should be discussed in an issue first.

---

## Reporting Issues

When opening an issue, please include:

- **Module affected** (FinOps, SecOps, MapInventory, etc.)
- **Steps to reproduce**
- **Expected vs. actual behavior**
- **Browser and OS** (for frontend issues)
- **Python version** (for backend issues)
- **Error logs** from `logs/requests.log` if applicable (redact any AWS account info)

---

Thank you for contributing to ScanBox!
