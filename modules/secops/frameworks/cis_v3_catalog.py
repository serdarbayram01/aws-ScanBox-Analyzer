"""
SecOps — CIS Amazon Web Services Foundations Benchmark (cis_aws_v3, v3.0.0) control catalog.

Read-only metadata: control_id -> {title, section, level (if any)}.
Used by SecOps drill-down to show full control titles next to the bare
IDs that inventory modules already place on each finding's `frameworks` dict.

Source: cloud-audit (https://github.com/gebalamariusz/cloud-audit, MIT)
        compliance/frameworks/cis_aws_v3.json
Auto-generated 2026-06-01. To extend with bilingual TR titles, add
`'title_tr'` entries inline — they will be picked up by title_for(id, lang).
"""

FRAMEWORK_ID      = 'cis_aws_v3'
FRAMEWORK_NAME    = 'CIS Amazon Web Services Foundations Benchmark'
FRAMEWORK_VERSION = '3.0.0'
FINDINGS_KEY      = 'CIS'    # key used in finding["frameworks"]

CONTROLS = {
    '1.1': {
        'title':   'Maintain current contact details',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.2': {
        'title':   'Ensure security contact information is registered',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.3': {
        'title':   'Ensure security questions are registered in the AWS account',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.4': {
        'title':   "Ensure no 'root' user account access key exists",
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.5': {
        'title':   "Ensure MFA is enabled for the 'root' user account",
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.6': {
        'title':   "Ensure hardware MFA is enabled for the 'root' user account",
        'section': '1 - Identity and Access Management',
        'level':   'L2',
    },
    '1.7': {
        'title':   "Eliminate use of the 'root' user for administrative and daily tasks",
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.8': {
        'title':   'Ensure IAM password policy requires minimum length of 14 or greater',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.9': {
        'title':   'Ensure IAM password policy prevents password reuse',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '3.1': {
        'title':   'Ensure CloudTrail is enabled in all regions',
        'section': '3 - Logging',
        'level':   'L1',
    },
    '3.2': {
        'title':   'Ensure CloudTrail log file validation is enabled',
        'section': '3 - Logging',
        'level':   'L2',
    },
    '3.3': {
        'title':   'Ensure AWS Config is enabled in all regions',
        'section': '3 - Logging',
        'level':   'L2',
    },
    '3.4': {
        'title':   'Ensure S3 bucket access logging is enabled on the CloudTrail S3 bucket',
        'section': '3 - Logging',
        'level':   'L1',
    },
    '3.5': {
        'title':   'Ensure CloudTrail logs are encrypted at rest using KMS CMKs',
        'section': '3 - Logging',
        'level':   'L2',
    },
    '3.6': {
        'title':   'Ensure rotation for customer-created symmetric CMKs is enabled',
        'section': '3 - Logging',
        'level':   'L2',
    },
    '3.7': {
        'title':   'Ensure VPC flow logging is enabled in all VPCs',
        'section': '3 - Logging',
        'level':   'L2',
    },
    '3.8': {
        'title':   'Ensure that Object-level logging for write events is enabled for S3 bucket',
        'section': '3 - Logging',
        'level':   'L2',
    },
    '3.9': {
        'title':   'Ensure that Object-level logging for read events is enabled for S3 bucket',
        'section': '3 - Logging',
        'level':   'L2',
    },
    '4.1': {
        'title':   'Ensure unauthorized API calls are monitored',
        'section': '4 - Monitoring',
        'level':   'L2',
    },
    '4.2': {
        'title':   'Ensure management console sign-in without MFA is monitored',
        'section': '4 - Monitoring',
        'level':   'L1',
    },
    '4.3': {
        'title':   "Ensure usage of 'root' account is monitored",
        'section': '4 - Monitoring',
        'level':   'L1',
    },
    '4.4': {
        'title':   'Ensure IAM policy changes are monitored',
        'section': '4 - Monitoring',
        'level':   'L1',
    },
    '4.5': {
        'title':   'Ensure CloudTrail configuration changes are monitored',
        'section': '4 - Monitoring',
        'level':   'L1',
    },
    '4.6': {
        'title':   'Ensure AWS Management Console authentication failures are monitored',
        'section': '4 - Monitoring',
        'level':   'L2',
    },
    '4.7': {
        'title':   'Ensure disabling or scheduled deletion of customer-created CMKs is monitored',
        'section': '4 - Monitoring',
        'level':   'L2',
    },
    '4.8': {
        'title':   'Ensure S3 bucket policy changes are monitored',
        'section': '4 - Monitoring',
        'level':   'L1',
    },
    '4.9': {
        'title':   'Ensure AWS Config configuration changes are monitored',
        'section': '4 - Monitoring',
        'level':   'L2',
    },
    '5.1': {
        'title':   'Ensure no Network ACLs allow ingress from 0.0.0.0/0 to remote server administration ports',
        'section': '5 - Networking',
        'level':   'L1',
    },
    '5.2': {
        'title':   'Ensure no security groups allow ingress from 0.0.0.0/0 to remote server administration ports',
        'section': '5 - Networking',
        'level':   'L1',
    },
    '5.3': {
        'title':   'Ensure no security groups allow ingress from ::/0 to remote server administration ports',
        'section': '5 - Networking',
        'level':   'L1',
    },
    '5.4': {
        'title':   'Ensure the default security group of every VPC restricts all traffic',
        'section': '5 - Networking',
        'level':   'L2',
    },
    '5.5': {
        'title':   "Ensure routing tables for VPC peering are 'least access'",
        'section': '5 - Networking',
        'level':   'L2',
    },
    '5.6': {
        'title':   'Ensure that EC2 Metadata Service only allows IMDSv2',
        'section': '5 - Networking',
        'level':   'L1',
    },
    '1.10': {
        'title':   'Ensure multi-factor authentication (MFA) is enabled for all IAM users that have a console password',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.11': {
        'title':   'Do not setup access keys during initial user setup',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.12': {
        'title':   'Ensure credentials unused for 45 days or greater are disabled',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.13': {
        'title':   'Ensure there is only one active access key available for any single IAM user',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.14': {
        'title':   'Ensure access keys are rotated every 90 days or less',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.15': {
        'title':   'Ensure IAM Users Receive Permissions Only Through Groups',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.16': {
        'title':   "Ensure IAM policies that allow full '*:*' administrative privileges are not attached",
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.17': {
        'title':   'Ensure a support role has been created to manage incidents with AWS Support',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.18': {
        'title':   'Ensure IAM instance roles are used for AWS resource access from instances',
        'section': '1 - Identity and Access Management',
        'level':   'L2',
    },
    '1.19': {
        'title':   'Ensure that all the expired SSL/TLS certificates stored in AWS IAM are removed',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.20': {
        'title':   'Ensure that IAM Access Analyzer is enabled for all regions',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '1.21': {
        'title':   'Ensure IAM users are managed centrally via identity federation or AWS Organizations',
        'section': '1 - Identity and Access Management',
        'level':   'L2',
    },
    '1.22': {
        'title':   'Ensure access to AWSCloudShellFullAccess is restricted',
        'section': '1 - Identity and Access Management',
        'level':   'L1',
    },
    '4.10': {
        'title':   'Ensure security group changes are monitored',
        'section': '4 - Monitoring',
        'level':   'L2',
    },
    '4.11': {
        'title':   'Ensure Network Access Control Lists (NACL) changes are monitored',
        'section': '4 - Monitoring',
        'level':   'L2',
    },
    '4.12': {
        'title':   'Ensure changes to network gateways are monitored',
        'section': '4 - Monitoring',
        'level':   'L1',
    },
    '4.13': {
        'title':   'Ensure route table changes are monitored',
        'section': '4 - Monitoring',
        'level':   'L1',
    },
    '4.14': {
        'title':   'Ensure VPC changes are monitored',
        'section': '4 - Monitoring',
        'level':   'L1',
    },
    '4.15': {
        'title':   'Ensure AWS Organizations changes are monitored',
        'section': '4 - Monitoring',
        'level':   'L1',
    },
    '4.16': {
        'title':   'Ensure AWS Security Hub is enabled',
        'section': '4 - Monitoring',
        'level':   'L2',
    },
    '2.1.1': {
        'title':   'Ensure S3 Bucket Policy is set to deny HTTP requests',
        'section': '2 - Storage',
        'level':   'L2',
    },
    '2.1.2': {
        'title':   'Ensure MFA Delete is enabled on S3 buckets',
        'section': '2 - Storage',
        'level':   'L2',
    },
    '2.1.3': {
        'title':   'Ensure all data in Amazon S3 has been discovered, classified and secured when required',
        'section': '2 - Storage',
        'level':   'L2',
    },
    '2.1.4': {
        'title':   "Ensure that S3 Buckets are configured with 'Block public access (bucket settings)'",
        'section': '2 - Storage',
        'level':   'L1',
    },
    '2.2.1': {
        'title':   'Ensure EBS Volume Encryption is Enabled in all Regions',
        'section': '2 - Storage',
        'level':   'L1',
    },
    '2.3.1': {
        'title':   'Ensure that encryption-at-rest is enabled for RDS Instances',
        'section': '2 - Storage',
        'level':   'L1',
    },
    '2.3.2': {
        'title':   'Ensure Auto Minor Version Upgrade feature is Enabled for RDS Instances',
        'section': '2 - Storage',
        'level':   'L1',
    },
    '2.3.3': {
        'title':   'Ensure that public access is not given to RDS Instance',
        'section': '2 - Storage',
        'level':   'L1',
    },
    '2.4.1': {
        'title':   'Ensure that encryption is enabled for EFS file systems',
        'section': '2 - Storage',
        'level':   'L1',
    },
}


def title_for(control_id: str, lang: str = 'en') -> str:
    """Return the title of a control, or empty string if unknown.

    Pass lang='tr' to fetch a Turkish title if one has been added inline.
    Falls back to English when no Turkish translation exists yet.
    """
    c = CONTROLS.get(control_id) or {}
    if lang == 'tr' and c.get('title_tr'):
        return c['title_tr']
    return c.get('title', '')


def known(control_id: str) -> bool:
    return control_id in CONTROLS


def all_ids() -> list:
    return sorted(CONTROLS.keys(), key=lambda k: (len(k), k))


# ---------------------------------------------------------------------------
# CIS AWS Foundations Benchmark v1.x/v2.0 → v3.0 crosswalk
# Source: CIS published changelog. v3.0 reorganised Section 2/3 logging
# controls; old 2.x → new 3.x for most logging items. Uncertain mappings
# documented inline. Unmapped IDs fall through unchanged.
# Idempotent: a v3 ID stays unchanged (not a key here).
# ---------------------------------------------------------------------------

OLD_TO_NEW = {
    # Section 2 (Storage / Logging in v2) → Section 2 (Storage) / 3 (Logging) in v3
    '2.4':   '3.2',         # CloudTrail log file validation
    '2.5':   '3.5',         # AWS Config enabled in all regions
    '2.5.1': '3.5',         # ScanBox sub-numbered Config check (umbrella → 3.5)
    '2.5.2': '3.5',
    '2.5.3': '3.5',
    '2.6.1': '3.6',         # S3 access logging on CloudTrail bucket
    '2.7':   '3.7',         # CloudTrail logs at rest encryption with KMS CMK
    '2.1.5': '2.1.1',       # S3 BPA (consolidated under 2.1.1 in v3)
    '2.2.2': '2.2.1',       # EBS volume encryption at rest by default
    # Section 3 (Monitoring) — most numbers already match; a few moved
    '3.10':  '3.8',         # CMK rotation enabled
    '3.12':  '3.9',         # VPC flow logging enabled
    # ScanBox's "3.1–3.14" range-as-string is non-standard; cannot map — left
    # untouched so the drift matrix continues to flag it for source cleanup.
}


def translate_id(old_id: str) -> str:
    """Return the v3.0 ID for a v1.x/v2.0 ID, or the input unchanged. Idempotent."""
    return OLD_TO_NEW.get(old_id, old_id)


def translate_list(ids):
    """Map translate_id over a list, preserving order + de-duplicating mergers."""
    if not ids:
        return ids
    seen, out = set(), []
    for old in ids:
        new = OLD_TO_NEW.get(old, old)
        if new not in seen:
            seen.add(new)
            out.append(new)
    return out
