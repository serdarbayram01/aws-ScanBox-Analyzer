"""
Topology — drawio (mxGraph) shape style mapping.

Maps ScanBox resource types (the `type` field on scan-result entries) to
drawio's `mxgraph.aws4` stencil style snippets. The output of these snippets
goes verbatim into the `style="..."` attribute of <mxCell> elements; when the
generated .drawio file is opened in https://app.diagrams.net/, drawio renders
each cell with its native AWS Architecture v4 icon.

References:
- mxgraph.aws4 stencils: https://github.com/jgraph/drawio-libs/tree/master/aws4
- drawio-mcp-server output vocabulary
"""

# ------------------------------------------------------------------ Containers

# Region — outer container.
REGION_STYLE = (
    'points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],'
    '[1,1],[0.75,1],[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];'
    'outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;'
    'fontStyle=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;'
    'shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_region;'
    'strokeColor=#00A4A6;fillColor=none;verticalAlign=top;align=left;'
    'spacingLeft=30;fontColor=#147EBA;dashed=1;'
)

# VPC — second-level container, inside region.
VPC_STYLE = (
    'points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],'
    '[1,1],[0.75,1],[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];'
    'outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;'
    'fontStyle=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;'
    'shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_vpc;'
    'strokeColor=#248814;fillColor=none;verticalAlign=top;align=left;'
    'spacingLeft=30;fontColor=#248814;'
)

# Availability Zone — third-level container, inside VPC.
AZ_STYLE = (
    'points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],'
    '[1,1],[0.75,1],[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];'
    'outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;'
    'fontStyle=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;'
    'shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_availability_zone;'
    'strokeColor=#147EBA;fillColor=none;verticalAlign=top;align=left;'
    'spacingLeft=30;fontColor=#147EBA;dashed=1;'
)

# --- Tier-based subnet container styles ----
# Web/Edge (public) — green
SUBNET_WEB_STYLE = (
    'points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],'
    '[1,1],[0.75,1],[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];'
    'outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=11;'
    'fontStyle=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;'
    'shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_security_group;'
    'grStroke=0;strokeColor=#7AA116;fillColor=#E9F3E6;verticalAlign=top;'
    'align=left;spacingLeft=15;fontColor=#248814;'
)
# App / Compute / EKS — blue
SUBNET_APP_STYLE = (
    'points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],'
    '[1,1],[0.75,1],[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];'
    'outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=11;'
    'fontStyle=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;'
    'shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_security_group;'
    'grStroke=0;strokeColor=#147EBA;fillColor=#E6F2F8;verticalAlign=top;'
    'align=left;spacingLeft=15;fontColor=#147EBA;'
)
# Data tier (RDS / ElastiCache subnet group) — dark blue (matches RDS color)
SUBNET_DATA_STYLE = (
    'points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],'
    '[1,1],[0.75,1],[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];'
    'outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=11;'
    'fontStyle=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;'
    'shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_security_group;'
    'grStroke=0;strokeColor=#3334B9;fillColor=#E6E6F2;verticalAlign=top;'
    'align=left;spacingLeft=15;fontColor=#3334B9;'
)
# Management / bastion — orange
SUBNET_MGMT_STYLE = (
    'points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],'
    '[1,1],[0.75,1],[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];'
    'outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=11;'
    'fontStyle=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;'
    'shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_security_group;'
    'grStroke=0;strokeColor=#ED7100;fillColor=#FBE9D9;verticalAlign=top;'
    'align=left;spacingLeft=15;fontColor=#ED7100;'
)

# Backwards-compat aliases (existing callers).
PUBLIC_SUBNET_STYLE  = SUBNET_WEB_STYLE
PRIVATE_SUBNET_STYLE = SUBNET_APP_STYLE

# ------------------------------------------------------------------ Resources

# Common base for resourceIcon shapes.
_RES_BASE = (
    'sketch=0;points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],'
    '[0,1,0],[0.25,1,0],[0.5,1,0],[0.75,1,0],[1,1,0],'
    '[0,0.25,0],[0,0.5,0],[0,0.75,0],[1,0.25,0],[1,0.5,0],[1,0.75,0]];'
    'outlineConnect=0;fontColor=#232F3E;gradientColor=none;dashed=0;'
    'verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;'
    'fontSize=12;fontStyle=0;aspect=fixed;'
    'shape=mxgraph.aws4.resourceIcon;'
)

# AWS Compute orange.
_COMPUTE_FILL = '#ED7100'
# AWS Database blue.
_DB_FILL = '#3334B9'
# AWS Storage green.
_STORAGE_FILL = '#7AA116'
# AWS Networking purple (VPC, RouteTable, IGW, NAT, ELB, ...).
_NETWORK_FILL = '#8C4FFF'
# AWS Security red.
_SECURITY_FILL = '#DD344C'
# AWS Management/governance pink.
_MGMT_FILL = '#E7157B'
# AWS App-integration pink.
_APP_FILL = '#E7157B'

