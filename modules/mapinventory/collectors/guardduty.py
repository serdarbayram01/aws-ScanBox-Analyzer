"""
Map Inventory — GuardDuty Collector
Resource types: detector, ip-set, threat-intel-set, filter
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_guardduty_resources(session, region, account_id):
    """Collect all GuardDuty resource types in the given region."""
    resources = []
    try:
        gd = session.client('guardduty', region_name=region)
    except Exception:
        return resources

    # ── Detectors ────────────────────────────────────────────────────
    detector_ids = []
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = gd.list_detectors(**kwargs)
            detector_ids.extend(resp.get('DetectorIds', []))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        return resources

    for det_id in detector_ids:
        det_arn = f"arn:aws:guardduty:{region}:{account_id}:detector/{det_id}"
        details = {}
        tags_dict = {}

        try:
            det = gd.get_detector(DetectorId=det_id)
            details = {
                'status': det.get('Status', ''),
                'finding_publishing_frequency': det.get('FindingPublishingFrequency', ''),
                'service_role': det.get('ServiceRole', ''),
                'created_at': det.get('CreatedAt', ''),
                'updated_at': det.get('UpdatedAt', ''),
                'data_sources': str(det.get('DataSources', {})),
            }
            tags_dict = det.get('Tags', {})
            # GuardDuty returns tags as a flat dict, not a list
            if isinstance(tags_dict, list):
                tags_dict = tags_to_dict(tags_dict)
        except Exception:
            pass

        resources.append(make_resource(
            service='guardduty',
            resource_type='detector',
            resource_id=det_id,
            arn=det_arn,
            name=f"detector-{det_id}",
            region=region,
            details=details,
            tags=tags_dict,
        ))

        # ── IP Sets (per detector) ──────────────────────────────────
        try:
            next_token = None
            while True:
                kwargs = {'DetectorId': det_id}
                if next_token:
                    kwargs['NextToken'] = next_token
                resp = gd.list_ip_sets(**kwargs)
                for ip_set_id in resp.get('IpSetIds', []):
                    try:
                        ip_set = gd.get_ip_set(DetectorId=det_id, IpSetId=ip_set_id)
                        ip_name = ip_set.get('Name', ip_set_id)
                        ip_arn = f"arn:aws:guardduty:{region}:{account_id}:detector/{det_id}/ipset/{ip_set_id}"
                        ip_tags = ip_set.get('Tags', {})
                        if isinstance(ip_tags, list):
                            ip_tags = tags_to_dict(ip_tags)
                        resources.append(make_resource(
                            service='guardduty',
                            resource_type='ip-set',
                            resource_id=ip_set_id,
                            arn=ip_arn,
                            name=ip_name,
                            region=region,
                            details={
                                'detector_id': det_id,
                                'format': ip_set.get('Format', ''),
                                'location': ip_set.get('Location', ''),
                                'status': ip_set.get('Status', ''),
                            },
                            tags=ip_tags,
                        ))
                    except Exception:
                        pass
                next_token = resp.get('NextToken')
                if not next_token:
                    break
        except Exception:
            pass

        # ── Threat Intel Sets (per detector) ─────────────────────────
        try:
            next_token = None
            while True:
                kwargs = {'DetectorId': det_id}
                if next_token:
                    kwargs['NextToken'] = next_token
                resp = gd.list_threat_intel_sets(**kwargs)
                for tis_id in resp.get('ThreatIntelSetIds', []):
                    try:
                        tis = gd.get_threat_intel_set(DetectorId=det_id, ThreatIntelSetId=tis_id)
                        tis_name = tis.get('Name', tis_id)
                        tis_arn = f"arn:aws:guardduty:{region}:{account_id}:detector/{det_id}/threatintelset/{tis_id}"
                        tis_tags = tis.get('Tags', {})
                        if isinstance(tis_tags, list):
                            tis_tags = tags_to_dict(tis_tags)
                        resources.append(make_resource(
                            service='guardduty',
                            resource_type='threat-intel-set',
                            resource_id=tis_id,
                            arn=tis_arn,
                            name=tis_name,
                            region=region,
                            details={
                                'detector_id': det_id,
                                'format': tis.get('Format', ''),
                                'location': tis.get('Location', ''),
                                'status': tis.get('Status', ''),
                            },
                            tags=tis_tags,
                        ))
                    except Exception:
                        pass
                next_token = resp.get('NextToken')
                if not next_token:
                    break
        except Exception:
            pass

        # ── Filters (per detector) ───────────────────────────────────
        try:
            next_token = None
            while True:
                kwargs = {'DetectorId': det_id}
                if next_token:
                    kwargs['NextToken'] = next_token
                resp = gd.list_filters(**kwargs)
                for filter_name in resp.get('FilterNames', []):
                    try:
                        filt = gd.get_filter(DetectorId=det_id, FilterName=filter_name)
                        filt_arn = f"arn:aws:guardduty:{region}:{account_id}:detector/{det_id}/filter/{filter_name}"
                        filt_tags = filt.get('Tags', {})
                        if isinstance(filt_tags, list):
                            filt_tags = tags_to_dict(filt_tags)
                        resources.append(make_resource(
                            service='guardduty',
                            resource_type='filter',
                            resource_id=filter_name,
                            arn=filt_arn,
                            name=filt.get('Name', filter_name),
                            region=region,
                            details={
                                'detector_id': det_id,
                                'description': filt.get('Description', ''),
                                'action': filt.get('Action', ''),
                                'rank': filt.get('Rank', 0),
                            },
                            tags=filt_tags,
                        ))
                    except Exception:
                        pass
                next_token = resp.get('NextToken')
                if not next_token:
                    break
        except Exception:
            pass

    return resources
