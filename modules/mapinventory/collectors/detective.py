"""
Map Inventory — Detective Collector
Resource types: graph
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_detective_resources(session, region, account_id):
    """Collect Amazon Detective resources in the given region."""
    resources = []
    try:
        client = session.client('detective', region_name=region)
    except Exception:
        return resources

    # ── Behavior Graphs ──────────────────────────────────────────────
    try:
        graphs = []
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_graphs(**kwargs)
            graphs.extend(resp.get('GraphList', []))
            next_token = resp.get('NextToken')
            if not next_token:
                break

        for graph in graphs:
            graph_arn = graph.get('Arn', '')
            created = str(graph.get('CreatedTime', ''))
            # Graph ARN is the identifier
            graph_id = graph_arn.rsplit('/', 1)[-1] if '/' in graph_arn else graph_arn

            # Get tags for the graph
            tags = {}
            try:
                tag_resp = client.list_tags_for_resource(ResourceArn=graph_arn)
                tags = tag_resp.get('Tags', {})
            except Exception:
                pass

            resources.append(make_resource(
                service='detective',
                resource_type='graph',
                resource_id=graph_id,
                arn=graph_arn,
                name=graph_id,
                region=region,
                details={
                    'created_time': created,
                },
                tags=tags,
            ))
    except Exception:
        pass

    return resources
