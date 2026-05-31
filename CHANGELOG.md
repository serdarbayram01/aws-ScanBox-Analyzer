# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

For versioning rules and release process, see [VERSIONING.md](VERSIONING.md).

---

## [Unreleased]

*Nothing yet — contributions welcome!*

---

## [2.0.0] - 2026-05-15

### Added — AWS Reference module (no AWS credentials required)

New sidebar module **AWS Reference** (`/awsref`) — sits between News and Health in the Modules group. Provides two profile-independent, **auth-free** views:

- **AWS Services tab** — service catalog (37 services across Compute, Storage, Network, Database, Containers, Security & Identity, Messaging, Observability, AI/ML categories) filtered by selected region or Local Zone. Optional one-click TCP latency probe shows p50/p95 ms per endpoint. Scope badge marks each service as `lz-data-plane` / `regional` / `global` / `lz-link-local`.
- **Region Matrix tab** — full matrix of 29 AWS public regions + 32 known Local Zones with TCP-handshake latency (p50 / p95) from the host running ScanBox. Sortable, searchable, "reachable only" toggle.

### Key constraint — zero AWS authentication

This module deliberately does **not** import `boto3` and **does not** require any AWS credentials, IAM role, SSO session, or AWS_PROFILE. All data comes from:

1. **Static Python catalog** ported from the `ist-LZ-TEST` Go reference (`modules/awsref/aws_catalog.py`).
2. **Public AWS JSON sources** over plain HTTPS GET (no signing) — `api.regional-table.region-services.aws.a2z.com`, `ip-ranges.amazonaws.com` (helper available in `modules/awsref/public_sources.py` for future expansion).
3. **TCP socket probes** using Python stdlib `socket` to `s3.<region>.amazonaws.com:443` and per-service endpoints — measures handshake RTT only, no payload, no auth headers.

ScanBox can be deployed on any internet-connected machine — no AWS account needed for this module.

### Files added

- `modules/awsref/__init__.py`, `aws_catalog.py`, `probe.py`, `cache.py`, `public_sources.py`, `routes.py`
- `templates/awsref/index.html`
- `static/awsref/css/awsref.css`, `static/awsref/js/awsref.js`

### Files modified

- `app.py` — blueprint import + register, rate-limit prefix tuple, `_wants_json` prefix check, `active_module` allow-list
- `templates/base.html` — sidebar nav-item between News and Health (globe SVG icon, `data-i18n="nav_module_awsref"`)
- `static/js/i18n.js` — TR + EN keys (`awsref_*`, `nav_module_awsref`, etc.)

### Notes

- **VERSION 1.5.0 → 2.0.0** (MAJOR per VERSIONING.md: "MAJOR = new sidebar module")
- 4 API endpoints: `GET /awsref/api/regions`, `/awsref/api/services`, `/awsref/api/region-matrix`, `/awsref/api/endpoints`
- Cache TTLs: 5 min for TCP probes, 24 h for the regional catalog, 12 h for AWS IP-ranges
- Parallelism: `ThreadPoolExecutor(12)` for probe fan-out (~0.6s for 60+ endpoints)
- Demo mode (`SCANBOX_DEMO=1`) unaffected — module doesn't read profile data

### Added — AWS News module (`/news`)

New sidebar module **AWS News** — sits above Health. Mirrors the AWS "What's New" feed as a vanilla-JS + Jinja page with first-class filtering and search.

- Fuzzy search powered by Fuse.js (weighted fields, 0.35 threshold, 180 ms debounce, `Cmd/Ctrl + K`, `Esc`).
- Multi-select **Categories** dropdown (internal search + count badge) + radio **Date** filter (All / 7 / 14 / 30 days) + active-filter pill row with one-click X to clear.
- Tag extraction against a 150-entry AWS service vocabulary (`modules/news/aws_services.py`); per-tag colour via a local djb2 palette in `news.js`.
- Backend `fetcher.py` parses RSS with stdlib only (`urllib`, `re`, `html`, `hashlib`) — no new pip deps. 5-min soft TTL + `threading.Lock`; `?force=1` bypasses the cache.
- Endpoints: `GET /news`, `GET /news/api/feed`, `POST /news/api/refresh`.
- Auto-recomputed `isNew` badges so they don't go stale across days.
- Bilingual TR + EN, theme-aware (uses existing `theme.css` variables; no hard-coded colours).
- Module is independent: removing it = delete `modules/news/`, `templates/news/`, `static/news/`, and ~6 lines of wiring in `app.py` / `base.html` / `i18n.js`.

