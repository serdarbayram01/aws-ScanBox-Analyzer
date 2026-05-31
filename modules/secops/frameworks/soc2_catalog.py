"""SOC2 Type II — Trust Service Criteria (TSC 2017, Revised 2022).

Catalog of AICPA Trust Service Criteria control IDs with bilingual titles
and TSC category mapping. Used by SecOps scanner to aggregate findings into
SOC2 compliance scores and pillar drill-down.

Disclaimer: ScanBox provides a SOC2 readiness assessment of automated
technical controls. It does not constitute a SOC 2 examination and does not
replace evaluation by a licensed CPA firm. Many TSC controls (organizational,
governance, procedural) require manual review and are not covered here.
"""

# Pillars in display order. The catalog currently does not include Privacy
# (P) controls — companies opting into Privacy TSC would extend the catalog.
SOC2_PILLARS = [
    'Common Criteria',
    'Availability',
    'Confidentiality',
    'Processing Integrity',
]

_PREFIX_TO_PILLAR = {
    'CC': 'Common Criteria',
    'A':  'Availability',
    'C':  'Confidentiality',
    'PI': 'Processing Integrity',
    'PT': 'Confidentiality',  # legacy mapping — older SOC2 used PT for privacy
    'P':  'Confidentiality',
}


def pillar_for(control_id):
    """Map a SOC2 control ID (e.g. 'CC6.1') to its TSC pillar."""
    if not control_id:
        return None
    cid = control_id.strip().upper()
    for prefix in ('CC', 'PI', 'PT', 'A', 'C', 'P'):
        if cid.startswith(prefix):
            return _PREFIX_TO_PILLAR.get(prefix)
    return None


