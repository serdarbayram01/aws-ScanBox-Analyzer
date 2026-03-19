"""
Map Inventory — AWS Config Collector
Resource types: configuration-recorder, delivery-channel, config-rule,
                configuration-aggregator, conformance-pack
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_config_resources(session, region, account_id):
    """Collect all AWS Config resource types in the given region."""
    resources = []
    try:
        cfg = session.client('config', region_name=region)
    except Exception:
        return resources

    # ── Configuration Recorders ──────────────────────────────────────
    try:
        resp = cfg.describe_configuration_recorders()
        recorder_names = []
        for rec in resp.get('ConfigurationRecorders', []):
            rec_name = rec.get('name', '')
            recorder_names.append(rec_name)
            role_arn = rec.get('roleARN', '')
            recording_group = rec.get('recordingGroup', {})
            arn = f"arn:aws:config:{region}:{account_id}:config-recorder/{rec_name}"
            details = {
                'role_arn': role_arn,
                'all_supported': recording_group.get('allSupported', False),
                'include_global_resource_types': recording_group.get('includeGlobalResourceTypes', False),
                'resource_types': recording_group.get('resourceTypes', []),
            }
            resources.append(make_resource(
                service='config',
                resource_type='configuration-recorder',
                resource_id=rec_name,
                arn=arn,
                name=rec_name,
                region=region,
                details=details,
                tags={},
            ))

        # Enrich with recorder status
        if recorder_names:
            try:
                status_resp = cfg.describe_configuration_recorder_status(
                    ConfigurationRecorderNames=recorder_names
                )
                status_map = {}
                for s in status_resp.get('ConfigurationRecordersStatus', []):
                    status_map[s.get('name', '')] = {
                        'recording': s.get('recording', False),
                        'last_status': s.get('lastStatus', ''),
                        'last_start_time': str(s.get('lastStartTime', '')),
                        'last_stop_time': str(s.get('lastStopTime', '')),
                    }
                for r in resources:
                    if r['type'] == 'configuration-recorder' and r['id'] in status_map:
                        r['details'].update(status_map[r['id']])
            except Exception:
                pass
    except Exception:
        pass

    # ── Delivery Channels ────────────────────────────────────────────
    try:
        resp = cfg.describe_delivery_channels()
        for ch in resp.get('DeliveryChannels', []):
            ch_name = ch.get('name', '')
            arn = f"arn:aws:config:{region}:{account_id}:delivery-channel/{ch_name}"
            resources.append(make_resource(
                service='config',
                resource_type='delivery-channel',
                resource_id=ch_name,
                arn=arn,
                name=ch_name,
                region=region,
                details={
                    's3_bucket_name': ch.get('s3BucketName', ''),
                    's3_key_prefix': ch.get('s3KeyPrefix', ''),
                    'sns_topic_arn': ch.get('snsTopicARN', ''),
                    'delivery_frequency': ch.get('configSnapshotDeliveryProperties', {}).get('deliveryFrequency', ''),
                },
                tags={},
            ))
    except Exception:
        pass

    # ── Config Rules ─────────────────────────────────────────────────
    try:
        paginator = cfg.get_paginator('describe_config_rules')
        for page in paginator.paginate():
            for rule in page.get('ConfigRules', []):
                rule_name = rule.get('ConfigRuleName', '')
                rule_arn = rule.get('ConfigRuleArn', '')
                rule_id = rule.get('ConfigRuleId', '')
                source = rule.get('Source', {})
                tags_dict = {}
                try:
                    tag_resp = cfg.list_tags_for_resource(
                        ResourceArn=rule_arn
                    )
                    tags_dict = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass
                resources.append(make_resource(
                    service='config',
                    resource_type='config-rule',
                    resource_id=rule_id,
                    arn=rule_arn,
                    name=rule_name,
                    region=region,
                    details={
                        'state': rule.get('ConfigRuleState', ''),
                        'source_owner': source.get('Owner', ''),
                        'source_identifier': source.get('SourceIdentifier', ''),
                        'maximum_execution_frequency': rule.get('MaximumExecutionFrequency', ''),
                        'created_by': rule.get('CreatedBy', ''),
                        'description': rule.get('Description', ''),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # ── Configuration Aggregators ────────────────────────────────────
    try:
        paginator = cfg.get_paginator('describe_configuration_aggregators')
        for page in paginator.paginate():
            for agg in page.get('ConfigurationAggregators', []):
                agg_name = agg.get('ConfigurationAggregatorName', '')
                agg_arn = agg.get('ConfigurationAggregatorArn', '')
                account_agg = agg.get('AccountAggregationSources', [])
                org_agg = agg.get('OrganizationAggregationSource', {})
                resources.append(make_resource(
                    service='config',
                    resource_type='configuration-aggregator',
                    resource_id=agg_name,
                    arn=agg_arn,
                    name=agg_name,
                    region=region,
                    details={
                        'account_aggregation_sources_count': len(account_agg),
                        'organization_aggregation_role_arn': org_agg.get('RoleArn', ''),
                        'organization_all_regions': org_agg.get('AllAwsRegions', False),
                        'creation_time': str(agg.get('CreationTime', '')),
                        'last_updated_time': str(agg.get('LastUpdatedTime', '')),
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── Conformance Packs ────────────────────────────────────────────
    try:
        paginator = cfg.get_paginator('describe_conformance_packs')
        for page in paginator.paginate():
            for cp in page.get('ConformancePackDetails', []):
                cp_name = cp.get('ConformancePackName', '')
                cp_arn = cp.get('ConformancePackArn', '')
                cp_id = cp.get('ConformancePackId', '')
                resources.append(make_resource(
                    service='config',
                    resource_type='conformance-pack',
                    resource_id=cp_id,
                    arn=cp_arn,
                    name=cp_name,
                    region=region,
                    details={
                        'delivery_s3_bucket': cp.get('DeliveryS3Bucket', ''),
                        'delivery_s3_key_prefix': cp.get('DeliveryS3KeyPrefix', ''),
                        'created_by': cp.get('CreatedBy', ''),
                        'last_update_requested_time': str(cp.get('LastUpdateRequestedTime', '')),
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