#### Files added (news)

- `modules/news/__init__.py`, `routes.py`, `fetcher.py`, `aws_services.py`, `data/.gitkeep`, `data/whats-new.json` (seeded)
- `templates/news/index.html`
- `static/news/css/news.css`, `static/news/js/news.js`

#### i18n hardening (shipped with news)

- `applyTranslations()` in `static/js/i18n.js` is now **closure-bound** — it looks up via `TRANSLATIONS` directly instead of calling the global `t()`. Fuse.js (loaded later) was declaring a top-level `t` symbol that shadowed ours, making translated strings render as Fuse's class-constructor source. Do not revert this change.
- `data-i18n-placeholder` attribute is now recognised by the applier; `data-i18n` auto-routes to `.placeholder` when the element has one.

### Added — Topology Architecture View

New auto-generated architecture view in the Topology module — produces a draw.io-style layered diagram from the inventoried resources (VPC / subnets / ALB / EC2 / RDS / Lambda / S3 etc.) instead of the flat resource list.

- `modules/topology/architecture_view.py` — layout engine: layered grouping (Internet → Edge → VPC → Subnets → Workloads → Data Plane), edge inference from security-group references, route tables, and ENI bindings.
- `modules/topology/drawio_styles.py` — mxGraph style strings reused by the renderer.
- `modules/topology/icon_map.py` — AWS service → SVG icon mapping.
- `static/topology/css/architecture-view.css`, `static/topology/js/architecture-view.js`, `static/topology/icons/` — frontend renderer + AWS Architecture Icon set.

### Fixed — AWS Reference `/awsref`

- **Service Endpoints table now scrolls inside its own card** with a sticky header + filter row, instead of running off the bottom of the page and leaving lower services unreachable. Mirrors the LZ Services Catalog pattern (`max-height: calc(100vh - 300px)`, `position: sticky` on both header rows). Fixes a CSS-specificity bug where `.awsref-services-table th.awsref-sortable { position: relative }` (0,2,1) silently beat the original sticky rule (0,1,2) — the sort-header row never stuck, the filter row floated alone, and data rows bled through the 36 px gap. Equal-specificity override placed later in the file wins on source order.
- **"About this view" panel** now renders properly in both **TR and EN** on all four tabs (Local probe / Full mesh / Comparison / Metrics). Two coupled bugs fixed: 25 missing EN translations added to `TRANSLATIONS.en` in `static/js/i18n.js`; and 12 description `<p>` tags switched from `data-i18n` (textContent — would render `<b>` markup as literal text) to `data-i18n-html` (innerHTML). Plain-text Comparison `<th>`/`<td>` cells stay on `data-i18n` to keep the `innerHTML` surface narrow.

### Repo hygiene

- `.gitignore` now excludes `0-Referans/` (325 MB of dev-reference material) and `HANDOVER.md` (per-session internal notes) so neither lands in public releases.

---

## [1.5.0] - 2026-05-15

### Added

#### SecOps — 5 new service inventory modules (P2: data, vuln-scan, sensitive-data, search, cache)

Service count grows from **24 → 29**. Each module follows the established
`run_checks(session, exclude_defaults, regions)` pattern, with per-region
fan-out where applicable, graceful degradation on AccessDenied / OptIn /
"not enabled" errors, and full TR + EN bilingual content.

- **`backup.py` (AWS Backup)** — 5 checks
  - Vault KMS encryption (CIS 2.3.1, HIPAA 164.312(a)(2)(iv), SOC2 CC6.7)
  - Vault Lock immutable retention (HIPAA 164.312(c)(1), SOC2 PI1.4/PI1.5 — SEC 17a-4(f) ransomware-resilience)
  - Backup plan exists per region (HIPAA 164.308(a)(7)(ii)(A), SOC2 A1.2)
  - Plan retention >= 30 days (worst-case across all rules)
  - Plan has cross-region copy action (WAFR REL13)

