"""Prüft DeskLayout.json und zeichnet daraus grundriss.svg.

Aufruf:  python grundriss_erzeugen.py
Alle Maße in Zentimetern, Ursprung = Raummitte, +x nach rechts (Osten),
+y nach unten (Süden) – das entspricht der UE-Draufsicht (X rechts, Y unten).
yaw = Blickrichtung der Person, die den Platz benutzt (0° = +x, 90° = +y).
"""
import json
import math
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).parent
ROOM_W, ROOM_D = 1600, 1100          # Innenmaß
HX, HY = ROOM_W / 2, ROOM_D / 2
WALL = 25

DESK_W, DESK_D = 160, 80             # Tischplatte
CHAIR_ZONE = 80                      # Stuhl + Zurückrollen hinter dem Tisch
SEAT_OFFSET = 75                     # Tischmitte -> Sitzmitte
BOARD_W, BOARD_D = 200, 10           # Wandtafel
STAND_ZONE = 100                     # Stehfläche vor der Tafel
CHAIR = 60                           # Besprechungsstuhl
MEET_TABLE = (540, 0, 220, 100)      # cx, cy, Breite (x), Tiefe (y)
GLASS_X = 280                        # Glaswand Besprechungsraum (West)
GLASS_Y = 330                        # Glaswand Besprechungsraum (Nord/Süd, ±)
MIN_AISLE = 120


def footprint(p):
    """Achsparallele Grundfläche eines Platzes inkl. Nutzungszone (x0, y0, x1, y1)."""
    a = math.radians(p["yaw"])
    fx, fy = round(math.cos(a)), round(math.sin(a))   # Blickrichtung (nur 0/90/180/270)
    x, y = p["x"], p["y"]
    if p["type"] == "desk":
        # Tisch quer zur Blickrichtung, Stuhlzone entgegen der Blickrichtung
        w, d = (DESK_D, DESK_W) if fx else (DESK_W, DESK_D)
        box = [x - w / 2, y - d / 2, x + w / 2, y + d / 2]
        if fx > 0: box[0] -= CHAIR_ZONE
        if fx < 0: box[2] += CHAIR_ZONE
        if fy > 0: box[1] -= CHAIR_ZONE
        if fy < 0: box[3] += CHAIR_ZONE
        return box
    if p["type"] == "station":
        w, d = (BOARD_D, BOARD_W) if fx else (BOARD_W, BOARD_D)
        box = [x - w / 2, y - d / 2, x + w / 2, y + d / 2]
        # Person steht vor der Tafel, also entgegen der Blickrichtung
        if fx > 0: box[0] -= STAND_ZONE
        if fx < 0: box[2] += STAND_ZONE
        if fy > 0: box[1] -= STAND_ZONE
        if fy < 0: box[3] += STAND_ZONE
        return box
    return [x - CHAIR / 2, y - CHAIR / 2, x + CHAIR / 2, y + CHAIR / 2]


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0)
    dy = max(b[1] - a[3], a[1] - b[3], 0)
    return math.hypot(dx, dy)


def check(places):
    errors = []
    ids = [p["deskId"] for p in places]
    expected = [f"desk-{i}" for i in range(1, 9)] + ["station-pulls", "station-queue"] + [f"meeting-{i}" for i in range(1, 5)]
    if sorted(ids) != sorted(expected):
        errors.append(f"IDs stimmen nicht: {sorted(set(expected) ^ set(ids))}")
    boxes = {p["deskId"]: footprint(p) for p in places}
    for pid, b in boxes.items():
        if b[0] < -HX or b[2] > HX or b[1] < -HY or b[3] > HY:
            errors.append(f"{pid} ragt aus dem Raum")
    for (ia, a), (ib, b) in combinations(boxes.items(), 2):
        if overlap(a, b):
            errors.append(f"{ia} überlappt {ib}")
    tx, ty, tw, td = MEET_TABLE
    table = [tx - tw / 2, ty - td / 2, tx + tw / 2, ty + td / 2]
    for pid, b in boxes.items():
        if overlap(b, table):
            errors.append(f"{pid} überlappt den Besprechungstisch")
    # Gänge zwischen den Tischinseln und zur Glaswand
    desks = [b for pid, b in boxes.items() if pid.startswith("desk")]
    xs = sorted({(b[0], b[2]) for b in desks})
    islands = []
    for x0, x1 in xs:
        if islands and x0 - islands[-1][1] < 10:
            islands[-1][1] = max(islands[-1][1], x1)
        else:
            islands.append([x0, x1])
    aisles = [islands[i + 1][0] - islands[i][1] for i in range(len(islands) - 1)]
    aisles.append(GLASS_X - islands[-1][1])
    aisles.append(islands[0][0] + HX)
    for w in aisles:
        if w < MIN_AISLE:
            errors.append(f"Gang nur {w:.0f} cm breit")
    return boxes, islands, aisles, errors


