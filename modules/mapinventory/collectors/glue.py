"""
Map Inventory — Glue Collector
Resource types: database, table, job, crawler, connection, registry
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_glue_resources(session, region, account_id):
    """Collect all Glue resource types in the given region."""
    resources = []
    try:
        glue = session.client('glue', region_name=region)
    except Exception:
        return resources

    # ── Databases & Tables ───────────────────────────────────────────
    try:
        db_paginator = glue.get_paginator('get_databases')
        for db_page in db_paginator.paginate():
            for db in db_page.get('DatabaseList', []):
                db_name = db.get('Name', '')
                db_arn = f"arn:aws:glue:{region}:{account_id}:database/{db_name}"
                resources.append(make_resource(
                    service='glue',
                    resource_type='database',
                    resource_id=db_name,
                    arn=db_arn,
                    name=db_name,
                    region=region,
                    details={
                        'description': db.get('Description', ''),
                        'location_uri': db.get('LocationUri', ''),
                        'catalog_id': db.get('CatalogId', ''),
                        'create_time': str(db.get('CreateTime', '')),
                    },
                    tags={},
                ))

                # Tables in this database
                try:
                    tbl_paginator = glue.get_paginator('get_tables')
                    for tbl_page in tbl_paginator.paginate(DatabaseName=db_name):
                        for tbl in tbl_page.get('TableList', []):
                            tbl_name = tbl.get('Name', '')
                            tbl_arn = f"arn:aws:glue:{region}:{account_id}:table/{db_name}/{tbl_name}"
                            storage = tbl.get('StorageDescriptor', {})
                            resources.append(make_resource(
                                service='glue',
                                resource_type='table',
                                resource_id=f"{db_name}/{tbl_name}",
                                arn=tbl_arn,
                                name=tbl_name,
                                region=region,
                                details={
                                    'database_name': db_name,
                                    'description': tbl.get('Description', ''),
                                    'table_type': tbl.get('TableType', ''),
                                    'owner': tbl.get('Owner', ''),
                                    'location': storage.get('Location', ''),
                                    'input_format': storage.get('InputFormat', ''),
                                    'output_format': storage.get('OutputFormat', ''),
                                    'columns_count': len(storage.get('Columns', [])),
                                    'partition_keys': [p.get('Name', '') for p in tbl.get('PartitionKeys', [])],
                                    'create_time': str(tbl.get('CreateTime', '')),
                                    'update_time': str(tbl.get('UpdateTime', '')),
                                    'catalog_id': tbl.get('CatalogId', ''),
                                },
                                tags={},
                            ))
                except Exception:
                    pass
    except Exception:
        pass

    # ── Jobs ─────────────────────────────────────────────────────────
    try:
        job_paginator = glue.get_paginator('get_jobs')
        for page in job_paginator.paginate():
            for job in page.get('Jobs', []):
                job_name = job.get('Name', '')
                job_arn = f"arn:aws:glue:{region}:{account_id}:job/{job_name}"
                tags_dict = {}
                try:
                    tag_resp = glue.get_tags(ResourceArn=job_arn)
                    tags_dict = tag_resp.get('Tags', {})
                    if isinstance(tags_dict, list):
                        tags_dict = tags_to_dict(tags_dict)
                except Exception:
                    pass
                resources.append(make_resource(
                    service='glue',
                    resource_type='job',
                    resource_id=job_name,
                    arn=job_arn,
                    name=job_name,
                    region=region,
                    details={
                        'description': job.get('Description', ''),
                        'role': job.get('Role', ''),
                        'glue_version': job.get('GlueVersion', ''),
                        'command_name': job.get('Command', {}).get('Name', ''),
                        'command_script_location': job.get('Command', {}).get('ScriptLocation', ''),
                        'max_retries': job.get('MaxRetries', 0),
                        'timeout': job.get('Timeout', ''),
                        'max_capacity': job.get('MaxCapacity', ''),
                        'number_of_workers': job.get('NumberOfWorkers', ''),
                        'worker_type': job.get('WorkerType', ''),
                        'execution_class': job.get('ExecutionClass', ''),
                        'created_on': str(job.get('CreatedOn', '')),
                        'last_modified_on': str(job.get('LastModifiedOn', '')),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # ── Crawlers ─────────────────────────────────────────────────────
    try:
        crawler_paginator = glue.get_paginator('get_crawlers')
        for page in crawler_paginator.paginate():
            for crawler in page.get('Crawlers', []):
                crawler_name = crawler.get('Name', '')
                crawler_arn = f"arn:aws:glue:{region}:{account_id}:crawler/{crawler_name}"
                resources.append(make_resource(
                    service='glue',
                    resource_type='crawler',
                    resource_id=crawler_name,
                    arn=crawler_arn,
                    name=crawler_name,
                    region=region,
                    details={
                        'role': crawler.get('Role', ''),
                        'database_name': crawler.get('DatabaseName', ''),
                        'description': crawler.get('Description', ''),
                        'state': crawler.get('State', ''),
                        'table_prefix': crawler.get('TablePrefix', ''),
                        'schedule': crawler.get('Schedule', {}).get('ScheduleExpression', ''),
                        'classifiers': crawler.get('Classifiers', []),
                        'targets_s3': len(crawler.get('Targets', {}).get('S3Targets', [])),
                        'targets_jdbc': len(crawler.get('Targets', {}).get('JdbcTargets', [])),
                        'targets_catalog': len(crawler.get('Targets', {}).get('CatalogTargets', [])),
                        'creation_time': str(crawler.get('CreationTime', '')),
                        'last_updated': str(crawler.get('LastUpdated', '')),
                        'last_crawl_status': crawler.get('LastCrawl', {}).get('Status', ''),
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── Connections ──────────────────────────────────────────────────
    try:
        conn_paginator = glue.get_paginator('get_connections')
        for page in conn_paginator.paginate():
            for conn in page.get('ConnectionList', []):
                conn_name = conn.get('Name', '')
                conn_arn = f"arn:aws:glue:{region}:{account_id}:connection/{conn_name}"
                physical = conn.get('PhysicalConnectionRequirements', {})
                resources.append(make_resource(
                    service='glue',
                    resource_type='connection',
                    resource_id=conn_name,
                    arn=conn_arn,
                    name=conn_name,
                    region=region,
                    details={
                        'connection_type': conn.get('ConnectionType', ''),
                        'description': conn.get('Description', ''),
                        'creation_time': str(conn.get('CreationTime', '')),
                        'last_updated_time': str(conn.get('LastUpdatedTime', '')),
                        'subnet_id': physical.get('SubnetId', ''),
                        'security_group_ids': physical.get('SecurityGroupIdList', []),
                        'availability_zone': physical.get('AvailabilityZone', ''),
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── Registries ───────────────────────────────────────────────────
    try:
        reg_paginator = glue.get_paginator('list_registries')
        for page in reg_paginator.paginate():
            for reg in page.get('Registries', []):
                reg_name = reg.get('RegistryName', '')
                reg_arn = reg.get('RegistryArn', '')
                resources.append(make_resource(
                    service='glue',
                    resource_type='registry',
                    resource_id=reg_name,
                    arn=reg_arn,
                    name=reg_name,
                    region=region,
                    details={
                        'status': reg.get('Status', ''),
                        'description': reg.get('Description', ''),
                        'created_time': str(reg.get('CreatedTime', '')),
                        'updated_time': str(reg.get('UpdatedTime', '')),
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
