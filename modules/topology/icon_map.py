"""
Topology — ScanBox resource type → vendored aws-icons SVG path.

Used by the SVG renderer (browser inline preview). Drawio export does NOT
use these — drawio uses its built-in mxgraph.aws4 stencils directly.

Vendor source: https://github.com/MKAbuMattar/aws-icons (MIT, npm aws-icons@3.3.0).
Vendored under: /static/topology/icons/aws-icons/{architecture-group, architecture-service, resource}/*.svg

`icon_for(resource_type)` returns a *URL path* (starts with /static/...) that
the browser can resolve directly when embedded as <image href="...">.
"""

ICON_BASE = '/static/topology/icons/aws-icons'

# Container-level icons (top-left corner of each container).
CONTAINER_ICONS = {
    'region':         f'{ICON_BASE}/architecture-group/Region.svg',
    'vpc':            f'{ICON_BASE}/architecture-group/VirtualprivatecloudVPC.svg',
    'az':             None,   # AZ has no badge in MKAbuMattar set; use text-only label
    'public_subnet':  f'{ICON_BASE}/architecture-group/Publicsubnet.svg',
    'private_subnet': f'{ICON_BASE}/architecture-group/Privatesubnet.svg',
    'aws_cloud':      f'{ICON_BASE}/architecture-group/AWSCloud.svg',
    'aws_account':   f'{ICON_BASE}/architecture-group/AWSAccount.svg',
}

# Resource-level icons. For each ScanBox `type`, the chosen SVG.
# Prefer architecture-service/ (full-color tiles) for primary services; resource/
# (line-art chips) for sub-resources like IGW / NAT / RouteTable that are
# typically drawn at a smaller scale.
RESOURCE_ICONS = {
    # Compute
    'ec2':              f'{ICON_BASE}/architecture-service/AmazonEC2.svg',
    'lambda':           f'{ICON_BASE}/architecture-service/AWSLambda.svg',
    'ecs':              f'{ICON_BASE}/architecture-service/AmazonElasticContainerService.svg',
    'eks':              f'{ICON_BASE}/architecture-service/AmazonElasticKubernetesService.svg',
    # Database
    'rds':              f'{ICON_BASE}/architecture-service/AmazonRDS.svg',
    'dynamodb':         f'{ICON_BASE}/architecture-service/AmazonDynamoDB.svg',
    # Storage
    's3':               f'{ICON_BASE}/architecture-service/AmazonSimpleStorageService.svg',
    'efs':              f'{ICON_BASE}/architecture-service/AmazonEFS.svg',
    # Networking — sub-resources (resource/ folder, line-art)
    'igw':              f'{ICON_BASE}/resource/AmazonVPCInternetGateway.svg',
    'nat':              f'{ICON_BASE}/resource/AmazonVPCNATGateway.svg',
    'route_table':      f'{ICON_BASE}/resource/AmazonRoute53RouteTable.svg',
    'vpc_endpoint':     f'{ICON_BASE}/resource/AmazonVPCEndpoints.svg',
    'eip':              f'{ICON_BASE}/resource/AmazonEC2ElasticIPAddress.svg',
    'nacl':             f'{ICON_BASE}/resource/AmazonVPCNetworkAccessControlList.svg',
    'security_group':   f'{ICON_BASE}/architecture-service/AmazonVirtualPrivateCloud.svg',
    'eni':              f'{ICON_BASE}/resource/AmazonVPCRouter.svg',
    # Networking — service-level
    'transit_gateway':  f'{ICON_BASE}/architecture-service/AWSTransitGateway.svg',
    'direct_connect':   f'{ICON_BASE}/architecture-service/AWSDirectConnect.svg',
    'vpn':              f'{ICON_BASE}/architecture-service/AWSSitetoSiteVPN.svg',
    'cloudfront':       f'{ICON_BASE}/architecture-service/AmazonCloudFront.svg',
    'route53':          f'{ICON_BASE}/architecture-service/AmazonRoute53.svg',
    'elb':              f'{ICON_BASE}/architecture-service/ElasticLoadBalancing.svg',
    'apigateway':       f'{ICON_BASE}/architecture-service/AmazonAPIGateway.svg',
    'network_firewall': f'{ICON_BASE}/architecture-service/AWSNetworkFirewall.svg',
    'peering':          f'{ICON_BASE}/architecture-service/AmazonVirtualPrivateCloud.svg',
    'acm':              f'{ICON_BASE}/architecture-service/AWSCertificateManager.svg',
    'cognito':          f'{ICON_BASE}/architecture-service/AmazonCognito.svg',
}

# Generic fallback (the AWS-Cloud architecture-group icon).
FALLBACK_ICON = f'{ICON_BASE}/architecture-group/AWSCloud.svg'


def icon_for(resource_type: str) -> str:
    """Return the vendored SVG URL path for a ScanBox resource type.

    Always returns a usable path — falls back to the AWS-Cloud icon for unknown
    types so the SVG never has a broken image reference.
    """
    return RESOURCE_ICONS.get(resource_type) or FALLBACK_ICON


def container_icon(kind: str):
    """Return the SVG URL for a container kind, or None if no badge applies."""
    return CONTAINER_ICONS.get(kind)
