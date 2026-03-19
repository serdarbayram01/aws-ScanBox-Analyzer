"""
Map Inventory — SES v2 Collector
Resource types: email-identity, configuration-set, contact-list,
                email-template, dedicated-ip-pool
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_sesv2_resources(session, region, account_id):
    """Collect SES v2 resources for a given region."""
    resources = []
    try:
        client = session.client('sesv2', region_name=region)
    except Exception:
        return resources

    # ── Email Identities ──────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'PageSize': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_email_identities(**kwargs)
            for ident in resp.get('EmailIdentities', []):
                ident_name = ident.get('IdentityName', '')
                ident_type = ident.get('IdentityType', '')
                arn = f"arn:aws:ses:{region}:{account_id}:identity/{ident_name}"

                details_dict = {
                    'identity_type': ident_type,
                    'sending_enabled': ident.get('SendingEnabled', False),
                    'verification_status': ident.get('VerificationStatus', ''),
                }
                tags = {}

                try:
                    detail = client.get_email_identity(EmailIdentity=ident_name)
                    dkim = detail.get('DkimAttributes', {})
                    details_dict.update({
                        'dkim_signing_enabled': dkim.get('SigningEnabled', False),
                        'dkim_status': dkim.get('Status', ''),
                        'dkim_signing_attributes_origin': dkim.get('SigningAttributesOrigin', ''),
                        'mail_from_domain': detail.get('MailFromAttributes', {}).get('MailFromDomain', ''),
                        'mail_from_status': detail.get('MailFromAttributes', {}).get('MailFromDomainStatus', ''),
                        'feedback_forwarding_status': detail.get('FeedbackForwardingStatus', False),
                        'configuration_set_name': detail.get('ConfigurationSetName', ''),
                    })
                    tag_list = detail.get('Tags', [])
                    tags = tags_to_dict(tag_list)
                except Exception:
                    pass

                resources.append(make_resource(
                    service='sesv2',
                    resource_type='email-identity',
                    resource_id=ident_name,
                    arn=arn,
                    name=ident_name,
                    region=region,
                    details=details_dict,
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Configuration Sets ────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'PageSize': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_configuration_sets(**kwargs)
            for cs_name in resp.get('ConfigurationSets', []):
                arn = f"arn:aws:ses:{region}:{account_id}:configuration-set/{cs_name}"

                details_dict = {}
                tags = {}
                try:
                    detail = client.get_configuration_set(ConfigurationSetName=cs_name)
                    sending = detail.get('SendingOptions', {})
                    tracking = detail.get('TrackingOptions', {})
                    reputation = detail.get('ReputationOptions', {})
                    suppression = detail.get('SuppressionOptions', {})
                    details_dict = {
                        'sending_enabled': sending.get('SendingEnabled', False),
                        'custom_redirect_domain': tracking.get('CustomRedirectDomain', ''),
                        'reputation_metrics_enabled': reputation.get('ReputationMetricsEnabled', False),
                        'suppressed_reasons': suppression.get('SuppressedReasons', []),
                    }
                    tag_list = detail.get('Tags', [])
                    tags = tags_to_dict(tag_list)
                except Exception:
                    pass

                resources.append(make_resource(
                    service='sesv2',
                    resource_type='configuration-set',
                    resource_id=cs_name,
                    arn=arn,
                    name=cs_name,
                    region=region,
                    details=details_dict,
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Contact Lists ─────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'PageSize': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_contact_lists(**kwargs)
            for cl in resp.get('ContactLists', []):
                cl_name = cl.get('ContactListName', '')
                arn = f"arn:aws:ses:{region}:{account_id}:contact-list/{cl_name}"

                details_dict = {
                    'last_updated_timestamp': str(cl.get('LastUpdatedTimestamp', '')),
                }
                tags = {}
                try:
                    detail = client.get_contact_list(ContactListName=cl_name)
                    details_dict.update({
                        'description': detail.get('Description', ''),
                        'topics': [
                            {
                                'name': t.get('TopicName', ''),
                                'display_name': t.get('DisplayName', ''),
                                'default_subscription_status': t.get('DefaultSubscriptionStatus', ''),
                            }
                            for t in detail.get('Topics', [])
                        ],
                        'created_timestamp': str(detail.get('CreatedTimestamp', '')),
                    })
                    tag_list = detail.get('Tags', [])
                    tags = tags_to_dict(tag_list)
                except Exception:
                    pass

                resources.append(make_resource(
                    service='sesv2',
                    resource_type='contact-list',
                    resource_id=cl_name,
                    arn=arn,
                    name=cl_name,
                    region=region,
                    details=details_dict,
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Email Templates ───────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'PageSize': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_email_templates(**kwargs)
            for tmpl in resp.get('TemplatesMetadata', []):
                tmpl_name = tmpl.get('TemplateName', '')
                arn = f"arn:aws:ses:{region}:{account_id}:template/{tmpl_name}"

                resources.append(make_resource(
                    service='sesv2',
                    resource_type='email-template',
                    resource_id=tmpl_name,
                    arn=arn,
                    name=tmpl_name,
                    region=region,
                    details={
                        'created_timestamp': str(tmpl.get('CreatedTimestamp', '')),
                    },
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Dedicated IP Pools ────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'PageSize': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_dedicated_ip_pools(**kwargs)
            for pool_name in resp.get('DedicatedIpPools', []):
                arn = f"arn:aws:ses:{region}:{account_id}:dedicated-ip-pool/{pool_name}"

                details_dict = {}
                try:
                    ips = client.get_dedicated_ips(PoolName=pool_name)
                    ip_list = ips.get('DedicatedIps', [])
                    details_dict = {
                        'dedicated_ip_count': len(ip_list),
                        'ips': [
                            {
                                'ip': ip.get('Ip', ''),
                                'warmup_status': ip.get('WarmupStatus', ''),
                                'warmup_percentage': ip.get('WarmupPercentage', 0),
                            }
                            for ip in ip_list[:10]  # Limit to first 10 for brevity
                        ],
                    }
                except Exception:
                    pass

                resources.append(make_resource(
                    service='sesv2',
                    resource_type='dedicated-ip-pool',
                    resource_id=pool_name,
                    arn=arn,
                    name=pool_name,
                    region=region,
                    details=details_dict,
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
