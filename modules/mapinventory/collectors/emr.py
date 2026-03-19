"""
Map Inventory — EMR Collector
Resource types: cluster, studio, serverless-application
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_emr_resources(session, region, account_id):
    """Collect all EMR resource types in the given region."""
    resources = []

    # ── EMR Clusters ─────────────────────────────────────────────────
    try:
        emr = session.client('emr', region_name=region)
        active_states = [
            'STARTING', 'BOOTSTRAPPING', 'RUNNING', 'WAITING',
            'TERMINATING'
        ]
        next_marker = None
        while True:
            kwargs = {'ClusterStates': active_states}
            if next_marker:
                kwargs['Marker'] = next_marker
            resp = emr.list_clusters(**kwargs)
            for cluster_summary in resp.get('Clusters', []):
                cluster_id = cluster_summary.get('Id', '')
                cluster_name = cluster_summary.get('Name', cluster_id)
                cluster_arn = cluster_summary.get('ClusterArn', '')
                status = cluster_summary.get('Status', {})
                details = {
                    'state': status.get('State', ''),
                    'state_change_reason': str(status.get('StateChangeReason', {})),
                    'normalized_instance_hours': cluster_summary.get('NormalizedInstanceHours', 0),
                }

                # Describe for full details
                try:
                    desc = emr.describe_cluster(ClusterId=cluster_id)
                    cl = desc.get('Cluster', {})
                    cluster_arn = cl.get('ClusterArn', cluster_arn)
                    details.update({
                        'state': cl.get('Status', {}).get('State', details.get('state', '')),
                        'release_label': cl.get('ReleaseLabel', ''),
                        'applications': [a.get('Name', '') for a in cl.get('Applications', [])],
                        'auto_terminate': cl.get('AutoTerminate', False),
                        'termination_protected': cl.get('TerminationProtected', False),
                        'visible_to_all_users': cl.get('VisibleToAllUsers', False),
                        'log_uri': cl.get('LogUri', ''),
                        'master_public_dns_name': cl.get('MasterPublicDnsName', ''),
                        'instance_collection_type': cl.get('InstanceCollectionType', ''),
                        'ec2_instance_attributes': {
                            'ec2_key_name': cl.get('Ec2InstanceAttributes', {}).get('Ec2KeyName', ''),
                            'ec2_subnet_id': cl.get('Ec2InstanceAttributes', {}).get('Ec2SubnetId', ''),
                            'ec2_availability_zone': cl.get('Ec2InstanceAttributes', {}).get('Ec2AvailabilityZone', ''),
                        },
                        'scale_down_behavior': cl.get('ScaleDownBehavior', ''),
                        'ebs_root_volume_size': cl.get('EbsRootVolumeSize', 0),
                    })
                    tags = cl.get('Tags', [])
                except Exception:
                    tags = []

                resources.append(make_resource(
                    service='emr',
                    resource_type='cluster',
                    resource_id=cluster_id,
                    arn=cluster_arn,
                    name=cluster_name,
                    region=region,
                    details=details,
                    tags=tags_to_dict(tags),
                ))
            next_marker = resp.get('Marker')
            if not next_marker:
                break
    except Exception:
        pass

    # ── EMR Studios ──────────────────────────────────────────────────
    try:
        emr = session.client('emr', region_name=region)
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['Marker'] = next_token
            resp = emr.list_studios(**kwargs)
            for studio_summary in resp.get('Studios', []):
                studio_id = studio_summary.get('StudioId', '')
                studio_name = studio_summary.get('Name', studio_id)
                details = {
                    'url': studio_summary.get('Url', ''),
                    'auth_mode': studio_summary.get('AuthMode', ''),
                    'creation_time': str(studio_summary.get('CreationTime', '')),
                    'description': studio_summary.get('Description', ''),
                }

                # Describe for full details
                try:
                    desc = emr.describe_studio(StudioId=studio_id)
                    st = desc.get('Studio', {})
                    details.update({
                        'vpc_id': st.get('VpcId', ''),
                        'subnet_ids': st.get('SubnetIds', []),
                        'service_role': st.get('ServiceRole', ''),
                        'user_role': st.get('UserRole', ''),
                        'workspace_security_group_id': st.get('WorkspaceSecurityGroupId', ''),
                        'engine_security_group_id': st.get('EngineSecurityGroupId', ''),
                        'default_s3_location': st.get('DefaultS3Location', ''),
                        'idp_auth_url': st.get('IdpAuthUrl', ''),
                        'idp_relay_state_parameter_name': st.get('IdpRelayStateParameterName', ''),
                    })
                    tags = st.get('Tags', [])
                except Exception:
                    tags = []

                studio_arn = f"arn:aws:emr:{region}:{account_id}:studio/{studio_id}"
                resources.append(make_resource(
                    service='emr',
                    resource_type='studio',
                    resource_id=studio_id,
                    arn=studio_arn,
                    name=studio_name,
                    region=region,
                    details=details,
                    tags=tags_to_dict(tags),
                ))
            next_token = resp.get('Marker')
            if not next_token:
                break
    except Exception:
        pass

    # ── EMR Serverless Applications ──────────────────────────────────
    try:
        emr_sl = session.client('emr-serverless', region_name=region)
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = emr_sl.list_applications(**kwargs)
            for app_summary in resp.get('applications', []):
                app_id = app_summary.get('id', '')
                app_name = app_summary.get('name', app_id)
                app_arn = app_summary.get('arn', '')
                details = {
                    'state': app_summary.get('state', ''),
                    'type': app_summary.get('type', ''),
                    'release_label': app_summary.get('releaseLabel', ''),
                    'state_details': app_summary.get('stateDetails', ''),
                    'created_at': str(app_summary.get('createdAt', '')),
                    'updated_at': str(app_summary.get('updatedAt', '')),
                    'architecture': app_summary.get('architecture', ''),
                }

                # Tags
                tags_dict = {}
                try:
                    tag_resp = emr_sl.list_tags_for_resource(resourceArn=app_arn)
                    tags_dict = tag_resp.get('tags', {})
                    if isinstance(tags_dict, list):
                        tags_dict = tags_to_dict(tags_dict)
                except Exception:
                    pass

                resources.append(make_resource(
                    service='emr',
                    resource_type='serverless-application',
                    resource_id=app_id,
                    arn=app_arn,
                    name=app_name,
                    region=region,
                    details=details,
                    tags=tags_dict,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
