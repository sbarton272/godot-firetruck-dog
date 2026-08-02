#!/usr/bin/env python3
"""Render 5 Painswick-derived town layouts as SVGs directly from the OSM
GeoJSON export. Each layout clips a rectangular sub-bbox of the real village,
then styles the features (roads by highway class, buildings as Cotswold-stone
polygons, churches highlighted, waterways blue, walls/hedges dashed brown)."""
import json, math, os, html

GEO = "notes/plans/2026-08-02-painswick-maps/export.geojson"
OUT_DIR = "notes/plans/2026-08-02-painswick-maps"

# ---- palette ----
COL_FIELD_BG = "#c6d99b"
COL_FIELD_FILL = "#b8d18a"
COL_MEADOW = "#c6dc93"
COL_ORCHARD = "#c9d99b"
COL_WATER = "#8ecad6"
COL_WATER_STROKE = "#4d8ba0"
COL_STONE_FILL = "#e7dec5"
COL_STONE_STROKE = "#8a7c58"
COL_BUILDING_FILL = "#cdbf99"
COL_BUILDING_STROKE = "#7a6b46"
COL_CHURCH_FILL = "#b8ab84"
COL_CHURCH_STROKE = "#4a3a1c"
COL_WALL = "#6b5533"
COL_HEDGE = "#4a6a35"
COL_TITLE = "#3a2a10"

# highway styles (stroke width scales with bbox size at render time)
HIGHWAY_STYLES = {
    "primary":       ("#f2c568", "#7a5b1a", 1.35),
    "secondary":     ("#f4d17a", "#7a5b1a", 1.25),
    "tertiary":      ("#f7dfa0", "#7a5b1a", 1.15),
    "unclassified":  ("#ffffff", "#6b5b3a", 1.00),
    "residential":   ("#ffffff", "#6b5b3a", 1.00),
    "service":       ("#f5f0e2", "#8a7a58", 0.75),
    "living_street": ("#efe7d3", "#8a7a58", 0.85),
    "track":         ("#e8d9b8", "#8a7a58", 0.60),
    "footway":       ("#f2e4c8", "#a08858", 0.35),
    "path":          ("#f2e4c8", "#a08858", 0.30),
    "steps":         ("#e2c7a0", "#8a7358", 0.40),
    "pedestrian":    ("#f5efdc", "#a08858", 0.90),
    "cycleway":      ("#f2e4c8", "#a08858", 0.35),
}

# ---- geo helpers ----
def bbox_intersects_geom(bbox, geom):
    """True if any coord of geom is inside bbox (cheap, good enough)."""
    minlon, minlat, maxlon, maxlat = bbox
    def w(c):
        if not isinstance(c, (list, tuple)): return False
        if c and isinstance(c[0], (int, float)) and len(c) >= 2:
            lon, lat = c[0], c[1]
            return minlon <= lon <= maxlon and minlat <= lat <= maxlat
        return any(w(x) for x in c)
    return w(geom.get("coordinates"))

def project(lon, lat, bbox, W, H):
    x = (lon - bbox[0]) / (bbox[2] - bbox[0]) * W
    y = H - (lat - bbox[1]) / (bbox[3] - bbox[1]) * H
    return x, y

def coords_to_path(coords, bbox, W, H, close=False):
    """Convert a LineString or a Polygon ring to an SVG path 'd'."""
    parts = []
    for i, (lon, lat) in enumerate(coords):
        x, y = project(lon, lat, bbox, W, H)
        parts.append(f"{'M' if i==0 else 'L'}{x:.1f},{y:.1f}")
    if close: parts.append("Z")
    return "".join(parts)

def polygon_to_path(coords, bbox, W, H):
    """coords is [outer ring, hole, hole, ...]"""
    ds = []
    for ring in coords:
        ds.append(coords_to_path(ring, bbox, W, H, close=True))
    return " ".join(ds)