# ---------------------------------------------------------------- Zeichnung
INK = "#23272a"
MUTED = "#7b8085"
LINE = "#c9c6bf"
CONCRETE = "#d9d6cf"
OAK = "#e8dcc8"
GLASS = "#9fb4ba"
ACCENT = "#b08d57"


def svg(places, boxes, islands, aisles):
    out = []
    w = out.append
    vb = (-HX - 120, -HY - 170, ROOM_W + 240, ROOM_D + 370)
    w(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb[0]} {vb[1]} {vb[2]} {vb[3]}" '
      f'width="{vb[2] * 0.75:.0f}" height="{vb[3] * 0.75:.0f}" font-family="Helvetica, Arial, sans-serif">')
    w('<title>Agent Office – Grundriss Erdgeschoss</title>')
    w('<defs><pattern id="hatch" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
      f'<line x1="0" y1="0" x2="0" y2="12" stroke="{MUTED}" stroke-width="2"/></pattern>'
      '<pattern id="oak" width="40" height="400" patternUnits="userSpaceOnUse">'
      f'<rect width="40" height="400" fill="{OAK}"/><line x1="0" y1="0" x2="0" y2="400" stroke="#ddcfb8" stroke-width="1.5"/></pattern></defs>')
    w(f'<rect x="{vb[0]}" y="{vb[1]}" width="{vb[2]}" height="{vb[3]}" fill="#f7f5f0"/>')

    # Boden
    w(f'<rect x="{-HX}" y="{-HY}" width="{ROOM_W}" height="{ROOM_D}" fill="url(#oak)"/>')
    # Wände (Sichtbeton) Nord + Ost, Fensterfronten West + Süd
    w(f'<rect x="{-HX - WALL}" y="{-HY - WALL}" width="{ROOM_W + 2 * WALL}" height="{WALL}" fill="url(#hatch)" stroke="{INK}" stroke-width="3"/>')
    w(f'<rect x="{HX}" y="{-HY}" width="{WALL}" height="{ROOM_D + WALL}" fill="url(#hatch)" stroke="{INK}" stroke-width="3"/>')
    for x0, y0, x1, y1 in [(-HX - WALL, -HY, -HX, HY + WALL), (-HX - WALL, HY, HX, HY + WALL)]:
        w(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="#eef3f4" stroke="{INK}" stroke-width="3"/>')
    w(f'<line x1="{-HX - WALL / 2}" y1="{-HY}" x2="{-HX - WALL / 2}" y2="{HY + WALL / 2}" stroke="{GLASS}" stroke-width="4"/>')
    w(f'<line x1="{-HX - WALL / 2}" y1="{HY + WALL / 2}" x2="{HX}" y2="{HY + WALL / 2}" stroke="{GLASS}" stroke-width="4"/>')
    for i in range(1, 6):   # Fensterpfosten
        y = -HY + i * ROOM_D / 6
        w(f'<line x1="{-HX - WALL}" y1="{y}" x2="{-HX}" y2="{y}" stroke="{INK}" stroke-width="3"/>')
    for i in range(1, 8):
        x = -HX + i * ROOM_W / 8
        w(f'<line x1="{x}" y1="{HY}" x2="{x}" y2="{HY + WALL}" stroke="{INK}" stroke-width="3"/>')
    # Eingang Nordwand
    w(f'<rect x="160" y="{-HY - WALL - 2}" width="100" height="{WALL + 4}" fill="url(#oak)"/>')
    w(f'<path d="M160 {-HY} A100 100 0 0 1 260 {-HY + 100}" fill="none" stroke="{MUTED}" stroke-width="2" stroke-dasharray="6 6"/>')
    w(f'<line x1="160" y1="{-HY}" x2="160" y2="{-HY + 100}" stroke="{INK}" stroke-width="3"/>')
    w(f'<text x="210" y="{-HY - WALL - 14}" text-anchor="middle" font-size="20" fill="{MUTED}">EINGANG</text>')

    # Besprechungsraum (Glas)
    w(f'<rect x="{GLASS_X}" y="{-GLASS_Y}" width="{HX - GLASS_X}" height="{2 * GLASS_Y}" fill="#ffffff" fill-opacity="0.35"/>')
    gl = f'stroke="{GLASS}" stroke-width="6"'
    w(f'<line x1="{GLASS_X}" y1="{-GLASS_Y}" x2="{HX}" y2="{-GLASS_Y}" {gl}/>')
    w(f'<line x1="{GLASS_X}" y1="{GLASS_Y}" x2="{HX}" y2="{GLASS_Y}" {gl}/>')
    w(f'<line x1="{GLASS_X}" y1="{-GLASS_Y}" x2="{GLASS_X}" y2="{-GLASS_Y + 90}" {gl}/>')
    w(f'<line x1="{GLASS_X}" y1="{-GLASS_Y + 190}" x2="{GLASS_X}" y2="{GLASS_Y}" {gl}/>')
    w(f'<path d="M{GLASS_X} {-GLASS_Y + 90} A100 100 0 0 1 {GLASS_X + 100} {-GLASS_Y + 190}" fill="none" stroke="{MUTED}" stroke-width="2" stroke-dasharray="6 6"/>')
    w(f'<text x="{(GLASS_X + HX) / 2}" y="{-GLASS_Y + 50}" text-anchor="middle" font-size="22" letter-spacing="3" fill="{MUTED}">BESPRECHUNG</text>')
    tx, ty, tw, td = MEET_TABLE
    w(f'<rect x="{tx - tw / 2}" y="{ty - td / 2}" width="{tw}" height="{td}" rx="8" fill="#ffffff" stroke="{INK}" stroke-width="3"/>')

    # Küche + Lounge (Möblierung, keine Plätze)
    w(f'<rect x="380" y="{HY - 65}" width="400" height="65" fill="{CONCRETE}" stroke="{INK}" stroke-width="2"/>')
    w(f'<text x="580" y="{HY - 85}" text-anchor="middle" font-size="20" letter-spacing="3" fill="{MUTED}">KÜCHE</text>')
    w(f'<rect x="-640" y="400" width="240" height="90" rx="20" fill="#8a948a" stroke="{INK}" stroke-width="2"/>')
    w(f'<circle cx="-520" cy="330" r="40" fill="#ffffff" stroke="{INK}" stroke-width="2"/>')
    w(f'<text x="-520" y="260" text-anchor="middle" font-size="20" letter-spacing="3" fill="{MUTED}">LOUNGE</text>')
    for cx, cy in [(-760, -500), (-760, 500), (330, 500), (340, -500)]:
        w(f'<circle cx="{cx}" cy="{cy}" r="28" fill="#9aa592" stroke="{INK}" stroke-width="1.5"/>')

    # Plätze
    for p in places:
        pid, x, y, yaw = p["deskId"], p["x"], p["y"], p["yaw"]
        a = math.radians(yaw)
        fx, fy = math.cos(a), math.sin(a)
        b = boxes[pid]
        w(f'<rect x="{b[0]}" y="{b[1]}" width="{b[2] - b[0]}" height="{b[3] - b[1]}" fill="none" stroke="{LINE}" stroke-width="1.5" stroke-dasharray="4 5"/>')
        if p["type"] == "desk":
            dw, dd = (DESK_D, DESK_W) if abs(fx) > 0.5 else (DESK_W, DESK_D)
            w(f'<rect x="{x - dw / 2}" y="{y - dd / 2}" width="{dw}" height="{dd}" fill="#ffffff" stroke="{INK}" stroke-width="3"/>')
            mx, my = x + fx * 28, y + fy * 28            # Monitor zur Tischmitte hin
            w(f'<line x1="{mx - 35 * abs(fy)}" y1="{my - 35 * abs(fx)}" x2="{mx + 35 * abs(fy)}" y2="{my + 35 * abs(fx)}" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>')
            sx, sy = x - fx * SEAT_OFFSET, y - fy * SEAT_OFFSET
            w(f'<circle cx="{sx}" cy="{sy}" r="24" fill="{CONCRETE}" stroke="{INK}" stroke-width="2"/>')
            w(f'<text x="{x}" y="{y + 7}" text-anchor="middle" font-size="20" font-weight="bold" fill="{INK}">{pid}</text>')
        elif p["type"] == "station":
            w(f'<rect x="{x - BOARD_W / 2}" y="{y - BOARD_D / 2}" width="{BOARD_W}" height="{BOARD_D}" fill="{ACCENT}" stroke="{INK}" stroke-width="2"/>')
            w(f'<text x="{x}" y="{y + 140}" text-anchor="middle" font-size="20" font-weight="bold" fill="{INK}">{pid}</text>')
            w(f'<text x="{x}" y="{y + 164}" text-anchor="middle" font-size="17" fill="{MUTED}">{p["label"]}</text>')
            sx, sy = x - fx * 70, y - fy * 70
            w(f'<circle cx="{sx}" cy="{sy}" r="6" fill="{INK}"/>')
        else:
            w(f'<rect x="{x - 25}" y="{y - 25}" width="50" height="50" rx="10" fill="{CONCRETE}" stroke="{INK}" stroke-width="2"/>')
            ly = y + (-42 if fy > 0.5 else 52) if abs(fy) > 0.5 else y + 62
            w(f'<text x="{x}" y="{ly}" text-anchor="middle" font-size="18" font-weight="bold" fill="{INK}">{pid}</text>')
        # Blickrichtungspfeil
        ox, oy = (x - fx * SEAT_OFFSET, y - fy * SEAT_OFFSET) if p["type"] == "desk" else (x, y) if p["type"] == "meeting" else (x - fx * 70, y - fy * 70)
        ex, ey = ox + fx * 26, oy + fy * 26
        w(f'<line x1="{ox}" y1="{oy}" x2="{ex}" y2="{ey}" stroke="{ACCENT}" stroke-width="3"/>')
        px, py = -fy, fx
        w(f'<polygon points="{ex + fx * 10},{ey + fy * 10} {ex + px * 7},{ey + py * 7} {ex - px * 7},{ey - py * 7}" fill="{ACCENT}"/>')

    # Gangmaße
    def dim_h(x0, x1, y, label):
        w(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{INK}" stroke-width="1.5"/>')
        for xx in (x0, x1):
            w(f'<line x1="{xx}" y1="{y - 10}" x2="{xx}" y2="{y + 10}" stroke="{INK}" stroke-width="1.5"/>')
        w(f'<text x="{(x0 + x1) / 2}" y="{y - 10}" text-anchor="middle" font-size="16" fill="{INK}">{label}</text>')

    dim_h(islands[0][1], islands[1][0], 215, f"{islands[1][0] - islands[0][1]:.0f}")
    dim_h(islands[1][1], GLASS_X, 215, f"{GLASS_X - islands[1][1]:.0f}")
    dim_h(-HX, islands[0][0], 215, f"{islands[0][0] + HX:.0f}")
    # Raummaße
    dim_h(-HX, HX, HY + WALL + 55, f"{ROOM_W} cm")
    w(f'<line x1="{HX + WALL + 45}" y1="{-HY}" x2="{HX + WALL + 45}" y2="{HY}" stroke="{INK}" stroke-width="1.5"/>')
    for yy in (-HY, HY):
        w(f'<line x1="{HX + WALL + 35}" y1="{yy}" x2="{HX + WALL + 55}" y2="{yy}" stroke="{INK}" stroke-width="1.5"/>')
    w(f'<text x="{HX + WALL + 75}" y="0" font-size="16" fill="{INK}" transform="rotate(90 {HX + WALL + 75} 0)" text-anchor="middle">{ROOM_D} cm</text>')

    # Ursprung + Achsen
    w(f'<circle cx="0" cy="0" r="7" fill="none" stroke="{ACCENT}" stroke-width="2"/>')
    w(f'<line x1="-14" y1="0" x2="14" y2="0" stroke="{ACCENT}" stroke-width="2"/><line x1="0" y1="-14" x2="0" y2="14" stroke="{ACCENT}" stroke-width="2"/>')

    # Kopf + Legende
    top = -HY - 120
    w(f'<text x="{-HX}" y="{top}" font-size="40" font-weight="bold" fill="{INK}">Agent Office – Grundriss</text>')
    w(f'<text x="{-HX}" y="{top + 34}" font-size="19" fill="{MUTED}">Maße in cm · Ursprung (0,0) = Raummitte · +x Osten (rechts), +y Süden (unten) · yaw 0° = +x, 90° = +y</text>')
    lx = HX - 520
    w(f'<g font-size="16" fill="{INK}">'
      f'<line x1="{lx}" y1="{top - 8}" x2="{lx + 30}" y2="{top - 8}" stroke="{ACCENT}" stroke-width="3"/><text x="{lx + 40}" y="{top - 2}">Blickrichtung (yaw)</text>'
      f'<rect x="{lx}" y="{top + 12}" width="30" height="16" fill="none" stroke="{LINE}" stroke-dasharray="4 5" stroke-width="1.5"/><text x="{lx + 40}" y="{top + 26}">Nutzungszone (Tisch + Stuhl)</text>'
      f'<line x1="{lx + 270}" y1="{top - 8}" x2="{lx + 300}" y2="{top - 8}" stroke="{GLASS}" stroke-width="5"/><text x="{lx + 310}" y="{top - 2}">Glas / Fenster</text>'
      f'<rect x="{lx + 270}" y="{top + 12}" width="30" height="16" fill="url(#hatch)" stroke="{INK}"/><text x="{lx + 310}" y="{top + 26}">Sichtbeton</text></g>')
    # Maßstab
    sy = HY + WALL + 120
    for i in range(5):
        w(f'<rect x="{-HX + i * 100}" y="{sy}" width="100" height="12" fill="{INK if i % 2 == 0 else "#ffffff"}" stroke="{INK}" stroke-width="1.5"/>')
    w(f'<text x="{-HX}" y="{sy + 36}" font-size="16" fill="{INK}">0</text><text x="{-HX + 500}" y="{sy + 36}" font-size="16" fill="{INK}" text-anchor="end">5 m</text>')
    w(f'<text x="{HX}" y="{sy + 12}" font-size="16" fill="{MUTED}" text-anchor="end">Tisch 160 × 80 · Tafel 200 × 10 · Besprechungstisch 220 × 100 · Gänge ≥ {MIN_AISLE}</text>')
    w('</svg>')
    return "\n".join(out)


if __name__ == "__main__":
    places = json.loads((HERE / "DeskLayout.json").read_text(encoding="utf-8"))
    boxes, islands, aisles, errors = check(places)
    if errors:
        raise SystemExit("Fehler:\n- " + "\n- ".join(errors))
    (HERE / "grundriss.svg").write_text(svg(places, boxes, islands, aisles), encoding="utf-8")
    print(f"OK: {len(places)} Plätze, keine Überlappung, Gänge {', '.join(f'{a:.0f}' for a in aisles)} cm")
