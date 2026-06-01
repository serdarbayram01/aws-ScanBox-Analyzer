"""
SecOps — HIPAA Security Rule (hipaa_security, v45 CFR Part 164 Subpart C) control catalog.

Read-only metadata: control_id -> {title, section, level (if any)}.
Used by SecOps drill-down to show full control titles next to the bare
IDs that inventory modules already place on each finding's `frameworks` dict.

Source: cloud-audit (https://github.com/gebalamariusz/cloud-audit, MIT)
        compliance/frameworks/hipaa_security.json
Auto-generated 2026-06-01. To extend with bilingual TR titles, add
`'title_tr'` entries inline — they will be picked up by title_for(id, lang).
"""

FRAMEWORK_ID      = 'hipaa_security'
FRAMEWORK_NAME    = 'HIPAA Security Rule'
FRAMEWORK_VERSION = '45 CFR Part 164 Subpart C'
FINDINGS_KEY      = 'HIPAA'    # key used in finding["frameworks"]

CONTROLS = {
    '164.310(b)': {
        'title':   'Workstation Use',
        'section': 'Physical Safeguards',
        'level':   'Required',
    },
    '164.310(c)': {
        'title':   'Workstation Security',
        'section': 'Physical Safeguards',
        'level':   'Required',
    },
    '164.312(b)': {
        'title':   'Audit Controls',
        'section': 'Technical Safeguards',
        'level':   'Required',
    },
    '164.312(d)': {
        'title':   'Person or Entity Authentication',
        'section': 'Technical Safeguards',
        'level':   'Required',
    },
    '164.308(a)(2)': {
        'title':   'Assigned Security Responsibility',
        'section': 'Administrative Safeguards',
        'level':   'Required',
    },
    '164.308(a)(8)': {
        'title':   'Evaluation',
        'section': 'Administrative Safeguards',
        'level':   'Required',
    },
    '164.308(b)(1)': {
        'title':   'Business Associate Contracts and Other Arrangements',
        'section': 'Administrative Safeguards',
        'level':   'Required',
    },
    '164.310(a)(1)': {
        'title':   'Facility Access Controls',
        'section': 'Physical Safeguards',
        'level':   'Addressable',
    },
    '164.310(d)(1)': {
        'title':   'Device and Media Controls',
        'section': 'Physical Safeguards',
        'level':   'Required',
    },
    '164.312(a)(1)': {
        'title':   'Access Control',
        'section': 'Technical Safeguards',
        'level':   'Required',
    },
    '164.312(c)(1)': {
        'title':   'Integrity',
        'section': 'Technical Safeguards',
        'level':   'Required',
    },
    '164.312(c)(2)': {
        'title':   'Integrity - Mechanism to Authenticate Electronic Protected Health Information',
        'section': 'Technical Safeguards',
        'level':   'Addressable',
    },
    '164.312(e)(1)': {
        'title':   'Transmission Security',
        'section': 'Technical Safeguards',
        'level':   'Required',
    },
    '164.308(a)(1)(i)': {
        'title':   'Security Management Process - Risk Analysis',
        'section': 'Administrative Safeguards',
        'level':   'Required',
    },
    '164.308(a)(3)(i)': {
        'title':   'Workforce Security - Authorization and/or Supervision',
        'section': 'Administrative Safeguards',
        'level':   'Addressable',
    },
    '164.308(a)(4)(i)': {
        'title':   'Information Access Management - Isolating Healthcare Clearinghouse Functions',
        'section': 'Administrative Safeguards',
        'level':   'Required',
    },
    '164.308(a)(5)(i)': {
        'title':   'Security Awareness and Training - Security Reminders',
        'section': 'Administrative Safeguards',
        'level':   'Addressable',
    },
    '164.308(a)(6)(i)': {
        'title':   'Security Incident Procedures - Response and Reporting',
        'section': 'Administrative Safeguards',
        'level':   'Required',
    },
    '164.308(a)(7)(i)': {
        'title':   'Contingency Plan - Data Backup Plan',
        'section': 'Administrative Safeguards',
        'level':   'Required',
    },
    '164.308(a)(7)(v)': {
        'title':   'Contingency Plan - Applications and Data Criticality Analysis',
        'section': 'Administrative Safeguards',
        'level':   'Addressable',
    },
    '164.310(a)(2)(i)': {
        'title':   'Facility Access Controls - Contingency Operations',
        'section': 'Physical Safeguards',
        'level':   'Addressable',
    },
    '164.310(d)(2)(i)': {
        'title':   'Device and Media Controls - Disposal',
        'section': 'Physical Safeguards',
        'level':   'Required',
    },
    '164.312(a)(2)(i)': {
        'title':   'Access Control - Unique User Identification',
        'section': 'Technical Safeguards',
        'level':   'Required',
    },
    '164.312(e)(2)(i)': {
        'title':   'Transmission Security - Integrity Controls',
        'section': 'Technical Safeguards',
        'level':   'Addressable',
    },
    '164.308(a)(3)(ii)': {
        'title':   'Workforce Security - Workforce Clearance Procedure',
        'section': 'Administrative Safeguards',
        'level':   'Addressable',
    },
    '164.308(a)(4)(ii)': {
        'title':   'Information Access Management - Access Authorization',
        'section': 'Administrative Safeguards',
        'level':   'Addressable',
    },
    '164.308(a)(5)(ii)': {
        'title':   'Security Awareness and Training - Protection from Malicious Software',
        'section': 'Administrative Safeguards',
        'level':   'Addressable',
    },
    '164.308(a)(5)(iv)': {
        'title':   'Security Awareness and Training - Password Management',
        'section': 'Administrative Safeguards',
        'level':   'Addressable',
    },
    '164.308(a)(7)(ii)': {
        'title':   'Contingency Plan - Disaster Recovery Plan',
        'section': 'Administrative Safeguards',
        'level':   'Required',
    },
    '164.308(a)(7)(iv)': {
        'title':   'Contingency Plan - Testing and Revision Procedures',
        'section': 'Administrative Safeguards',
        'level':   'Addressable',
    },
    '164.310(a)(2)(ii)': {
        'title':   'Facility Access Controls - Facility Security Plan',
        'section': 'Physical Safeguards',
        'level':   'Addressable',
    },
    '164.310(a)(2)(iv)': {
        'title':   'Facility Access Controls - Maintenance Records',
        'section': 'Physical Safeguards',
        'level':   'Addressable',
    },
    '164.310(d)(2)(ii)': {
        'title':   'Device and Media Controls - Media Re-use',
        'section': 'Physical Safeguards',
        'level':   'Required',
    },
    '164.310(d)(2)(iv)': {
        'title':   'Device and Media Controls - Data Backup and Storage',
        'section': 'Physical Safeguards',
        'level':   'Addressable',
    },
    '164.312(a)(2)(ii)': {
        'title':   'Access Control - Emergency Access Procedure',
        'section': 'Technical Safeguards',
        'level':   'Required',
    },
    '164.312(a)(2)(iv)': {
        'title':   'Access Control - Encryption and Decryption',
        'section': 'Technical Safeguards',
        'level':   'Addressable',
    },
    '164.312(e)(2)(ii)': {
        'title':   'Transmission Security - Encryption',
        'section': 'Technical Safeguards',
        'level':   'Addressable',
    },
    '164.308(a)(3)(iii)': {
        'title':   'Workforce Security - Termination Procedures',
        'section': 'Administrative Safeguards',
        'level':   'Addressable',
    },
    '164.308(a)(4)(iii)': {
        'title':   'Information Access Management - Access Establishment and Modification',
        'section': 'Administrative Safeguards',
        'level':   'Addressable',
    },
    '164.308(a)(5)(iii)': {
        'title':   'Security Awareness and Training - Log-in Monitoring',
        'section': 'Administrative Safeguards',
        'level':   'Addressable',
    },
    '164.308(a)(7)(iii)': {
        'title':   'Contingency Plan - Emergency Mode Operation Plan',
        'section': 'Administrative Safeguards',
        'level':   'Required',
    },
    '164.310(a)(2)(iii)': {
        'title':   'Facility Access Controls - Access Control and Validation Procedures',
        'section': 'Physical Safeguards',
        'level':   'Addressable',
    },
    '164.310(d)(2)(iii)': {
        'title':   'Device and Media Controls - Accountability',
        'section': 'Physical Safeguards',
        'level':   'Addressable',
    },
    '164.312(a)(2)(iii)': {
        'title':   'Access Control - Automatic Logoff',
        'section': 'Technical Safeguards',
        'level':   'Addressable',
    },
    '164.308(a)(1)(ii)(A)': {
        'title':   'Security Management Process - Risk Management',
        'section': 'Administrative Safeguards',
        'level':   'Required',
    },
    '164.308(a)(1)(ii)(B)': {
        'title':   'Security Management Process - Sanction Policy',
        'section': 'Administrative Safeguards',
        'level':   'Required',
    },
    '164.308(a)(1)(ii)(C)': {
        'title':   'Security Management Process - Information System Activity Review',
        'section': 'Administrative Safeguards',
        'level':   'Required',
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
# 4 widened-catalog entries — real HIPAA Security/Breach-Notification Rule
# subsections that the auto-generated catalog from cloud-audit's JSON did
# not include (they existed only as sub-level controls there). ScanBox
# findings already reference these IDs inline.
# ---------------------------------------------------------------------------

CONTROLS.update({
    '164.308(a)(3)': {
        'title':   'Administrative Safeguards — Workforce Security',
        'section': 'Administrative Safeguards',
    },
    '164.308(a)(7)(ii)(A)': {
        'title':   'Contingency Plan — Data Backup Plan (Required)',
        'section': 'Administrative Safeguards — Contingency Plan',
    },
    '164.308(a)(7)(ii)(B)': {
        'title':   'Contingency Plan — Disaster Recovery Plan (Required)',
        'section': 'Administrative Safeguards — Contingency Plan',
    },
    '164.402': {
        'title':   'Breach Notification — Definitions',
        'section': '45 CFR Part 164 Subpart D',
    },
})


# ---------------------------------------------------------------------------
# HIPAA has no version migration (Security Rule control IDs are stable since
# 2003). The translator pattern is kept here for symmetry with iso27001_catalog
# and cis_v3_catalog so scanner.translate_finding() can call all three
# uniformly without per-framework branching.
# ---------------------------------------------------------------------------

OLD_TO_NEW = {}   # no version migration for HIPAA


def translate_id(old_id: str) -> str:
    """Identity for HIPAA — no version migration."""
    return old_id


def translate_list(ids):
    """Identity for HIPAA (still de-duplicates if the caller passes dupes)."""
    if not ids:
        return ids
    seen, out = set(), []
    for x in ids:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
