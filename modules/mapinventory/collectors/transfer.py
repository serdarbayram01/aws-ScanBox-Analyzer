"""
Map Inventory — AWS Transfer Family Collector
Resource types: server, user, host-key, workflow, connector, certificate, profile, agreement, web-app
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_transfer_resources(session, region, account_id):
    """Collect AWS Transfer Family resources."""
    resources = []
    try:
        client = session.client('transfer', region_name=region)
    except Exception:
        return resources

    # ── Servers ───────────────────────────────────────────────────────
    server_ids = []
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 1000}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_servers(**kwargs)
            for srv in resp.get('Servers', []):
                srv_id = srv.get('ServerId', '')
                server_ids.append(srv_id)
                srv_arn = srv.get('Arn', f"arn:aws:transfer:{region}:{account_id}:server/{srv_id}")
                tags = {}
                try:
                    detail = client.describe_server(ServerId=srv_id)
                    s = detail.get('Server', {})
                    tags = tags_to_dict(s.get('Tags', []))
                    resources.append(make_resource(
                        service='transfer',
                        resource_type='server',
                        resource_id=srv_id,
                        arn=srv_arn,
                        name=srv_id,
                        region=region,
                        details={
                            'state': s.get('State', ''),
                            'protocols': s.get('Protocols', []),
                            'endpoint_type': s.get('EndpointType', ''),
                            'identity_provider_type': s.get('IdentityProviderType', ''),
                            'domain': s.get('Domain', ''),
                            'logging_role': s.get('LoggingRole', ''),
                            'user_count': s.get('UserCount', 0),
                        },
                        tags=tags,
                    ))
                except Exception:
                    resources.append(make_resource(
                        service='transfer',
                        resource_type='server',
                        resource_id=srv_id,
                        arn=srv_arn,
                        name=srv_id,
                        region=region,
                        details={'state': srv.get('State', '')},
                        tags={},
                    ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Users (per server) ────────────────────────────────────────────
    for srv_id in server_ids:
        try:
            next_token = None
            while True:
                kwargs = {'ServerId': srv_id, 'MaxResults': 1000}
                if next_token:
                    kwargs['NextToken'] = next_token
                resp = client.list_users(**kwargs)
                for u in resp.get('Users', []):
                    user_name = u.get('UserName', '')
                    user_arn = u.get('Arn', f"arn:aws:transfer:{region}:{account_id}:user/{srv_id}/{user_name}")
                    resources.append(make_resource(
                        service='transfer',
                        resource_type='user',
                        resource_id=f"{srv_id}/{user_name}",
                        arn=user_arn,
                        name=user_name,
                        region=region,
                        details={
                            'server_id': srv_id,
                            'role': u.get('Role', ''),
                            'home_directory': u.get('HomeDirectory', ''),
                            'home_directory_type': u.get('HomeDirectoryType', ''),
                            'ssh_public_key_count': len(u.get('SshPublicKeys', [])),
                        },
                        tags={},
                    ))
                next_token = resp.get('NextToken')
                if not next_token:
                    break
        except Exception:
            pass

    # ── Host Keys (per server) ────────────────────────────────────────
    for srv_id in server_ids:
        try:
            next_token = None
            while True:
                kwargs = {'ServerId': srv_id, 'MaxResults': 1000}
                if next_token:
                    kwargs['NextToken'] = next_token
                resp = client.list_host_keys(**kwargs)
                for hk in resp.get('HostKeys', []):
                    hk_id = hk.get('HostKeyId', '')
                    hk_arn = hk.get('Arn', f"arn:aws:transfer:{region}:{account_id}:host-key/{srv_id}/{hk_id}")
                    resources.append(make_resource(
                        service='transfer',
                        resource_type='host-key',
                        resource_id=f"{srv_id}/{hk_id}",
                        arn=hk_arn,
                        name=hk_id,
                        region=region,
                        details={
                            'server_id': srv_id,
                            'fingerprint': hk.get('Fingerprint', ''),
                            'type': hk.get('Type', ''),
                            'description': hk.get('Description', ''),
                            'date_imported': str(hk.get('DateImported', '')),
                        },
                        tags={},
                    ))
                next_token = resp.get('NextToken')
                if not next_token:
                    break
        except Exception:
            pass

    # ── Workflows ─────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 1000}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_workflows(**kwargs)
            for wf in resp.get('Workflows', []):
                wf_id = wf.get('WorkflowId', '')
                wf_arn = wf.get('Arn', f"arn:aws:transfer:{region}:{account_id}:workflow/{wf_id}")
                resources.append(make_resource(
                    service='transfer',
                    resource_type='workflow',
                    resource_id=wf_id,
                    arn=wf_arn,
                    name=wf.get('Description', wf_id),
                    region=region,
                    details={
                        'description': wf.get('Description', ''),
                    },
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Connectors ────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 1000}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_connectors(**kwargs)
            for conn in resp.get('Connectors', []):
                conn_id = conn.get('ConnectorId', '')
                conn_arn = conn.get('Arn', f"arn:aws:transfer:{region}:{account_id}:connector/{conn_id}")
                resources.append(make_resource(
                    service='transfer',
                    resource_type='connector',
                    resource_id=conn_id,
                    arn=conn_arn,
                    name=conn_id,
                    region=region,
                    details={
                        'url': conn.get('Url', ''),
                    },
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Certificates ──────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 1000}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_certificates(**kwargs)
            for cert in resp.get('Certificates', []):
                cert_id = cert.get('CertificateId', '')
                cert_arn = cert.get('Arn', f"arn:aws:transfer:{region}:{account_id}:certificate/{cert_id}")
                resources.append(make_resource(
                    service='transfer',
                    resource_type='certificate',
                    resource_id=cert_id,
                    arn=cert_arn,
                    name=cert_id,
                    region=region,
                    details={
                        'status': cert.get('Status', ''),
                        'usage': cert.get('Usage', ''),
                        'type': cert.get('Type', ''),
                        'active_date': str(cert.get('ActiveDate', '')),
                        'inactive_date': str(cert.get('InactiveDate', '')),
                    },
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Profiles ──────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 1000}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_profiles(**kwargs)
            for prof in resp.get('Profiles', []):
                prof_id = prof.get('ProfileId', '')
                prof_arn = prof.get('Arn', f"arn:aws:transfer:{region}:{account_id}:profile/{prof_id}")
                resources.append(make_resource(
                    service='transfer',
                    resource_type='profile',
                    resource_id=prof_id,
                    arn=prof_arn,
                    name=prof_id,
                    region=region,
                    details={
                        'profile_type': prof.get('ProfileType', ''),
                        'as2_id': prof.get('As2Id', ''),
                    },
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Agreements (per server) ───────────────────────────────────────
    for srv_id in server_ids:
        try:
            next_token = None
            while True:
                kwargs = {'ServerId': srv_id, 'MaxResults': 1000}
                if next_token:
                    kwargs['NextToken'] = next_token
                resp = client.list_agreements(**kwargs)
                for agr in resp.get('Agreements', []):
                    agr_id = agr.get('AgreementId', '')
                    agr_arn = agr.get('Arn', f"arn:aws:transfer:{region}:{account_id}:agreement/{srv_id}/{agr_id}")
                    resources.append(make_resource(
                        service='transfer',
                        resource_type='agreement',
                        resource_id=f"{srv_id}/{agr_id}",
                        arn=agr_arn,
                        name=agr_id,
                        region=region,
                        details={
                            'server_id': srv_id,
                            'status': agr.get('Status', ''),
                            'description': agr.get('Description', ''),
                        },
                        tags={},
                    ))
                next_token = resp.get('NextToken')
                if not next_token:
                    break
        except Exception:
            pass

    # ── Web Apps ──────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 1000}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_web_apps(**kwargs)
            for app in resp.get('WebApps', []):
                app_id = app.get('WebAppId', '')
                app_arn = app.get('Arn', f"arn:aws:transfer:{region}:{account_id}:web-app/{app_id}")
                resources.append(make_resource(
                    service='transfer',
                    resource_type='web-app',
                    resource_id=app_id,
                    arn=app_arn,
                    name=app_id,
                    region=region,
                    details={},
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