def svg_size_for_bbox(bbox, target_w=1000, max_h=800):
    """Preserve real aspect ratio (equirectangular at bbox mid-lat)."""
    minlon, minlat, maxlon, maxlat = bbox
    mid_lat = (minlat + maxlat) / 2
    m_per_deg_lat = 111320.0
    m_per_deg_lon = 111320.0 * math.cos(math.radians(mid_lat))
    dx_m = (maxlon - minlon) * m_per_deg_lon
    dy_m = (maxlat - minlat) * m_per_deg_lat
    W = target_w
    H = W * dy_m / dx_m
    if H > max_h:
        H = max_h; W = H * dx_m / dy_m
    return round(W), round(H), dx_m, dy_m

# ---- rendering ----
def render_layout(features, layout, out_path):
    bbox = layout["bbox"]
    W, H, dx_m, dy_m = svg_size_for_bbox(bbox)
    HEADER_H = 84
    FOOTER_H = 52
    TOTAL_H = round(H + HEADER_H + FOOTER_H)
    # transform group so the map lives in a HEADER_H..HEADER_H+H band
    map_offset_y = HEADER_H

    # scale road widths & building strokes with map metres-per-pixel
    m_per_px = dx_m / W
    def road_stroke(base_mult):
        # target ~4.5m road at unclassified base
        return max(1.2, 4.5 * base_mult / m_per_px)

    layers = {
        "landuse_field": [],
        "landuse_meadow": [],
        "landuse_grass": [],
        "landuse_orchard": [],
        "landuse_farmyard": [],
        "landuse_cemetery": [],
        "landuse_forest": [],
        "water": [],
        "waterway": [],
        "road_shadow": [],
        "road": [],
        "footway": [],
        "building": [],
        "church_building": [],
        "barrier_wall": [],
        "barrier_hedge": [],
        "barrier_fence": [],
    }
    named_church_pts = []
    named_building_pts = []

    for f in features:
        geom = f.get("geometry") or {}
        gt = geom.get("type")
        props = f.get("properties") or {}
        if not gt: continue
        coords = geom.get("coordinates")

        # LANDUSE
        lu = props.get("landuse")
        if lu and gt in ("Polygon", "MultiPolygon"):
            polys = coords if gt == "MultiPolygon" else [coords]
            for poly in polys:
                d = polygon_to_path(poly, bbox, W, H)
                key = None
                if lu in ("farmland",): key = "landuse_field"
                elif lu in ("meadow","grass"): key = "landuse_meadow"
                elif lu == "orchard": key = "landuse_orchard"
                elif lu == "farmyard": key = "landuse_farmyard"
                elif lu == "cemetery": key = "landuse_cemetery"
                elif lu == "forest": key = "landuse_forest"
                if key: layers[key].append(d)

        # WATER
        if props.get("natural") == "water" and gt in ("Polygon","MultiPolygon"):
            polys = coords if gt == "MultiPolygon" else [coords]
            for poly in polys:
                layers["water"].append(polygon_to_path(poly, bbox, W, H))
        if props.get("waterway") and gt == "LineString":
            layers["waterway"].append(coords_to_path(coords, bbox, W, H))

        # BARRIERS
        barrier = props.get("barrier")
        if barrier and gt == "LineString":
            d = coords_to_path(coords, bbox, W, H)
            if barrier in ("wall","retaining_wall"): layers["barrier_wall"].append(d)
            elif barrier == "hedge": layers["barrier_hedge"].append(d)
            elif barrier == "fence": layers["barrier_fence"].append(d)

        # HIGHWAY
        hw = props.get("highway")
        if hw and gt == "LineString":
            style = HIGHWAY_STYLES.get(hw, HIGHWAY_STYLES["unclassified"])
            fill, stroke, mult = style
            d = coords_to_path(coords, bbox, W, H)
            sw = road_stroke(mult)
            if hw in ("footway","path","cycleway","steps"):
                layers["footway"].append((d, fill, stroke, sw))
            else:
                layers["road_shadow"].append((d, sw + 3, "#5a4a2a"))
                layers["road"].append((d, sw, fill))

        # BUILDINGS
        b = props.get("building")
        if b and gt in ("Polygon","MultiPolygon"):
            polys = coords if gt == "MultiPolygon" else [coords]
            is_church = (b == "church") or "church" in (props.get("name","") or "").lower() or props.get("religion") == "christian"
            for poly in polys:
                d = polygon_to_path(poly, bbox, W, H)
                if is_church:
                    layers["church_building"].append(d)
                    # centroid for marker
                    xs, ys = [], []
                    for (lon,lat) in poly[0]:
                        x, y = project(lon, lat, bbox, W, H)
                        xs.append(x); ys.append(y)
                    if xs:
                        named_church_pts.append((sum(xs)/len(xs), sum(ys)/len(ys),
                                                 props.get("name","")))
                else:
                    layers["building"].append(d)

    # ---- build SVG ----
    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {TOTAL_H}" font-family="Georgia, serif">')
    parts.append('<defs>')
    parts.append(f'<clipPath id="mapclip"><rect x="0" y="0" width="{W}" height="{H}"/></clipPath>')
    parts.append(f'<pattern id="fldp" width="18" height="18" patternUnits="userSpaceOnUse" patternTransform="rotate(30)">'
                 f'<rect width="18" height="18" fill="{COL_FIELD_FILL}"/>'
                 f'<line x1="0" y1="0" x2="0" y2="18" stroke="#a8c47a" stroke-width="1.5"/>'
                 f'</pattern>')
    parts.append(f'<pattern id="ymed" width="14" height="14" patternUnits="userSpaceOnUse">'
                 f'<rect width="14" height="14" fill="{COL_MEADOW}"/>'
                 f'<circle cx="7" cy="7" r="1" fill="#8fa860"/>'
                 f'</pattern>')
    parts.append('</defs>')

    # Header band
    parts.append(f'<rect x="0" y="0" width="{W}" height="{HEADER_H}" fill="#f5efdc"/>')
    parts.append(f'<text x="18" y="30" font-size="22" font-weight="bold" fill="{COL_TITLE}">'
                 f'{html.escape(layout["title"])}</text>')
    parts.append(f'<text x="18" y="52" font-size="12" fill="{COL_TITLE}">'
                 f'{html.escape(layout["subtitle"])}</text>')
    parts.append(f'<text x="18" y="70" font-size="11" fill="#5a4a2a" font-style="italic">'
                 f'Source: OpenStreetMap contributors. bbox {bbox[1]:.4f},{bbox[0]:.4f} → {bbox[3]:.4f},{bbox[2]:.4f} '
                 f'({dx_m:.0f} × {dy_m:.0f} m).</text>')

    # Map background: base field colour, then map viewport clipped to header offset
    parts.append(f'<g transform="translate(0,{map_offset_y})">')
    parts.append(f'<g clip-path="url(#mapclip)">')
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="url(#fldp)"/>')

    # order: landuse -> water -> road_shadow -> road -> footway -> buildings -> church -> barriers -> labels
    for d in layers["landuse_forest"]:
        parts.append(f'<path d="{d}" fill="#a9c78b" stroke="#5a7a3a" stroke-width="0.6" opacity="0.85"/>')
    for d in layers["landuse_field"]:
        parts.append(f'<path d="{d}" fill="url(#fldp)" stroke="#8a7c58" stroke-width="0.6" stroke-dasharray="3 2" opacity="0.95"/>')
    for d in layers["landuse_meadow"] + layers["landuse_grass"]:
        parts.append(f'<path d="{d}" fill="url(#ymed)" stroke="#8a7c58" stroke-width="0.5" stroke-dasharray="3 2" opacity="0.85"/>')
    for d in layers["landuse_orchard"]:
        parts.append(f'<path d="{d}" fill="{COL_ORCHARD}" stroke="#5a7a3a" stroke-width="0.5" opacity="0.85"/>')
    for d in layers["landuse_farmyard"]:
        parts.append(f'<path d="{d}" fill="#d9c98f" stroke="#8a7c58" stroke-width="0.6" opacity="0.85"/>')
    for d in layers["landuse_cemetery"]:
        parts.append(f'<path d="{d}" fill="#d4dfae" stroke="#6a7a3a" stroke-width="0.6" stroke-dasharray="2 2" opacity="0.9"/>')

    for d in layers["water"]:
        parts.append(f'<path d="{d}" fill="{COL_WATER}" stroke="{COL_WATER_STROKE}" stroke-width="1"/>')
    for d in layers["waterway"]:
        parts.append(f'<path d="{d}" fill="none" stroke="{COL_WATER_STROKE}" stroke-width="2.5" stroke-linecap="round"/>')

    # road shadow then road
    for d, sw, col in layers["road_shadow"]:
        parts.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{sw:.2f}" stroke-linecap="round" stroke-linejoin="round"/>')
    for d, sw, col in layers["road"]:
        parts.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{sw:.2f}" stroke-linecap="round" stroke-linejoin="round"/>')

    for d, fill, stroke, sw in layers["footway"]:
        parts.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw:.2f}" stroke-dasharray="4 3" opacity="0.7"/>')

    for d in layers["building"]:
        parts.append(f'<path d="{d}" fill="{COL_BUILDING_FILL}" stroke="{COL_BUILDING_STROKE}" stroke-width="0.7"/>')
    for d in layers["church_building"]:
        parts.append(f'<path d="{d}" fill="{COL_CHURCH_FILL}" stroke="{COL_CHURCH_STROKE}" stroke-width="1.2"/>')

    for d in layers["barrier_wall"]:
        parts.append(f'<path d="{d}" fill="none" stroke="{COL_WALL}" stroke-width="1.6" stroke-dasharray="6 3" opacity="0.9"/>')
    for d in layers["barrier_hedge"]:
        parts.append(f'<path d="{d}" fill="none" stroke="{COL_HEDGE}" stroke-width="2.2" opacity="0.85"/>')
    for d in layers["barrier_fence"]:
        parts.append(f'<path d="{d}" fill="none" stroke="{COL_WALL}" stroke-width="1.1" stroke-dasharray="3 2" opacity="0.85"/>')

    # cross symbol for churches (small +)
    for cx, cy, name in named_church_pts:
        parts.append(f'<g transform="translate({cx:.1f},{cy:.1f})">'
                     f'<circle r="10" fill="#f5efdc" stroke="{COL_CHURCH_STROKE}" stroke-width="1"/>'
                     f'<line x1="0" y1="-6" x2="0" y2="6" stroke="{COL_CHURCH_STROKE}" stroke-width="2"/>'
                     f'<line x1="-4" y1="-2" x2="4" y2="-2" stroke="{COL_CHURCH_STROKE}" stroke-width="2"/>'
                     f'</g>')

    # labels (from layout config)
    for lbl in layout.get("labels", []):
        lon, lat = lbl["lonlat"]
        x, y = project(lon, lat, bbox, W, H)
        anchor = lbl.get("anchor","start")
        parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{lbl.get("size",11)}" '
                     f'text-anchor="{anchor}" fill="{lbl.get("color","#3a2a10")}" '
                     f'font-style="{lbl.get("style","italic")}" font-weight="{lbl.get("weight","normal")}" '
                     f'stroke="white" stroke-width="3" paint-order="stroke" stroke-linejoin="round">'
                     f'{html.escape(lbl["text"])}</text>')

    # truck start + fire markers
    def marker(lonlat, color, letter, name):
        x, y = project(lonlat[0], lonlat[1], bbox, W, H)
        parts.append(f'<g transform="translate({x:.1f},{y:.1f})">'
                     f'<circle r="12" fill="{color}" stroke="#1a1a1a" stroke-width="1.5"/>'
                     f'<text y="4" text-anchor="middle" font-size="13" font-weight="bold" fill="white">{letter}</text>'
                     f'</g>')
        parts.append(f'<text x="{x+16:.1f}" y="{y+5:.1f}" font-size="11" fill="#1a1a1a" '
                     f'stroke="white" stroke-width="3" paint-order="stroke" stroke-linejoin="round">{html.escape(name)}</text>')

    if "truck" in layout: marker(layout["truck"], "#2a5a9e", "S", "truck start")
    if "fire" in layout:  marker(layout["fire"],  "#d94f2a", "F", "FIRE")

    # compass in top-right
    parts.append(f'<g transform="translate({W-40},34)">'
                 f'<circle r="22" fill="#f5efdc" stroke="{COL_STONE_STROKE}" stroke-width="1.2"/>'
                 f'<line x1="0" y1="-18" x2="0" y2="18" stroke="{COL_STONE_STROKE}"/>'
                 f'<line x1="-18" y1="0" x2="18" y2="0" stroke="{COL_STONE_STROKE}"/>'
                 f'<text y="-8" text-anchor="middle" font-size="11" font-weight="bold" fill="{COL_TITLE}">N</text>'
                 f'<text y="16" text-anchor="middle" font-size="11" fill="{COL_TITLE}">S</text>'
                 f'<text x="-13" y="4" font-size="11" fill="{COL_TITLE}">W</text>'
                 f'<text x="9" y="4" font-size="11" fill="{COL_TITLE}">E</text>'
                 f'</g>')

    # scale bar (100 m)
    px_100m = 100.0 / m_per_px
    parts.append(f'<g transform="translate(18,{H-24})">'
                 f'<line x1="0" y1="0" x2="{px_100m:.1f}" y2="0" stroke="{COL_TITLE}" stroke-width="3"/>'
                 f'<line x1="0" y1="-4" x2="0" y2="4" stroke="{COL_TITLE}" stroke-width="2"/>'
                 f'<line x1="{px_100m:.1f}" y1="-4" x2="{px_100m:.1f}" y2="4" stroke="{COL_TITLE}" stroke-width="2"/>'
                 f'<text x="{px_100m/2:.1f}" y="-8" text-anchor="middle" font-size="11" fill="{COL_TITLE}">100 m</text>'
                 f'</g>')

    parts.append('</g>')  # close clip-path group
    parts.append('</g>')  # close map group

    # Footer legend
    fy = HEADER_H + H + 22
    lg = [
        ('rect', COL_BUILDING_FILL, COL_BUILDING_STROKE, 'building'),
        ('rect', COL_CHURCH_FILL, COL_CHURCH_STROKE, 'church'),
        ('road', '#f2c568', '#7a5b1a', 'A-road (primary)'),
        ('road', '#ffffff', '#6b5b3a', 'lane / residential'),
        ('rect', 'url(#fldp)', '#8a7c58', 'field'),
        ('rect', COL_WATER, COL_WATER_STROKE, 'water'),
        ('dash', COL_WALL, None, 'wall'),
        ('dash', COL_HEDGE, None, 'hedge'),
    ]
    x_cursor = 18
    for kind, fill, stroke, label in lg:
        if kind == 'rect':
            parts.append(f'<rect x="{x_cursor}" y="{fy-9}" width="16" height="10" fill="{fill}" stroke="{stroke}"/>')
        elif kind == 'road':
            parts.append(f'<line x1="{x_cursor}" y1="{fy-4}" x2="{x_cursor+16}" y2="{fy-4}" stroke="{stroke}" stroke-width="6" stroke-linecap="butt"/>')
            parts.append(f'<line x1="{x_cursor}" y1="{fy-4}" x2="{x_cursor+16}" y2="{fy-4}" stroke="{fill}" stroke-width="4"/>')
        elif kind == 'dash':
            dash = "6 3" if fill == COL_WALL else "0"
            parts.append(f'<line x1="{x_cursor}" y1="{fy-4}" x2="{x_cursor+16}" y2="{fy-4}" stroke="{fill}" stroke-width="2" stroke-dasharray="{dash}"/>')
        parts.append(f'<text x="{x_cursor+22}" y="{fy}" font-size="11" fill="{COL_TITLE}">{label}</text>')
        x_cursor += 22 + 8 * len(label) + 14

    # markers legend
    parts.append(f'<circle cx="{x_cursor}" cy="{fy-4}" r="6" fill="#2a5a9e"/><text x="{x_cursor+10}" y="{fy}" font-size="11" fill="{COL_TITLE}">truck start</text>')
    x_cursor += 90
    parts.append(f'<circle cx="{x_cursor}" cy="{fy-4}" r="6" fill="#d94f2a"/><text x="{x_cursor+10}" y="{fy}" font-size="11" fill="{COL_TITLE}">fire</text>')

    parts.append('</svg>')
    with open(out_path, 'w') as f:
        f.write('\n'.join(parts))

