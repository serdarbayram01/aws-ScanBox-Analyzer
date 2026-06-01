"""
SecOps — ISO/IEC 27001:2022 - Annex A Controls (iso27001_2022, v2022) control catalog.

Read-only metadata: control_id -> {title, section, level (if any)}.
Used by SecOps drill-down to show full control titles next to the bare
IDs that inventory modules already place on each finding's `frameworks` dict.

Source: cloud-audit (https://github.com/gebalamariusz/cloud-audit, MIT)
        compliance/frameworks/iso27001_2022.json
Auto-generated 2026-06-01. To extend with bilingual TR titles, add
`'title_tr'` entries inline — they will be picked up by title_for(id, lang).
"""

FRAMEWORK_ID      = 'iso27001_2022'
FRAMEWORK_NAME    = 'ISO/IEC 27001:2022 - Annex A Controls'
FRAMEWORK_VERSION = '2022'
FINDINGS_KEY      = 'ISO27001'    # key used in finding["frameworks"]

CONTROLS = {
    'A.5.1': {
        'title':   'Policies for information security',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.2': {
        'title':   'Information security roles and responsibilities',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.3': {
        'title':   'Segregation of duties',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.4': {
        'title':   'Management responsibilities',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.5': {
        'title':   'Contact with authorities',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.6': {
        'title':   'Contact with special interest groups',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.7': {
        'title':   'Threat intelligence',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.8': {
        'title':   'Information security in project management',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.9': {
        'title':   'Inventory of information and other associated assets',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.6.1': {
        'title':   'Screening',
        'section': 'A.6 - People Controls',
        'level':   '',
    },
    'A.6.2': {
        'title':   'Terms and conditions of employment',
        'section': 'A.6 - People Controls',
        'level':   '',
    },
    'A.6.3': {
        'title':   'Information security awareness, education and training',
        'section': 'A.6 - People Controls',
        'level':   '',
    },
    'A.6.4': {
        'title':   'Disciplinary process',
        'section': 'A.6 - People Controls',
        'level':   '',
    },
    'A.6.5': {
        'title':   'Responsibilities after termination or change of employment',
        'section': 'A.6 - People Controls',
        'level':   '',
    },
    'A.6.6': {
        'title':   'Confidentiality or non-disclosure agreements',
        'section': 'A.6 - People Controls',
        'level':   '',
    },
    'A.6.7': {
        'title':   'Remote working',
        'section': 'A.6 - People Controls',
        'level':   '',
    },
    'A.6.8': {
        'title':   'Information security event reporting',
        'section': 'A.6 - People Controls',
        'level':   '',
    },
    'A.7.1': {
        'title':   'Physical security perimeters',
        'section': 'A.7 - Physical Controls',
        'level':   '',
    },
    'A.7.2': {
        'title':   'Physical entry',
        'section': 'A.7 - Physical Controls',
        'level':   '',
    },
    'A.7.3': {
        'title':   'Securing offices, rooms and facilities',
        'section': 'A.7 - Physical Controls',
        'level':   '',
    },
    'A.7.4': {
        'title':   'Physical security monitoring',
        'section': 'A.7 - Physical Controls',
        'level':   '',
    },
    'A.7.5': {
        'title':   'Protecting against physical and environmental threats',
        'section': 'A.7 - Physical Controls',
        'level':   '',
    },
    'A.7.6': {
        'title':   'Working in secure areas',
        'section': 'A.7 - Physical Controls',
        'level':   '',
    },
    'A.7.7': {
        'title':   'Clear desk and clear screen',
        'section': 'A.7 - Physical Controls',
        'level':   '',
    },
    'A.7.8': {
        'title':   'Equipment siting and protection',
        'section': 'A.7 - Physical Controls',
        'level':   '',
    },
    'A.7.9': {
        'title':   'Security of assets off-premises',
        'section': 'A.7 - Physical Controls',
        'level':   '',
    },
    'A.8.1': {
        'title':   'User endpoint devices',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.2': {
        'title':   'Privileged access rights',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.3': {
        'title':   'Information access restriction',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.4': {
        'title':   'Access to source code',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.5': {
        'title':   'Secure authentication',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.6': {
        'title':   'Capacity management',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.7': {
        'title':   'Protection against malware',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.8': {
        'title':   'Management of technical vulnerabilities',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.9': {
        'title':   'Configuration management',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.5.10': {
        'title':   'Acceptable use of information and other associated assets',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.11': {
        'title':   'Return of assets',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.12': {
        'title':   'Classification of information',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.13': {
        'title':   'Labelling of information',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.14': {
        'title':   'Information transfer',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.15': {
        'title':   'Access control',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.16': {
        'title':   'Identity management',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.17': {
        'title':   'Authentication information',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.18': {
        'title':   'Access rights',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.19': {
        'title':   'Information security in supplier relationships',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.20': {
        'title':   'Addressing information security within supplier agreements',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.21': {
        'title':   'Managing information security in the ICT supply chain',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.22': {
        'title':   'Monitoring, review and change management of supplier services',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.23': {
        'title':   'Information security for use of cloud services',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.24': {
        'title':   'Information security incident management planning and preparation',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.25': {
        'title':   'Assessment and decision on information security events',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.26': {
        'title':   'Response to information security incidents',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.27': {
        'title':   'Learning from information security incidents',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.28': {
        'title':   'Collection of evidence',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.29': {
        'title':   'Information security during disruption',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.30': {
        'title':   'ICT readiness for business continuity',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.31': {
        'title':   'Legal, statutory, regulatory and contractual requirements',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.32': {
        'title':   'Intellectual property rights',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.33': {
        'title':   'Protection of records',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.34': {
        'title':   'Privacy and protection of personal information',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.35': {
        'title':   'Independent review of information security',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.36': {
        'title':   'Compliance with policies, rules and standards for information security',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.5.37': {
        'title':   'Documented operating procedures',
        'section': 'A.5 - Organizational Controls',
        'level':   '',
    },
    'A.7.10': {
        'title':   'Storage media',
        'section': 'A.7 - Physical Controls',
        'level':   '',
    },
    'A.7.11': {
        'title':   'Supporting utilities',
        'section': 'A.7 - Physical Controls',
        'level':   '',
    },
    'A.7.12': {
        'title':   'Cabling security',
        'section': 'A.7 - Physical Controls',
        'level':   '',
    },
    'A.7.13': {
        'title':   'Equipment maintenance',
        'section': 'A.7 - Physical Controls',
        'level':   '',
    },
    'A.7.14': {
        'title':   'Secure disposal or re-use of equipment',
        'section': 'A.7 - Physical Controls',
        'level':   '',
    },
    'A.8.10': {
        'title':   'Information deletion',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.11': {
        'title':   'Data masking',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.12': {
        'title':   'Data leakage prevention',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.13': {
        'title':   'Information backup',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.14': {
        'title':   'Redundancy of information processing facilities',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.15': {
        'title':   'Logging',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.16': {
        'title':   'Monitoring activities',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.17': {
        'title':   'Clock synchronization',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.18': {
        'title':   'Use of privileged utility programs',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.19': {
        'title':   'Installation of software on operational systems',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.20': {
        'title':   'Networks security',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.21': {
        'title':   'Security of network services',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.22': {
        'title':   'Segregation of networks',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.23': {
        'title':   'Web filtering',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.24': {
        'title':   'Use of cryptography',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.25': {
        'title':   'Secure development life cycle',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.26': {
        'title':   'Application security requirements',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.27': {
        'title':   'Secure system architecture and engineering principles',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.28': {
        'title':   'Secure coding',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.29': {
        'title':   'Security testing in development and acceptance',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.30': {
        'title':   'Outsourced development',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.31': {
        'title':   'Separation of development, test and production environments',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.32': {
        'title':   'Change management',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.33': {
        'title':   'Test information',
        'section': 'A.8 - Technological Controls',
        'level':   '',
    },
    'A.8.34': {
        'title':   'Protection of information systems during audit testing',
        'section': 'A.8 - Technological Controls',
        'level':   '',
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
# ISO/IEC 27001:2013 → 2022 crosswalk
# Source: ISO/IEC 27001:2022 Annex B. 114 → 93 controls reorganised into
# four themes (5/6/7/8 = Organisational/People/Physical/Technological).
# Several 2013 controls merged (e.g. all A.12.4.x logging → single A.8.15).
# Idempotent: a 2022 ID stays unchanged (not a key here).
# ---------------------------------------------------------------------------

OLD_TO_NEW = {
    # Cryptography
    'A.10.1.1': 'A.8.24',   # Cryptographic controls policy
    'A.10.1.2': 'A.8.24',   # Key management (merged into A.8.24)
    # Operations security — backup, logging, vulnerabilities
    'A.12.3.1': 'A.8.13',   # Information backup
    'A.12.4.1': 'A.8.15',   # Event logging
    'A.12.4.2': 'A.8.15',   # Protection of log information (merged)
    'A.12.4.3': 'A.8.15',   # Administrator and operator logs (merged)
    'A.12.6.1': 'A.8.8',    # Management of technical vulnerabilities
    # Network controls
    'A.13.1.1': 'A.8.20',   # Network controls → Networks security
    'A.13.1.2': 'A.8.21',   # Security of network services
    'A.13.1.3': 'A.8.22',   # Segregation in networks
    'A.13.2.3': 'A.8.20',   # Electronic messaging — closest match
    # Application / system development
    'A.14.1.2': 'A.8.26',   # Securing application services on public networks
    'A.14.1.3': 'A.8.26',   # Protecting application services transactions (merged)
    'A.14.2.1': 'A.8.25',   # Secure development policy → Secure development lifecycle
    'A.14.2.5': 'A.8.27',   # Secure system engineering principles
    # Incident management
    'A.16.1.4': 'A.5.25',   # Assessment and decision on info security events
    'A.16.1.5': 'A.5.26',   # Response to information security incidents
    # Business continuity
    'A.17.1.2': 'A.5.30',   # Implementing IS continuity → ICT readiness for BC
    'A.17.2.1': 'A.8.14',   # Availability of info processing facilities → Redundancy
    # Compliance
    'A.18.1.1': 'A.5.31',   # Identification of applicable legislation
    'A.18.1.3': 'A.5.33',   # Protection of records
    'A.18.1.4': 'A.5.34',   # Privacy and protection of PII
    'A.18.2.2': 'A.5.36',   # Compliance with security policies and standards
    # Access control (A.9.* family moved to A.5.15/16/17/18 / A.8.5)
    'A.9.1.2':  'A.5.15',   # Access to networks and network services
    'A.9.2.3':  'A.5.18',   # Management of privileged access rights
    'A.9.2.4':  'A.5.17',   # Management of secret authentication information
    'A.9.4.1':  'A.5.15',   # Information access restriction
    'A.9.4.2':  'A.8.5',    # Secure log-on procedures → Secure authentication
    'A.9.4.3':  'A.5.17',   # Password management system → Authentication information
    # Suppliers
    'A.15.1.1': 'A.5.19',   # Info security policy for supplier relationships
}


def translate_id(old_id: str) -> str:
    """Return the 2022 ID for a 2013 ID, or the input unchanged. Idempotent."""
    return OLD_TO_NEW.get(old_id, old_id)


def translate_list(ids):
    """Map translate_id over a list, preserving order + de-duplicating mergers.

    Multiple 2013 IDs can merge to one 2022 ID (A.12.4.1/2/3 → A.8.15);
    dedup keeps the framework score honest (one finding, one control).
    """
    if not ids:
        return ids
    seen, out = set(), []
    for old in ids:
        new = OLD_TO_NEW.get(old, old)
        if new not in seen:
            seen.add(new)
            out.append(new)
    return out
