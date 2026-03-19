"""
Map Inventory — AWS AppConfig Collector
Resource types: application, environment, configuration-profile
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_appconfig_resources(session, region, account_id):
    """Collect AWS AppConfig resources in the given region."""
    resources = []
    try:
        client = session.client('appconfig', region_name=region)
    except Exception:
        return resources

    # ── Applications ─────────────────────────────────────────────────
    app_list = []
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_applications(**kwargs)
            items = resp.get('Items', [])
            app_list.extend(items)
            next_token = resp.get('NextToken')
            if not next_token:
                break

        for app in app_list:
            app_id = app.get('Id', '')
            app_name = app.get('Name', app_id)
            arn = f"arn:aws:appconfig:{region}:{account_id}:application/{app_id}"

            # Get tags
            tags = {}
            try:
                tag_resp = client.list_tags_for_resource(ResourceArn=arn)
                tags = tag_resp.get('Tags', {})
            except Exception:
                pass

            resources.append(make_resource(
                service='appconfig',
                resource_type='application',
                resource_id=app_id,
                arn=arn,
                name=app_name,
                region=region,
                details={
                    'description': app.get('Description', ''),
                },
                tags=tags,
            ))

            # ── Environments per Application ─────────────────────────
            try:
                env_next = None
                while True:
                    env_kwargs = {'ApplicationId': app_id}
                    if env_next:
                        env_kwargs['NextToken'] = env_next
                    env_resp = client.list_environments(**env_kwargs)
                    for env in env_resp.get('Items', []):
                        env_id = env.get('Id', '')
                        env_name = env.get('Name', env_id)
                        env_arn = f"arn:aws:appconfig:{region}:{account_id}:application/{app_id}/environment/{env_id}"

                        env_tags = {}
                        try:
                            et_resp = client.list_tags_for_resource(ResourceArn=env_arn)
                            env_tags = et_resp.get('Tags', {})
                        except Exception:
                            pass

                        resources.append(make_resource(
                            service='appconfig',
                            resource_type='environment',
                            resource_id=f"{app_id}/{env_id}",
                            arn=env_arn,
                            name=env_name,
                            region=region,
                            details={
                                'application_id': app_id,
                                'application_name': app_name,
                                'description': env.get('Description', ''),
                                'state': env.get('State', ''),
                            },
                            tags=env_tags,
                        ))
                    env_next = env_resp.get('NextToken')
                    if not env_next:
                        break
            except Exception:
                pass

            # ── Configuration Profiles per Application ───────────────
            try:
                cp_next = None
                while True:
                    cp_kwargs = {'ApplicationId': app_id}
                    if cp_next:
                        cp_kwargs['NextToken'] = cp_next
                    cp_resp = client.list_configuration_profiles(**cp_kwargs)
                    for profile in cp_resp.get('Items', []):
                        profile_id = profile.get('Id', '')
                        profile_name = profile.get('Name', profile_id)
                        profile_arn = f"arn:aws:appconfig:{region}:{account_id}:application/{app_id}/configurationprofile/{profile_id}"

                        cp_tags = {}
                        try:
                            ct_resp = client.list_tags_for_resource(ResourceArn=profile_arn)
                            cp_tags = ct_resp.get('Tags', {})
                        except Exception:
                            pass

                        resources.append(make_resource(
                            service='appconfig',
                            resource_type='configuration-profile',
                            resource_id=f"{app_id}/{profile_id}",
                            arn=profile_arn,
                            name=profile_name,
                            region=region,
                            details={
                                'application_id': app_id,
                                'application_name': app_name,
                                'description': profile.get('Description', ''),
                                'location_uri': profile.get('LocationUri', ''),
                                'type': profile.get('Type', ''),
                            },
                            tags=cp_tags,
                        ))
                    cp_next = cp_resp.get('NextToken')
                    if not cp_next:
                        break
            except Exception:
                pass
    except Exception:
        pass

    return resources