# ---- LAYOUT DEFINITIONS ----
# St Mary's church at approx (-2.19478, 51.78527).
LAYOUTS = [
    dict(
        slug="1-town-core",
        title="Option 1 — Town Centre Core (around St Mary's)",
        subtitle="Tight medieval knot: Bisley St, New St, Victoria St, St Mary's St, Friday St, top of Tibbiwell. Church + Town Hall dead centre.",
        bbox=(-2.1975, 51.7838, -2.1912, 51.7876),
        labels=[
            dict(lonlat=(-2.1948, 51.7863), text="Bisley St", size=12),
            dict(lonlat=(-2.1947, 51.78585), text="New St",   size=12),
            dict(lonlat=(-2.1937, 51.78580), text="Friday St", size=10),
            dict(lonlat=(-2.1929, 51.78500), text="Tibbiwell →", size=11),
            dict(lonlat=(-2.1942, 51.78576), text="Victoria St", size=10),
            dict(lonlat=(-2.1948, 51.7853),  text="St Mary's + 99 yews", size=11, weight="bold"),
            dict(lonlat=(-2.1947, 51.78603), text="Town Hall", size=10),
        ],
        truck=(-2.1938, 51.7842),  # arriving up New St from S
        fire=(-2.1918,  51.7867),  # cottage on Vicarage St / Hollyhock corner
    ),
    dict(
        slug="2-north-y-gateway",
        title="Option 2 — North Y-Gateway (Cheltenham & Gloucester meet)",
        subtitle="Slip in from the north: Cheltenham Rd + Gloucester St Y-junction, Butt Green + Pullens Rd loops, Croft Primary, down to top of New St.",
        bbox=(-2.1980, 51.7870, -2.1898, 51.7905),
        labels=[
            dict(lonlat=(-2.1930, 51.7900), text="Cheltenham Rd", size=12),
            dict(lonlat=(-2.1945, 51.7890), text="Gloucester St", size=12),
            dict(lonlat=(-2.1940, 51.7893), text="Pullens Rd", size=11),
            dict(lonlat=(-2.1958, 51.7887), text="Butt Green", size=11),
            dict(lonlat=(-2.1962, 51.7881), text="Croft Primary", size=10),
            dict(lonlat=(-2.1946, 51.7873), text="→ New St", size=11),
        ],
        truck=(-2.1930, 51.7902),  # arriving down Cheltenham Rd
        fire=(-2.1958,  51.7884),  # cottage near Croft
    ),
    dict(
        slug="3-east-slope-stream",
        title="Option 3 — East Slope to Painswick Stream",
        subtitle="Vicarage St and lanes descend E from the church to the Painswick Stream. Recreation Ground fills the N; churchyard + church on W edge.",
        bbox=(-2.1955, 51.7840, -2.1858, 51.7880),
        labels=[
            dict(lonlat=(-2.1908, 51.78628), text="Vicarage St", size=12),
            dict(lonlat=(-2.1948, 51.7853),  text="St Mary's", size=11, weight="bold"),
            dict(lonlat=(-2.1902, 51.7873),  text="Recreation Ground", size=11),
            dict(lonlat=(-2.1870, 51.7860),  text="→ Painswick Stream", size=11, color=COL_WATER_STROKE),
            dict(lonlat=(-2.1916, 51.7849),  text="Tibbiwell Lane", size=10),
        ],
        truck=(-2.1948, 51.7860),  # west edge next to church
        fire=(-2.1880,  51.7853),  # old mill / house down by stream
    ),
    dict(
        slug="4-a46-spine",
        title="Option 4 — Full A46 Spine (Cheltenham → Stroud Rd)",
        subtitle="Long thin: the whole A46 through the village. Side lanes stub off left & right; the church sits on the west shoulder mid-way. Longest drive.",
        bbox=(-2.1975, 51.7815, -2.1905, 51.7900),
        labels=[
            dict(lonlat=(-2.1930, 51.7896), text="Cheltenham Rd (enters N)", size=11),
            dict(lonlat=(-2.1946, 51.7886), text="Gloucester St", size=11),
            dict(lonlat=(-2.1947, 51.78621),text="New St", size=12, weight="bold"),
            dict(lonlat=(-2.1948, 51.7853), text="St Mary's", size=11, weight="bold"),
            dict(lonlat=(-2.1935, 51.7830), text="Stroud Rd →", size=11),
            dict(lonlat=(-2.1916, 51.7849), text="Tibbiwell", size=10),
            dict(lonlat=(-2.1930, 51.7845), text="Kemps Ln", size=10),
        ],
        truck=(-2.1930, 51.7898),  # start at Cheltenham approach
        fire=(-2.1945,  51.7825),  # house at Stroud Rd end
    ),
    dict(
        slug="5-southeast-knot",
        title="Option 5 — South-East Knot (max maze)",
        subtitle="The densest lane tangle: Tibbiwell, Hale, Kemps, Knapp, Ticklestone, top of Kingsmill. St Mary's anchors the NW corner; Painswick Stream to the SE.",
        bbox=(-2.1955, 51.7810, -2.1875, 51.7860),
        labels=[
            dict(lonlat=(-2.1948, 51.7853), text="St Mary's", size=11, weight="bold"),
            dict(lonlat=(-2.1916, 51.78487),text="Tibbiwell Lane", size=11),
            dict(lonlat=(-2.1940, 51.78478),text="Hale Lane", size=10),
            dict(lonlat=(-2.1933, 51.78449),text="Kemps Lane", size=10),
            dict(lonlat=(-2.1939, 51.78264),text="Knapp Lane", size=10),
            dict(lonlat=(-2.1927, 51.78155),text="Ticklestone Ln", size=10),
        ],
        truck=(-2.1948, 51.7855),  # by church
        fire=(-2.1900,  51.7818),  # cottage down at Ticklestone/Knapp
    ),
]

def main():
    with open(GEO) as f:
        gj = json.load(f)
    features = gj["features"]
    os.makedirs(OUT_DIR, exist_ok=True)
    for L in LAYOUTS:
        sub = [f for f in features if bbox_intersects_geom(L["bbox"], f.get("geometry") or {})]
        out = f"{OUT_DIR}/2026-08-02-painswick-layout-{L['slug']}.svg"
        render_layout(sub, L, out)
        print(f"wrote {out}  ({len(sub)} features)")

if __name__ == "__main__":
    main()