# 43 SOC2 TSC controls — title paraphrased from AICPA TSC 2017/2022 (control
# IDs are AICPA standard, not subject to copyright). Manual=organisational
# control requiring human review; Partial=mixed automated/manual; Automated=
# scanner can fully assess.
SOC2_CONTROLS = {
    # ----- CC1: Control Environment -----
    'CC1.1': {
        'section': 'CC1 - Control Environment',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Demonstrates commitment to integrity and ethical values',
        'title_tr': 'Dürüstlük ve etik değerlere bağlılığı gösterir',
    },
    'CC1.2': {
        'section': 'CC1 - Control Environment',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Board exercises oversight of internal control',
        'title_tr': 'Yönetim kurulu iç kontrolün gözetimini yürütür',
    },
    'CC1.3': {
        'section': 'CC1 - Control Environment',
        'pillar': 'Common Criteria',
        'assessment': 'Partial',
        'title':    'Establishes structures, authorities, and responsibilities',
        'title_tr': 'Yapılar, yetkiler ve sorumlulukları oluşturur',
    },
    'CC1.4': {
        'section': 'CC1 - Control Environment',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Demonstrates commitment to competent individuals',
        'title_tr': 'Yetkin bireylere bağlılığı gösterir',
    },
    'CC1.5': {
        'section': 'CC1 - Control Environment',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Holds individuals accountable for internal control',
        'title_tr': 'Bireyleri iç kontrolden sorumlu tutar',
    },

    # ----- CC2: Communication & Information -----
    'CC2.1': {
        'section': 'CC2 - Communication and Information',
        'pillar': 'Common Criteria',
        'assessment': 'Partial',
        'title':    'Obtains and uses relevant quality information',
        'title_tr': 'Kaliteli ve ilgili bilgileri elde eder ve kullanır',
    },
    'CC2.2': {
        'section': 'CC2 - Communication and Information',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Internally communicates information for internal control',
        'title_tr': 'İç kontrol için bilgileri kurum içinde iletir',
    },
    'CC2.3': {
        'section': 'CC2 - Communication and Information',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Communicates with external parties',
        'title_tr': 'Dış taraflarla iletişim kurar',
    },

    # ----- CC3: Risk Assessment -----
    'CC3.1': {
        'section': 'CC3 - Risk Assessment',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Specifies objectives with sufficient clarity',
        'title_tr': 'Hedefleri yeterli netlikte tanımlar',
    },
    'CC3.2': {
        'section': 'CC3 - Risk Assessment',
        'pillar': 'Common Criteria',
        'assessment': 'Partial',
        'title':    'Identifies and analyzes risks',
        'title_tr': 'Riskleri tanımlar ve analiz eder',
    },
    'CC3.3': {
        'section': 'CC3 - Risk Assessment',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Considers potential for fraud',
        'title_tr': 'Hile olasılığını dikkate alır',
    },
    'CC3.4': {
        'section': 'CC3 - Risk Assessment',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Identifies and assesses changes affecting internal control',
        'title_tr': 'İç kontrolü etkileyen değişiklikleri belirler ve değerlendirir',
    },

    # ----- CC4: Monitoring Activities -----
    'CC4.1': {
        'section': 'CC4 - Monitoring Activities',
        'pillar': 'Common Criteria',
        'assessment': 'Partial',
        'title':    'Conducts ongoing and separate evaluations',
        'title_tr': 'Sürekli ve ayrı değerlendirmeler yürütür',
    },
    'CC4.2': {
        'section': 'CC4 - Monitoring Activities',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Communicates internal control deficiencies',
        'title_tr': 'İç kontrol eksikliklerini bildirir',
    },

    # ----- CC5: Control Activities -----
    'CC5.1': {
        'section': 'CC5 - Control Activities',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Selects and develops control activities',
        'title_tr': 'Kontrol faaliyetlerini seçer ve geliştirir',
    },
    'CC5.2': {
        'section': 'CC5 - Control Activities',
        'pillar': 'Common Criteria',
        'assessment': 'Partial',
        'title':    'Selects and develops general controls over technology',
        'title_tr': 'Teknoloji üzerinde genel kontroller seçer ve geliştirir',
    },
    'CC5.3': {
        'section': 'CC5 - Control Activities',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Deploys control activities through policies and procedures',
        'title_tr': 'Politika ve prosedürlerle kontrol faaliyetlerini uygular',
    },

    # ----- CC6: Logical & Physical Access Controls -----
    'CC6.1': {
        'section': 'CC6 - Logical and Physical Access Controls',
        'pillar': 'Common Criteria',
        'assessment': 'Automated',
        'title':    'Implements logical access security software, infrastructure, and architectures',
        'title_tr': 'Mantıksal erişim güvenliği yazılımı, altyapısı ve mimarilerini uygular',
    },
    'CC6.2': {
        'section': 'CC6 - Logical and Physical Access Controls',
        'pillar': 'Common Criteria',
        'assessment': 'Automated',
        'title':    'Registers and authorizes new internal and external users',
        'title_tr': 'Yeni iç ve dış kullanıcıları kaydeder ve yetkilendirir',
    },
    'CC6.3': {
        'section': 'CC6 - Logical and Physical Access Controls',
        'pillar': 'Common Criteria',
        'assessment': 'Automated',
        'title':    'Authorizes, modifies, and removes access based on roles and responsibilities',
        'title_tr': 'Roller ve sorumluluklara göre erişimi yetkilendirir, değiştirir ve kaldırır',
    },
    'CC6.4': {
        'section': 'CC6 - Logical and Physical Access Controls',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Restricts physical access to facilities and protected information assets',
        'title_tr': 'Tesis ve korunan bilgi varlıklarına fiziksel erişimi kısıtlar',
    },
    'CC6.5': {
        'section': 'CC6 - Logical and Physical Access Controls',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Disposes of data, hardware, and software securely',
        'title_tr': 'Veri, donanım ve yazılımları güvenli şekilde imha eder',
    },
    'CC6.6': {
        'section': 'CC6 - Logical and Physical Access Controls',
        'pillar': 'Common Criteria',
        'assessment': 'Automated',
        'title':    'Implements logical access security measures against external threats',
        'title_tr': 'Dış tehditlere karşı mantıksal erişim güvenlik önlemleri uygular',
    },
    'CC6.7': {
        'section': 'CC6 - Logical and Physical Access Controls',
        'pillar': 'Common Criteria',
        'assessment': 'Automated',
        'title':    'Restricts the transmission, movement, and removal of information',
        'title_tr': 'Bilginin iletilmesini, taşınmasını ve kaldırılmasını kısıtlar',
    },
    'CC6.8': {
        'section': 'CC6 - Logical and Physical Access Controls',
        'pillar': 'Common Criteria',
        'assessment': 'Partial',
        'title':    'Implements controls to prevent or detect unauthorized software',
        'title_tr': 'Yetkisiz yazılımı önlemek veya tespit etmek için kontroller uygular',
    },

    # ----- CC7: System Operations -----
    'CC7.1': {
        'section': 'CC7 - System Operations',
        'pillar': 'Common Criteria',
        'assessment': 'Automated',
        'title':    'Detects and monitors changes to configurations',
        'title_tr': 'Yapılandırma değişikliklerini tespit eder ve izler',
    },
    'CC7.2': {
        'section': 'CC7 - System Operations',
        'pillar': 'Common Criteria',
        'assessment': 'Automated',
        'title':    'Monitors system components for anomalies and security events',
        'title_tr': 'Sistem bileşenlerini anomali ve güvenlik olayları için izler',
    },
    'CC7.3': {
        'section': 'CC7 - System Operations',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Evaluates security events to determine response',
        'title_tr': 'Yanıtı belirlemek için güvenlik olaylarını değerlendirir',
    },
    'CC7.4': {
        'section': 'CC7 - System Operations',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Responds to security incidents per established response programs',
        'title_tr': 'Güvenlik olaylarına belirlenmiş yanıt programlarına göre tepki verir',
    },
    'CC7.5': {
        'section': 'CC7 - System Operations',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Recovers from identified security incidents',
        'title_tr': 'Tespit edilen güvenlik olaylarından kurtarır',
    },

    # ----- CC8: Change Management -----
    'CC8.1': {
        'section': 'CC8 - Change Management',
        'pillar': 'Common Criteria',
        'assessment': 'Partial',
        'title':    'Authorizes, designs, develops, tests, approves, and implements changes',
        'title_tr': 'Değişiklikleri yetkilendirir, tasarlar, geliştirir, test eder, onaylar ve uygular',
    },

    # ----- CC9: Risk Mitigation -----
    'CC9.1': {
        'section': 'CC9 - Risk Mitigation',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Identifies, selects, and develops risk mitigation activities',
        'title_tr': 'Risk azaltma faaliyetlerini belirler, seçer ve geliştirir',
    },
    'CC9.2': {
        'section': 'CC9 - Risk Mitigation',
        'pillar': 'Common Criteria',
        'assessment': 'Manual',
        'title':    'Manages vendor and business partner risk',
        'title_tr': 'Tedarikçi ve iş ortağı riskini yönetir',
    },

    # ----- A1: Availability -----
    'A1.1': {
        'section': 'A1 - Availability',
        'pillar': 'Availability',
        'assessment': 'Partial',
        'title':    'Maintains current processing capacity to support availability commitments',
        'title_tr': 'Erişilebilirlik taahhütlerini desteklemek için mevcut işleme kapasitesini korur',
    },
    'A1.2': {
        'section': 'A1 - Availability',
        'pillar': 'Availability',
        'assessment': 'Automated',
        'title':    'Authorizes and implements environmental protections, backup, and recovery',
        'title_tr': 'Çevresel korumaları, yedekleme ve kurtarmayı yetkilendirir ve uygular',
    },
    'A1.3': {
        'section': 'A1 - Availability',
        'pillar': 'Availability',
        'assessment': 'Manual',
        'title':    'Tests recovery plan procedures',
        'title_tr': 'Kurtarma planı prosedürlerini test eder',
    },

    # ----- C1: Confidentiality -----
    'C1.1': {
        'section': 'C1 - Confidentiality',
        'pillar': 'Confidentiality',
        'assessment': 'Partial',
        'title':    'Identifies and maintains confidential information',
        'title_tr': 'Gizli bilgileri tanımlar ve sürdürür',
    },
    'C1.2': {
        'section': 'C1 - Confidentiality',
        'pillar': 'Confidentiality',
        'assessment': 'Automated',
        'title':    'Disposes of confidential information to meet objectives',
        'title_tr': 'Hedefleri karşılamak için gizli bilgileri imha eder',
    },

    # ----- PI1: Processing Integrity -----
    'PI1.1': {
        'section': 'PI1 - Processing Integrity',
        'pillar': 'Processing Integrity',
        'assessment': 'Manual',
        'title':    'Obtains, generates, uses, and communicates relevant quality information',
        'title_tr': 'İlgili kaliteli bilgileri elde eder, üretir, kullanır ve iletir',
    },
    'PI1.2': {
        'section': 'PI1 - Processing Integrity',
        'pillar': 'Processing Integrity',
        'assessment': 'Manual',
        'title':    'Implements policies for inputs to support processing integrity',
        'title_tr': 'İşlem bütünlüğünü desteklemek için girdi politikaları uygular',
    },
    'PI1.3': {
        'section': 'PI1 - Processing Integrity',
        'pillar': 'Processing Integrity',
        'assessment': 'Manual',
        'title':    'Implements policies for processing to support integrity',
        'title_tr': 'Bütünlüğü desteklemek için işleme politikaları uygular',
    },
    'PI1.4': {
        'section': 'PI1 - Processing Integrity',
        'pillar': 'Processing Integrity',
        'assessment': 'Partial',
        'title':    'Implements policies for outputs to support processing integrity',
        'title_tr': 'İşlem bütünlüğünü desteklemek için çıktı politikaları uygular',
    },
    'PI1.5': {
        'section': 'PI1 - Processing Integrity',
        'pillar': 'Processing Integrity',
        'assessment': 'Partial',
        'title':    'Implements policies for storage to support processing integrity',
        'title_tr': 'İşlem bütünlüğünü desteklemek için depolama politikaları uygular',
    },
}


def list_automated_controls():
    """Return control IDs that scanner can fully assess (used for coverage calc)."""
    return [cid for cid, meta in SOC2_CONTROLS.items() if meta['assessment'] == 'Automated']


def list_manual_controls():
    """Return control IDs that require human review (for Setup Guide checklist)."""
    return [cid for cid, meta in SOC2_CONTROLS.items() if meta['assessment'] == 'Manual']
