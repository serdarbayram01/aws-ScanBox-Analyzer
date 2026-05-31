"""
Topology — AWS Architecture Reference View renderer.

One hierarchical model, two output formats:

    scan_results/{profile}.json (existing cache)
        → build_hierarchy(scan, vpc_id) → Region tree
            → to_drawio(root)             → mxGraphModel XML  (.drawio)
            → to_svg(root, theme)         → standalone SVG    (browser inline)

The SVG renderer uses vendored MKAbuMattar/aws-icons SVGs from
`/static/topology/icons/aws-icons/`. The drawio renderer uses drawio's
built-in mxgraph.aws4 stencils — diagrams.net renders them natively.

Both renderers share the same layout sizing constants so the two outputs
look visually consistent.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Iterable

from .drawio_styles import (
    CONTAINER_STYLES,
    RESOURCE_BOX,
    style_for,
)
from .icon_map import container_icon, icon_for

# ---------------------------------------------------------------------------
# Layout constants (drawn from the AWS Architecture Reference style)
#
# The diagram grows HORIZONTALLY: AZs are tiled side-by-side inside a VPC,
# and subnets stack vertically within each AZ. This keeps even 6+ AZs on
# a single screen-height while remaining readable.
# ---------------------------------------------------------------------------

PAD_REGION       = 36
PAD_VPC          = 30
PAD_AZ           = 22
PAD_SUBNET       = 18

TITLE_BAR_H      = 38   # room for the container's title — wide enough to fit
                        # "Public Subnet: subnet-0123abcd…" without truncation.
SUBNET_TITLE_H   = 30

RES_W, RES_H     = RESOURCE_BOX                # 78 x 78 (matches drawio_styles)
RES_LABEL_H      = 22                          # below-icon label space
RES_GAP          = 14
SUBNET_GAP_Y     = 16
AZ_GAP_X         = 26
VPC_GAP_X        = 30

# A subnet must be wide enough to host its title bar.  Empirically a 16-char
# id ("subnet-1234abcd") at 11.5 px Inter weighs about 200 px; with badge +
# RT pill we want ~260 minimum.
SUBNET_MIN_W     = 240
SUBNET_MIN_H     = SUBNET_TITLE_H + RES_H + RES_LABEL_H + 2 * PAD_SUBNET

# Resources rendered inside subnet boxes (the running workload of that subnet).
# RDS / ELB live in multiple subnets simultaneously and are distributed there
# during build_hierarchy. ENIs are added too but only when they're not
# already represented by a NAT / ELB / RDS / EC2 (deduplicated by description).
SUBNET_RESOURCE_TYPES = {
    'ec2', 'rds', 'lambda', 'ecs', 'eks', 'efs',
    'nat', 'vpc_endpoint', 'elb', 'apigateway', 'eni',
}
# Resources rendered as VPC-edge/banner items (not inside a subnet).
VPC_EDGE_RESOURCES = {'igw', 'transit_gateway', 'vpn', 'direct_connect',
                      'network_firewall'}
# Resources rendered as a compact "shelf" inside the VPC (one-per-resource
# tile, below the AZ row). These are shared services that don't belong to
# a single subnet.
VPC_SHELF_RESOURCES = {'route_table', 'security_group', 'nacl', 'eip'}


def _eni_is_redundant(eni: dict) -> bool:
    """ENIs that duplicate a resource we already render (NAT, ELB, RDS, EC2)."""
    desc = (eni.get('description') or '').lower()
    itype = (eni.get('interface_type') or '').lower()
    if itype == 'nat_gateway':
        return True
    if eni.get('instance_id'):
        return True  # already shown as the EC2 instance
    if desc.startswith('interface for nat gateway'):
        return True
    if desc.startswith('elb '):
        return True
    if 'rdsnetworkinterface' in desc:
        return True
    if desc.startswith('elasticache') or desc.startswith('elasticfilesystem'):
        return True
    return False


def _label_for_resource(rtype: str, raw: dict) -> tuple[str, str]:
    """Return (line1, line2) text for a resource icon. line2 may be ''."""
    name = raw.get('name') or raw.get('id') or rtype
    if rtype == 'ec2':
        line1 = _truncate(name, 18)
        bits = []
        if raw.get('instance_type'): bits.append(raw['instance_type'])
        if raw.get('state'):         bits.append(raw['state'])
        if raw.get('private_ip'):    bits.append(raw['private_ip'])
        return line1, _truncate(' • '.join(bits), 28)
    if rtype == 'rds':
        line1 = _truncate(raw.get('id') or name, 22)
        bits = []
        if raw.get('engine'):         bits.append(raw['engine'])
        if raw.get('instance_class'): bits.append(raw['instance_class'])
        if raw.get('multi_az'):       bits.append('multi-AZ')
        return line1, _truncate(' • '.join(bits), 28)
    if rtype == 'elb':
        line1 = _truncate(raw.get('name') or raw.get('id') or 'ELB', 22)
        scheme = raw.get('scheme') or ''
        kind   = raw.get('lb_type') or raw.get('type') or 'ELB'
        return line1, _truncate(f'{kind} • {scheme}', 28)
    if rtype == 'nat':
        return _truncate(raw.get('id') or 'nat', 18), _truncate(raw.get('public_ip') or '', 28)
    if rtype == 'lambda':
        return _truncate(raw.get('name') or raw.get('id') or 'lambda', 22), _truncate(raw.get('runtime') or '', 28)
    if rtype == 'eni':
        idstr = _truncate(raw.get('id') or 'eni', 18)
        desc  = raw.get('description') or raw.get('interface_type') or ''
        return idstr, _truncate(desc, 28)
    if rtype == 'vpc_endpoint':
        return _truncate(raw.get('id') or 'vpce', 18), _truncate(raw.get('service_name') or '', 28)
    if rtype == 'eks':
        return _truncate(raw.get('name') or raw.get('id') or 'eks', 22), _truncate(raw.get('version') or '', 28)
    if rtype == 'ecs':
        return _truncate(raw.get('name') or raw.get('id') or 'ecs', 22), ''
    if rtype == 'apigateway':
        return _truncate(raw.get('name') or raw.get('id') or 'apigw', 22), _truncate(raw.get('protocol') or '', 28)
    if rtype == 'efs':
        return _truncate(raw.get('id') or 'efs', 22), _truncate(raw.get('lifecycle_state') or '', 28)
    return _truncate(name, 18), ''


def _label_for_shelf(rtype: str, raw: dict) -> tuple[str, str]:
    """Compact tile labels for the VPC shelf items (1 line + tiny detail)."""
    if rtype == 'route_table':
        line1 = _truncate(raw.get('id') or 'rt', 16)
        is_main = any(a.get('main') for a in (raw.get('associations') or []))
        n_assoc = sum(1 for a in (raw.get('associations') or []) if a.get('subnet_id'))
        kind = 'IGW' if raw.get('has_igw_route') else ('main' if is_main else 'priv')
        return line1, f'{kind} • {n_assoc} subnets'
    if rtype == 'security_group':
        line1 = _truncate(raw.get('id') or 'sg', 16)
        ic = raw.get('inbound_rules_count') or 0
        oc = raw.get('outbound_rules_count') or 0
        return line1, f'in:{ic} • out:{oc}'
    if rtype == 'nacl':
        return _truncate(raw.get('id') or 'acl', 16), 'default' if raw.get('is_default') else 'custom'
    if rtype == 'eip':
        return _truncate(raw.get('public_ip') or raw.get('id') or 'eip', 16), \
               'attached' if raw.get('association_id') else 'orphan'
    return _truncate(raw.get('id') or rtype, 16), ''


def _truncate(text: str, n: int) -> str:
    """Mid-truncate for IDs / long labels so headers never overflow."""
    if not text or len(text) <= n:
        return text
    return text[:n - 1] + '…'


# Tier classification — buckets a subnet into the canonical AWS architecture tiers.
TIER_LABELS = {
    'web':  'Web/Edge',
    'app':  'App/EKS',
    'data': 'Data',
    'mgmt': 'Management',
}
TIER_COLORS = {
    'web':  {'border': '#7AA116', 'fill': '#E9F3E6', 'fg': '#248814'},
    'app':  {'border': '#147EBA', 'fill': '#E6F2F8', 'fg': '#147EBA'},
    'data': {'border': '#3334B9', 'fill': '#E6E6F2', 'fg': '#3334B9'},
    'mgmt': {'border': '#ED7100', 'fill': '#FBE9D9', 'fg': '#ED7100'},
}


def _classify_tier(subnet_raw: dict, route_tables: list[dict],
                   db_subnet_ids: set[str] | None = None) -> str:
    """Pick a tier for a subnet using a few signals — in priority order:

    1. Public subnet → web/edge.
    2. Name contains mgmt/admin/bastion/jump → mgmt.
    3. Name contains data/rds/db/cache/redis → data.
    4. Subnet appears in any RDS DB-subnet-group → data.
    5. Subnet CIDR is a /24 with a "high" third-octet (>=100) and is private →
       commonly a data subnet pattern in AWS reference architectures.
    6. Otherwise → app (default for private subnets).
    """
    name = (subnet_raw.get('name') or '').lower()
    if any(k in name for k in ('mgmt', 'admin', 'bastion', 'jump')):
        return 'mgmt'
    if subnet_raw.get('is_public'):
        return 'web'
    if any(k in name for k in ('data', 'rds', 'db', 'cache', 'redis')):
        return 'data'
    if db_subnet_ids and subnet_raw.get('id') in db_subnet_ids:
        return 'data'
    # Detect typical "data slot" pattern: small (/24+) private subnet with
    # high third octet (≥100) — matches the canonical 10.X.100/101/102.0/24
    # data-tier convention used by AWS reference architectures.
    cidr = subnet_raw.get('cidr') or ''
    try:
        if cidr:
            base, prefix = cidr.split('/')
            prefix = int(prefix)
            octets = [int(o) for o in base.split('.')]
            if prefix >= 23 and len(octets) == 4 and octets[2] >= 100:
                return 'data'
    except ValueError:
        pass
    return 'app'


def _state_opacity(raw: dict) -> int:
    """Stopped/terminated/failed instances render at 60% opacity in drawio."""
    state = (raw.get('state') or raw.get('status') or '').lower()
    if state in ('stopped', 'terminated', 'shutting-down', 'failed', 'detached'):
        return 60
    return 100


# ---------------------------------------------------------------------------
# Hierarchy data classes
# ---------------------------------------------------------------------------


@dataclass
class Resource:
    type:     str
    id:       str
    name:     str
    region:   str
    az:       str = ''
    subnet_id: str = ''
    line1:    str = ''   # main label below the icon
    line2:    str = ''   # secondary detail line (instance type, state, IP, ...)
    line3:    str = ''   # third line (multi-AZ note, etc)
    opacity:  int = 100  # 100 = full; 60 = dimmed (stopped EC2 etc.)
    extra:    dict = field(default_factory=dict)
    # populated by layout
    x: int = 0; y: int = 0; w: int = RES_W; h: int = RES_H + RES_LABEL_H


@dataclass
class Subnet:
    id:        str
    name:      str
    region:    str
    az:        str
    cidr:      str
    is_public: bool
    tier:      str = 'app'    # 'web' | 'app' | 'data' | 'mgmt'
    route_table_id:        str = ''
    route_table_target:    str = ''   # 'IGW' | 'NAT' | 'local' | ''
    resources: list[Resource] = field(default_factory=list)
    x: int = 0; y: int = 0; w: int = SUBNET_MIN_W; h: int = SUBNET_MIN_H


@dataclass
class Az:
    name:    str
    region:  str
    subnets: list[Subnet] = field(default_factory=list)
    x: int = 0; y: int = 0; w: int = 0; h: int = 0


@dataclass
class Vpc:
    id:     str
    name:   str
    region: str
    cidr:   str
    azs:    list[Az]      = field(default_factory=list)
    edges:  list[Resource] = field(default_factory=list)  # IGW, TGW, VPN, DC
    shelf:  list[Resource] = field(default_factory=list)  # RT, SG, NACL, EIP
    shared: list[Resource] = field(default_factory=list)  # multi-AZ services (RDS, ALB, EFS, EKS Control Plane)
    x: int = 0; y: int = 0; w: int = 0; h: int = 0


@dataclass
class Region:
    name: str
    vpcs:           list[Vpc]      = field(default_factory=list)
    off_vpc:        list[Resource] = field(default_factory=list)  # VPC endpoints, TGW (region-level)
    external_actors: list[Resource] = field(default_factory=list)  # User, Internet, On-Prem
    title:          str = ''       # title bar text
    subtitle:       str = ''       # title bar second line
    x: int = 0; y: int = 0; w: int = 0; h: int = 0


# ---------------------------------------------------------------------------
# Hierarchy builder — reshape scan JSON into Region tree
# ---------------------------------------------------------------------------


def _resources_by_type(scan_resources: list[dict], type_: str) -> list[dict]:
    return [r for r in scan_resources if r.get('type') == type_]


def _route_table_for_subnet(scan_resources: Iterable[dict], subnet_id: str) -> str:
    """Find the route table associated with a subnet (explicit assoc, then main)."""
    main_rt = ''
    for rt in (r for r in scan_resources if r.get('type') == 'route_table'):
        for assoc in rt.get('associations') or []:
            if assoc.get('subnet_id') == subnet_id:
                return rt.get('id', '')
            if assoc.get('main'):
                main_rt = rt.get('id', '')
    return main_rt


def build_hierarchy(scan: dict, vpc_id: str) -> Region | None:
    """Build the Region → VPC → AZ → Subnet → Resource tree for one VPC.

    Returns None if the requested VPC isn't found in the scan.
    """
    if not scan or 'resources' not in scan:
        return None
    rs: list[dict] = scan.get('resources') or []

    vpc_record = next((r for r in rs if r.get('type') == 'vpc' and r.get('id') == vpc_id), None)
    if vpc_record is None:
        return None

    region_name = vpc_record.get('region') or ''
    vpc = Vpc(
        id=vpc_record['id'],
        name=vpc_record.get('name') or vpc_record['id'],
        region=region_name,
        cidr=vpc_record.get('cidr') or '',
    )

    # Pre-collect VPC's route tables — needed for tier classification.
    vpc_rts = [r for r in rs if r.get('type') == 'route_table' and r.get('vpc_id') == vpc.id]

    # Collect every subnet that belongs to an RDS DB subnet group so we can
    # mark them as the "Data" tier even if they aren't named accordingly.
    db_subnet_ids: set[str] = set()
    for r in rs:
        if r.get('type') == 'rds':
            db_subnet_ids.update(r.get('subnet_ids') or [])

    def rt_target(rt: dict) -> str:
        if rt.get('has_igw_route'): return 'IGW'
        for rr in (rt.get('routes') or []):
            if 'NatGatewayId' in (rr or {}) or (rr or {}).get('nat_gateway_id'):
                return 'NAT'
        return 'local'

    # Subnets in this VPC, grouped by AZ.
    subnets_in_vpc = [s for s in rs
                      if s.get('type') == 'subnet' and s.get('vpc_id') == vpc.id]

    az_map: dict[str, Az] = {}
    for s in subnets_in_vpc:
        az_name = s.get('az') or 'unknown'
        if az_name not in az_map:
            az_map[az_name] = Az(name=az_name, region=region_name)
        rt_id = _route_table_for_subnet(rs, s['id'])
        rt = next((r for r in vpc_rts if r.get('id') == rt_id), None)
        subnet = Subnet(
            id=s['id'],
            name=s.get('name') or s['id'],
            region=s.get('region') or region_name,
            az=az_name,
            cidr=s.get('cidr') or '',
            is_public=bool(s.get('is_public')),
            tier=_classify_tier(s, vpc_rts, db_subnet_ids),
            route_table_id=rt_id,
            route_table_target=rt_target(rt) if rt else '',
        )
        az_map[az_name].subnets.append(subnet)

    # Order subnets within an AZ by tier so visual stack is web → app → data → mgmt.
    TIER_ORDER = {'web': 0, 'app': 1, 'data': 2, 'mgmt': 3}
    for az in az_map.values():
        az.subnets.sort(key=lambda x: (TIER_ORDER.get(x.tier, 9), x.cidr or x.id))
    vpc.azs = [az_map[k] for k in sorted(az_map.keys())]

    subnet_lookup = {sub.id: sub for az in vpc.azs for sub in az.subnets}

    def _make_resource(rtype, raw, *, subnet_id='', extra_line: str = ''):
        line1, line2 = _label_for_resource(rtype, raw)
        return Resource(
            type=rtype,
            id=raw.get('id') or '',
            name=raw.get('name') or raw.get('id') or rtype,
            region=raw.get('region') or region_name,
            az=raw.get('az') or '',
            subnet_id=subnet_id or raw.get('subnet_id') or '',
            line1=line1, line2=line2, line3=extra_line,
            opacity=_state_opacity(raw),
            extra=raw,
        )

    # Identify multi-AZ services upfront so we can dedup them into vpc.shared.
    # A service is multi-AZ if its subnet_ids spans 2+ AZs (i.e. distinct AZs
    # for those subnets) — typical for ALB, RDS multi-AZ subnet group, EFS,
    # EKS Control Plane.
    def _spans_multiple_azs(raw: dict) -> tuple[bool, int]:
        sids = raw.get('subnet_ids') or []
        if not sids and raw.get('subnet_id'):
            sids = [raw['subnet_id']]
        azs = set()
        for sid in sids:
            sub = subnet_lookup.get(sid)
            if sub:
                azs.add(sub.az)
        return (len(azs) >= 2, len(azs))

    for r in rs:
        rtype = r.get('type')
        if rtype not in SUBNET_RESOURCE_TYPES:
            continue
        rv = r.get('vpc_id')
        if rv and rv != vpc.id:
            continue

        # ENI: skip the ones already represented elsewhere.
        if rtype == 'eni' and _eni_is_redundant(r):
            continue

        # RDS / ELB / EKS / EFS spanning multiple AZs → render ONCE at the
        # VPC's shared band rather than once per subnet. Single-AZ resources
        # still go inside their subnet.
        if rtype in ('rds', 'elb', 'eks', 'efs'):
            multi, az_count = _spans_multiple_azs(r)
            if multi:
                line3 = f'spans {az_count} AZs'
                # multi-AZ RDS often has multi_az flag too — keep label clean
                if rtype == 'rds' and r.get('multi_az'):
                    line3 = f'Multi-AZ • spans {az_count} AZs'
                vpc.shared.append(_make_resource(rtype, r, extra_line=line3))
                continue
            # Single-AZ — fall through to subnet placement.
            sids = r.get('subnet_ids') or ([] if not r.get('subnet_id') else [r['subnet_id']])
            for sid in sids:
                if sid in subnet_lookup:
                    subnet_lookup[sid].resources.append(_make_resource(rtype, r, subnet_id=sid))
            continue

        sub_id = r.get('subnet_id') or ''
        if sub_id and sub_id in subnet_lookup:
            subnet_lookup[sub_id].resources.append(_make_resource(rtype, r, subnet_id=sub_id))

    # ---- VPC-edge resources (IGW / TGW / VPN / DC / Network Firewall) -----
    for r in rs:
        rtype = r.get('type')
        if rtype not in VPC_EDGE_RESOURCES:
            continue
        # IGW reports `vpc_ids` (list) since one IGW can attach to one VPC at a time.
        attached = r.get('vpc_ids') or ([r['vpc_id']] if r.get('vpc_id') else [])
        if rtype == 'igw' and vpc.id not in attached:
            continue
        # TGW / VPN / DC: only include if explicitly tied to this VPC.
        if rtype != 'igw':
            if r.get('vpc_id') and r['vpc_id'] != vpc.id:
                continue
        vpc.edges.append(_make_resource(rtype, r))

    # ---- VPC-shelf resources (Route Tables, SGs, NACLs, EIPs) -----------
    eip_eni_ids = {sub.id: True for az in vpc.azs for sub in az.subnets}  # noop placeholder
    for r in rs:
        rtype = r.get('type')
        if rtype not in VPC_SHELF_RESOURCES:
            continue
        if rtype == 'eip':
            # EIPs aren't tagged with vpc_id; include those whose ENI lives in this VPC.
            target_eni = r.get('network_interface_id')
            if target_eni:
                # Find the parent ENI in scan; if it's in this VPC, keep it.
                parent = next((x for x in rs if x.get('type') == 'eni' and x.get('id') == target_eni), None)
                if parent and parent.get('vpc_id') and parent['vpc_id'] != vpc.id:
                    continue
            else:
                # Orphan EIPs — show them at the VPC's shelf as well.
                pass
        else:
            if r.get('vpc_id') and r['vpc_id'] != vpc.id:
                continue
        line1, line2 = _label_for_shelf(rtype, r)
        vpc.shelf.append(Resource(
            type=rtype,
            id=r.get('id') or '',
            name=r.get('name') or r.get('id') or rtype,
            region=r.get('region') or region_name,
            line1=line1, line2=line2,
            extra=r,
        ))

    # ---- Off-VPC services (Region-level) ---------------------------------
    # Anything that lives at the region/account scope rather than inside
    # a subnet — VPC interface/gateway endpoints, transit gateways, etc.
    region = Region(name=region_name, vpcs=[vpc])
    for r in rs:
        rtype = r.get('type')
        if rtype == 'vpc_endpoint' and r.get('vpc_id') == vpc.id:
            line1, line2 = _label_for_resource('vpc_endpoint', r)
            ep_kind = (r.get('endpoint_type') or r.get('vpc_endpoint_type') or
                       r.get('type_endpoint') or '').title() or 'Endpoint'
            line2 = f'{ep_kind} • {line2}' if line2 else ep_kind
            region.off_vpc.append(Resource(
                type='vpc_endpoint',
                id=r.get('id') or '',
                name=r.get('name') or r.get('id') or 'vpce',
                region=region_name,
                line1=line1, line2=line2, extra=r,
            ))
        elif rtype == 'transit_gateway':
            region.off_vpc.append(Resource(
                type='transit_gateway',
                id=r.get('id') or '',
                name=r.get('name') or r.get('id') or 'tgw',
                region=region_name,
                line1=_truncate(r.get('id') or 'tgw', 22),
                line2='Transit Gateway',
                extra=r,
            ))

    # ---- External actors (Internet, On-Premises) -------------------------
    has_igw = any(e.type == 'igw' for e in vpc.edges)
    has_vpn_or_dc = any(e.type in ('vpn', 'direct_connect', 'transit_gateway') for e in vpc.edges)
    if has_igw:
        region.external_actors.append(Resource(
            type='_actor_user', id='end-user', name='End User', region=region_name,
            line1='End User', line2='HTTPS clients',
        ))
        region.external_actors.append(Resource(
            type='_actor_internet', id='internet', name='Internet', region=region_name,
            line1='Internet', line2='Public traffic',
        ))
    if has_vpn_or_dc:
        region.external_actors.append(Resource(
            type='_actor_onprem', id='onprem', name='On-Premises', region=region_name,
            line1='On-Premises', line2='Customer datacenter',
        ))

    # ---- Title bar -----------------------------------------------------
    profile = (scan or {}).get('profile') or ''
    az_count = len(vpc.azs)
    region.title    = (f'{profile} • ' if profile else '') + f'VPC Architecture ({region_name}) — Tier-based view'
    region.subtitle = f'VPC {vpc.id}  |  CIDR {vpc.cidr or "—"}  |  {az_count} AZ  |  Audience: technical'

    return region


def hierarchy_summary(root: Region | None) -> str:
    """ASCII-tree dump for debugging / Phase 2 verification."""
    if root is None:
        return '(no hierarchy)'
    lines = [f'Region {root.name}']
    for vpc in root.vpcs:
        lines.append(f'  VPC {vpc.id} ({vpc.cidr}) — {vpc.name}')
        for edge in vpc.edges:
            lines.append(f'    [edge] {edge.type} {edge.id}')
        for az in vpc.azs:
            lines.append(f'    AZ {az.name}')
            for subnet in az.subnets:
                kind = 'Public ' if subnet.is_public else 'Private'
                lines.append(f'      {kind}Subnet {subnet.id} ({subnet.cidr}) rt={subnet.route_table_id or "-"}')
                for res in subnet.resources:
                    lines.append(f'        {res.type} {res.id}')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Layout — bottom-up measure, top-down position
# ---------------------------------------------------------------------------


def _layout_subnet(subnet: Subnet) -> None:
    """Place resources in a 2-3 column grid inside the subnet — wider AZs
    benefit from a 3-col grid; tiny subnets fall back to 1 col.
    """
    n = len(subnet.resources)
    # Web/edge subnets typically host NAT + VPN-EC2 + TGW attachment ENI = 3
    # items; data tier is small. App tier may have 8+ EC2 instances.
    if n == 0:
        cols = 1
    elif subnet.tier == 'app' and n >= 4:
        cols = 4   # 4-col grid for big EC2 fleets (matches reference)
    elif n <= 2:
        cols = n
    elif n <= 6:
        cols = 3
    else:
        cols = 4
    rows = max(1, (n + cols - 1) // cols) if n else 1

    inner_w = cols * RES_W + (cols - 1) * RES_GAP
    inner_h = rows * (RES_H + RES_LABEL_H) + (rows - 1) * RES_GAP if n else 0

    subnet.w = max(SUBNET_MIN_W, inner_w + 2 * PAD_SUBNET)
    subnet.h = max(SUBNET_MIN_H, SUBNET_TITLE_H + inner_h + 2 * PAD_SUBNET)

    if n == 0:
        return
    x0 = (subnet.w - inner_w) // 2
    y0 = SUBNET_TITLE_H + PAD_SUBNET
    for i, res in enumerate(subnet.resources):
        col = i % cols
        row = i // cols
        res.x = x0 + col * (RES_W + RES_GAP)
        res.y = y0 + row * (RES_H + RES_LABEL_H + RES_GAP)
        res.w = RES_W
        res.h = RES_H + RES_LABEL_H


def _layout_az(az: Az) -> None:
    """Subnets stack VERTICALLY inside an AZ. The AZ itself becomes a column."""
    for subnet in az.subnets:
        _layout_subnet(subnet)
    if not az.subnets:
        az.w = SUBNET_MIN_W + 2 * PAD_AZ
        az.h = TITLE_BAR_H + 2 * PAD_AZ + 60
        return
    col_w = max(s.w for s in az.subnets)
    total_h = sum(s.h for s in az.subnets) + SUBNET_GAP_Y * (len(az.subnets) - 1)
    az.w = col_w + 2 * PAD_AZ
    az.h = TITLE_BAR_H + total_h + 2 * PAD_AZ

    # Stretch every subnet to the AZ column width so borders align.
    y = TITLE_BAR_H + PAD_AZ
    for subnet in az.subnets:
        subnet.x = PAD_AZ
        subnet.y = y
        if subnet.w < col_w:
            # widen + recenter resources
            extra = col_w - subnet.w
            for res in subnet.resources:
                res.x += extra // 2
            subnet.w = col_w
        y += subnet.h + SUBNET_GAP_Y


SHELF_TILE_W   = 132
SHELF_TILE_H   = 60
SHELF_GAP      = 10
SHELF_GROUP_GAP = 18
SHELF_HEADER_H  = 24
SHELF_GROUP_PAD = 10


def _layout_shelf(vpc: Vpc, available_w: int) -> tuple[int, dict]:
    """Compute height needed for the shelf band given a max width.

    Returns (band_height, group_layouts) where group_layouts is a dict mapping
    resource type → list of (resource, x, y) tuples relative to the band's
    top-left corner.
    """
    if not vpc.shelf:
        return 0, {}

    # Group by type, preserve scan order inside each group.
    groups: dict[str, list[Resource]] = {}
    for res in vpc.shelf:
        groups.setdefault(res.type, []).append(res)
    type_order = ['route_table', 'security_group', 'nacl', 'eip']
    ordered = [(t, groups[t]) for t in type_order if t in groups]

    # We render each group as a label header + a row (or wrapped rows) of tiles.
    layouts: dict = {}
    y = 0
    for tname, items in ordered:
        # how many tiles fit in available_w?
        per_row = max(1, (available_w - 2 * SHELF_GROUP_PAD + SHELF_GAP) //
                      (SHELF_TILE_W + SHELF_GAP))
        rows = (len(items) + per_row - 1) // per_row
        layouts[tname] = []
        cy = y + SHELF_HEADER_H
        for i, item in enumerate(items):
            row = i // per_row
            col = i % per_row
            tx = SHELF_GROUP_PAD + col * (SHELF_TILE_W + SHELF_GAP)
            ty = cy + row * (SHELF_TILE_H + SHELF_GAP)
            layouts[tname].append((item, tx, ty))
        rows_h = rows * SHELF_TILE_H + (rows - 1) * SHELF_GAP
        y += SHELF_HEADER_H + rows_h + SHELF_GROUP_GAP
    band_h = y - SHELF_GROUP_GAP if ordered else 0
    return band_h, layouts


SHARED_BAND_H_TOP = 24   # gap above the shared band
SHARED_BAND_H_GAP = 14
SHARED_TILE_W     = 110
SHARED_TILE_H     = RES_H + RES_LABEL_H + 18  # extra room for "spans N AZs" line


def _layout_vpc(vpc: Vpc) -> None:
    """Layout strategy (clean / tier-based):
       1. IGW + edge services along the VPC's left edge.
       2. Shared multi-AZ services (RDS, ALB, EFS, EKS Control Plane) in a band
          right below the title bar — once each, not per-subnet.
       3. AZ columns side-by-side, each column's subnets stacked top→bottom in
          tier order: web → app → data → mgmt.
       4. Shelf (RT / SG / NACL / EIP) below the AZ row.
    """
    for az in vpc.azs:
        _layout_az(az)

    edge_count = sum(1 for e in vpc.edges if e.type in VPC_EDGE_RESOURCES)
    edge_strip_w = RES_W + 2 * RES_GAP if edge_count else 0
    edge_strip_h = (edge_count * (RES_H + RES_LABEL_H + RES_GAP)) if edge_count else 0

    if not vpc.azs:
        vpc.w = max(480, edge_strip_w + 2 * PAD_VPC)
        vpc.h = max(200, TITLE_BAR_H + edge_strip_h + 2 * PAD_VPC)
        return

    az_total_w = sum(a.w for a in vpc.azs) + AZ_GAP_X * (len(vpc.azs) - 1)
    az_max_h   = max(a.h for a in vpc.azs)

    inner_w = max(az_total_w + edge_strip_w, 600)

    # Shared band — multi-AZ services, laid out in a row above the AZs.
    shared_count = len(vpc.shared)
    shared_band_h = 0
    if shared_count:
        shared_band_h = SHARED_BAND_H_TOP + SHARED_TILE_H + SHARED_BAND_H_GAP

    # Compute the shelf band (RT / SG / NACL / EIP).
    shelf_band_h, shelf_layout = _layout_shelf(vpc, inner_w)

    vpc.w = inner_w + 2 * PAD_VPC
    vpc.h = (TITLE_BAR_H + shared_band_h + max(az_max_h, edge_strip_h) +
             2 * PAD_VPC + (shelf_band_h + SHELF_GROUP_GAP if shelf_band_h else 0))

    # Place edge resources on the left strip, vertically (start below shared band).
    ex = PAD_VPC + (edge_strip_w - RES_W) // 2 if edge_strip_w else 0
    ey = TITLE_BAR_H + shared_band_h + PAD_VPC
    for edge in vpc.edges:
        if edge.type not in VPC_EDGE_RESOURCES:
            continue
        edge.x = ex
        edge.y = ey
        edge.w = RES_W
        edge.h = RES_H + RES_LABEL_H
        ey += RES_H + RES_LABEL_H + RES_GAP

    # Place shared resources horizontally in their band.
    if shared_count:
        # Center the row inside the available inner width.
        total_shared_w = shared_count * SHARED_TILE_W + (shared_count - 1) * RES_GAP
        sx0 = max(PAD_VPC, (vpc.w - total_shared_w) // 2)
        sy0 = TITLE_BAR_H + SHARED_BAND_H_TOP
        for i, s in enumerate(vpc.shared):
            s.x = sx0 + i * (SHARED_TILE_W + RES_GAP)
            s.y = sy0
            s.w = SHARED_TILE_W
            s.h = SHARED_TILE_H

    # Place AZs side-by-side under the shared band.
    az_y = TITLE_BAR_H + shared_band_h + PAD_VPC
    x = PAD_VPC + edge_strip_w
    for az in vpc.azs:
        az.x = x
        az.y = az_y
        # Stretch each AZ to match the tallest one for visual symmetry.
        if az.h < az_max_h:
            az.h = az_max_h
        x += az.w + AZ_GAP_X

    # Shelf relative to VPC top-left, below the AZ band.
    if shelf_layout:
        band_top = az_y + max(az_max_h, edge_strip_h) + SHELF_GROUP_GAP
        for tname, items in shelf_layout.items():
            for res, rx, ry in items:
                res.x = PAD_VPC + edge_strip_w + rx
                res.y = band_top + ry
                res.w = SHELF_TILE_W
                res.h = SHELF_TILE_H


TITLE_BAR_BIG_H   = 60   # global title bar above region
ACTOR_BAR_H       = 96   # external actor strip above region
OFFVPC_COL_W      = 180  # right-column for off-VPC services (vpc endpoints, tgw)
OFFVPC_TILE_H     = 110


def _layout_region(region: Region) -> None:
    for vpc in region.vpcs:
        _layout_vpc(vpc)
    if not region.vpcs:
        region.w = 600; region.h = 300
        return

    has_actors  = bool(region.external_actors)
    has_offvpc  = bool(region.off_vpc)
    actor_h     = ACTOR_BAR_H if has_actors else 0
    title_h     = TITLE_BAR_BIG_H

    # Region container width must fit VPC + optional off-VPC right column.
    vpc_total_w = sum(v.w for v in region.vpcs) + VPC_GAP_X * (len(region.vpcs) - 1)
    offvpc_strip_w = (OFFVPC_COL_W + VPC_GAP_X) if has_offvpc else 0
    inner_w = vpc_total_w + offvpc_strip_w
    max_h   = max(v.h for v in region.vpcs)

    region.w = inner_w + 2 * PAD_REGION
    region.h = title_h + actor_h + TITLE_BAR_H + max_h + 2 * PAD_REGION

    # Region is anchored top-left after title + actors strips.
    region_top_y = title_h + actor_h
    region_inner_top = region_top_y + TITLE_BAR_H + PAD_REGION

    # Position external actors (relative to canvas).
    if has_actors:
        gap = ACTOR_BAR_H - 12
        # Spread actors evenly across the region width.
        n = len(region.external_actors)
        slot_w = max(180, region.w // max(n, 2))
        for i, a in enumerate(region.external_actors):
            # Pin User to the left, On-Prem to the right, Internet between.
            if a.type == '_actor_user':       a.x = PAD_REGION + 20
            elif a.type == '_actor_onprem':   a.x = region.w - PAD_REGION - 80 - 100
            else:                             a.x = PAD_REGION + 200
            a.y = title_h + 16
            a.w = 80
            a.h = 80

    # Position VPCs.
    x = PAD_REGION
    for vpc in region.vpcs:
        vpc.x = x
        vpc.y = region_inner_top - region_top_y  # relative to region container
        x += vpc.w + VPC_GAP_X

    # Position off-VPC services (right column, inside region).
    if has_offvpc:
        ox = vpc_total_w + VPC_GAP_X + (OFFVPC_COL_W - 78) // 2
        oy = TITLE_BAR_H + PAD_REGION + 40   # below region title
        for s in region.off_vpc:
            s.x = ox
            s.y = oy
            s.w = 78
            s.h = 78
            oy += OFFVPC_TILE_H

    # Region container's box position (relative to canvas top-left).
    region.x = PAD_REGION
    region.y = region_top_y


def layout(region: Region) -> None:
    _layout_region(region)


# ---------------------------------------------------------------------------
# drawio (mxGraph) renderer
# ---------------------------------------------------------------------------


def _mx_geometry(parent: ET.Element, x: int, y: int, w: int, h: int) -> None:
    g = ET.SubElement(parent, 'mxGeometry', {
        'x': str(x), 'y': str(y),
        'width': str(w), 'height': str(h),
        'as': 'geometry',
    })


def _mx_cell(root: ET.Element, *, cell_id: str, value: str, style: str,
             parent_id: str, vertex: bool = True,
             x: int = 0, y: int = 0, w: int = 0, h: int = 0) -> ET.Element:
    cell = ET.SubElement(root, 'mxCell', {
        'id':     cell_id,
        'value':  value,
        'style':  style,
        'parent': parent_id,
        'vertex': '1' if vertex else '0',
    })
    _mx_geometry(cell, x, y, w, h)
    return cell


def to_drawio(region: Region) -> str:
    """Serialize a Region tree to a complete drawio XML document.

    Output is openable in https://app.diagrams.net/ via File → Open or via
    the `?title=...#R<base64>` URL fragment.
    """
    layout(region)

    mxfile = ET.Element('mxfile', {'host': 'app.diagrams.net', 'type': 'device'})
    diagram_name = f'VPC {region.vpcs[0].id}' if region.vpcs else 'Topology'
    diagram = ET.SubElement(mxfile, 'diagram', {
        'id':   region.vpcs[0].id if region.vpcs else 'topology',
        'name': diagram_name,
    })
    model = ET.SubElement(diagram, 'mxGraphModel', {
        'dx': '1422', 'dy': '800', 'grid': '1', 'gridSize': '10',
        'guides': '1', 'tooltips': '1', 'connect': '1', 'arrows': '1',
        'fold': '1', 'page': '1', 'pageScale': '1',
        'pageWidth':  str(region.w + 80),
        'pageHeight': str(region.h + 80),
        'math': '0', 'shadow': '0',
    })
    root = ET.SubElement(model, 'root')
    ET.SubElement(root, 'mxCell', {'id': '0'})
    ET.SubElement(root, 'mxCell', {'id': '1', 'parent': '0'})

    # Region container (absolute coords)
    rid = f'region-{region.name or "r"}'
    _mx_cell(root,
             cell_id=rid,
             value=f'Region: {region.name}',
             style=CONTAINER_STYLES['region'],
             parent_id='1',
             x=region.x + 20, y=region.y + 20,
             w=region.w, h=region.h)

    for vpc in region.vpcs:
        vid = f'vpc-{vpc.id}'
        _mx_cell(root,
                 cell_id=vid,
                 value=f'VPC: {vpc.id}' + (f' ({vpc.cidr})' if vpc.cidr else ''),
                 style=CONTAINER_STYLES['vpc'],
                 parent_id=rid,
                 x=vpc.x, y=vpc.y, w=vpc.w, h=vpc.h)

        # Edge resources (IGW, TGW, VPN, DC, Network Firewall) on left strip.
        for edge in vpc.edges:
            if edge.type not in VPC_EDGE_RESOURCES:
                continue
            _mx_cell(root,
                     cell_id=f'edge-{edge.id}',
                     value=_truncate(edge.id, 16),
                     style=style_for(edge.type),
                     parent_id=vid,
                     x=edge.x, y=edge.y,
                     w=edge.w, h=edge.h - RES_LABEL_H)

        for az in vpc.azs:
            azid = f'az-{vpc.id}-{az.name}'
            _mx_cell(root,
                     cell_id=azid,
                     value=f'AZ: {az.name}',
                     style=CONTAINER_STYLES['az'],
                     parent_id=vid,
                     x=az.x, y=az.y, w=az.w, h=az.h)

            for subnet in az.subnets:
                # Tier-based subnet style (web/app/data/mgmt)
                from .drawio_styles import style_for_tier, style_with_opacity
                kind_word = 'Public' if subnet.is_public else 'Private'
                tier_label = TIER_LABELS.get(subnet.tier, subnet.tier.title())
                rt_part = ''
                if subnet.route_table_id:
                    rt_part = f' • RT: {_truncate(subnet.route_table_id, 12)} ({subnet.route_table_target or "local"})'
                head_value = (
                    f'{kind_word} Subnet • {tier_label} tier&#10;'
                    f'{subnet.id}'
                    + (f' ({subnet.cidr})' if subnet.cidr else '')
                    + rt_part
                )
                sid = f'subnet-{subnet.id}'
                _mx_cell(root,
                         cell_id=sid,
                         value=head_value,
                         style=style_for_tier(subnet.tier),
                         parent_id=azid,
                         x=subnet.x, y=subnet.y,
                         w=subnet.w, h=subnet.h)

                for res in subnet.resources:
                    label = res.line1 or res.name or res.id
                    if res.line2:
                        label = f'{label}\n{res.line2}'
                    _mx_cell(root,
                             cell_id=f'res-{res.id}-{sid}',
                             value=label,
                             style=style_with_opacity(style_for(res.type), res.opacity),
                             parent_id=sid,
                             x=res.x, y=res.y,
                             w=res.w, h=res.h - RES_LABEL_H)

        # Cross-AZ shared services (multi-AZ RDS, ALB, EFS, EKS Control Plane)
        for s in vpc.shared:
            label = s.line1 or s.id
            if s.line2: label = f'{label}\n{s.line2}'
            if s.line3: label = f'{label}\n{s.line3}'
            _mx_cell(root,
                     cell_id=f'shared-{s.type}-{s.id}',
                     value=label,
                     style=style_with_opacity(style_for(s.type), s.opacity),
                     parent_id=vid,
                     x=s.x, y=s.y,
                     w=s.w, h=s.h)

        # Shelf: Route Tables / SGs / NACLs / EIPs as compact cards under the AZs.
        for s in vpc.shelf:
            label = s.line1 or s.id
            if s.line2:
                label = f'{label}\n{s.line2}'
            _mx_cell(root,
                     cell_id=f'shelf-{s.type}-{s.id}',
                     value=label,
                     style=style_for(s.type),
                     parent_id=vid,
                     x=s.x, y=s.y,
                     w=s.w, h=s.h)

    # ---- Off-VPC services (region right column) ----
    for s in region.off_vpc:
        label = s.line1 or s.id
        if s.line2: label = f'{label}\n{s.line2}'
        _mx_cell(root,
                 cell_id=f'offvpc-{s.type}-{s.id}',
                 value=label,
                 style=style_for(s.type),
                 parent_id=rid,
                 x=s.x, y=s.y, w=s.w, h=s.h)

    # ET serialization → string
    ET.indent(mxfile, space='  ')
    xml_bytes = ET.tostring(mxfile, encoding='UTF-8', xml_declaration=True)
    return xml_bytes.decode('utf-8')


# ---------------------------------------------------------------------------
# SVG renderer (browser inline preview, theme-aware, fully self-contained)
#
# IMPORTANT: icons are inlined as <symbol> definitions and referenced via
# <use href="#sym-..."> so the SVG is self-contained. Earlier versions used
# <image href="/static/topology/icons/..."> which only worked while the SVG
# was served from Flask — downloaded .svg/.png files showed empty boxes
# because the relative href could not resolve.
# ---------------------------------------------------------------------------

# Canonical AWS-Architecture-Reference colours — matches the drawio mxgraph.aws4
# palette so the inline SVG and the .drawio export look visually identical.
_PALETTE = {
    'region':         {'stroke': '#00A4A6', 'fill': 'none',    'fg': '#147EBA'},
    'vpc':            {'stroke': '#248814', 'fill': 'none',    'fg': '#248814'},
    'az':             {'stroke': '#147EBA', 'fill': 'none',    'fg': '#147EBA'},
    'public_subnet':  {'stroke': '#7AA116', 'fill': '#E9F3E6', 'fg': '#3F6634'},
    'private_subnet': {'stroke': '#147EBA', 'fill': '#E6F2F8', 'fg': '#0E5A8A'},
    # Tier-aware subnet colors (matches reference)
    'subnet_web':  {'stroke': '#7AA116', 'fill': '#E9F3E6', 'fg': '#248814'},
    'subnet_app':  {'stroke': '#147EBA', 'fill': '#E6F2F8', 'fg': '#147EBA'},
    'subnet_data': {'stroke': '#3334B9', 'fill': '#E6E6F2', 'fg': '#3334B9'},
    'subnet_mgmt': {'stroke': '#ED7100', 'fill': '#FBE9D9', 'fg': '#ED7100'},
}

_PALETTE_DARK = {
    'region':         {'stroke': '#00A4A6', 'fill': 'none',    'fg': '#7CDCDD'},
    'vpc':            {'stroke': '#7CC34F', 'fill': 'none',    'fg': '#7CC34F'},
    'az':             {'stroke': '#5BC0EB', 'fill': 'none',    'fg': '#5BC0EB'},
    'public_subnet':  {'stroke': '#7AA116', 'fill': '#1d2614', 'fg': '#9BD661'},
    'private_subnet': {'stroke': '#147EBA', 'fill': '#0f1d2a', 'fg': '#5BC0EB'},
    'subnet_web':  {'stroke': '#7AA116', 'fill': '#1d2614', 'fg': '#9BD661'},
    'subnet_app':  {'stroke': '#147EBA', 'fill': '#0f1d2a', 'fg': '#5BC0EB'},
    'subnet_data': {'stroke': '#7676E0', 'fill': '#161628', 'fg': '#A4A4F2'},
    'subnet_mgmt': {'stroke': '#ED7100', 'fill': '#2a1c0c', 'fg': '#F5A35C'},
}


def _palette(theme: str) -> dict:
    return _PALETTE_DARK if theme == 'dark' else _PALETTE


# ----- Icon vendor SVG → inline <symbol> -----------------------------------

import os
import re as _re

_ICON_FS_ROOT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'static', 'topology', 'icons', 'aws-icons',
))


def _icon_filesystem_path(href: str) -> str | None:
    """Convert a /static/topology/icons/aws-icons/X URL to a local fs path."""
    if not href:
        return None
    prefix = '/static/topology/icons/aws-icons/'
    if not href.startswith(prefix):
        return None
    rel = href[len(prefix):]
    candidate = os.path.normpath(os.path.join(_ICON_FS_ROOT, rel))
    if not candidate.startswith(_ICON_FS_ROOT):
        return None  # path traversal guard
    return candidate if os.path.isfile(candidate) else None


def _icon_id(href: str) -> str:
    """Stable, valid-XML id derived from the icon filename."""
    base = os.path.splitext(os.path.basename(href))[0]
    safe = _re.sub(r'[^A-Za-z0-9]+', '-', base).strip('-').lower()
    return f'sym-{safe}'


_SVG_HEAD_RE = _re.compile(r'^.*?<svg([^>]*)>(.*)</svg>\s*$', _re.DOTALL | _re.IGNORECASE)
_NS_RE       = _re.compile(r'\s*xmlns(?::[\w-]+)?="[^"]*"')


def _icon_to_symbol(href: str) -> tuple[str, str] | None:
    """Read a vendored SVG and rewrite it as a <symbol id="...">...</symbol>.

    Returns (symbol_id, symbol_xml_fragment) or None when the icon is missing.
    The result is appended verbatim to the master SVG's <defs> block.
    """
    fs = _icon_filesystem_path(href)
    if not fs:
        return None
    try:
        with open(fs, 'r', encoding='utf-8') as f:
            raw = f.read()
    except (OSError, UnicodeDecodeError):
        return None

    m = _SVG_HEAD_RE.match(raw.strip())
    if not m:
        return None
    attrs_str, inner = m.group(1), m.group(2)
    # Pull the viewBox if present (most aws-icons SVGs declare 0 0 64 64).
    vb_match = _re.search(r'viewBox\s*=\s*"([^"]+)"', attrs_str)
    viewbox = vb_match.group(1) if vb_match else '0 0 64 64'
    # Strip xmlns attributes — invalid inside <symbol> in some renderers,
    # also redundant since the parent <svg> already declares the namespace.
    inner_clean = _NS_RE.sub('', inner).strip()

    sid = _icon_id(href)
    symbol = (
        f'<symbol id="{sid}" viewBox="{viewbox}" overflow="visible">'
        f'{inner_clean}'
        f'</symbol>'
    )
    return sid, symbol


def _collect_icon_hrefs(region: Region) -> list[str]:
    """Walk the tree, collect every icon URL we'll need to inline."""
    hrefs: list[str] = []
    seen: set[str] = set()

    def add(h):
        if h and h not in seen:
            seen.add(h); hrefs.append(h)

    add(container_icon('region'))
    add(container_icon('vpc'))
    add(container_icon('public_subnet'))
    add(container_icon('private_subnet'))
    # Off-VPC services (region right-column)
    for s in region.off_vpc:
        add(icon_for(s.type))
    for vpc in region.vpcs:
        for edge in vpc.edges:
            add(icon_for(edge.type))
        for s in vpc.shared:                # cross-AZ shared resources
            add(icon_for(s.type))
        for az in vpc.azs:
            for subnet in az.subnets:
                if subnet.route_table_id:
                    add(icon_for('route_table'))
                for res in subnet.resources:
                    add(icon_for(res.type))
        for s in vpc.shelf:
            add(icon_for(s.type))
    return hrefs


