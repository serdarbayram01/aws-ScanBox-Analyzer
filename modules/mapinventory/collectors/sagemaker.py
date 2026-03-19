"""
Map Inventory — Amazon SageMaker Collector
Resource types: notebook-instance, endpoint, model, training-job, processing-job
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_sagemaker_resources(session, region, account_id):
    """Collect SageMaker resources."""
    resources = []
    try:
        client = session.client('sagemaker', region_name=region)
    except Exception:
        return resources

    # ── Notebook Instances ────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_notebook_instances(**kwargs)
            for nb in resp.get('NotebookInstances', []):
                nb_name = nb.get('NotebookInstanceName', '')
                nb_arn = nb.get('NotebookInstanceArn', '')

                tags = {}
                try:
                    tag_resp = client.list_tags(ResourceArn=nb_arn)
                    tags = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='sagemaker',
                    resource_type='notebook-instance',
                    resource_id=nb_name,
                    arn=nb_arn,
                    name=nb_name,
                    region=region,
                    details={
                        'instance_type': nb.get('InstanceType', ''),
                        'status': nb.get('NotebookInstanceStatus', ''),
                        'url': nb.get('Url', ''),
                        'creation_time': str(nb.get('CreationTime', '')),
                        'last_modified_time': str(nb.get('LastModifiedTime', '')),
                        'direct_internet_access': nb.get('DirectInternetAccess', ''),
                        'volume_size_gb': nb.get('VolumeSizeInGB', 0),
                    },
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Endpoints ─────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_endpoints(**kwargs)
            for ep in resp.get('Endpoints', []):
                ep_name = ep.get('EndpointName', '')
                ep_arn = ep.get('EndpointArn', '')

                tags = {}
                try:
                    tag_resp = client.list_tags(ResourceArn=ep_arn)
                    tags = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='sagemaker',
                    resource_type='endpoint',
                    resource_id=ep_name,
                    arn=ep_arn,
                    name=ep_name,
                    region=region,
                    details={
                        'status': ep.get('EndpointStatus', ''),
                        'creation_time': str(ep.get('CreationTime', '')),
                        'last_modified_time': str(ep.get('LastModifiedTime', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Models ────────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_models(**kwargs)
            for model in resp.get('Models', []):
                model_name = model.get('ModelName', '')
                model_arn = model.get('ModelArn', '')

                tags = {}
                try:
                    tag_resp = client.list_tags(ResourceArn=model_arn)
                    tags = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='sagemaker',
                    resource_type='model',
                    resource_id=model_name,
                    arn=model_arn,
                    name=model_name,
                    region=region,
                    details={
                        'creation_time': str(model.get('CreationTime', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Training Jobs ─────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_training_jobs(**kwargs)
            for tj in resp.get('TrainingJobSummaries', []):
                tj_name = tj.get('TrainingJobName', '')
                tj_arn = tj.get('TrainingJobArn', '')

                tags = {}
                try:
                    tag_resp = client.list_tags(ResourceArn=tj_arn)
                    tags = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='sagemaker',
                    resource_type='training-job',
                    resource_id=tj_name,
                    arn=tj_arn,
                    name=tj_name,
                    region=region,
                    details={
                        'status': tj.get('TrainingJobStatus', ''),
                        'creation_time': str(tj.get('CreationTime', '')),
                        'training_start_time': str(tj.get('TrainingStartTime', '')),
                        'training_end_time': str(tj.get('TrainingEndTime', '')),
                        'last_modified_time': str(tj.get('LastModifiedTime', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Processing Jobs ───────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_processing_jobs(**kwargs)
            for pj in resp.get('ProcessingJobSummaries', []):
                pj_name = pj.get('ProcessingJobName', '')
                pj_arn = pj.get('ProcessingJobArn', '')

                tags = {}
                try:
                    tag_resp = client.list_tags(ResourceArn=pj_arn)
                    tags = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='sagemaker',
                    resource_type='processing-job',
                    resource_id=pj_name,
                    arn=pj_arn,
                    name=pj_name,
                    region=region,
                    details={
                        'status': pj.get('ProcessingJobStatus', ''),
                        'creation_time': str(pj.get('CreationTime', '')),
                        'processing_end_time': str(pj.get('ProcessingEndTime', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
