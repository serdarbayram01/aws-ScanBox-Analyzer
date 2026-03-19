# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

For versioning rules and release process, see [VERSIONING.md](VERSIONING.md).

---

## [Unreleased]

*Nothing yet — contributions welcome!*

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
