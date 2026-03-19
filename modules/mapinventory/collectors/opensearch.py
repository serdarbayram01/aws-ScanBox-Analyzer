"""
Map Inventory — Amazon OpenSearch Service Collector
Resource types: domain, serverless-collection
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_opensearch_resources(session, region, account_id):
    """Collect OpenSearch domains and serverless collections."""
    resources = []

    # ── Domains (managed OpenSearch / Elasticsearch) ──────────────────
    try:
        client = session.client('opensearch', region_name=region)
        resp = client.list_domain_names()
        domain_names = [d['DomainName'] for d in resp.get('DomainNames', [])]

        # describe_domains accepts up to 5 at a time
        for i in range(0, len(domain_names), 5):
            batch = domain_names[i:i + 5]
            desc_resp = client.describe_domains(DomainNames=batch)
            for domain in desc_resp.get('DomainStatusList', []):
                domain_name = domain.get('DomainName', '')
                domain_arn = domain.get('ARN', '')
                cluster_cfg = domain.get('ClusterConfig', {})
                ebs_opts = domain.get('EBSOptions', {})
                encrypt_at_rest = domain.get('EncryptionAtRestOptions', {})
                node_to_node = domain.get('NodeToNodeEncryptionOptions', {})
                vpc_opts = domain.get('VPCOptions', {})

                tags = {}
                try:
                    tag_resp = client.list_tags(ARN=domain_arn)
                    tags = tags_to_dict(tag_resp.get('TagList', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='opensearch',
                    resource_type='domain',
                    resource_id=domain_name,
                    arn=domain_arn,
                    name=domain_name,
                    region=region,
                    details={
                        'engine_version': domain.get('EngineVersion', ''),
                        'instance_type': cluster_cfg.get('InstanceType', ''),
                        'instance_count': cluster_cfg.get('InstanceCount', 0),
                        'dedicated_master_enabled': cluster_cfg.get('DedicatedMasterEnabled', False),
                        'zone_awareness_enabled': cluster_cfg.get('ZoneAwarenessEnabled', False),
                        'ebs_enabled': ebs_opts.get('EBSEnabled', False),
                        'volume_type': ebs_opts.get('VolumeType', ''),
                        'volume_size': ebs_opts.get('VolumeSize', 0),
                        'encrypt_at_rest': encrypt_at_rest.get('Enabled', False),
                        'node_to_node_encryption': node_to_node.get('Enabled', False),
                        'vpc_id': vpc_opts.get('VPCId', ''),
                        'endpoint': domain.get('Endpoint', domain.get('Endpoints', {}).get('vpc', '')),
                        'processing': domain.get('Processing', False),
                        'created': domain.get('Created', False),
                        'deleted': domain.get('Deleted', False),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Serverless Collections ────────────────────────────────────────
    try:
        aoss = session.client('opensearchserverless', region_name=region)
        # list_collections uses batchGet pattern; first list, then describe
        next_token = None
        collection_summaries = []
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = aoss.list_collections(**kwargs)
            collection_summaries.extend(resp.get('collectionSummaries', []))
            next_token = resp.get('nextToken')
            if not next_token:
                break

        for coll in collection_summaries:
            coll_id = coll.get('id', '')
            coll_name = coll.get('name', coll_id)
            coll_arn = coll.get('arn', f"arn:aws:aoss:{region}:{account_id}:collection/{coll_id}")

            tags = {}
            try:
                tag_resp = aoss.list_tags_for_resource(resourceArn=coll_arn)
                tags = {t['key']: t['value'] for t in tag_resp.get('tags', []) if 'key' in t}
            except Exception:
                pass

            resources.append(make_resource(
                service='opensearch',
                resource_type='serverless-collection',
                resource_id=coll_id,
                arn=coll_arn,
                name=coll_name,
                region=region,
                details={
                    'status': coll.get('status', ''),
                    'type': coll.get('type', ''),
                },
                tags=tags,
            ))
    except Exception:
        pass

    return resources
