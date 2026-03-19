"""
WAFR Knowledge Base — Static definitions for AWS Well-Architected Framework controls.
Contains control codes, descriptions, doc links, and finding-to-advice template mappings.
"""

# ---------------------------------------------------------------------------
# WAFR Pillar definitions
# ---------------------------------------------------------------------------
PILLARS = {
    'SEC': {
        'name_en': 'Security',
        'name_tr': 'Guvenlik',
        'description_en': 'Protect data, systems and assets through risk assessment, identity management, encryption and monitoring.',
        'description_tr': 'Risk degerlendirme, kimlik yonetimi, sifreleme ve izleme yoluyla verileri, sistemleri ve varliklari koruma.',
    },
    'OPS': {
        'name_en': 'Operational Excellence',
        'name_tr': 'Operasyonel Mukemmellik',
        'description_en': 'Run and monitor systems to deliver business value and continually improve processes and procedures.',
        'description_tr': 'Is degeri sunmak ve surecleri surekli iyilestirmek icin sistemleri calistirma ve izleme.',
    },
    'REL': {
        'name_en': 'Reliability',
        'name_tr': 'Guvenilirlik',
        'description_en': 'Ensure workloads perform their intended function correctly and consistently, recovering quickly from failures.',
        'description_tr': 'Is yuklerinin amaclanan islevlerini dogru ve tutarli bir sekilde yerine getirmesini ve arizalardan hizla kurtulmasini saglama.',
    },
    'PERF': {
        'name_en': 'Performance Efficiency',
        'name_tr': 'Performans Verimliligi',
        'description_en': 'Use computing resources efficiently to meet system requirements and maintain efficiency as demand changes.',
        'description_tr': 'Sistem gereksinimlerini karsilamak ve talep degistikce verimliligi korumak icin bilisim kaynaklarini verimli kullanma.',
    },
    'COST': {
        'name_en': 'Cost Optimization',
        'name_tr': 'Maliyet Optimizasyonu',
        'description_en': 'Avoid unnecessary costs, understand spending and control fund allocation, select the right resource types and quantities.',
        'description_tr': 'Gereksiz maliyetlerden kacinma, harcamalari anlama, dogru kaynak turlerini ve miktarlarini secme.',
    },
    'SUS': {
        'name_en': 'Sustainability',
        'name_tr': 'Surdurulebilirlik',
        'description_en': 'Minimize the environmental impact of running cloud workloads through efficient resource use and managed services.',
        'description_tr': 'Verimli kaynak kullanimi ve yonetilen servisler araciligiyla bulut is yuklerinin cevresel etkisini en aza indirme.',
    },
}

# ---------------------------------------------------------------------------
# WAFR Control codes with descriptions and AWS doc links
# ---------------------------------------------------------------------------
WAFR_CONTROLS = {
    # ── Security ──
    'SEC01': {
        'pillar': 'SEC',
        'title_en': 'Securely operate your workload',
        'title_tr': 'Is yukunuzu guvenli bir sekilde isletin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_securely_operate_workload.html',
    },
    'SEC02': {
        'pillar': 'SEC',
        'title_en': 'Manage identities for people and machines',
        'title_tr': 'Kullanicilar ve makineler icin kimlikleri yonetin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_identities_identity.html',
    },
    'SEC03': {
        'pillar': 'SEC',
        'title_en': 'Manage permissions for people and machines',
        'title_tr': 'Kullanicilar ve makineler icin izinleri yonetin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_permissions_permissions.html',
    },
    'SEC04': {
        'pillar': 'SEC',
        'title_en': 'Detect and investigate security events',
        'title_tr': 'Guvenlik olaylarini tespit edin ve arastirin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_detect_investigate_events.html',
    },
    'SEC05': {
        'pillar': 'SEC',
        'title_en': 'Protect network resources',
        'title_tr': 'Ag kaynaklarini koruyun',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_network_protection.html',
    },
    'SEC06': {
        'pillar': 'SEC',
        'title_en': 'Protect compute resources',
        'title_tr': 'Islem kaynaklarini koruyun',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_protect_compute.html',
    },
    'SEC07': {
        'pillar': 'SEC',
        'title_en': 'Classify data',
        'title_tr': 'Verileri siniflandirin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_data_classification.html',
    },
    'SEC08': {
        'pillar': 'SEC',
        'title_en': 'Protect data at rest',
        'title_tr': 'Duran verileri koruyun',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_protect_data_rest.html',
    },
    'SEC09': {
        'pillar': 'SEC',
        'title_en': 'Protect data in transit',
        'title_tr': 'Aktarim halindeki verileri koruyun',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_protect_data_transit.html',
    },
    'SEC10': {
        'pillar': 'SEC',
        'title_en': 'Anticipate, respond to, and recover from incidents',
        'title_tr': 'Olaylari ongorun, mudahale edin ve kurtarin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_incident_response.html',
    },
    'SEC11': {
        'pillar': 'SEC',
        'title_en': 'Application security',
        'title_tr': 'Uygulama guvenligi',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_application_security.html',
    },
    # ── Operational Excellence ──
    'OPS01': {
        'pillar': 'OPS',
        'title_en': 'Determine what your priorities are',
        'title_tr': 'Onceliklerinizi belirleyin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_priorities.html',
    },
    'OPS02': {
        'pillar': 'OPS',
        'title_en': 'Structure your organization to support your outcomes',
        'title_tr': 'Organizasyonunuzu sonuclarinizi destekleyecek sekilde yapilandirin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_org_structure.html',
    },
    'OPS03': {
        'pillar': 'OPS',
        'title_en': 'Support your organizational culture',
        'title_tr': 'Organizasyon kulturunuzu destekleyin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_org_culture.html',
    },
    'OPS04': {
        'pillar': 'OPS',
        'title_en': 'Implement observability',
        'title_tr': 'Gozlemlenebilirligi uygulayin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_observability.html',
    },
    'OPS05': {
        'pillar': 'OPS',
        'title_en': 'Design for operations',
        'title_tr': 'Operasyonlar icin tasarlayin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_design_operations.html',
    },
    'OPS06': {
        'pillar': 'OPS',
        'title_en': 'Reduce defects, ease remediation, and improve flow into production',
        'title_tr': 'Hatalari azaltin, duzeltmeyi kolaylastirin ve uretime akisi iyilestirin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_reduce_defects.html',
    },
    'OPS07': {
        'pillar': 'OPS',
        'title_en': 'Mitigate deployment risks',
        'title_tr': 'Dagitim risklerini azaltin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mitigate_deployment_risks.html',
    },
    'OPS08': {
        'pillar': 'OPS',
        'title_en': 'Know the status of your workloads and operations',
        'title_tr': 'Is yuklerinizin ve operasyonlarinizin durumunu bilin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_workload_status.html',
    },
    'OPS09': {
        'pillar': 'OPS',
        'title_en': 'Manage workload and operations events',
        'title_tr': 'Is yuku ve operasyon olaylarini yonetin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_manage_events.html',
    },
    'OPS10': {
        'pillar': 'OPS',
        'title_en': 'Evolve operations',
        'title_tr': 'Operasyonlari gelistirin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve.html',
    },
    'OPS11': {
        'pillar': 'OPS',
        'title_en': 'Practice continuous improvement',
        'title_tr': 'Surekli iyilestirmeyi uygulama',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve.html',
    },
    # ── Reliability ──
    'REL01': {
        'pillar': 'REL',
        'title_en': 'Manage service quotas and constraints',
        'title_tr': 'Servis kotalrini ve kisitlamalari yonetin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_service_quotas.html',
    },
    'REL02': {
        'pillar': 'REL',
        'title_en': 'Plan your network topology',
        'title_tr': 'Ag topolojinizi planlayin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_network_topology.html',
    },
    'REL03': {
        'pillar': 'REL',
        'title_en': 'Design your workload service architecture',
        'title_tr': 'Is yuku servis mimarinizi tasarlayin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_service_architecture.html',
    },
    'REL04': {
        'pillar': 'REL',
        'title_en': 'Design interactions in a distributed system to prevent failures',
        'title_tr': 'Dagitik sistemde etkilesimleri ariza onleyecek sekilde tasarlayin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure.html',
    },
    'REL05': {
        'pillar': 'REL',
        'title_en': 'Design interactions in a distributed system to mitigate or withstand failures',
        'title_tr': 'Dagitik sistemde etkilesimleri arizalara dayanikli tasarlayin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure.html',
    },
    'REL06': {
        'pillar': 'REL',
        'title_en': 'Monitor workload resources',
        'title_tr': 'Is yuku kaynaklarini izleyin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_monitor_workload.html',
    },
    'REL07': {
        'pillar': 'REL',
        'title_en': 'Design your workload to adapt to changes in demand',
        'title_tr': 'Is yukunuzu talep degisikliklerine uyum saglayacak sekilde tasarlayin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_adapt_to_demand.html',
    },
    'REL08': {
        'pillar': 'REL',
        'title_en': 'Implement change',
        'title_tr': 'Degisikligi uygulayin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_tracking_change_management.html',
    },
    'REL09': {
        'pillar': 'REL',
        'title_en': 'Back up data',
        'title_tr': 'Verileri yedekleyin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_data_backup.html',
    },
    'REL10': {
        'pillar': 'REL',
        'title_en': 'Use fault isolation to protect your workload',
        'title_tr': 'Is yukunuzu korumak icin ariza izolasyonu kullanin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_fault_isolation.html',
    },
    'REL11': {
        'pillar': 'REL',
        'title_en': 'Design your workload to withstand component failures',
        'title_tr': 'Is yukunuzu bilesen arizalarina dayanikli tasarlayin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_withstand_component_failure.html',
    },
    'REL12': {
        'pillar': 'REL',
        'title_en': 'Test reliability',
        'title_tr': 'Guvenilirligi test edin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_test_reliability.html',
    },
    'REL13': {
        'pillar': 'REL',
        'title_en': 'Plan for disaster recovery',
        'title_tr': 'Felaket kurtarma planlayin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery.html',
    },
    # ── Performance Efficiency ──
    'PERF01': {
        'pillar': 'PERF',
        'title_en': 'Select the best compute options',
        'title_tr': 'En iyi islem seceneklerini secin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_compute.html',
    },
    'PERF02': {
        'pillar': 'PERF',
        'title_en': 'Select the best storage options',
        'title_tr': 'En iyi depolama seceneklerini secin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_storage.html',
    },
    'PERF03': {
        'pillar': 'PERF',
        'title_en': 'Select the best database options',
        'title_tr': 'En iyi veritabani seceneklerini secin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_database.html',
    },
    'PERF04': {
        'pillar': 'PERF',
        'title_en': 'Select the best networking options',
        'title_tr': 'En iyi ag seceneklerini secin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_networking.html',
    },
    'PERF05': {
        'pillar': 'PERF',
        'title_en': 'Use a process for continual improvement',
        'title_tr': 'Surekli iyilestirme icin bir surec kullanin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_process.html',
    },
    'PERF06': {
        'pillar': 'PERF',
        'title_en': 'Monitor your resources',
        'title_tr': 'Kaynaklarinizi izleyin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_monitor.html',
    },
    'PERF07': {
        'pillar': 'PERF',
        'title_en': 'Use tradeoffs to improve performance',
        'title_tr': 'Performansi iyilestirmek icin odunlesimler kullanin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_tradeoffs.html',
    },
    'PERF08': {
        'pillar': 'PERF',
        'title_en': 'Optimize over time',
        'title_tr': 'Zamanla optimize edin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_optimize.html',
    },
    # ── Cost Optimization ──
    'COST01': {
        'pillar': 'COST',
        'title_en': 'Practice cloud financial management',
        'title_tr': 'Bulut finansal yonetimini uygulama',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_cloud_financial_management.html',
    },
    'COST02': {
        'pillar': 'COST',
        'title_en': 'Governance',
        'title_tr': 'Yonetisim',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_governance.html',
    },
    'COST03': {
        'pillar': 'COST',
        'title_en': 'Monitor cost and usage',
        'title_tr': 'Maliyet ve kullanimi izleyin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_monitor_usage.html',
    },
    'COST04': {
        'pillar': 'COST',
        'title_en': 'Decommission resources',
        'title_tr': 'Kullanilmayan kaynaklari kaldirun',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_decomissioning_resources.html',
    },
    'COST05': {
        'pillar': 'COST',
        'title_en': 'Select the correct resource type, size, and number',
        'title_tr': 'Dogru kaynak turunu, boyutunu ve sayisini secin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_type_size_number_resources.html',
    },
    'COST06': {
        'pillar': 'COST',
        'title_en': 'Select the best pricing model',
        'title_tr': 'En iyi fiyatlandirma modelini secin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_pricing_model.html',
    },
    'COST07': {
        'pillar': 'COST',
        'title_en': 'Plan for data transfer charges',
        'title_tr': 'Veri aktarim ucretlerini planlayin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_data_transfer.html',
    },
    'COST08': {
        'pillar': 'COST',
        'title_en': 'Manage demand and supply resources',
        'title_tr': 'Talep ve arz kaynaklarini yonetin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_manage_demand_supply.html',
    },
    'COST09': {
        'pillar': 'COST',
        'title_en': 'Evaluate new services',
        'title_tr': 'Yeni servisleri degerlendirin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_new_services.html',
    },
    'COST10': {
        'pillar': 'COST',
        'title_en': 'Evaluate cost when selecting services',
        'title_tr': 'Servis secerken maliyeti degerlendirin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_evaluating_cost.html',
    },
    'COST11': {
        'pillar': 'COST',
        'title_en': 'Optimize over time',
        'title_tr': 'Zamanla optimize edin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_optimize_over_time.html',
    },
    # ── Sustainability ──
    'SUS01': {
        'pillar': 'SUS',
        'title_en': 'Choose region based on business requirements and sustainability goals',
        'title_tr': 'Is gereksinimleri ve surdurulebilirlik hedeflerine gore bolge secin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_region.html',
    },
    'SUS02': {
        'pillar': 'SUS',
        'title_en': 'Align SLAs with sustainability goals',
        'title_tr': "SLA'lari surdurulebilirlik hedefleriyle uyumlayın",
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_user.html',
    },
    'SUS03': {
        'pillar': 'SUS',
        'title_en': 'Optimize software and architecture for async and scheduled jobs',
        'title_tr': 'Asenkron ve zamanlanmis isler icin yazilim ve mimariyi optimize edin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_software.html',
    },
    'SUS04': {
        'pillar': 'SUS',
        'title_en': 'Use efficient hardware and software offerings',
        'title_tr': 'Verimli donanim ve yazilim tekliflerini kullanin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_hardware.html',
    },
    'SUS05': {
        'pillar': 'SUS',
        'title_en': 'Reduce the sustainability impact of data',
        'title_tr': 'Verinin surdurulebilirlik etkisini azaltin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_data.html',
    },
    'SUS06': {
        'pillar': 'SUS',
        'title_en': 'Select the correct development and deployment patterns',
        'title_tr': 'Dogru gelistirme ve dagitim desenlerini secin',
        'doc_url': 'https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_dev.html',
    },
}


