# Versioning Strategy — ScanBox AWS FinSecOps Analyzer

This document defines the versioning rules for ScanBox. All maintainers should follow this guide when planning releases.

## Version Format

```
MAJOR.MINOR.PATCH
```

- **Single source of truth:** The `VERSION` file in the project root
- **Format:** [Semantic Versioning 2.0.0](https://semver.org/)
- **Current version:** Read from `VERSION` file, injected into `app.py` and About page at runtime

---

## Starting Point

| Version | Meaning |
|---|---|
| **1.0.0** | First public release. All 7 core modules functional: FinOps, SecOps, MapInventory, Topology, Advice, Health, About |

We start at `1.0.0` (not `0.x.x`) because the application is already feature-complete and production-usable.

---

## When to Bump Each Number

### PATCH (1.0.x) — Bug fixes & small improvements

Bump PATCH when the change is **invisible to the user's workflow**. No new features, no breaking changes.

| Change | Example | Version |
|---|---|---|
| Bug fix in existing module | Fix SecOps radar chart not rendering in Safari | 1.0.0 → 1.0.1 |
| CSS/UI fix | Fix dark mode text color on Health page | 1.0.1 → 1.0.2 |
| Performance improvement | Reduce MapInventory scan time by optimizing collectors | 1.0.2 → 1.0.3 |
| Dependency update (non-breaking) | Update boto3 from 1.28 to 1.34 | 1.0.3 → 1.0.4 |
| Translation fix | Fix typo in Turkish SecOps finding description | 1.0.4 → 1.0.5 |
| New SecOps check in existing module | Add S3 Object Lock check to `s3.py` | 1.0.5 → 1.0.6 |
| New MapInventory collector | Add AWS Backup collector | 1.0.6 → 1.0.7 |
| Security fix | Fix XSS in report filenames | 1.0.7 → 1.0.8 |

**Rule of thumb:** If users don't need to learn anything new, it's a PATCH.

### MINOR (1.x.0) — New features & enhancements

Bump MINOR when there is a **new capability the user can see and use**, but nothing existing breaks.

| Change | Example | Version |
|---|---|---|
| New SecOps inventory module | Add `redshift.py` — a whole new service to scan | 1.0.0 → 1.1.0 |
| New dashboard chart/visualization | Add cost forecast chart to FinOps | 1.1.0 → 1.2.0 |
| New report format | Add JSON export alongside HTML/CSV/PDF | 1.2.0 → 1.3.0 |
| New Topology view level | Add "Expert" level with flow logs | 1.3.0 → 1.4.0 |
| New Advice pillar or rule engine | Add custom rules support | 1.4.0 → 1.5.0 |
| New Health monitor | Add SSL certificate expiry monitoring | 1.5.0 → 1.6.0 |
| New compliance framework | Add SOC 2 framework to SecOps | 1.6.0 → 1.7.0 |
| New language support | Add German (DE) to i18n | 1.7.0 → 1.8.0 |
| Multi-user authentication | Add login/session support | 1.8.0 → 1.9.0 |
| New API endpoints | Add `/api/v1/export` REST API | 1.9.0 → 1.10.0 |
| Major UI redesign (non-breaking) | New dashboard layout with drag & drop | 1.10.0 → 1.11.0 |

**Rule of thumb:** If users get something new to explore/use, it's a MINOR. Resets PATCH to 0.

### MAJOR (x.0.0) — Breaking changes or new modules

Bump MAJOR when there is a **fundamental change** that could break existing workflows, integrations, or require users to take action.

| Change | Example | Version |
|---|---|---|
| New top-level module | Add "Compliance" as 8th module in sidebar | 1.x.x → 2.0.0 |
| Another new module | Add "Cost Forecasting" module | 2.x.x → 3.0.0 |
| Breaking API change | Rename `/secops/api/scan` to `/api/v2/secops/scan` | x.x.x → (x+1).0.0 |
| Breaking config change | Change from env vars to `config.yaml` | x.x.x → (x+1).0.0 |
| Python version requirement change | Require Python 3.11+ (was 3.8+) | x.x.x → (x+1).0.0 |
| Database migration | Switch from JSON file cache to SQLite | x.x.x → (x+1).0.0 |
| Complete UI framework change | Migrate from vanilla JS to React | x.x.x → (x+1).0.0 |
| Report format change (breaking) | Change PDF layout incompatible with old templates | x.x.x → (x+1).0.0 |

**Rule of thumb:** If users must change how they use the app, or the sidebar gains a new module, it's a MAJOR. Resets MINOR and PATCH to 0.

---

## Decision Flowchart

```
Is this change BREAKING existing functionality?
├── YES → MAJOR (x+1).0.0
└── NO
    ├── Does it add a NEW top-level module (sidebar item)?
    │   ├── YES → MAJOR (x+1).0.0
    │   └── NO
    │       ├── Does it add a NEW user-facing feature?
    │       │   ├── YES → MINOR x.(y+1).0
    │       │   └── NO → PATCH x.y.(z+1)
    │       └── Is it a new SecOps/MapInventory sub-module only?
    │           ├── YES, single collector/check → PATCH x.y.(z+1)
    │           └── YES, entire new service module → MINOR x.(y+1).0
```

---

## Projected Version Roadmap

This is an **example** of how versions might evolve:

```
1.0.0   Initial release (current)
1.0.1   Bug fixes, CSS tweaks
1.0.2   New S3 checks in SecOps
1.1.0   Add Redshift SecOps inventory module
1.2.0   Add cost forecast chart to FinOps
1.3.0   Add SOC 2 compliance framework
1.3.1   Fix Advice report PDF layout
1.4.0   Add JSON export format
1.5.0   Add multi-language support (DE)
2.0.0   Add "Compliance Center" module (new sidebar item)
2.1.0   Add scheduled scan support
2.2.0   Add email notification system
3.0.0   Add "Cost Forecasting" module (new sidebar item)
3.0.1   Bug fixes
3.1.0   Add SSO provider configuration UI
4.0.0   Migrate to REST API v2 (breaking API change)
```

---

## Release Process

### 1. Update VERSION file

```bash
echo "1.1.0" > VERSION
```

### 2. Update CHANGELOG.md

Move items from `[Unreleased]` to the new version section:

```markdown
## [1.1.0] - 2025-04-15

### Added
- Redshift security inventory module with 8 checks (SecOps)
- New "Database Security" section in SecOps radar chart

### Fixed
- MapInventory scan timeout not properly cancelling remaining tasks
```

### 3. Update README.md (if needed)

Update the "Latest" version under the Changelog section if it's a notable release.

### 4. Commit and tag

```bash
git add VERSION CHANGELOG.md README.md
git commit -m "release: v1.1.0 — add Redshift SecOps module"
git tag -a v1.1.0 -m "v1.1.0 — Add Redshift SecOps inventory module"
git push origin main --tags
```

### 5. Create GitHub Release

```bash
gh release create v1.1.0 \
  --title "v1.1.0 — Redshift Security Scanning" \
  --notes-file CHANGELOG_EXCERPT.md
```

Or create the release manually on GitHub from the tag.

---

## Special Cases

### Multiple changes in one release

If a release includes both bug fixes AND new features, use the **highest** bump:
- 3 bug fixes + 1 new feature = **MINOR** (not PATCH)
- 2 new features + 1 breaking change = **MAJOR** (not MINOR)

### Pre-release versions (optional, for future use)

If you want beta testing before a major release:
```
2.0.0-beta.1    First beta of v2
2.0.0-beta.2    Second beta
2.0.0-rc.1      Release candidate
2.0.0           Final release
```

### Hotfix workflow

For urgent fixes on a released version:
```bash
git checkout -b hotfix/1.0.1 v1.0.0
# fix the bug
echo "1.0.1" > VERSION
git commit -am "fix: critical XSS in report download"
git tag -a v1.0.1 -m "v1.0.1 — Security hotfix"
git checkout main
git merge hotfix/1.0.1
```

---

## Module vs. Version Mapping

Since ScanBox is module-based, here's a clear mapping:

| What changed | Where | Version bump |
|---|---|---|
| New check inside `inventory/s3.py` | SecOps sub-module | PATCH |
| New file `inventory/redshift.py` | SecOps new service | MINOR |
| New collector `collectors/backup.py` | MapInventory collector | PATCH |
| New view level in Topology | Topology feature | MINOR |
| New WAFR rule in `wafr_knowledge.py` | Advice rule | PATCH |
| New monitoring thread in Health | Health feature | MINOR |
| Entirely new sidebar module | New Blueprint | **MAJOR** |
