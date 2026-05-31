"""SecOps — AWS Config Checks: enabled per region, rules compliance."""
from .base import make_finding, not_available
SERVICE = 'Config'

def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('config_regions', SERVICE, str(exc))]

    # Multi-account aggregator check — runs ONCE from us-east-1 (account-level concept).
    # An aggregator is essential for centralised compliance visibility across an
    # AWS Organization or a list of accounts/regions.
    try:
        cfg_global = session.client('config', region_name='us-east-1')
        aggs = cfg_global.describe_configuration_aggregators().get('ConfigurationAggregators', [])
        has_agg = len(aggs) > 0
        agg_types = set()
        for a in aggs:
            if a.get('OrganizationAggregationSource'):
                agg_types.add('Organization')
            if a.get('AccountAggregationSources'):
                agg_types.add('Account-list')
        findings.append(make_finding(
            id='config_aggregator',
            title='AWS Config multi-account aggregator',
            title_tr='AWS Config çoklu hesap toplayıcı',
            description=(
                f'{"Found " + str(len(aggs)) + " configuration aggregator(s): " + ", ".join(sorted(agg_types)) if has_agg else "No configuration aggregator found"}. '
                f'Aggregators give a unified compliance view across accounts/regions — '
                f'required for AWS Organizations security tooling and centralised audit dashboards.'
            ),
            description_tr=(
                f'{str(len(aggs)) + " yapılandırma toplayıcı bulundu: " + ", ".join(sorted(agg_types)) if has_agg else "Yapılandırma toplayıcı bulunamadı"}. '
                f'Toplayıcılar hesaplar/bölgeler genelinde birleşik bir uyumluluk görünümü sağlar — '
                f'AWS Organizations güvenlik araçları ve merkezi denetim panoları için gereklidir.'
            ),
            severity='LOW', status='PASS' if has_agg else 'WARNING',
            service=SERVICE, resource_id='account',
            resource_type='AWS::Config::ConfigurationAggregator', region='global',
            frameworks={
                'SOC2':     ['CC7.1', 'CC4.1'],
                'ISO27001': ['A.12.4.1', 'A.18.2.2'],
                'WAFR':     {'pillar': 'Operational Excellence', 'controls': ['OPS01', 'OPS04']},
            },
            remediation=(
                'Config → Aggregators → Create aggregator. For Organizations: select '
                '"My organization"; otherwise add individual accounts + regions. '
                'Enable from the security/audit account.'
            ),
            remediation_tr=(
                'Config → Aggregators → Toplayıcı oluştur. Organizations için: '
                '"My organization" seçin; aksi takdirde tek tek hesaplar + bölgeler ekleyin. '
                'Güvenlik/denetim hesabından etkinleştirin.'
            ),
            details={'count': len(aggs), 'sources': sorted(agg_types)},
        ))
    except Exception as exc:
        findings.append(not_available('config_aggregator', SERVICE, str(exc)))

    for region in regions:
        cfg = session.client('config', region_name=region)
        try:
            recorders = cfg.describe_configuration_recorders()['ConfigurationRecorders']
            if not recorders:
                findings.append(make_finding(
                    id=f'config_enabled_{region}',
                    title=f'AWS Config enabled: {region}',
                    title_tr=f'AWS Config aktif: {region}',
                    description=f'AWS Config is not enabled in {region}.',
                    description_tr=f'{region} bölgesinde AWS Config etkin değil.',
                    severity='HIGH', status='FAIL',
                    service=SERVICE, resource_id=region,
                    resource_type='AWS::Config::ConfigurationRecorder', region=region,
                    frameworks={
                                'SOC2': ['CC7.1', 'CC8.1'],'CIS': ['3.5'], 'HIPAA': ['164.312(b)'], 'ISO27001': ['A.12.4.1'],
                                'WAFR': {'pillar': 'Operational Excellence', 'controls': ['OPS01']}},
                    remediation=f'Config Console ({region}) → Set up Config → Enable recording.',
                    remediation_tr=f'Config Konsol ({region}) → Config\'i kur → Kaydı etkinleştir.',
                ))
                continue

            rec_name = recorders[0]['name']
            status_list = cfg.describe_configuration_recorder_status(
                ConfigurationRecorderNames=[rec_name])['ConfigurationRecordersStatus']
            recording = status_list[0].get('recording', False) if status_list else False

            findings.append(make_finding(
                id=f'config_recording_{region}',
                title=f'AWS Config recording active: {region}',
                title_tr=f'AWS Config kaydı aktif: {region}',
                description=f'AWS Config recorder in {region} should be actively recording.',
                description_tr=f'{region} bölgesindeki AWS Config kaydedicisi aktif kaydetmelidir.',
                severity='HIGH', status='PASS' if recording else 'FAIL',
                service=SERVICE, resource_id=rec_name,
                resource_type='AWS::Config::ConfigurationRecorder', region=region,
                frameworks={
                            'SOC2': ['CC7.1'],'CIS': ['3.5'], 'ISO27001': ['A.12.4.1'],
                            'WAFR': {'pillar': 'Operational Excellence', 'controls': ['OPS01']}},
                remediation=f'Config Console ({region}) → Start recording.',
                remediation_tr=f'Config Konsol ({region}) → Kaydı başlat.',
            ))

            # Check for non-compliant rules
            try:
                rules = cfg.describe_compliance_by_config_rule(
                    ComplianceTypes=['NON_COMPLIANT'])['ComplianceByConfigRules']
                for rule in rules[:20]:
                    rule_name = rule['ConfigRuleName']
                    findings.append(make_finding(
                        id=f'config_rule_noncompliant_{rule_name}_{region}',
                        title=f'Config rule non-compliant: {rule_name}',
                        title_tr=f'Config kuralı uyumsuz: {rule_name}',
                        description=f'AWS Config rule {rule_name} in {region} has non-compliant resources.',
                        description_tr=f'{region} bölgesindeki AWS Config kuralı {rule_name} uyumsuz kaynaklara sahip.',
                        severity='MEDIUM', status='FAIL',
                        service=SERVICE, resource_id=rule_name,
                        resource_type='AWS::Config::ConfigRule', region=region,
                        frameworks={
                                    'SOC2': ['CC7.1'],'WAFR': {'pillar': 'Operational Excellence', 'controls': ['OPS01']}},
                        remediation=f'Config Console → Rules → {rule_name} → View non-compliant resources.',
                        remediation_tr=f'Config Konsol → Kurallar → {rule_name} → Uyumsuz kaynakları görüntüle.',
                    ))
            except Exception:
                pass

        except Exception as exc:
            findings.append(not_available(f'config_{region}', SERVICE, str(exc)))
    return findings
