"""
Map Inventory — Amazon Bedrock Collector
Resource types: custom-model, provisioned-model-throughput, guardrail, model-customization-job
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_bedrock_resources(session, region, account_id):
    """Collect Amazon Bedrock resources."""
    resources = []
    try:
        client = session.client('bedrock', region_name=region)
    except Exception:
        return resources

    # ── Custom Models ─────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'maxResults': 100}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_custom_models(**kwargs)
            for model in resp.get('modelSummaries', []):
                model_name = model.get('modelName', '')
                model_arn = model.get('modelArn', '')

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(resourceARN=model_arn)
                    tags = {t['key']: t['value'] for t in tag_resp.get('tags', []) if 'key' in t}
                except Exception:
                    pass

                resources.append(make_resource(
                    service='bedrock',
                    resource_type='custom-model',
                    resource_id=model_name,
                    arn=model_arn,
                    name=model_name,
                    region=region,
                    details={
                        'base_model_arn': model.get('baseModelArn', ''),
                        'base_model_name': model.get('baseModelName', ''),
                        'creation_time': str(model.get('creationTime', '')),
                        'customization_type': model.get('customizationType', ''),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Provisioned Model Throughputs ─────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'maxResults': 100}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_provisioned_model_throughputs(**kwargs)
            for pmt in resp.get('provisionedModelSummaries', []):
                pmt_name = pmt.get('provisionedModelName', '')
                pmt_arn = pmt.get('provisionedModelArn', '')

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(resourceARN=pmt_arn)
                    tags = {t['key']: t['value'] for t in tag_resp.get('tags', []) if 'key' in t}
                except Exception:
                    pass

                resources.append(make_resource(
                    service='bedrock',
                    resource_type='provisioned-model-throughput',
                    resource_id=pmt_name,
                    arn=pmt_arn,
                    name=pmt_name,
                    region=region,
                    details={
                        'model_arn': pmt.get('modelArn', ''),
                        'desired_model_arn': pmt.get('desiredModelArn', ''),
                        'status': pmt.get('status', ''),
                        'commitment_duration': pmt.get('commitmentDuration', ''),
                        'commitment_expiration_time': str(pmt.get('commitmentExpirationTime', '')),
                        'model_units': pmt.get('modelUnits', 0),
                        'desired_model_units': pmt.get('desiredModelUnits', 0),
                        'creation_time': str(pmt.get('creationTime', '')),
                        'last_modified_time': str(pmt.get('lastModifiedTime', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Guardrails ────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'maxResults': 100}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_guardrails(**kwargs)
            for gr in resp.get('guardrails', []):
                gr_id = gr.get('id', '')
                gr_name = gr.get('name', gr_id)
                gr_arn = gr.get('arn', f"arn:aws:bedrock:{region}:{account_id}:guardrail/{gr_id}")

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(resourceARN=gr_arn)
                    tags = {t['key']: t['value'] for t in tag_resp.get('tags', []) if 'key' in t}
                except Exception:
                    pass

                resources.append(make_resource(
                    service='bedrock',
                    resource_type='guardrail',
                    resource_id=gr_id,
                    arn=gr_arn,
                    name=gr_name,
                    region=region,
                    details={
                        'version': gr.get('version', ''),
                        'status': gr.get('status', ''),
                        'description': gr.get('description', ''),
                        'created_at': str(gr.get('createdAt', '')),
                        'updated_at': str(gr.get('updatedAt', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Model Customization Jobs ──────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'maxResults': 100}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_model_customization_jobs(**kwargs)
            for job in resp.get('modelCustomizationJobSummaries', []):
                job_name = job.get('jobName', '')
                job_arn = job.get('jobArn', '')

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(resourceARN=job_arn)
                    tags = {t['key']: t['value'] for t in tag_resp.get('tags', []) if 'key' in t}
                except Exception:
                    pass

                resources.append(make_resource(
                    service='bedrock',
                    resource_type='model-customization-job',
                    resource_id=job_name,
                    arn=job_arn,
                    name=job_name,
                    region=region,
                    details={
                        'status': job.get('status', ''),
                        'base_model_identifier': job.get('baseModelIdentifier', ''),
                        'custom_model_name': job.get('customModelName', ''),
                        'customization_type': job.get('customizationType', ''),
                        'creation_time': str(job.get('creationTime', '')),
                        'end_time': str(job.get('endTime', '')),
                        'last_modified_time': str(job.get('lastModifiedTime', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
