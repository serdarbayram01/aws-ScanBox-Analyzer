"""
Map Inventory — SSM (Systems Manager) Collector
Resource types: parameter, document (Owner=Self), maintenance-window,
                patch-baseline (Self only), association
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_ssm_resources(session, region, account_id):
    """Collect Systems Manager resources for a given region."""
    resources = []
    try:
        client = session.client('ssm', region_name=region)
    except Exception:
        return resources

    # ── Parameters ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_parameters')
        for page in paginator.paginate():
            for param in page.get('Parameters', []):
                p_name = param.get('Name', '')
                p_type = param.get('Type', '')
                arn = f"arn:aws:ssm:{region}:{account_id}:parameter{p_name}" if p_name.startswith('/') \
                    else f"arn:aws:ssm:{region}:{account_id}:parameter/{p_name}"

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(
                        ResourceType='Parameter', ResourceId=p_name)
                    tags = tags_to_dict(tag_resp.get('TagList', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='ssm',
                    resource_type='parameter',
                    resource_id=p_name,
                    arn=arn,
                    name=p_name,
                    region=region,
                    details={
                        'type': p_type,
                        'tier': param.get('Tier', ''),
                        'version': param.get('Version', 0),
                        'data_type': param.get('DataType', ''),
                        'last_modified_date': str(param.get('LastModifiedDate', '')),
                        'last_modified_user': param.get('LastModifiedUser', ''),
                        'description': param.get('Description', ''),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Documents (Owner=Self only) ───────────────────────────────────
    try:
        paginator = client.get_paginator('list_documents')
        for page in paginator.paginate(
            Filters=[{'Key': 'Owner', 'Values': ['Self']}]
        ):
            for doc in page.get('DocumentIdentifiers', []):
                doc_name = doc.get('Name', '')
                doc_version = doc.get('DocumentVersion', '')
                arn = f"arn:aws:ssm:{region}:{account_id}:document/{doc_name}"
                tags_list = doc.get('Tags', [])

                resources.append(make_resource(
                    service='ssm',
                    resource_type='document',
                    resource_id=doc_name,
                    arn=arn,
                    name=doc_name,
                    region=region,
                    details={
                        'document_type': doc.get('DocumentType', ''),
                        'document_format': doc.get('DocumentFormat', ''),
                        'document_version': doc_version,
                        'schema_version': doc.get('SchemaVersion', ''),
                        'platform_types': doc.get('PlatformTypes', []),
                        'target_type': doc.get('TargetType', ''),
                        'created_date': str(doc.get('CreatedDate', '')),
                    },
                    tags=tags_to_dict(tags_list),
                ))
    except Exception:
        pass

    # ── Maintenance Windows ───────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_maintenance_windows')
        for page in paginator.paginate():
            for mw in page.get('WindowIdentities', []):
                mw_id = mw.get('WindowId', '')
                mw_name = mw.get('Name', mw_id)
                arn = f"arn:aws:ssm:{region}:{account_id}:maintenancewindow/{mw_id}"

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(
                        ResourceType='MaintenanceWindow', ResourceId=mw_id)
                    tags = tags_to_dict(tag_resp.get('TagList', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='ssm',
                    resource_type='maintenance-window',
                    resource_id=mw_id,
                    arn=arn,
                    name=mw_name,
                    region=region,
                    details={
                        'enabled': mw.get('Enabled', False),
                        'duration': mw.get('Duration', 0),
                        'cutoff': mw.get('Cutoff', 0),
                        'schedule': mw.get('Schedule', ''),
                        'description': mw.get('Description', ''),
                        'next_execution_time': mw.get('NextExecutionTime', ''),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Patch Baselines (Self only) ───────────────────────────────────
    try:
        paginator = client.get_paginator('describe_patch_baselines')
        for page in paginator.paginate(
            Filters=[{'Key': 'OWNER', 'Values': ['Self']}]
        ):
            for pb in page.get('BaselineIdentities', []):
                pb_id = pb.get('BaselineId', '')
                pb_name = pb.get('BaselineName', pb_id)
                arn = f"arn:aws:ssm:{region}:{account_id}:patchbaseline/{pb_id}"

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(
                        ResourceType='PatchBaseline', ResourceId=pb_id)
                    tags = tags_to_dict(tag_resp.get('TagList', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='ssm',
                    resource_type='patch-baseline',
                    resource_id=pb_id,
                    arn=arn,
                    name=pb_name,
                    region=region,
                    details={
                        'operating_system': pb.get('OperatingSystem', ''),
                        'default_baseline': pb.get('DefaultBaseline', False),
                        'description': pb.get('BaselineDescription', ''),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Associations ──────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_associations')
        for page in paginator.paginate():
            for assoc in page.get('Associations', []):
                assoc_id = assoc.get('AssociationId', '')
                assoc_name = assoc.get('AssociationName', '') or assoc.get('Name', assoc_id)
                doc_name = assoc.get('Name', '')
                arn = f"arn:aws:ssm:{region}:{account_id}:association/{assoc_id}"

                resources.append(make_resource(
                    service='ssm',
                    resource_type='association',
                    resource_id=assoc_id,
                    arn=arn,
                    name=assoc_name,
                    region=region,
                    details={
                        'document_name': doc_name,
                        'document_version': assoc.get('DocumentVersion', ''),
                        'association_version': assoc.get('AssociationVersion', ''),
                        'schedule_expression': assoc.get('ScheduleExpression', ''),
                        'last_execution_date': str(assoc.get('LastExecutionDate', '')),
                        'overview_status': assoc.get('Overview', {}).get('Status', ''),
                        'targets': assoc.get('Targets', []),
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