# ----- Low-level SVG element helpers ---------------------------------------

def _svg_rect(parent: ET.Element, *, x: int, y: int, w: int, h: int,
              kind: str, theme: str, dashed: bool = False,
              radius: int = 6) -> None:
    pal = _palette(theme)[kind]
    attrs = {
        'x': str(x), 'y': str(y), 'width': str(w), 'height': str(h),
        'rx': str(radius), 'ry': str(radius),
        'fill':   pal['fill'],
        'stroke': pal['stroke'],
        'stroke-width': '2',
    }
    if dashed:
        attrs['stroke-dasharray'] = '6,4'
    ET.SubElement(parent, 'rect', attrs)


def _svg_text(parent: ET.Element, *, x: int, y: int, text: str,
              kind: str, theme: str, size: int = 12, weight: str = '600') -> None:
    fg = _palette(theme)[kind]['fg']
    t = ET.SubElement(parent, 'text', {
        'x': str(x), 'y': str(y),
        'fill': fg,
        'font-family': "'Inter', system-ui, sans-serif",
        'font-size': str(size),
        'font-weight': weight,
    })
    t.text = text


def _svg_label(parent: ET.Element, *, x: int, y: int, text: str,
               theme: str, color: str | None = None, size: int = 11,
               anchor: str = 'middle', weight: str = '500') -> None:
    fg = color or ('#dee5ef' if theme == 'dark' else '#1f2c3d')
    t = ET.SubElement(parent, 'text', {
        'x': str(x), 'y': str(y),
        'fill': fg,
        'font-family': "'Inter', system-ui, sans-serif",
        'font-size': str(size),
        'font-weight': weight,
        'text-anchor': anchor,
    })
    t.text = text