# (resIcon, fill_color) per resource type.
_RES_MAP = {
    # Compute
    'ec2':              ('mxgraph.aws4.ec2',                              _COMPUTE_FILL),
    'lambda':           ('mxgraph.aws4.lambda',                           _COMPUTE_FILL),
    'ecs':              ('mxgraph.aws4.elastic_container_service',        _COMPUTE_FILL),
    'eks':              ('mxgraph.aws4.elastic_kubernetes_service',       _COMPUTE_FILL),
    # Database
    'rds':              ('mxgraph.aws4.rds',                              _DB_FILL),
    'dynamodb':         ('mxgraph.aws4.dynamodb',                         _DB_FILL),
    # Storage
    's3':               ('mxgraph.aws4.s3',                               _STORAGE_FILL),
    'efs':              ('mxgraph.aws4.elastic_file_system',              _STORAGE_FILL),
    # Networking
    'igw':              ('mxgraph.aws4.internet_gateway',                 _NETWORK_FILL),
    'nat':              ('mxgraph.aws4.nat_gateway',                      _NETWORK_FILL),
    'route_table':      ('mxgraph.aws4.route_table',                      _NETWORK_FILL),
    'vpc_endpoint':     ('mxgraph.aws4.endpoints',                        _NETWORK_FILL),
    'eip':              ('mxgraph.aws4.elastic_ip_address',               _NETWORK_FILL),
    'transit_gateway':  ('mxgraph.aws4.transit_gateway',                  _NETWORK_FILL),
    'direct_connect':   ('mxgraph.aws4.direct_connect',                   _NETWORK_FILL),
    'vpn':              ('mxgraph.aws4.client_vpn',                       _NETWORK_FILL),
    'cloudfront':       ('mxgraph.aws4.cloudfront',                       _NETWORK_FILL),
    'route53':          ('mxgraph.aws4.route_53',                         _NETWORK_FILL),
    'elb':              ('mxgraph.aws4.elastic_load_balancing',           _NETWORK_FILL),
    'apigateway':       ('mxgraph.aws4.api_gateway',                      _APP_FILL),
    'network_firewall': ('mxgraph.aws4.network_firewall',                 _SECURITY_FILL),
    'peering':          ('mxgraph.aws4.peering_connection',               _NETWORK_FILL),
    # Security
    'security_group':   ('mxgraph.aws4.identity_and_access_management_iam', _SECURITY_FILL),
    'nacl':             ('mxgraph.aws4.network_access_analyzer',          _SECURITY_FILL),
    'acm':              ('mxgraph.aws4.certificate_manager',              _SECURITY_FILL),
}


def style_for(resource_type: str) -> str:
    """Return a complete drawio style string for a ScanBox resource type.

    Falls back to a neutral grey "Generic" resource icon when the type isn't mapped.
    """
    res = _RES_MAP.get(resource_type)
    if res is None:
        # Generic fallback — uses the "AWS Cloud" mark.
        return _RES_BASE + 'resIcon=mxgraph.aws4.cloud;fillColor=#232F3E;strokeColor=#232F3E;'
    res_icon, fill = res
    return _RES_BASE + f'resIcon={res_icon};fillColor={fill};strokeColor={fill};'


# ------------------------------------------------------------------ Convenience

CONTAINER_STYLES = {
    'region':         REGION_STYLE,
    'vpc':            VPC_STYLE,
    'az':             AZ_STYLE,
    'public_subnet':  PUBLIC_SUBNET_STYLE,
    'private_subnet': PRIVATE_SUBNET_STYLE,
    # Tier-based aliases
    'subnet_web':     SUBNET_WEB_STYLE,
    'subnet_app':     SUBNET_APP_STYLE,
    'subnet_data':    SUBNET_DATA_STYLE,
    'subnet_mgmt':    SUBNET_MGMT_STYLE,
}


def style_for_tier(tier: str) -> str:
    """Look up the subnet container style for a tier name."""
    return CONTAINER_STYLES.get('subnet_' + tier, SUBNET_APP_STYLE)


def style_with_opacity(base_style: str, opacity_pct: int) -> str:
    """Append `opacity=<n>` to a drawio style string (used for stopped EC2)."""
    if opacity_pct >= 100:
        return base_style
    return base_style + f';opacity={opacity_pct};'

# Resource sizes used both by the drawio renderer (mxGeometry) and the SVG
# renderer (so the two stay visually consistent).
RESOURCE_BOX = (78, 78)