# ---------------------------------------------------------------------------
# Risk severity mapping: SecOps severity + WAFR pillar → Risk level
# ---------------------------------------------------------------------------
def map_risk(severity, pillar='SEC'):
    """Map SecOps finding severity to assessment risk level."""
    sev = (severity or '').upper()
    if sev in ('CRITICAL',):
        return 'HIGH'
    if sev in ('HIGH',):
        return 'HIGH' if pillar in ('SEC', 'REL') else 'MEDIUM'
    if sev in ('MEDIUM',):
        return 'MEDIUM'
    return 'LOW'


# ---------------------------------------------------------------------------
# Service-to-WAFR mapping: which checks map to which WAFR codes
# ---------------------------------------------------------------------------
# Maps SecOps finding id patterns to WAFR codes + professional advice templates
SERVICE_ADVICE_RULES = {
    # ── IAM ──
    'IAM': {
        'category_en': 'User & Account Management',
        'category_tr': 'Kullanici ve Hesap Yonetimi',
        'rules': [
            {
                'match': lambda f: 'mfa' in f.get('id', '').lower() or 'mfa' in f.get('title', '').lower(),
                'wafr': ['SEC02'],
                'risk': 'HIGH',
                'finding_en': 'Multi-Factor Authentication (MFA) is not enabled for IAM users. This significantly increases the risk of credential-based attacks and unauthorized access.',
                'finding_tr': 'IAM kullanicilari icin Cok Faktorlu Kimlik Dogrulama (MFA) etkinlestirilmemistir. Bu durum, kimlik bilgisi tabanli saldiri ve yetkisiz erisim riskini onemli olcude artirmaktadir.',
                'recommendation_en': 'Enable MFA for all IAM users immediately. Virtual MFA (Authenticator apps) is recommended as a minimum. For privileged accounts, consider hardware MFA tokens.',
                'recommendation_tr': 'Tum IAM kullanicilari icin MFA derhal etkinlestirilmelidir. Minimum olarak sanal MFA (Authenticator uygulamalari) onerilir. Ayricalikli hesaplar icin donanim MFA token\'lari degerlendirilmelidir.',
            },
            {
                'match': lambda f: 'access_key' in f.get('id', '').lower() or 'access key' in f.get('title', '').lower(),
                'wafr': ['SEC02', 'SEC03'],
                'risk': 'HIGH',
                'finding_en': 'Active access keys detected that have not been rotated. Long-lived credentials pose a significant security risk if compromised.',
                'finding_tr': 'Rotate edilmemis aktif erisim anahtarlari tespit edilmistir. Uzun omurlu kimlik bilgileri, ele gecirilmesi durumunda onemli bir guvenlik riski olusturmaktadir.',
                'recommendation_en': 'Implement automatic access key rotation strategy. Deactivate or delete keys that have not been used for 90+ days. Prefer IAM Roles with temporary credentials over long-term access keys.',
                'recommendation_tr': 'Otomatik erisim anahtari rotasyon stratejisi uygulanmalidir. 90+ gun kullanilmayan anahtarlar devre disi birakilmali veya silinmelidir. Uzun vadeli erisim anahtarlari yerine gecici kimlik bilgileri iceren IAM Roller tercih edilmelidir.',
            },
            {
                'match': lambda f: 'password_policy' in f.get('id', '').lower() or 'password' in f.get('title', '').lower(),
                'wafr': ['SEC02'],
                'risk': 'MEDIUM',
                'finding_en': 'IAM password policy does not meet security best practices. Weak password policies increase the risk of brute-force attacks.',
                'finding_tr': 'IAM parola politikasi guvenlik en iyi uygulamalarini karsilamamaktadir. Zayif parola politikalari kaba kuvvet saldiri riskini artirmaktadir.',
                'recommendation_en': 'Configure a strong password policy: minimum 14 characters, require uppercase, lowercase, numbers, and symbols. Enable password expiration (90 days) and prevent password reuse.',
                'recommendation_tr': 'Guclu bir parola politikasi yapilandirilmalidir: minimum 14 karakter, buyuk harf, kucuk harf, rakam ve sembol zorunlulugu. Parola suresi dolumu (90 gun) etkinlestirilmeli ve parola tekrar kullanimi engellenmelidir.',
            },
            {
                'match': lambda f: 'admin' in f.get('id', '').lower() or 'administrator' in f.get('title', '').lower(),
                'wafr': ['SEC03'],
                'risk': 'HIGH',
                'finding_en': 'Users with AdministratorAccess policy detected. Full admin privileges on any account represent a significant blast radius if credentials are compromised.',
                'finding_tr': 'AdministratorAccess politikasina sahip kullanicilar tespit edilmistir. Herhangi bir hesapta tam yonetici yetkileri, kimlik bilgilerinin ele gecirilmesi durumunda genis bir etki alanina sahiptir.',
                'recommendation_en': 'Apply least privilege principle. Replace AdministratorAccess with scoped policies. Use IAM groups and roles instead of direct user policy attachments. Admin access should be granted only for break-glass scenarios.',
                'recommendation_tr': 'En az yetki prensibi uygulanmalidir. AdministratorAccess, kapsami daraltilmis politikalarla degistirilmelidir. Dogrudan kullanici politika atamalari yerine IAM gruplari ve roller kullanilmalidir. Yonetici erisimi yalnizca acil durum senaryolari icin verilmelidir.',
            },
            {
                'match': lambda f: 'identity_center' in f.get('id', '').lower() or 'sso' in f.get('title', '').lower() or 'identity center' in f.get('title', '').lower(),
                'wafr': ['SEC01', 'SEC02'],
                'risk': 'MEDIUM',
                'finding_en': 'AWS Identity Center (SSO) is not configured. Centralized identity management is not in use, relying on long-lived IAM credentials.',
                'finding_tr': 'AWS Identity Center (SSO) yapilandirilmamistir. Merkezi kimlik yonetimi kullanilmamakta, uzun omurlu IAM kimlik bilgilerine bagimlilik devam etmektedir.',
                'recommendation_en': 'Configure AWS Identity Center for centralized identity management. This provides single sign-on (SSO), token-based temporary credentials, and unified access control across all accounts.',
                'recommendation_tr': 'Merkezi kimlik yonetimi icin AWS Identity Center yapilandirilmalidir. Bu yapi tek noktadan erisim (SSO), token tabanli gecici kimlik bilgileri ve tum hesaplarda birlesik erisim kontrolu saglar.',
            },
            {
                'match': lambda f: 'organizations' in f.get('id', '').lower() or 'organization' in f.get('title', '').lower(),
                'wafr': ['SEC01', 'OPS01', 'COST02'],
                'risk': 'MEDIUM',
                'finding_en': 'AWS Organizations is not in use. Without multi-account strategy, environment isolation and centralized governance are not achievable.',
                'finding_tr': 'AWS Organizations kullanilmamaktadir. Coklu hesap stratejisi olmadan ortam izolasyonu ve merkezi yonetisim saglanamamaktadir.',
                'recommendation_en': 'Implement AWS Organizations with Service Control Policies (SCPs) for centralized governance. Separate dev, staging, and production into dedicated accounts for security boundary enforcement.',
                'recommendation_tr': 'Merkezi yonetisim icin Service Control Policies (SCP) ile AWS Organizations uygulanmalidir. Guvenlik siniri uygulamasi icin dev, staging ve production ayri hesaplara ayrilmalidir.',
            },
            {
                'match': lambda f: True,  # fallback for other IAM findings
                'wafr': ['SEC02', 'SEC03'],
                'risk': 'MEDIUM',
                'finding_en': None,  # use original finding text
                'finding_tr': None,
                'recommendation_en': 'Review IAM configuration against AWS security best practices. Ensure least privilege, MFA enforcement, and regular credential rotation.',
                'recommendation_tr': 'IAM yapilandirmasi AWS guvenlik en iyi uygulamalarina gore gozden gecirilmelidir. En az yetki, MFA zorunlulugu ve duzenli kimlik bilgisi rotasyonu saglanmalidir.',
            },
        ],
    },
    # ── S3 ──
    'S3': {
        'category_en': 'S3 Bucket Configuration',
        'category_tr': 'S3 Bucket Yapilandirmasi',
        'rules': [
            {
                'match': lambda f: 'versioning' in f.get('id', '').lower(),
                'wafr': ['REL09', 'SEC08'],
                'risk': 'HIGH',
                'finding_en': 'S3 bucket versioning is disabled. Accidental deletions or overwrites cannot be recovered without versioning enabled.',
                'finding_tr': 'S3 bucket versiyonlama devre disidir. Versiyonlama etkinlestirilmeden kazara silme veya uzerine yazma islemlerinden kurtarma mumkun degildir.',
                'recommendation_en': 'Enable versioning on all critical buckets. Implement lifecycle rules to manage version costs (e.g., move old versions to S3 Standard-IA after 30 days, Glacier after 90 days).',
                'recommendation_tr': 'Tum kritik bucket\'larda versiyonlama etkinlestirilmelidir. Versiyon maliyetlerini yonetmek icin yasam dongusu kurallari uygulanmalidir (ornegin: eski versiyonlari 30 gun sonra S3 Standard-IA\'ya, 90 gun sonra Glacier\'a tasima).',
            },
            {
                'match': lambda f: 'encryption' in f.get('id', '').lower() or 'encrypt' in f.get('title', '').lower(),
                'wafr': ['SEC08'],
                'risk': 'HIGH',
                'finding_en': 'S3 bucket server-side encryption is not properly configured. Data at rest may not be adequately protected.',
                'finding_tr': 'S3 bucket sunucu tarafli sifreleme uygun sekilde yapilandirilmamistir. Duran veriler yeterince korunmuyor olabilir.',
                'recommendation_en': 'Enable SSE-S3 or SSE-KMS encryption on all buckets. For sensitive data, use SSE-KMS with customer-managed keys (CMK) for granular access control.',
                'recommendation_tr': 'Tum bucket\'larda SSE-S3 veya SSE-KMS sifreleme etkinlestirilmelidir. Hassas veriler icin, ayrintili erisim kontrolu saglayan musteri tarafindan yonetilen anahtarlarla (CMK) SSE-KMS kullanilmalidir.',
            },
            {
                'match': lambda f: 'public' in f.get('id', '').lower() or 'public access' in f.get('title', '').lower(),
                'wafr': ['SEC05', 'SEC08'],
                'risk': 'HIGH',
                'finding_en': 'S3 bucket public access block is not fully configured. Public buckets can lead to data exposure and compliance violations.',
                'finding_tr': 'S3 bucket genel erisim engeli tam olarak yapilandirilmamistir. Genel erisime acik bucket\'lar veri ifsa ve uyumluluk ihlallerine yol acabilir.',
                'recommendation_en': 'Enable Block Public Access at both account and bucket level. Review bucket policies and ACLs to ensure no unintended public access.',
                'recommendation_tr': 'Hem hesap hem de bucket duzeyinde Block Public Access etkinlestirilmelidir. Istenmeyen genel erisim olmadigindan emin olmak icin bucket politikalari ve ACL\'ler gozden gecirilmelidir.',
            },
            {
                'match': lambda f: 'logging' in f.get('id', '').lower() or 'access log' in f.get('title', '').lower(),
                'wafr': ['SEC04', 'OPS04'],
                'risk': 'MEDIUM',
                'finding_en': 'S3 access logging is not enabled. Without logging, it is not possible to audit who accessed what data and when.',
                'finding_tr': 'S3 erisim gunlugu etkinlestirilmemistir. Gunluk olmadan kimin hangi veriye ne zaman eristigini denetlemek mumkun degildir.',
                'recommendation_en': 'Enable S3 access logging for all buckets containing sensitive or business-critical data. Store logs in a dedicated logging bucket with appropriate retention policies.',
                'recommendation_tr': 'Hassas veya is acidan kritik veri iceren tum bucket\'lar icin S3 erisim gunlugu etkinlestirilmelidir. Gunlukler uygun saklama politikalariyla ozel bir gunluk bucket\'inda saklanmalidir.',
            },
            {
                'match': lambda f: 'lifecycle' in f.get('id', '').lower(),
                'wafr': ['COST03', 'COST04'],
                'risk': 'MEDIUM',
                'finding_en': 'S3 lifecycle policies are not configured. Without lifecycle management, storage costs can grow uncontrolled.',
                'finding_tr': 'S3 yasam dongusu politikalari yapilandirilmamistir. Yasam dongusu yonetimi olmadan depolama maliyetleri kontrolsuz buyuyebilir.',
                'recommendation_en': 'Implement S3 Intelligent-Tiering or lifecycle rules based on access frequency. Move infrequently accessed data to Standard-IA (30 days), Glacier (90 days), or Deep Archive (180 days).',
                'recommendation_tr': 'Erisim sikligina dayali S3 Intelligent-Tiering veya yasam dongusu kurallari uygulanmalidir. Seyrek erisilen veriler Standard-IA\'ya (30 gun), Glacier\'a (90 gun) veya Deep Archive\'a (180 gun) tasinmalidir.',
            },
            {
                'match': lambda f: 'mfa_delete' in f.get('id', '').lower(),
                'wafr': ['SEC02', 'SEC08'],
                'risk': 'MEDIUM',
                'finding_en': 'MFA Delete is not enabled on S3 buckets. Without MFA Delete, permanent deletion of objects can occur without additional verification.',
                'finding_tr': 'S3 bucket\'larinda MFA Delete etkinlestirilmemistir. MFA Delete olmadan, nesnelerin kalici silinmesi ek dogrulama olmadan gerceklesebilir.',
                'recommendation_en': 'Enable MFA Delete on production buckets containing critical data. This adds an extra layer of protection against accidental or malicious permanent deletions.',
                'recommendation_tr': 'Kritik veri iceren production bucket\'larinda MFA Delete etkinlestirilmelidir. Bu, kazara veya kasitli kalici silmelere karsi ek bir koruma katmani ekler.',
            },
            {
                'match': lambda f: True,
                'wafr': ['SEC08', 'COST03'],
                'risk': 'MEDIUM',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review S3 bucket configuration against AWS security and cost optimization best practices.',
                'recommendation_tr': 'S3 bucket yapilandirmasi AWS guvenlik ve maliyet optimizasyonu en iyi uygulamalarina gore gozden gecirilmelidir.',
            },
        ],
    },
    # ── EC2 ──
    'EC2': {
        'category_en': 'EC2 Usage & Security',
        'category_tr': 'EC2 Kullanimi ve Guvenligi',
        'rules': [
            {
                'match': lambda f: 'security_group' in f.get('id', '').lower() or 'security group' in f.get('title', '').lower(),
                'wafr': ['SEC05', 'SEC02'],
                'risk': 'HIGH',
                'finding_en': 'Security groups with overly permissive rules detected. Open ports (e.g., 0.0.0.0/0 on SSH port 22) expose instances to unauthorized access.',
                'finding_tr': 'Asiri izin verici kurallara sahip guvenlik gruplari tespit edilmistir. Acik portlar (ornegin SSH port 22\'de 0.0.0.0/0) instance\'lari yetkisiz erisime maruz birakmaktadir.',
                'recommendation_en': 'Restrict security group rules to specific IP ranges (e.g., corporate VPN CIDR). Replace SSH access with AWS Systems Manager Session Manager. Remove default "launch-wizard-*" security groups.',
                'recommendation_tr': 'Guvenlik grubu kurallari belirli IP araliklariyla sinirlandirilmalidir (ornegin sirket VPN CIDR). SSH erisimi AWS Systems Manager Session Manager ile degistirilmelidir. Varsayilan "launch-wizard-*" guvenlik gruplari kaldirilmalidir.',
            },
            {
                'match': lambda f: 'public_ip' in f.get('id', '').lower() or 'public ip' in f.get('title', '').lower() or 'public subnet' in f.get('title', '').lower(),
                'wafr': ['SEC05', 'REL02'],
                'risk': 'HIGH',
                'finding_en': 'EC2 instances are placed in public subnets with public IP addresses. This exposes compute resources directly to the internet.',
                'finding_tr': 'EC2 instance\'lari public subnet\'lerde konumlandirilmis ve public IP adresleri atanmistir. Bu durum islem kaynaklarini dogrudan internete maruz birakmaktadir.',
                'recommendation_en': 'Move EC2 instances to private subnets. Use ALB or bastion host for external access. If public IP is needed, use Elastic IP for stable addressing.',
                'recommendation_tr': 'EC2 instance\'lari private subnet\'lere tasinmalidir. Dis erisim icin ALB veya bastion host kullanilmalidir. Public IP gerekiyorsa, sabit adresleme icin Elastic IP kullanilmalidir.',
            },
            {
                'match': lambda f: 'ebs' in f.get('id', '').lower() or 'volume' in f.get('title', '').lower() or 'snapshot' in f.get('title', '').lower(),
                'wafr': ['REL09', 'COST03'],
                'risk': 'MEDIUM',
                'finding_en': 'EBS volumes or snapshots require attention. Missing backup strategy or unused volumes increase both risk and cost.',
                'finding_tr': 'EBS volume\'lari veya snapshot\'lar dikkat gerektirmektedir. Eksik yedekleme stratejisi veya kullanilmayan volume\'lar hem riski hem de maliyeti artirmaktadir.',
                'recommendation_en': 'Implement AWS Backup for EBS snapshot management. Remove unused volumes and outdated snapshots. Consider volume type optimization (gp3 over gp2).',
                'recommendation_tr': 'EBS snapshot yonetimi icin AWS Backup uygulanmalidir. Kullanilmayan volume\'lar ve guncel olmayan snapshot\'lar kaldirilmalidir. Volume turu optimizasyonu (gp2 yerine gp3) degerlendirilmelidir.',
            },
            {
                'match': lambda f: 'imdsv2' in f.get('id', '').lower() or 'metadata' in f.get('title', '').lower(),
                'wafr': ['SEC06'],
                'risk': 'HIGH',
                'finding_en': 'EC2 instances are not enforcing IMDSv2. IMDSv1 is vulnerable to SSRF attacks that can expose instance credentials.',
                'finding_tr': 'EC2 instance\'lari IMDSv2 zorunlu kilmamaktadir. IMDSv1, instance kimlik bilgilerini ifsa edebilen SSRF saldirilarina karsı savunmasizdir.',
                'recommendation_en': 'Enforce IMDSv2 on all EC2 instances by setting HttpTokens to "required". This prevents SSRF-based credential theft from the instance metadata service.',
                'recommendation_tr': 'HttpTokens ayarini "required" olarak yaparak tum EC2 instance\'larinda IMDSv2 zorunlu kilinmalidir. Bu, instance metadata hizmetinden SSRF tabanli kimlik bilgisi hirsizligini onler.',
            },
            {
                'match': lambda f: True,
                'wafr': ['SEC05', 'SEC06'],
                'risk': 'MEDIUM',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review EC2 security configuration. Ensure instances use private subnets, restrictive security groups, IMDSv2, and regular patching.',
                'recommendation_tr': 'EC2 guvenlik yapilandirmasi gozden gecirilmelidir. Instance\'larin private subnet, kisitlayici guvenlik gruplari, IMDSv2 ve duzenli yama kullandiginden emin olunmalidir.',
            },
        ],
    },
    # ── VPC ──
    'VPC': {
        'category_en': 'VPC & Network Architecture',
        'category_tr': 'VPC ve Ag Mimarisi',
        'rules': [
            {
                'match': lambda f: 'default_vpc' in f.get('id', '').lower() or 'default vpc' in f.get('title', '').lower(),
                'wafr': ['SEC05', 'REL02'],
                'risk': 'MEDIUM',
                'finding_en': 'Default VPC is still in use. Default VPCs are not designed for production workloads and lack proper network segmentation.',
                'finding_tr': 'Varsayilan VPC hala kullanilmaktadir. Varsayilan VPC\'ler production is yukleri icin tasarlanmamistir ve uygun ag segmentasyonundan yoksundur.',
                'recommendation_en': 'Create custom VPCs with proper three-tier architecture: public subnets (ALB, NAT GW), private subnets (compute, app), data subnets (RDS, ElastiCache). Plan for minimum 3 AZs.',
                'recommendation_tr': 'Uygun uc katmanli mimari ile ozel VPC\'ler olusturulmalidir: public subnet\'ler (ALB, NAT GW), private subnet\'ler (islem, uygulama), veri subnet\'leri (RDS, ElastiCache). Minimum 3 AZ icin planlanmalidir.',
            },
            {
                'match': lambda f: 'flow_log' in f.get('id', '').lower() or 'flow log' in f.get('title', '').lower(),
                'wafr': ['SEC04', 'OPS04'],
                'risk': 'MEDIUM',
                'finding_en': 'VPC Flow Logs are not enabled. Without flow logs, network traffic cannot be monitored or analyzed for security events.',
                'finding_tr': 'VPC Flow Log\'lari etkinlestirilmemistir. Flow log\'lar olmadan ag trafigi guvenlik olaylari icin izlenememekte veya analiz edilememektedir.',
                'recommendation_en': 'Enable VPC Flow Logs on all VPCs. Send logs to CloudWatch Logs or S3 for analysis. Set appropriate retention policies.',
                'recommendation_tr': 'Tum VPC\'lerde VPC Flow Log\'lari etkinlestirilmelidir. Analiz icin gunlukler CloudWatch Logs veya S3\'e gonderilmelidir. Uygun saklama politikalari belirlenmelidir.',
            },
            {
                'match': lambda f: 'nacl' in f.get('id', '').lower() or 'network acl' in f.get('title', '').lower(),
                'wafr': ['SEC05'],
                'risk': 'MEDIUM',
                'finding_en': 'Network ACLs are using default allow-all rules. Without proper NACL rules, subnet-level traffic filtering is not enforced.',
                'finding_tr': 'Network ACL\'ler varsayilan tumu-izin-ver kurallarini kullanmaktadir. Uygun NACL kurallari olmadan subnet duzeyinde trafik filtreleme uygulanmamaktadir.',
                'recommendation_en': 'Configure custom Network ACLs with explicit allow/deny rules for each subnet tier. Use NACLs as an additional layer of defense alongside security groups.',
                'recommendation_tr': 'Her subnet katmani icin acik izin ver/reddet kurallariyla ozel Network ACL\'ler yapilandirilmalidir. NACL\'ler guvenlik gruplariyla birlikte ek bir savunma katmani olarak kullanilmalidir.',
            },
            {
                'match': lambda f: True,
                'wafr': ['SEC05', 'REL02'],
                'risk': 'MEDIUM',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review VPC architecture for proper network segmentation, security group rules, and multi-AZ deployment.',
                'recommendation_tr': 'VPC mimarisi uygun ag segmentasyonu, guvenlik grubu kurallari ve coklu AZ dagitimi icin gozden gecirilmelidir.',
            },
        ],
    },
    # ── RDS ──
    'RDS': {
        'category_en': 'Database Configuration',
        'category_tr': 'Veritabani Yapilandirmasi',
        'rules': [
            {
                'match': lambda f: 'public' in f.get('id', '').lower() and 'access' in f.get('id', '').lower(),
                'wafr': ['SEC05', 'SEC08'],
                'risk': 'HIGH',
                'finding_en': 'RDS instance is configured as publicly accessible. This exposes the database directly to the internet, creating a critical security risk.',
                'finding_tr': 'RDS instance\'i genel erisime acik olarak yapilandirilmistir. Bu durum veritabanini dogrudan internete maruz birakmakta ve kritik bir guvenlik riski olusturmaktadir.',
                'recommendation_en': 'Disable public accessibility on RDS instances. Access should only be from private subnets. If remote management is needed, use AWS Client VPN or Session Manager.',
                'recommendation_tr': 'RDS instance\'larinda genel erisim devre disi birakilmalidir. Erisim yalnizca private subnet\'lerden saglanmalidir. Uzaktan yonetim gerekiyorsa AWS Client VPN veya Session Manager kullanilmalidir.',
            },
            {
                'match': lambda f: 'multi_az' in f.get('id', '').lower() or 'multi-az' in f.get('title', '').lower(),
                'wafr': ['REL10', 'REL11'],
                'risk': 'HIGH',
                'finding_en': 'RDS Multi-AZ deployment is not active. In case of an AZ-level failure, the database service will be completely unavailable.',
                'finding_tr': 'RDS Multi-AZ dagitimi aktif degildir. AZ duzeyinde bir ariza durumunda veritabani servisi tamamen kullanilmaz hale gelecektir.',
                'recommendation_en': 'Enable Multi-AZ deployment for all production databases. This provides automatic failover to a standby replica in a different AZ.',
                'recommendation_tr': 'Tum production veritabanlari icin Multi-AZ dagitimi etkinlestirilmelidir. Bu, farkli bir AZ\'deki yedek kopya otomatik yuk devretme saglar.',
            },
            {
                'match': lambda f: 'backup' in f.get('id', '').lower() or 'retention' in f.get('title', '').lower(),
                'wafr': ['REL09', 'OPS08'],
                'risk': 'MEDIUM',
                'finding_en': 'RDS automated backup retention period is below recommended levels. Short retention limits recovery options.',
                'finding_tr': 'RDS otomatik yedekleme saklama suresi onerilen seviyelerin altindadir. Kisa saklama suresi kurtarma seceneklerini sinirlamaktadir.',
                'recommendation_en': 'Set backup retention period to minimum 7 days for non-production, 14-35 days for production databases. Enable cross-region backup copy for disaster recovery.',
                'recommendation_tr': 'Yedekleme saklama suresi non-production icin minimum 7 gun, production veritabanlari icin 14-35 gun olarak ayarlanmalidir. Felaket kurtarma icin bolge arasi yedek kopyalama etkinlestirilmelidir.',
            },
            {
                'match': lambda f: 'encryption' in f.get('id', '').lower(),
                'wafr': ['SEC08'],
                'risk': 'HIGH',
                'finding_en': 'RDS instance encryption at rest is not enabled. Sensitive data stored in the database is not protected against physical media compromise.',
                'finding_tr': 'RDS instance duran veri sifreleme etkinlestirilmemistir. Veritabaninda depolanan hassas veriler fiziksel medya ihlallerine karsi korunmamaktadir.',
                'recommendation_en': 'Enable encryption at rest for all RDS instances using KMS. Note: existing unencrypted instances must be migrated via snapshot-restore.',
                'recommendation_tr': 'KMS kullanarak tum RDS instance\'lari icin duran veri sifreleme etkinlestirilmelidir. Not: Mevcut sifrelenmemis instance\'lar snapshot-restore yoluyla tasinmalidir.',
            },
            {
                'match': lambda f: True,
                'wafr': ['REL09', 'SEC08'],
                'risk': 'MEDIUM',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review RDS configuration for encryption, Multi-AZ, backup retention, and network isolation.',
                'recommendation_tr': 'RDS yapilandirmasi sifreleme, Multi-AZ, yedekleme saklama ve ag izolasyonu icin gozden gecirilmelidir.',
            },
        ],
    },
    # ── CloudTrail ──
    'CloudTrail': {
        'category_en': 'Audit & Logging',
        'category_tr': 'Denetim ve Gunlukleme',
        'rules': [
            {
                'match': lambda f: 'multi_region' in f.get('id', '').lower() or 'multi-region' in f.get('title', '').lower(),
                'wafr': ['SEC04', 'OPS04'],
                'risk': 'HIGH',
                'finding_en': 'CloudTrail multi-region trail is not enabled. API activity in non-primary regions is not being recorded.',
                'finding_tr': 'CloudTrail cok bolge izi etkinlestirilmemistir. Birincil olmayan bolgelerdeki API aktivitesi kaydedilmemektedir.',
                'recommendation_en': 'Enable a multi-region CloudTrail trail with log file validation. Store logs in a dedicated S3 bucket with versioning and MFA Delete.',
                'recommendation_tr': 'Gunluk dosyasi dogrulama ile cok bolge CloudTrail izi etkinlestirilmelidir. Gunlukler versiyonlama ve MFA Delete ile ozel bir S3 bucket\'inda saklanmalidir.',
            },
            {
                'match': lambda f: True,
                'wafr': ['SEC04'],
                'risk': 'MEDIUM',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Ensure CloudTrail is properly configured with multi-region coverage, log encryption, and integration with CloudWatch for real-time alerting.',
                'recommendation_tr': 'CloudTrail\'in cok bolge kapsami, gunluk sifreleme ve gercek zamanli uyari icin CloudWatch entegrasyonu ile uygun sekilde yapilandirildigindan emin olunmalidir.',
            },
        ],
    },
    # ── GuardDuty ──
    'GuardDuty': {
        'category_en': 'Threat Detection',
        'category_tr': 'Tehdit Tespiti',
        'rules': [
            {
                'match': lambda f: f.get('status') == 'FAIL',
                'wafr': ['SEC04', 'SEC10'],
                'risk': 'HIGH',
                'finding_en': 'Amazon GuardDuty is not enabled. Without continuous threat detection, malicious activity may go undetected.',
                'finding_tr': 'Amazon GuardDuty etkinlestirilmemistir. Surekli tehdit tespiti olmadan, kotu niyetli aktiviteler tespit edilemeyebilir.',
                'recommendation_en': 'Enable GuardDuty in all regions. Configure findings export to S3 and integrate with Security Hub for centralized security monitoring.',
                'recommendation_tr': 'Tum bolgelerde GuardDuty etkinlestirilmelidir. Bulgularin S3\'e aktarimi yapilandirilmali ve merkezi guvenlik izleme icin Security Hub ile entegre edilmelidir.',
            },
            {
                'match': lambda f: True,
                'wafr': ['SEC04'],
                'risk': 'MEDIUM',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Ensure GuardDuty is enabled and configured with all protection plans (S3, EKS, Lambda, RDS).',
                'recommendation_tr': 'GuardDuty\'nin tum koruma planlari (S3, EKS, Lambda, RDS) ile etkinlestirildiginden ve yapilandirildigindan emin olunmalidir.',
            },
        ],
    },
    # ── KMS ──
    'KMS': {
        'category_en': 'Encryption Key Management',
        'category_tr': 'Sifreleme Anahtar Yonetimi',
        'rules': [
            {
                'match': lambda f: 'rotation' in f.get('id', '').lower(),
                'wafr': ['SEC08'],
                'risk': 'MEDIUM',
                'finding_en': 'KMS key automatic rotation is not enabled. Without rotation, long-lived encryption keys increase the risk of cryptographic compromise.',
                'finding_tr': 'KMS anahtari otomatik rotasyonu etkinlestirilmemistir. Rotasyon olmadan uzun omurlu sifreleme anahtarlari kriptografik ihlal riskini artirmaktadir.',
                'recommendation_en': 'Enable automatic key rotation for all customer-managed KMS keys. AWS rotates keys annually while maintaining backward compatibility.',
                'recommendation_tr': 'Tum musteri tarafindan yonetilen KMS anahtarlari icin otomatik anahtar rotasyonu etkinlestirilmelidir. AWS, geriye donuk uyumlulugu koruyarak anahtarlari yillik olarak rotate eder.',
            },
            {
                'match': lambda f: True,
                'wafr': ['SEC08'],
                'risk': 'MEDIUM',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review KMS key policies, rotation settings, and usage patterns.',
                'recommendation_tr': 'KMS anahtar politikalari, rotasyon ayarlari ve kullanim desenleri gozden gecirilmelidir.',
            },
        ],
    },
    # ── Lambda ──
    'Lambda': {
        'category_en': 'Serverless Configuration',
        'category_tr': 'Sunucusuz Yapilandirma',
        'rules': [
            {
                'match': lambda f: 'runtime' in f.get('id', '').lower() or 'deprecated' in f.get('title', '').lower(),
                'wafr': ['SEC06', 'SEC11'],
                'risk': 'HIGH',
                'finding_en': 'Lambda functions using deprecated runtimes detected. Deprecated runtimes no longer receive security patches.',
                'finding_tr': 'Kullanimdan kaldirilan calisma zamanlarini kullanan Lambda fonksiyonlari tespit edilmistir. Kullanimdan kaldirilan calisma zamanlari artik guvenlik yamalari almamaktadir.',
                'recommendation_en': 'Upgrade Lambda functions to supported runtimes. Implement a runtime update strategy as part of regular maintenance.',
                'recommendation_tr': 'Lambda fonksiyonlari desteklenen calisma zamanlarina yukseltilmelidir. Duzenli bakimin bir parcasi olarak calisma zamani guncelleme stratejisi uygulanmalidir.',
            },
            {
                'match': lambda f: True,
                'wafr': ['SEC06', 'COST05'],
                'risk': 'MEDIUM',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review Lambda function configurations: memory allocation, timeout settings, VPC placement, and IAM role permissions.',
                'recommendation_tr': 'Lambda fonksiyon yapilandirmalari gozden gecirilmelidir: bellek tahsisi, zaman asimi ayarlari, VPC yerlesimi ve IAM rol izinleri.',
            },
        ],
    },
    # ── Config ──
    'Config': {
        'category_en': 'Configuration Compliance',
        'category_tr': 'Yapilandirma Uyumlulugu',
        'rules': [
            {
                'match': lambda f: f.get('status') == 'FAIL',
                'wafr': ['OPS04', 'SEC04'],
                'risk': 'MEDIUM',
                'finding_en': 'AWS Config is not enabled. Without Config, resource configuration changes are not tracked and compliance cannot be enforced automatically.',
                'finding_tr': 'AWS Config etkinlestirilmemistir. Config olmadan kaynak yapilandirma degisiklikleri izlenememekte ve uyumluluk otomatik olarak uygulanamamaktadir.',
                'recommendation_en': 'Enable AWS Config in all regions with configuration recording. Deploy managed Config Rules for automated compliance checking.',
                'recommendation_tr': 'Tum bolgelerde yapilandirma kaydi ile AWS Config etkinlestirilmelidir. Otomatik uyumluluk kontrolu icin yonetilen Config Kurallari dagitilmalidir.',
            },
            {
                'match': lambda f: True,
                'wafr': ['OPS04'],
                'risk': 'LOW',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review AWS Config rules and ensure all critical resource types are being recorded.',
                'recommendation_tr': 'AWS Config kurallari gozden gecirilmeli ve tum kritik kaynak turlerinin kaydedildiginden emin olunmalidir.',
            },
        ],
    },
    # ── EKS ──
    'EKS': {
        'category_en': 'EKS Cluster Management',
        'category_tr': 'EKS Cluster Yonetimi',
        'rules': [
            {
                'match': lambda f: 'public' in f.get('id', '').lower() or 'endpoint' in f.get('title', '').lower(),
                'wafr': ['SEC04', 'SEC05'],
                'risk': 'HIGH',
                'finding_en': 'EKS cluster API server endpoint is publicly accessible. This creates an unnecessary attack surface for the Kubernetes control plane.',
                'finding_tr': 'EKS cluster API sunucu ucnoktasi genel erisime aciktir. Bu, Kubernetes kontrol duzlemi icin gereksiz bir saldiri yuzeyi olusturmaktadir.',
                'recommendation_en': 'Set EKS API server to private endpoint access only. If public access is needed temporarily, restrict source IP allowlist to corporate VPN CIDR.',
                'recommendation_tr': 'EKS API sunucusu yalnizca ozel ucnokta erisimi olarak ayarlanmalidir. Gecici olarak genel erisim gerekiyorsa, kaynak IP izin listesi sirket VPN CIDR\'iyla sinirlandirilmalidir.',
            },
            {
                'match': lambda f: 'logging' in f.get('id', '').lower() or 'control plane' in f.get('title', '').lower(),
                'wafr': ['SEC04', 'OPS04'],
                'risk': 'MEDIUM',
                'finding_en': 'EKS control plane logging is not fully enabled. Without comprehensive logging, cluster operations cannot be properly audited.',
                'finding_tr': 'EKS kontrol duzlemi gunlukleri tam olarak etkinlestirilmemistir. Kapsamli gunlukleme olmadan cluster operasyonlari duzgun sekilde denetlenememektedir.',
                'recommendation_en': 'Enable all EKS control plane log types (api, audit, authenticator, controllerManager, scheduler). Send to CloudWatch Logs with appropriate retention.',
                'recommendation_tr': 'Tum EKS kontrol duzlemi gunluk turleri etkinlestirilmelidir (api, audit, authenticator, controllerManager, scheduler). Uygun saklama suresiyle CloudWatch Logs\'a gonderilmelidir.',
            },
            {
                'match': lambda f: True,
                'wafr': ['SEC05', 'COST06'],
                'risk': 'MEDIUM',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review EKS cluster configuration: private endpoint, logging, node group sizing, and Karpenter for autoscaling.',
                'recommendation_tr': 'EKS cluster yapilandirmasi gozden gecirilmelidir: ozel ucnokta, gunlukleme, node grubu boyutlandirma ve otomatik olceklendirme icin Karpenter.',
            },
        ],
    },
    # ── ELB ──
    'ELB': {
        'category_en': 'Load Balancing & Traffic Management',
        'category_tr': 'Yuk Dengeleme ve Trafik Yonetimi',
        'rules': [
            {
                'match': lambda f: 'ssl' in f.get('id', '').lower() or 'tls' in f.get('title', '').lower() or 'https' in f.get('title', '').lower(),
                'wafr': ['SEC09'],
                'risk': 'HIGH',
                'finding_en': 'Load balancer is not properly configured for TLS/SSL. Data in transit may not be encrypted.',
                'finding_tr': 'Yuk dengeleyici TLS/SSL icin uygun sekilde yapilandirilmamistir. Aktarim halindeki veriler sifrelenmemis olabilir.',
                'recommendation_en': 'Configure HTTPS listeners with TLS 1.2+ policy. Use ACM certificates for automatic renewal. Redirect HTTP to HTTPS.',
                'recommendation_tr': 'TLS 1.2+ politikasi ile HTTPS dinleyiciler yapilandirilmalidir. Otomatik yenileme icin ACM sertifikalari kullanilmalidir. HTTP, HTTPS\'e yonlendirilmelidir.',
            },
            {
                'match': lambda f: True,
                'wafr': ['SEC09', 'REL07'],
                'risk': 'MEDIUM',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review load balancer configuration for TLS settings, access logging, WAF integration, and health check configuration.',
                'recommendation_tr': 'Yuk dengeleyici yapilandirmasi TLS ayarlari, erisim gunlukleri, WAF entegrasyonu ve saglik kontrolu yapilandirmasi icin gozden gecirilmelidir.',
            },
        ],
    },
    # ── CloudWatch ──
    'CloudWatch': {
        'category_en': 'Monitoring & Observability',
        'category_tr': 'Izleme ve Gozlemlenebilirlik',
        'rules': [
            {
                'match': lambda f: 'alarm' in f.get('id', '').lower() or 'alarm' in f.get('title', '').lower(),
                'wafr': ['OPS08', 'REL06'],
                'risk': 'MEDIUM',
                'finding_en': 'Critical CloudWatch alarms are not configured. Without alarms, operational issues may not be detected in time.',
                'finding_tr': 'Kritik CloudWatch alarmlari yapilandirilmamistir. Alarmlar olmadan operasyonel sorunlar zamaninda tespit edilemeyebilir.',
                'recommendation_en': 'Configure CloudWatch alarms for critical metrics: CPU utilization, memory, disk space, error rates. Set up SNS notifications for alert escalation.',
                'recommendation_tr': 'Kritik metrikler icin CloudWatch alarmlari yapilandirilmalidir: CPU kullanimi, bellek, disk alani, hata oranlari. Alarm eskalasyonu icin SNS bildirimleri ayarlanmalidir.',
            },
            {
                'match': lambda f: 'retention' in f.get('id', '').lower() or 'log group' in f.get('title', '').lower(),
                'wafr': ['COST03', 'OPS04'],
                'risk': 'LOW',
                'finding_en': 'CloudWatch Log Groups with indefinite retention detected. Never-expire retention policy increases storage costs unnecessarily.',
                'finding_tr': 'Suresiz saklamaya sahip CloudWatch Log Gruplari tespit edilmistir. Suresi dolmayan saklama politikasi depolama maliyetlerini gereksiz yere artirmaktadir.',
                'recommendation_en': 'Set appropriate retention periods for log groups. Use Logs Insights for active analysis and move old logs to S3/Glacier for long-term archive.',
                'recommendation_tr': 'Log gruplari icin uygun saklama sureleri belirlenmelidir. Aktif analiz icin Logs Insights kullanilmali ve eski gunlukler uzun vadeli arsivleme icin S3/Glacier\'a tasinmalidir.',
            },
            {
                'match': lambda f: True,
                'wafr': ['OPS04', 'OPS08'],
                'risk': 'LOW',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review CloudWatch monitoring coverage and ensure all critical services have appropriate alarms and dashboards.',
                'recommendation_tr': 'CloudWatch izleme kapsami gozden gecirilmeli ve tum kritik servislerin uygun alarm ve panolara sahip oldugundan emin olunmalidir.',
            },
        ],
    },
    # ── CloudFront ──
    'CloudFront': {
        'category_en': 'Content Delivery & Edge Security',
        'category_tr': 'Icerik Dagitimi ve Uc Guvenligi',
        'rules': [
            {
                'match': lambda f: True,
                'wafr': ['SEC09', 'PERF04'],
                'risk': 'MEDIUM',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review CloudFront distributions for HTTPS enforcement, WAF integration, geo-restriction, and Origin Access Control (OAC).',
                'recommendation_tr': 'CloudFront dagitimlarini HTTPS zorunlulugu, WAF entegrasyonu, cografi kisitlama ve Origin Access Control (OAC) icin gozden gecirin.',
            },
        ],
    },
    # ── WAF ──
    'WAF': {
        'category_en': 'Web Application Firewall',
        'category_tr': 'Web Uygulama Guvenligi',
        'rules': [
            {
                'match': lambda f: f.get('status') == 'FAIL',
                'wafr': ['SEC05', 'SEC06'],
                'risk': 'HIGH',
                'finding_en': 'AWS WAF is not properly configured. Without WAF, web applications are exposed to common attacks (SQLi, XSS, DDoS).',
                'finding_tr': 'AWS WAF uygun sekilde yapilandirilmamistir. WAF olmadan web uygulamalari yaygin saldirilara (SQLi, XSS, DDoS) maruz kalmaktadir.',
                'recommendation_en': 'Deploy AWS WAF with managed rule groups (AWSManagedRulesCommonRuleSet, SQLiRuleSet, XSSRuleSet). Associate with ALB and CloudFront distributions.',
                'recommendation_tr': 'Yonetilen kural gruplariyla (AWSManagedRulesCommonRuleSet, SQLiRuleSet, XSSRuleSet) AWS WAF dagitilmalidir. ALB ve CloudFront dagitimlariyla iliskilendirilmelidir.',
            },
            {
                'match': lambda f: True,
                'wafr': ['SEC05'],
                'risk': 'MEDIUM',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review WAF rules and ensure comprehensive protection against OWASP Top 10 threats.',
                'recommendation_tr': 'WAF kurallari gozden gecirilmeli ve OWASP Top 10 tehditlere karsi kapsamli koruma saglanmalidir.',
            },
        ],
    },
    # ── Route53 ──
    'Route53': {
        'category_en': 'DNS Management',
        'category_tr': 'DNS Yonetimi',
        'rules': [
            {
                'match': lambda f: True,
                'wafr': ['REL02', 'SEC05'],
                'risk': 'LOW',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review Route53 configuration: use ALIAS records over A records for AWS resources, enable DNSSEC where applicable, and implement health checks.',
                'recommendation_tr': 'Route53 yapilandirmasi gozden gecirilmelidir: AWS kaynaklari icin A kayitlari yerine ALIAS kayitlari kullanilmali, uygulanabilir yerlerde DNSSEC etkinlestirilmeli ve saglik kontrolleri uygulanmalidir.',
            },
        ],
    },
    # ── ACM ──
    'ACM': {
        'category_en': 'Certificate Management',
        'category_tr': 'Sertifika Yonetimi',
        'rules': [
            {
                'match': lambda f: 'expir' in f.get('id', '').lower() or 'expir' in f.get('title', '').lower(),
                'wafr': ['SEC09'],
                'risk': 'HIGH',
                'finding_en': 'SSL/TLS certificates approaching expiration detected. Expired certificates cause service disruptions and security warnings.',
                'finding_tr': 'Suresi dolmak uzere olan SSL/TLS sertifikalari tespit edilmistir. Suresi dolan sertifikalar servis kesintilerine ve guvenlik uyarilarina neden olur.',
                'recommendation_en': 'Use ACM-managed certificates for automatic renewal. Set up CloudWatch alarms for certificate expiration monitoring.',
                'recommendation_tr': 'Otomatik yenileme icin ACM tarafindan yonetilen sertifikalar kullanilmalidir. Sertifika suresi dolumu izleme icin CloudWatch alarmlari ayarlanmalidir.',
            },
            {
                'match': lambda f: True,
                'wafr': ['SEC09'],
                'risk': 'LOW',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Ensure all public-facing services use ACM-managed certificates with automatic renewal.',
                'recommendation_tr': 'Genel erisime acik tum servislerin otomatik yenileme ile ACM tarafindan yonetilen sertifikalar kullandigindan emin olunmalidir.',
            },
        ],
    },
    # ── SecretsManager ──
    'SecretsManager': {
        'category_en': 'Secrets Management',
        'category_tr': 'Gizli Bilgi Yonetimi',
        'rules': [
            {
                'match': lambda f: 'rotation' in f.get('id', '').lower(),
                'wafr': ['SEC02', 'SEC08'],
                'risk': 'MEDIUM',
                'finding_en': 'Secrets without automatic rotation detected. Static secrets increase the risk of credential compromise.',
                'finding_tr': 'Otomatik rotasyonsuz gizli bilgiler tespit edilmistir. Statik gizli bilgiler kimlik bilgisi ihlali riskini artirmaktadir.',
                'recommendation_en': 'Enable automatic rotation for all secrets, especially database credentials. Use Lambda rotation functions for custom secrets.',
                'recommendation_tr': 'Tum gizli bilgiler icin, ozellikle veritabani kimlik bilgileri icin otomatik rotasyon etkinlestirilmelidir. Ozel gizli bilgiler icin Lambda rotasyon fonksiyonlari kullanilmalidir.',
            },
            {
                'match': lambda f: True,
                'wafr': ['SEC08'],
                'risk': 'LOW',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review secrets management practices. Ensure rotation policies are in place and access is logged.',
                'recommendation_tr': 'Gizli bilgi yonetimi uygulamalari gozden gecirilmelidir. Rotasyon politikalarinin mevcut ve erisimlerin kayit altinda oldugundan emin olunmalidir.',
            },
        ],
    },
    # ── ECR ──
    'ECR': {
        'category_en': 'Container Registry',
        'category_tr': 'Container Kayit Defteri',
        'rules': [
            {
                'match': lambda f: 'scan' in f.get('id', '').lower() or 'vulnerability' in f.get('title', '').lower(),
                'wafr': ['SEC06', 'SEC11'],
                'risk': 'HIGH',
                'finding_en': 'ECR image scanning is not enabled. Container images may contain known vulnerabilities that could be exploited in production.',
                'finding_tr': 'ECR imaj taramasi etkinlestirilmemistir. Container imajlari, production\'da istismar edilebilecek bilinen guvenlik aciklari icerebilir.',
                'recommendation_en': 'Enable ECR "Scan on push" for automatic vulnerability scanning. Implement lifecycle policies to remove untagged and old images.',
                'recommendation_tr': 'Otomatik guvenlik acigi taramasi icin ECR "Scan on push" etkinlestirilmelidir. Etiketsiz ve eski imajlari kaldirmak icin yasam dongusu politikalari uygulanmalidir.',
            },
            {
                'match': lambda f: 'lifecycle' in f.get('id', '').lower(),
                'wafr': ['COST04'],
                'risk': 'MEDIUM',
                'finding_en': 'ECR lifecycle policy is not configured. Old and untagged images accumulate and create unnecessary storage costs.',
                'finding_tr': 'ECR yasam dongusu politikasi yapilandirilmamistir. Eski ve etiketsiz imajlar birikerek gereksiz depolama maliyeti olusturmaktadir.',
                'recommendation_en': 'Configure ECR lifecycle policies: retain last 3-5 tagged images per repository, auto-delete untagged images after 7 days.',
                'recommendation_tr': 'ECR yasam dongusu politikalari yapilandirilmalidir: her depo icin son 3-5 etiketli imaji saklayin, etiketsiz imajlari 7 gun sonra otomatik silin.',
            },
            {
                'match': lambda f: True,
                'wafr': ['SEC06', 'COST04'],
                'risk': 'MEDIUM',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review ECR configuration for image scanning, lifecycle policies, and cross-region replication.',
                'recommendation_tr': 'ECR yapilandirmasi imaj taramasi, yasam dongusu politikalari ve bolge arasi coglama icin gozden gecirilmelidir.',
            },
        ],
    },
    # ── EFS ──
    'EFS': {
        'category_en': 'File Storage',
        'category_tr': 'Dosya Depolama',
        'rules': [
            {
                'match': lambda f: True,
                'wafr': ['SEC08', 'COST03'],
                'risk': 'LOW',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review EFS configuration for encryption, access points, backup policies, and lifecycle management.',
                'recommendation_tr': 'EFS yapilandirmasi sifreleme, erisim noktalari, yedekleme politikalari ve yasam dongusu yonetimi icin gozden gecirilmelidir.',
            },
        ],
    },
    # ── DynamoDB ──
    'DynamoDB': {
        'category_en': 'NoSQL Database',
        'category_tr': 'NoSQL Veritabani',
        'rules': [
            {
                'match': lambda f: 'backup' in f.get('id', '').lower() or 'pitr' in f.get('id', '').lower(),
                'wafr': ['REL09'],
                'risk': 'MEDIUM',
                'finding_en': 'DynamoDB Point-in-Time Recovery (PITR) is not enabled. Without PITR, accidental data deletions cannot be recovered.',
                'finding_tr': 'DynamoDB Noktasal Kurtarma (PITR) etkinlestirilmemistir. PITR olmadan kazara veri silmeleri kurtarilamaz.',
                'recommendation_en': 'Enable PITR for all DynamoDB tables. Enable on-demand backups for critical tables as additional protection.',
                'recommendation_tr': 'Tum DynamoDB tablolari icin PITR etkinlestirilmelidir. Ek koruma olarak kritik tablolar icin istege bagli yedeklemeler etkinlestirilmelidir.',
            },
            {
                'match': lambda f: True,
                'wafr': ['REL09', 'SEC08'],
                'risk': 'LOW',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review DynamoDB configuration for encryption, PITR, and capacity planning.',
                'recommendation_tr': 'DynamoDB yapilandirmasi sifreleme, PITR ve kapasite planlamasi icin gozden gecirilmelidir.',
            },
        ],
    },
    # ── SQS ──
    'SQS': {
        'category_en': 'Message Queue',
        'category_tr': 'Mesaj Kuyrugu',
        'rules': [
            {
                'match': lambda f: True,
                'wafr': ['SEC08', 'SEC09'],
                'risk': 'LOW',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review SQS queues for encryption at rest (SSE-KMS), access policies, and dead-letter queue configuration.',
                'recommendation_tr': 'SQS kuyruklari duran veri sifreleme (SSE-KMS), erisim politikalari ve olumektup kuyrugu yapilandirmasi icin gozden gecirilmelidir.',
            },
        ],
    },
    # ── SNS ──
    'SNS': {
        'category_en': 'Notification Service',
        'category_tr': 'Bildirim Servisi',
        'rules': [
            {
                'match': lambda f: True,
                'wafr': ['SEC08', 'SEC09'],
                'risk': 'LOW',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review SNS topics for encryption, access policies, and subscription confirmation enforcement.',
                'recommendation_tr': 'SNS konulari sifreleme, erisim politikalari ve abonelik dogrulama zorunlulugu icin gozden gecirilmelidir.',
            },
        ],
    },
    # ── ECS ──
    'ECS': {
        'category_en': 'Container Orchestration',
        'category_tr': 'Container Orkestrasyon',
        'rules': [
            {
                'match': lambda f: True,
                'wafr': ['SEC06', 'COST05'],
                'risk': 'MEDIUM',
                'finding_en': None,
                'finding_tr': None,
                'recommendation_en': 'Review ECS task definitions for secrets management, logging, IAM role permissions, and Fargate vs EC2 launch type selection.',
                'recommendation_tr': 'ECS gorev tanimlari gizli bilgi yonetimi, gunlukleme, IAM rol izinleri ve Fargate/EC2 baslatma turu secimi icin gozden gecirilmelidir.',
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Cost-specific advice templates (for FinOps data)
# ---------------------------------------------------------------------------
COST_ADVICE_TEMPLATES = {
    'no_budget': {
        'wafr': ['COST01', 'COST03'],
        'risk': 'MEDIUM',
        'finding_en': 'No AWS Budget is configured or existing budgets are not effectively utilized. Without budgets, cost overruns cannot be detected proactively.',
        'finding_tr': 'AWS Budget yapilandirilmamis veya mevcut butceler etkin kullanilmamaktadir. Butceler olmadan maliyet asimlari proaktif olarak tespit edilememektedir.',
        'recommendation_en': 'Configure AWS Budgets with appropriate thresholds and alert notifications. Set up both actual and forecasted budget alerts.',
        'recommendation_tr': 'Uygun esik degerleri ve uyari bildirimleriyle AWS Budgets yapilandirilmalidir. Hem gerceklesen hem de tahmin edilen butce uyarilari ayarlanmalidir.',
    },
    'no_savings_plan': {
        'wafr': ['COST06'],
        'risk': 'MEDIUM',
        'finding_en': 'No Savings Plans or Reserved Instances detected. On-Demand pricing is being used for all compute resources.',
        'finding_tr': 'Savings Plans veya Reserved Instance tespit edilmemistir. Tum islem kaynaklari icin On-Demand fiyatlandirma kullanilmaktadir.',
        'recommendation_en': 'Evaluate Compute Savings Plans for predictable workloads. Consider Reserved Instances for stable, long-running resources (EC2, RDS, ElastiCache).',
        'recommendation_tr': 'Ongorulebilir is yukleri icin Compute Savings Plans degerlendirilmelidir. Kararli, uzun sureli calisan kaynaklar (EC2, RDS, ElastiCache) icin Reserved Instance\'lar degerlendirilmelidir.',
    },
    'high_data_transfer': {
        'wafr': ['COST07'],
        'risk': 'MEDIUM',
        'finding_en': 'Significant data transfer costs detected, potentially indicating cross-region transfers or lack of CDN caching.',
        'finding_tr': 'Onemli veri aktarim maliyetleri tespit edilmistir; bu durum bolge arasi transferleri veya CDN onbellekleme eksikligini gosterebilir.',
        'recommendation_en': 'Implement CloudFront for static content delivery. Colocate related services in the same region. Use VPC Endpoints for AWS service access.',
        'recommendation_tr': 'Statik icerik dagitimi icin CloudFront uygulanmalidir. Ilgili servisler ayni bolgede konumlandirilmalidir. AWS servis erisimi icin VPC Endpoint\'ler kullanilmalidir.',
    },
    'underutilized_resources': {
        'wafr': ['COST05', 'SUS04'],
        'risk': 'LOW',
        'finding_en': 'Potential underutilized resources detected. Oversized or idle resources contribute to unnecessary costs.',
        'finding_tr': 'Potansiyel olarak yetersiz kullanilan kaynaklar tespit edilmistir. Asiri boyutlu veya bosta kalan kaynaklar gereksiz maliyetlere katkida bulunmaktadir.',
        'recommendation_en': 'Implement right-sizing based on CloudWatch metrics. Consider Spot instances for dev/test. Terminate unused resources.',
        'recommendation_tr': 'CloudWatch metriklerine dayali dogru boyutlandirma uygulanmalidir. Dev/test icin Spot instance degerlendirilmelidir. Kullanilmayan kaynaklar sonlandirilmalidir.',
    },
    'multi_region_cost': {
        'wafr': ['COST03', 'OPS01'],
        'risk': 'LOW',
        'finding_en': 'Resources are distributed across multiple regions. Multi-region deployment without clear strategy increases operational complexity and data transfer costs.',
        'finding_tr': 'Kaynaklar birden fazla bolgeye dagilmistir. Net bir strateji olmadan coklu bolge dagitimi operasyonel karmasikligi ve veri aktarim maliyetlerini artirmaktadir.',
        'recommendation_en': 'Define a clear region strategy aligned with latency requirements and data residency regulations. Consolidate non-essential resources to primary region.',
        'recommendation_tr': 'Gecikme gereksinimleri ve veri ikamet duzenlemeleriyle uyumlu net bir bolge stratejisi tanimlanmalidir. Temel olmayan kaynaklar birincil bolgeye konsolide edilmelidir.',
    },
}

# ---------------------------------------------------------------------------
# MapInventory-based advice templates (resource-level observations)
# ---------------------------------------------------------------------------
RESOURCE_ADVICE_TEMPLATES = {
    'stopped_instances': {
        'wafr': ['COST04'],
        'risk': 'LOW',
        'finding_en': 'Stopped EC2 instances detected. While compute cost is zero, attached EBS volumes continue to incur storage charges.',
        'finding_tr': 'Durdurulmus EC2 instance\'lari tespit edilmistir. Islem maliyeti sifir olsa da, ekli EBS volume\'lari depolama ucretleri olusturmaya devam etmektedir.',
        'recommendation_en': 'Evaluate stopped instances: take snapshots and terminate if no longer needed. Detach and delete unnecessary EBS volumes.',
        'recommendation_tr': 'Durdurulmus instance\'lar degerlendirilmelidir: artik gerekli degilse snapshot alinip sonlandirilmalidir. Gereksiz EBS volume\'lari ayrilmali ve silinmelidir.',
    },
    'untagged_resources': {
        'wafr': ['COST02', 'OPS01'],
        'risk': 'LOW',
        'finding_en': 'Resources without proper tagging detected. Without tags, cost allocation and resource ownership tracking become difficult.',
        'finding_tr': 'Uygun etiketleme yapilmamis kaynaklar tespit edilmistir. Etiketler olmadan maliyet tahsisi ve kaynak sahiplik takibi zorlasir.',
        'recommendation_en': 'Implement a mandatory tagging strategy: Environment, Owner, Project, CostCenter. Use AWS Organizations Tag Policies for enforcement.',
        'recommendation_tr': 'Zorunlu etiketleme stratejisi uygulanmalidir: Environment, Owner, Project, CostCenter. Uygulama icin AWS Organizations Tag Policies kullanilmalidir.',
    },
    'default_vpc_resources': {
        'wafr': ['SEC05', 'REL02'],
        'risk': 'MEDIUM',
        'finding_en': 'Resources deployed in default VPC detected. Default VPCs lack proper network segmentation required for production workloads.',
        'finding_tr': 'Varsayilan VPC\'de dagitilmis kaynaklar tespit edilmistir. Varsayilan VPC\'ler production is yukleri icin gereken uygun ag segmentasyonundan yoksundur.',
        'recommendation_en': 'Migrate resources from default VPC to custom VPCs with proper three-tier architecture and network isolation.',
        'recommendation_tr': 'Kaynaklari varsayilan VPC\'den uygun uc katmanli mimari ve ag izolasyonu ile ozel VPC\'lere tasinmalidir.',
    },
}