- **`inspector.py` (Amazon Inspector V2)** — up to 7 checks per region
  - Enabled-per-scan-type (EC2 / ECR / Lambda / LAMBDA_CODE)
  - Aggregated active CRITICAL / HIGH / MEDIUM finding rollups (one finding each)
  - Auto-skips finding queries when no scan type is enabled (no noise on greenfield accounts)

- **`macie.py` (Amazon Macie 2)** — 3 checks
  - Macie enabled per region (HIPAA 164.308(a)(1)(ii)(A), SOC2 CC3.2/C1.1)
  - Organization-level delegated administrator (account-scoped, runs once)
  - HIGH-severity sensitive-data finding rollup (PII / credentials / financial)

- **`opensearch.py` (Amazon OpenSearch Service)** — 6 checks per domain
  - At-rest encryption (`EncryptionAtRestOptions`)
  - Node-to-node encryption (in-cluster TLS)
  - Enforce HTTPS + TLS security policy
  - VPC endpoint (no public access)
  - Fine-grained access control + anonymous-auth disabled
  - Audit log publishing to CloudWatch Logs

- **`elasticache.py` (Amazon ElastiCache)** — 5 checks per Redis/Valkey replication group + 1 Memcached limitation finding
  - At-rest encryption (RDB / AOF snapshots)
  - In-transit TLS (RESP traffic protection)
  - AUTH token configured (Redis/Valkey only)
  - Automatic failover / Multi-AZ
  - Snapshot retention >= 1 day
  - Memcached cluster: explicit "encryption-unsupported" warning (CIS 2.6.1, HIPAA, SOC2 CC6.7)

### Changed

- **`scanner.py`** — `SERVICES_ORDER`, `MODULES_WITH_CHECKS`, `_MODULE_TO_CE_PATTERNS`, and `all_modules` list extended with the 5 new modules. Smart-service-detection (`_get_active_ce_services` + CE pattern matching) now triggers them only when Cost Explorer shows active spend for the corresponding AWS service, so accounts that don't use Backup/Inspector/Macie/OpenSearch/ElastiCache are not penalised with NOT_AVAILABLE noise.
- **`CE_SERVICE_MAP`** already had entries for these services (predating the modules) — they were previously routed to `MANUAL` "no automated checks" findings; now they produce real check coverage.

### Framework coverage gains

New mappings now exercised across all 5 frameworks:

- **CIS** — 2.3.1 (Backup vault encryption), 2.5.1 (OpenSearch encryption), 2.5.2 (VPC endpoint), 2.5.3 (audit logs), 2.6.1 (ElastiCache encryption + auth), 4.6 (Inspector)
- **HIPAA** — 164.402 (sensitive data breach notification), 164.308(a)(1)(ii)(A) (vuln management)
- **ISO27001** — A.8.2.1 (info classification), A.12.6.1 (technical vulns), A.18.1.4 (privacy), A.18.2.2 (compliance review)
- **SOC2** — CC3.2 (risk identification), C1.1 (confidential info), CC1.3 (delegated authority), CC7.1 (vuln monitoring)
- **WAFR** — SEC07 (data classification), SEC11 (incident lifecycle), REL10/REL11 (multi-AZ/failure isolation), REL13 (DR)

### Notes

