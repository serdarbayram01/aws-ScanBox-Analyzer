"""
Map Inventory — CloudTrail Collector
Resource types: trail, event-data-store
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_cloudtrail_resources(session, region, account_id):
    """Collect all CloudTrail resource types in the given region."""
    resources = []
    try:
        ct = session.client('cloudtrail', region_name=region)
    except Exception:
        return resources

    # ── Trails ───────────────────────────────────────────────────────
    try:
        resp = ct.describe_trails(includeShadowTrails=False)
        for trail in resp.get('trailList', []):
            trail_name = trail.get('Name', '')
            trail_arn = trail.get('TrailARN', '')
            home_region = trail.get('HomeRegion', region)

            # Only collect trails whose home region matches to avoid duplicates
            if home_region != region:
                continue

            details = {
                'home_region': home_region,
                's3_bucket_name': trail.get('S3BucketName', ''),
                's3_key_prefix': trail.get('S3KeyPrefix', ''),
                'log_file_validation_enabled': trail.get('LogFileValidationEnabled', False),
                'is_multi_region': trail.get('IsMultiRegionTrail', False),
                'is_organization_trail': trail.get('IsOrganizationTrail', False),
                'has_custom_event_selectors': trail.get('HasCustomEventSelectors', False),
                'has_insight_selectors': trail.get('HasInsightSelectors', False),
                'kms_key_id': trail.get('KmsKeyId', ''),
                'cloud_watch_logs_log_group_arn': trail.get('CloudWatchLogsLogGroupArn', ''),
                'sns_topic_arn': trail.get('SnsTopicARN', ''),
            }

            # Get trail status
            try:
                status = ct.get_trail_status(Name=trail_arn)
                details.update({
                    'is_logging': status.get('IsLogging', False),
                    'latest_delivery_time': str(status.get('LatestDeliveryTime', '')),
                    'latest_notification_time': str(status.get('LatestNotificationTime', '')),
                    'start_logging_time': str(status.get('StartLoggingTime', '')),
                    'stop_logging_time': str(status.get('StopLoggingTime', '')),
                    'latest_delivery_error': status.get('LatestDeliveryError', ''),
                })
            except Exception:
                pass

            # Tags
            tags_dict = {}
            try:
                tag_resp = ct.list_tags(ResourceIdList=[trail_arn])
                for tag_list in tag_resp.get('ResourceTagList', []):
                    tags_dict = tags_to_dict(tag_list.get('TagsList', []))
            except Exception:
                pass

            resources.append(make_resource(
                service='cloudtrail',
                resource_type='trail',
                resource_id=trail_name,
                arn=trail_arn,
                name=trail_name,
                region=region,
                details=details,
                tags=tags_dict,
            ))
    except Exception:
        pass

    # ── Event Data Stores ────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = ct.list_event_data_stores(**kwargs)
            for eds_summary in resp.get('EventDataStores', []):
                eds_arn = eds_summary.get('EventDataStoreArn', '')
                eds_name = eds_summary.get('Name', '')
                details = {
                    'status': eds_summary.get('Status', ''),
                    'retention_period': eds_summary.get('RetentionPeriod', ''),
                    'multi_region_enabled': eds_summary.get('MultiRegionEnabled', False),
                    'organization_enabled': eds_summary.get('OrganizationEnabled', False),
                }

                # Get full details
                try:
                    eds_detail = ct.get_event_data_store(EventDataStore=eds_arn)
                    details.update({
                        'status': eds_detail.get('Status', details.get('status', '')),
                        'retention_period': eds_detail.get('RetentionPeriod', details.get('retention_period', '')),
                        'termination_protection_enabled': eds_detail.get('TerminationProtectionEnabled', False),
                        'created_timestamp': str(eds_detail.get('CreatedTimestamp', '')),
                        'updated_timestamp': str(eds_detail.get('UpdatedTimestamp', '')),
                        'kms_key_id': eds_detail.get('KmsKeyId', ''),
                        'advanced_event_selectors_count': len(eds_detail.get('AdvancedEventSelectors', [])),
                    })
                except Exception:
                    pass

                resources.append(make_resource(
                    service='cloudtrail',
                    resource_type='event-data-store',
                    resource_id=eds_arn.split('/')[-1] if '/' in eds_arn else eds_arn,
                    arn=eds_arn,
                    name=eds_name,
                    region=region,
                    details=details,
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
