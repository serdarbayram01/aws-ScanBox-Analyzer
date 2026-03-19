"""
Map Inventory — Amazon AppFlow Collector
Resource types: flow, connector-profile
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_appflow_resources(session, region, account_id):
    """Collect Amazon AppFlow resources in the given region."""
    resources = []
    try:
        client = session.client('appflow', region_name=region)
    except Exception:
        return resources

    # ── Flows ────────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_flows(**kwargs)
            for flow in resp.get('flows', []):
                flow_name = flow.get('flowName', '')
                flow_arn = flow.get('flowArn', '')
                flow_status = flow.get('flowStatus', '')
                source_type = flow.get('sourceConnectorType', '')
                dest_type = flow.get('destinationConnectorType', '')
                trigger_type = flow.get('triggerType', '')
                created = str(flow.get('createdAt', ''))

                tags = flow.get('tags', {})

                resources.append(make_resource(
                    service='appflow',
                    resource_type='flow',
                    resource_id=flow_name,
                    arn=flow_arn,
                    name=flow_name,
                    region=region,
                    details={
                        'status': flow_status,
                        'source_connector_type': source_type,
                        'destination_connector_type': dest_type,
                        'trigger_type': trigger_type,
                        'description': flow.get('description', ''),
                        'created_at': created,
                        'last_updated_at': str(flow.get('lastUpdatedAt', '')),
                        'last_run_execution_details': flow.get('lastRunExecutionDetails', {}),
                        'source_connector_label': flow.get('sourceConnectorLabel', ''),
                        'destination_connector_label': flow.get('destinationConnectorLabel', ''),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Connector Profiles ───────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.describe_connector_profiles(**kwargs)
            for profile in resp.get('connectorProfileDetails', []):
                profile_name = profile.get('connectorProfileName', '')
                profile_arn = profile.get('connectorProfileArn', '')
                connector_type = profile.get('connectorType', '')
                connector_label = profile.get('connectorLabel', '')
                created = str(profile.get('createdAt', ''))

                resources.append(make_resource(
                    service='appflow',
                    resource_type='connector-profile',
                    resource_id=profile_name,
                    arn=profile_arn,
                    name=profile_name,
                    region=region,
                    details={
                        'connector_type': connector_type,
                        'connector_label': connector_label,
                        'connection_mode': profile.get('connectionMode', ''),
                        'credentials_arn': profile.get('credentialsArn', ''),
                        'created_at': created,
                        'last_updated_at': str(profile.get('lastUpdatedAt', '')),
                    },
                    tags={},
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