def _svg_label_two_lines(parent: ET.Element, *, x: int, y: int,
                         line1: str, line2: str, theme: str,
                         primary: str | None = None,
                         secondary: str | None = None) -> None:
    """Two-line text element. line1 weight 600, line2 muted/smaller."""
    if line1:
        _svg_label(parent, x=x, y=y, text=line1, theme=theme,
                   color=primary, size=10, weight='600')
    if line2:
        muted = secondary or ('#9bb1cc' if theme == 'dark' else '#5c6f87')
        _svg_label(parent, x=x, y=y + 12, text=line2, theme=theme,
                   color=muted, size=9, weight='500')


def _svg_use(parent: ET.Element, *, x: int, y: int, w: int, h: int,
             href: str, sym_index: dict, opacity: int = 100) -> None:
    """Place a vendored icon by referencing the pre-inlined <symbol>."""
    sid = sym_index.get(href)
    if not sid:
        return
    attrs = {
        'href':   f'#{sid}',
        'x':      str(x), 'y':      str(y),
        'width':  str(w), 'height': str(h),
    }
    if opacity < 100:
        attrs['opacity'] = f'{opacity / 100:.2f}'
    ET.SubElement(parent, 'use', attrs)


# ----- Main entry point ----------------------------------------------------

def to_svg(region: Region, theme: str = 'dark') -> str:
    """Serialize a Region tree to a self-contained SVG (icons inlined)."""
    layout(region)

    pad = 24
    total_w = region.w + 2 * pad
    total_h = region.h + 2 * pad
    bg = '#0e1219' if theme == 'dark' else '#f0f4f8'

    # ---- Build <defs> with every needed icon ------------------------
    sym_index: dict[str, str] = {}
    sym_xml_parts: list[str] = []
    for href in _collect_icon_hrefs(region):
        result = _icon_to_symbol(href)
        if not result:
            continue
        sid, sym_xml = result
        sym_index[href] = sid
        sym_xml_parts.append(sym_xml)
    defs_xml = '<defs>' + ''.join(sym_xml_parts) + '</defs>' if sym_xml_parts else ''

    # ---- Master SVG element via ET tree (we'll inject defs as raw XML) -----
    svg = ET.Element('svg', {
        'xmlns':       'http://www.w3.org/2000/svg',
        'xmlns:xlink': 'http://www.w3.org/1999/xlink',
        'viewBox':     f'0 0 {total_w} {total_h}',
        'width':       str(total_w),
        'height':      str(total_h),
        'font-family': "'Inter', system-ui, sans-serif",
    })
    ET.SubElement(svg, 'rect', {
        'x': '0', 'y': '0',
        'width': str(total_w), 'height': str(total_h),
        'fill': bg,
    })

    # ---- Title bar (top of canvas) ----
    if region.title:
        ET.SubElement(svg, 'rect', {
            'x': str(pad), 'y': str(pad),
            'width': str(region.w), 'height': str(TITLE_BAR_BIG_H),
            'rx': '6', 'ry': '6',
            'fill': '#232F3E',
        })
        _svg_label(svg, x=pad + 22, y=pad + 26,
                   text=region.title, theme=theme,
                   color='#FFFFFF', size=15, anchor='start', weight='700')
        if region.subtitle:
            _svg_label(svg, x=pad + 22, y=pad + 48,
                       text=region.subtitle, theme=theme,
                       color='#cdd9e8', size=11, anchor='start', weight='500')

    # ---- External actors strip (User / Internet / On-Prem) ----
    if region.external_actors:
        for a in region.external_actors:
            ax = pad + a.x
            ay = pad + a.y
            # Stub: simple rounded card with type-specific text icon (we don't
            # have AWS-icons for "User"/"Internet"; we use the User icon vendor
            # path as a fallback for actor visuals, otherwise placeholder rect).
            ET.SubElement(svg, 'rect', {
                'x': str(ax), 'y': str(ay),
                'width': str(a.w), 'height': str(a.h),
                'rx': '8', 'ry': '8',
                'fill': '#7D8998', 'opacity': '0.18',
                'stroke': '#7D8998', 'stroke-width': '1.5',
            })
            label_emoji = {'_actor_user': '👤', '_actor_internet': '🌐', '_actor_onprem': '🏢'}.get(a.type, '◆')
            _svg_label(svg, x=ax + a.w // 2, y=ay + 38,
                       text=label_emoji, theme=theme, size=24, weight='600',
                       color='#cdd9e8' if theme == 'dark' else '#3a4a5e')
            _svg_label(svg, x=ax + a.w // 2, y=ay + a.h + 14,
                       text=a.line1, theme=theme, size=11, weight='600')
            if a.line2:
                _svg_label(svg, x=ax + a.w // 2, y=ay + a.h + 28,
                           text=a.line2, theme=theme, size=9, weight='400',
                           color='#9bb1cc' if theme == 'dark' else '#5c6f87')

    # Region container — anchored at (region.x, region.y).
    rx = pad + region.x
    ry = pad + region.y
    _svg_rect(svg, x=rx, y=ry, w=region.w - 2 * region.x,
              h=region.h - region.y, kind='region', theme=theme,
              dashed=True, radius=10)
    if container_icon('region'):
        _svg_use(svg, x=rx + 10, y=ry + 8, w=24, h=24,
                 href=container_icon('region'), sym_index=sym_index)
    _svg_text(svg, x=rx + 42, y=ry + 25,
              text=f'Region: {region.name}', kind='region', theme=theme, size=13)

    # Off-VPC services (right column inside region)
    for s in region.off_vpc:
        ox = rx + s.x
        oy = ry + s.y
        _svg_use(svg, x=ox, y=oy, w=s.w, h=s.h,
                 href=icon_for(s.type), sym_index=sym_index)
        _svg_label_two_lines(svg, x=ox + s.w // 2, y=oy + s.h + 14,
                             line1=s.line1, line2=s.line2, theme=theme)

    for vpc in region.vpcs:
        vx, vy = rx + vpc.x, ry + vpc.y
        _svg_rect(svg, x=vx, y=vy, w=vpc.w, h=vpc.h,
                  kind='vpc', theme=theme, radius=8)
        if container_icon('vpc'):
            _svg_use(svg, x=vx + 10, y=vy + 8, w=24, h=24,
                     href=container_icon('vpc'), sym_index=sym_index)
        head = f'VPC: {_truncate(vpc.id, 22)}' + (f' ({vpc.cidr})' if vpc.cidr else '')
        _svg_text(svg, x=vx + 42, y=vy + 25, text=head,
                  kind='vpc', theme=theme, size=13)

        # Edge resources (left strip): IGW / TGW / VPN / DC / Network Firewall
        for edge in vpc.edges:
            if edge.type not in VPC_EDGE_RESOURCES:
                continue
            ix = vx + edge.x
            iy = vy + edge.y
            _svg_use(svg, x=ix, y=iy, w=RES_W, h=RES_H,
                     href=icon_for(edge.type), sym_index=sym_index)
            _svg_label(svg, x=ix + RES_W // 2, y=iy + RES_H + 14,
                       text=_truncate(edge.id, 18), theme=theme,
                       color=_palette(theme)['vpc']['fg'])

        # Cross-AZ shared band (multi-AZ RDS, ALB, EFS, EKS Control Plane)
        for s in vpc.shared:
            sx2, sy2 = vx + s.x, vy + s.y
            _svg_use(svg, x=sx2 + (s.w - RES_W) // 2, y=sy2,
                     w=RES_W, h=RES_H,
                     href=icon_for(s.type), sym_index=sym_index)
            cx = sx2 + s.w // 2
            _svg_label(svg, x=cx, y=sy2 + RES_H + 14,
                       text=s.line1, theme=theme, size=10, weight='700')
            if s.line2:
                _svg_label(svg, x=cx, y=sy2 + RES_H + 28,
                           text=s.line2, theme=theme, size=9, weight='500',
                           color='#9bb1cc' if theme == 'dark' else '#5c6f87')
            if s.line3:
                _svg_label(svg, x=cx, y=sy2 + RES_H + 42,
                           text=s.line3, theme=theme, size=9, weight='600',
                           color=_palette(theme)['vpc']['fg'])

        # AZ tiles, side-by-side
        for az in vpc.azs:
            ax, ay = vx + az.x, vy + az.y
            _svg_rect(svg, x=ax, y=ay, w=az.w, h=az.h,
                      kind='az', theme=theme, dashed=True, radius=8)
            _svg_text(svg, x=ax + 14, y=ay + 24,
                      text=f'AZ: {az.name}', kind='az', theme=theme, size=12)

            # Subnets stack vertically — colored by tier (web / app / data / mgmt).
            for subnet in az.subnets:
                sx, sy = ax + subnet.x, ay + subnet.y
                kind = 'subnet_' + subnet.tier  # palette key
                _svg_rect(svg, x=sx, y=sy, w=subnet.w, h=subnet.h,
                          kind=kind, theme=theme, radius=6)

                # Use the public/private vendored subnet badge (closest match).
                badge_kind = 'public_subnet' if subnet.is_public else 'private_subnet'
                badge_href = container_icon(badge_kind)
                if badge_href:
                    _svg_use(svg, x=sx + 6, y=sy + 6, w=20, h=20,
                             href=badge_href, sym_index=sym_index)

                kind_word = 'Public' if subnet.is_public else 'Private'
                tier_label = TIER_LABELS.get(subnet.tier, subnet.tier.title())
                head_text = f'{kind_word} Subnet • {tier_label} tier'
                _svg_text(svg, x=sx + 32, y=sy + 17, text=head_text,
                          kind=kind, theme=theme, size=11, weight='700')

                rt_part = ''
                if subnet.route_table_id:
                    target = subnet.route_table_target or 'local'
                    rt_part = f' • RT: {_truncate(subnet.route_table_id, 12)} ({target})'
                sub_meta = f'{_truncate(subnet.id, 22)}'
                if subnet.cidr:
                    sub_meta += f' ({subnet.cidr})'
                sub_meta += rt_part
                _svg_text(svg, x=sx + 32, y=sy + 30, text=sub_meta,
                          kind=kind, theme=theme, size=9, weight='500')

                for res in subnet.resources:
                    rx0 = sx + res.x
                    ry0 = sy + res.y
                    _svg_use(svg, x=rx0, y=ry0, w=RES_W, h=RES_H,
                             href=icon_for(res.type), sym_index=sym_index,
                             opacity=res.opacity)
                    line1 = res.line1 or _truncate(res.name or res.id or res.type, 18)
                    line2 = res.line2
                    # Dim labels on stopped resources to match the icon opacity.
                    primary_color = None
                    if res.opacity < 100:
                        primary_color = '#7a8aa3' if theme == 'dark' else '#7a8aa3'
                    _svg_label_two_lines(
                        svg, x=rx0 + RES_W // 2, y=ry0 + RES_H + 12,
                        line1=line1, line2=line2, theme=theme,
                        primary=primary_color,
                    )

        # ---- VPC shelf (Route Tables / Security Groups / NACLs / EIPs) ----
        if vpc.shelf:
            # Group again by type for header rendering — same order as layout.
            grouped: dict[str, list[Resource]] = {}
            for s in vpc.shelf:
                grouped.setdefault(s.type, []).append(s)
            type_label = {
                'route_table':    'Route Tables',
                'security_group': 'Security Groups',
                'nacl':           'Network ACLs',
                'eip':            'Elastic IPs',
            }
            # Header position lives just above the first tile of each group.
            for tname in ('route_table', 'security_group', 'nacl', 'eip'):
                items = grouped.get(tname) or []
                if not items:
                    continue
                first = items[0]
                hx = vx + first.x
                hy = vy + first.y - 8
                _svg_label(svg, x=hx, y=hy,
                           text=f'{type_label[tname]}  ({len(items)})',
                           theme=theme,
                           color=_palette(theme)['vpc']['fg'],
                           size=11, anchor='start', weight='700')
            # Render each shelf tile.
            for s in vpc.shelf:
                tx, ty = vx + s.x, vy + s.y
                # Compact card
                ET.SubElement(svg, 'rect', {
                    'x': str(tx), 'y': str(ty),
                    'width': str(s.w), 'height': str(s.h),
                    'rx': '5', 'ry': '5',
                    'fill': '#0f1d2a' if theme == 'dark' else '#ffffff',
                    'stroke': '#3F6A99' if theme == 'dark' else '#cdd9e8',
                    'stroke-width': '1',
                })
                # Icon in the left
                _svg_use(svg, x=tx + 8, y=ty + 14, w=28, h=28,
                         href=icon_for(s.type), sym_index=sym_index)
                # Two-line label on the right
                _svg_label(svg, x=tx + 44, y=ty + 22,
                           text=s.line1, theme=theme, anchor='start',
                           size=10, weight='600')
                _svg_label(svg, x=tx + 44, y=ty + 38,
                           text=s.line2, theme=theme, anchor='start',
                           size=9, weight='500',
                           color=('#9bb1cc' if theme == 'dark' else '#5c6f87'))

    ET.indent(svg, space='  ')
    body = ET.tostring(svg, encoding='unicode')

    # Inject the <defs> block (with raw symbol XML) after the opening <svg ...>.
    # We do this post-hoc because ET would escape the symbol HTML otherwise.
    if defs_xml:
        body = _re.sub(r'(<svg[^>]*>)', r'\1' + defs_xml, body, count=1)
    return body


__all__ = [
    'Region', 'Vpc', 'Az', 'Subnet', 'Resource',
    'build_hierarchy', 'hierarchy_summary',
    'to_drawio', 'to_svg', 'layout',
]