- All 5 modules are **opt-in via Cost Explorer**: if the AWS account doesn't use Backup, Inspector, Macie, OpenSearch, or ElastiCache, the modules are skipped (no IAM-permission noise, no NOT_AVAILABLE findings clogging the dashboard).
- **Inspector V2** is the only API used (the legacy `inspector` v1 client is EOL'd by AWS).
- Total new check IDs surface in Framework Compliance gauges, Capability Radar, WAFR/SOC2 pillar charts, Top Failed Controls, and Risk Treemap automatically — no frontend wiring required.
- Server header now reports `v1.5.0`.

---

## [1.4.0] - 2026-05-15

### Added

#### SecOps — 14 new security checks (Steampipe-inspired "Quick Wins")

Borrowed control ideas from the Turbot/Steampipe AWS compliance + perimeter + thrifty mod catalog and adapted them to the existing `make_finding(...)` shape. All checks include TR + EN text, dynamic severity where applicable, and framework mappings to CIS / HIPAA / ISO27001 / SOC2 / WAFR.

- **CloudTrail**
  - `cloudtrail_data_events_*` — verifies data-event logging (S3 object operations, Lambda invocations) is enabled. Required for PCI DSS 10.3.2 and detailed forensics.
  - `cloudtrail_insight_events_*` — checks for CloudTrail Insights subscription (ML-based API anomaly detection — ApiCallRateInsight / ApiErrorRateInsight).
- **S3**
  - `s3_bucket_mfa_delete_*` — flags versioned buckets without MFA Delete (ransomware resilience).
  - `s3_bucket_replication_*` — reports buckets without cross-region replication (DR / RTO / RPO).
  - `s3_bucket_object_lock_*` — surfaces buckets with WORM Object Lock (HIPAA, SEC 17a-4, PCI archival).
- **EC2**
  - `ec2_old_snapshots_*` — aggregates self-owned EBS snapshots older than 90 days per region, estimating monthly storage cost (~$0.05/GB-mo). Severity scales with cost.
- **VPC**
  - `vpc_flow_log_traffic_type_*` — verifies flow logs capture ALL traffic (not just ACCEPT) so REJECT events are available for investigations.
- **KMS**
  - `kms_multi_region_key_*` — audits multi-region keys (MRK), listing replicas and prompting review of the expanded cryptographic trust boundary.
- **RDS**
  - `rds_performance_insights_*` — flags instances without Performance Insights (query-level forensics for incident response).
- **Lambda**
  - `lambda_reserved_concurrency_*` — checks reserved concurrency limit to prevent runaway invocations exhausting the account-wide pool.
  - `lambda_dlq_*` — checks dead-letter queue configuration for async-invocation error visibility.
- **CloudFront**
  - `cf_geo_restriction_*` — verifies geo-restriction (data-residency and sanction compliance).
  - `cf_origin_shield_*` — checks Origin Shield (DDoS blast-radius reduction, cross-edge cost optimisation).
- **Config**
  - `config_aggregator` — single account-level check for Configuration Aggregator presence (Organizations-wide compliance visibility).

### Notes

- All checks degrade gracefully on `AccessDenied` / `ResourceNotFoundException` — a single missing IAM permission won't abort the whole scan.
- "Heavy" checks (EBS snapshots paginated across regions, Lambda concurrency per function) reuse the existing `ThreadPoolExecutor` fan-out pattern; no new infra needed.
- Framework dropdown / pillar drill-down charts pick up new findings automatically — no frontend wiring required.

---

## [1.3.0] - 2026-04-29

### Added

#### FinOps — Savings Opportunities Dashboard
- New collapsible **"Savings Opportunities"** section in `/finops/detail` (between Region Distribution and Budget Status)
- 4 KPI cards: potential monthly savings ($), idle resource count, Savings Plan coverage %, tag coverage %
- Sorted horizontal bar chart of savings categories (click to scroll to category drill-down)
- SP / RI coverage gauges (SVG ring, colour-graded by 80/50% thresholds)
- Tag coverage donut (fully tagged vs missing tags)
- Per-category drill-down `<details>` tables with resource ID, region, spec, age/CPU/throughput context, monthly $ — capped at 25 rows + "+N more" hint
- Full TR/EN bilingual labels (CLAUDE.md convention)

#### Backend — 11 new read-only collectors in `aws_client.py`
- `fetch_unattached_ebs` — available volumes per region with per-type pricing
- `fetch_unassociated_eips` — count × $3.65/mo
- `fetch_stopped_ec2` — instances stopped >30 days; reports attached EBS still being billed
- `fetch_idle_nat_gateways` — CloudWatch BytesOutToDestination <1GB over 14d
- `fetch_empty_load_balancers` — ALB/NLB with zero healthy targets across all target groups
- `fetch_orphan_rds_snapshots` — manual snapshots whose source DB is gone
- `fetch_low_cpu_ec2` — running instances with median CPU <5% over 14 days (right-sizing hint, COST05)
- `fetch_savings_plan_coverage` — last-month SP coverage % (Cost Explorer)
- `fetch_ri_coverage` — last-month RI coverage % (Cost Explorer)
- `fetch_cost_forecast` — 30-day forecast with 80% prediction interval
- `fetch_tag_coverage` — % of resources with all required tags (Owner/Environment/CostCenter)
- `fetch_savings_summary` — wrapper that fans all collectors out via `ThreadPoolExecutor(10)`, returns ranked categories + totals
- New `GET /finops/api/savings?profile=X` endpoint
- `/finops/api/detail` payload now includes `savings` field (parallel fetch, no extra round-trip)
- All collectors are try/except wrapped — AccessDenied / OptInRequired / RegionDisabled errors return `{status:'unavailable',reason:...}` instead of raising

#### Advice — Cost Optimization Assessment Enrichment
- 8 new `COST_ADVICE_TEMPLATES` entries with f-string-style placeholders for dynamic dollar amounts:
  `unattached_ebs`, `unassociated_eips`, `stopped_ec2_long`, `idle_nat_gateways`,
  `empty_load_balancers`, `orphan_rds_snapshots`, `underutilized_ec2_cpu`, `tag_governance`
- Severity now scales dynamically with monthly_cost / count thresholds (high-impact items rise to the top of the report)
- WAFR coverage extended: COST04 (decommission), COST05 (right-sizing — previously empty), COST07 (data transfer / NAT), plus existing COST01/COST02/COST03/COST06
- Total Cost Optimization findings: 4 → up to 12 per assessment (4 generic + 8 data-driven)
- `_fetch_finops_data(session, profile_name)` now wires the savings summary into the advisor pipeline

### Changed

- `_score_services` and overall aggregation now exclude `SUPPRESSED` from denominators (carry-over from v1.2.0 SOC2 work)
- `/finops/api/detail` thread join timeout raised 30s → 90s to accommodate the multi-region savings fan-out

### Out of scope (backlog)

Per user direction this release does **not** include AWS Compute Optimizer integration (right-sizing recommendations with explicit `estimatedMonthlySavings`), gp2→gp3 migration heuristics, S3 storage-class lifecycle gap analysis, DynamoDB on-demand vs provisioned analysis, Lambda over-provisioned concurrency, AWS Cost Anomaly Detection subscription management, or one-click remediation actions. These are tracked for a future release.

---

## [1.2.0] - 2026-04-28

### Added

#### SecOps — SOC2 Type II Framework
- AICPA Trust Service Criteria 2017/2022 catalog (43 controls: CC1.1–CC9.2, A1.1–A1.3, C1.1–C1.2, PI1.1–PI1.5) with bilingual TR/EN titles
- New `modules/secops/frameworks/soc2_catalog.py` with `pillar_for(control_id)` helper
- SOC2 control mapping added to all 23 SecOps inventory modules — every applicable finding now reports `'SOC2': [...]` alongside CIS/HIPAA/ISO27001/WAFR
- Dashboard: 5th gauge in Framework Compliance (auto-fit responsive grid)
- Dashboard: dedicated "SOC2 — Trust Service Criteria" pillar bar chart (next to WAFR), click any pillar to drill down
- Findings filter dropdown: SOC2 option

#### SecOps — Severity-Weighted Framework Scoring
- Per-framework scores now use `SEV_WEIGHTS` (CRITICAL=10, HIGH=7, MEDIUM=4, LOW=2, INFO=1) so a single CRITICAL FAIL has measurable impact instead of being averaged out by trivial PASSes
- WAFR pillar drill-down + new SOC2 pillar drill-down both use the same weighted formula
- Service score calculation continues to be unweighted (different surface, different intent)

#### SecOps — Suppression (Accepted-Risk / False-Positive)
- Mark a finding as accepted-risk via the row's "⊘ Suppress" button — modal asks for a reason (audit trail) before persisting to `modules/secops/data/suppressions/<profile>.json`
- Suppressed findings get a new `SUPPRESSED` status (purple), are hidden from the default Findings table view, and are excluded from score/coverage denominators
- "Restore" button on suppressed findings re-instates the prior status without rescanning
- New endpoints: `POST /secops/api/suppress`, `DELETE /secops/api/suppress`, `GET /secops/api/suppressions`
- Suppression dir is gitignored (per-user / per-profile data)

#### SecOps — Finding Delta Badges
- Each finding row now shows a delta vs the most recent previous scan: `NEW` (blue), `FIXED` (green), `REGR` (red — previously passing, now failing). Persisting findings show no badge.
- Backend `_compute_deltas` diffs the current scan against `data/scan_results/<profile>.json` (the previous cached scan) by finding ID
- Summary `deltas` counts (`new`, `fixed`, `regression`, `persisting`) added to scan results JSON for trend dashboards

### Fixed

- S3 bucket policy public-access check: `Effect: Deny` statements with wildcard Principal (typical "deny insecure transport" pattern), and statements scoped via `aws:SourceArn` / `aws:SourceAccount` / `aws:PrincipalOrgID` / VPC / IP conditions, are no longer falsely flagged as CRITICAL public-access. Only unscoped `Effect: Allow` + `Principal: "*"` triggers the finding.
- SecOps drill-down banner ("WAFR Pillar: …", "SOC2 Pillar: …", "Service / Region: …") now has a clickable Clear/Temizle button. Previously the message said "Click 'Clear' to reset" but the text was non-interactive.
- Cache banners gain a ✕ close button that's keyboard- and click-accessible.

---

## [1.1.0] - 2026-03-23

### Added

#### Topology Module — 3-Tier Architecture Diagram
- AWS 3-Tier Architecture layout: Web Tier (public subnets), Application Tier (private, non-DB), Database Tier (private, RDS)
- Region container with dashed teal border wrapping all VPCs per region
- Tier chevron labels on the left side (Web/App/DB) with color-coded indicators
- Route Table banners between tiers showing CIDR route summaries (public/private)
- Auxiliary AWS Services panel on the right side (IAM, GuardDuty, CloudWatch, CloudTrail, Backup, S3)
- Automatic 3-tier resource classification based on subnet publicity and resource type
- New container types: cloud, region, tier_web, tier_app, tier_db, aux_panel, rt_banner
- New AWS icons: IAM, IAM Identity Center, GuardDuty, CloudWatch, CloudTrail, Backup, AutoScaling
- Minimap click-and-drag navigation for panning the diagram viewport

#### Launcher Scripts — Auto-Install Prerequisites
- 4-phase prerequisite system: check all → display status table → install missing → start server
- `run.bat` (Windows): Auto-installs Python via winget or PowerShell download, pip via ensurepip/get-pip.py, venv, dependencies, optional AWS CLI
- `run.sh` (macOS/Linux): OS detection (macOS/Debian/RHEL/Arch/Alpine/SUSE), auto-installs Python via brew/apt/dnf/pacman/apk, pip, venv, dependencies, optional AWS CLI
- Prerequisites status display with [OK]/[--] indicators before any installation
- All installations prompt user for confirmation (Y/N) before proceeding
- Skips directly to server start when all prerequisites are already met

### Changed
- Topology container labels now use type-specific positioning: top-center for subnets/AZs, full-center for banners, top-left for VPCs/regions
- Dark/light theme colors extended with 10 new variables for 3-tier architecture containers

---

## [1.0.0] - 2026-03-19

First public release with 7 core modules.

### Added

#### Core Platform
- Flask-based web application with 8 modular blueprints (port 5100)
- Shared AWS client (`aws_client.py`) with Cost Explorer, EC2, STS, Budgets integration
- Cross-platform launchers (`run.sh` for macOS/Linux, `run.bat` for Windows)
- Demo mode (`SCANBOX_DEMO=1`) for safe showcasing without real AWS credentials
- Dark/light theme with OS preference detection and manual toggle
- Bilingual UI — full Turkish and English support with one-click switching
- SVG icon system (no emoji) via global `ICONS` object
- Request logging to `logs/requests.log` with method, path, status, and duration
- In-memory rate limiting (60 requests/minute per IP on API endpoints)
- Global error handlers (404/500) returning JSON for API paths, HTML for pages
- SSO/credential error detection with user-friendly red banner and copyable `aws sso login` command
- Centralized version management via `VERSION` file

#### FinOps Module
- Multi-account cost analysis dashboard with profile selection
- Monthly cost aggregation (1-12 months) with month-over-month comparison
- Per-service cost breakdown with daily granularity
- Region distribution analysis separating global/marketplace services from regional infrastructure
- EC2 inventory with vCPU, RAM, EBS volumes — fully sortable table with audit summary
- Budget tracking (actual vs. budgeted spend)
- Credits and discount detection
- HTML/CSV/PDF report generation per profile
- 5-minute API cache for Cost Explorer results

#### SecOps Module
- Security posture assessment scanning 24 AWS services
- 4 compliance frameworks: CIS AWS Foundations, HIPAA, ISO 27001, AWS WAFR
- Smart service detection via Cost Explorer (only scan active services)
- Parallel scanning with ThreadPoolExecutor and timeout handling
- Three-tier risk scoring: base score, severity-weighted score, coverage score
- 10 dashboard visualizations: radar, pass rate, service distribution, framework compliance, WAFR pillars, remediation progress, score trend, finding trend, severity heatmap, risk treemap
- Fullscreen radar chart modal
- Custom filter dropdowns (framework, severity, service, status)
- Scan history with trend tracking (localStorage, max 20 data points)
- Concurrency control with per-profile locking and 1-hour auto-release
- Auto-generated HTML/CSV/PDF reports after scan completion
- Inventory modules: IAM, S3, EC2, VPC, CloudTrail, GuardDuty, Config, CloudWatch, KMS, RDS, Lambda, ECS, EKS, ELB, DynamoDB, SQS, SNS, ECR, EFS, CloudFront, WAF, Route 53, ACM, Secrets Manager

#### MapInventory Module
- Resource discovery across 150+ AWS services
- Lock-free concurrency via `queue.Queue` for result collection
- `Semaphore(5)` limiting concurrent profile scans
- 10-minute global scan timeout with per-task 30s timeout
- Cost Explorer smart scanning (skip unused services)
- Single-pass metadata aggregation (service, region, type counts)
- Max 20 cached scans with auto-deletion of oldest
- HTML/CSV/PDF report generation with searchable resource tables

#### Topology Module
- VPC network architecture visualization
- 3 view levels: Basic, Medium, Detailed
- Parallel regional collection via ThreadPoolExecutor
- Resources: VPC, Subnet, IGW, NAT, Route Table, Peering, Security Group, NACL, VPC Endpoint, EIP, EC2, ECS, RDS, ELB, Lambda, EKS, API Gateway, Network Firewall, Transit Gateway, Direct Connect, VPN, CloudFront, S3, Route 53
- HTML/CSV/PDF report generation

#### Advice Module
- AWS Well-Architected Framework (WAFR) 6-pillar assessment
- Multi-source data fusion: SecOps findings + MapInventory resources + live Cost Explorer data
- Service-specific advice rules via `wafr_knowledge.py` knowledge base
- Prerequisite checking (validates SecOps + MapInventory scans exist)
- HTML report with interactive pillar breakdown
- PDF reports in English and Turkish

#### Health Module
- Real-time latency monitoring to 27 AWS regions via TCP handshake
- DNS health monitoring (Cloudflare + Google resolvers)
- AWS outage tracking from public status page (JSON + RSS fallback)
- Cloudflare status monitoring via public API
- 4 lazy-started daemon threads with exponential backoff
- Deque-based history (120 data points = 1 hour at 30s intervals)
- Frontend polling pauses when browser tab is hidden

#### About Module
- Application metadata and version information
- Module overview and capabilities summary
