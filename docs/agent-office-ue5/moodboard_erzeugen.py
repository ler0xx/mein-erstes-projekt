"""Zeichnet moodboard.svg: Stimmungsskizze (Perspektive), Palette, Materialien, Figurdetail.

Aufruf:  python moodboard_erzeugen.py
Alles selbst gezeichnet, keine fremden Bilder.
"""
import random
from pathlib import Path

HERE = Path(__file__).parent
rng = random.Random(4)

PALETTE = [
    ("Sichtbeton", "#B9B6AF"),
    ("Eiche geölt", "#A7825A"),
    ("Rauchglas", "#6F7A7D"),
    ("Anzug Anthrazit", "#1E2023"),
    ("Hemd Weiß", "#EDEBE6"),
    ("Stahl Schwarz", "#2B2D2F"),
    ("Wollfilz Salbei", "#7D8B78"),
    ("Messing", "#B08D57"),
    ("Tageslicht 5200 K", "#F4EFE6"),
]
# Agentenfarben – bewusst entsättigt, nur als kleine Akzente
AGENT = ["#B5654A", "#4F7A8C", "#8C7A3F", "#6E5E8C", "#5E8C6A", "#8C4F62", "#4F5E8C", "#A0763A"]
SKIN = ["#C79A7C", "#8D5B3E", "#E2BFA3", "#5C3B2A", "#B07D5B", "#D6AA8A"]
HAIR = ["#1B1714", "#3A2A1F", "#0E0D0C", "#5A4636", "#2A2522", "#7A7570"]

W, H = 1600, 1000
SK = 1000                      # Breite der Skizze
CX, CY, F, EYE = 500, 470, 520, 165   # Fluchtpunkt, Brennweite (px), Augenhöhe (cm)


def P(x, y, z):
    return CX + F * x / z, CY - F * (y - EYE) / z


def poly(pts, **attrs):
    a = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" {a}/>'


def quad_x(x, y0, y1, z0, z1, **a):      # Fläche bei konstantem x (Seitenwand)
    return poly([P(x, y0, z0), P(x, y1, z0), P(x, y1, z1), P(x, y0, z1)], **a)


def quad_y(y, x0, x1, z0, z1, **a):      # Fläche bei konstantem y (Boden/Decke/Tischplatte)
    return poly([P(x0, y, z0), P(x1, y, z0), P(x1, y, z1), P(x0, y, z1)], **a)


def quad_z(z, x0, x1, y0, y1, **a):      # Fläche bei konstantem z (frontal)
    return poly([P(x0, y0, z), P(x1, y0, z), P(x1, y1, z), P(x0, y1, z)], **a)


def line(a, b, **attrs):
    at = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" {at}/>'


def agent(x, z, facing_camera, i, seated=True):
    """Sitzende Figur, Mittelpunkt x/z in cm. Gibt SVG-Gruppe zurück."""
    s = F / z
    bx, by = P(x, 0, z)
    u = lambda dx, dy: (bx + dx * s, by - dy * s)   # cm -> px relativ zum Fußpunkt
    skin, hair, col = SKIN[i % len(SKIN)], HAIR[i % len(HAIR)], AGENT[i % len(AGENT)]
    g = []
    # Stuhl (Lehne nur von hinten sichtbar)
    if not facing_camera:
        g.append(poly([u(-24, 50), u(24, 50), u(22, 112), u(-22, 112)], fill="#2B2D2F"))
    # Rumpf / Sakko
    g.append(poly([u(-24, 48), u(24, 48), u(23, 100), u(17, 112), u(-17, 112), u(-23, 100)], fill="#1E2023"))
    if facing_camera:
        g.append(poly([u(-7, 112), u(7, 112), u(0, 82)], fill="#EDEBE6"))             # Hemd
        g.append(poly([u(-1.6, 109), u(1.6, 109), u(2.4, 86), u(0, 82), u(-2.4, 86)], fill="#0B0B0C"))  # Krawatte
        g.append(line(u(-2.6, 96), u(2.6, 96), stroke=col, stroke_width=max(1, 1.6 * s)))  # Krawattennadel
    # Hals + Kopf
    g.append(poly([u(-5, 110), u(5, 110), u(5, 118), u(-5, 118)], fill=skin))
    hx, hy = u(0, 129)
    g.append(f'<ellipse cx="{hx:.1f}" cy="{hy:.1f}" rx="{9.5 * s:.1f}" ry="{12 * s:.1f}" fill="{skin if facing_camera else hair}"/>')
    if facing_camera:
        g.append(f'<path d="M{u(-9.6, 131)[0]:.1f} {u(-9.6, 131)[1]:.1f} Q{hx:.1f} {u(0, 147)[1]:.1f} {u(9.6, 131)[0]:.1f} {u(9.6, 131)[1]:.1f} '
                 f'L{u(9, 135)[0]:.1f} {u(9, 135)[1]:.1f} Q{hx:.1f} {u(0, 142)[1]:.1f} {u(-9, 135)[0]:.1f} {u(-9, 135)[1]:.1f}Z" fill="{hair}"/>')
        # Sonnenbrille
        for sx in (-4.4, 4.4):
            ex, ey = u(sx, 128)
            g.append(f'<rect x="{ex - 3.6 * s:.1f}" y="{ey - 2.2 * s:.1f}" width="{7.2 * s:.1f}" height="{4.4 * s:.1f}" rx="{1.4 * s:.1f}" fill="#070708"/>')
        g.append(line(u(-1, 128.8), u(1, 128.8), stroke="#070708", stroke_width=max(0.8, 0.9 * s)))
    return "".join(g)


def sketch():
    o = []
    w = o.append
    w(f'<clipPath id="skc"><rect width="{SK}" height="{H}"/></clipPath><g clip-path="url(#skc)">')
    # Grundflächen (Raum: x ±520, y 0..310, z 160..1700)
    X0, X1, Y1, ZN, ZF = -520, 520, 310, 160, 1700
    w(quad_x(X0, 0, Y1, ZN, ZF, fill="#E9E6DE"))                       # Fensterwand (hell)
    w(quad_x(X1, 0, Y1, ZN, ZF, fill="url(#beton)"))                   # Betonwand
    w(quad_y(Y1, X0, X1, ZN, ZF, fill="#A9A6A0"))                      # Decke
    w(quad_y(0, X0, X1, ZN, ZF, fill="url(#eicheP)"))                  # Boden
    w(quad_z(ZF, X0, X1, 0, Y1, fill="#C9C7C1"))                       # Rückwand
    # Besprechungsraum hinten (Glas)
    w(quad_z(ZF - 2, -260, 380, 0, 270, fill="#8FA2A7", fill_opacity="0.35", stroke="#5C6669", stroke_width="1.2"))
    for gx in range(-260, 381, 160):
        w(line(P(gx, 0, ZF - 2), P(gx, 270, ZF - 2), stroke="#5C6669", stroke_width="1.2"))
    w(quad_y(74, -60, 200, ZF - 120, ZF - 60, fill="#D8D2C6"))        # Tisch dahinter
    # Fensterteilung + Sonnenflecken
    for z in range(ZN, ZF + 1, 180):
        w(line(P(X0, 0, z), P(X0, Y1, z), stroke="#7E8487", stroke_width=max(1, 900 / z)))
    w(line(P(X0, 12, ZN), P(X0, 12, ZF), stroke="#7E8487", stroke_width="2"))
    for z in range(ZN + 20, ZF - 150, 180):
        # flache Nachmittagssonne von links: Lichtparallelogramm auf dem Boden
        a, b = z + 20, z + 150
        w(poly([P(X0, 0, a), P(X0, 0, b), P(X0 + 380, 0, b + 120), P(X0 + 380, 0, a + 120)], fill="#FFE7BF", fill_opacity="0.42"))
    # Deckenleuchten
    for lx in (-260, 0, 260):
        w(line(P(lx, Y1 - 1, 300), P(lx, Y1 - 1, ZF - 40), stroke="#F7F4EC", stroke_width="4", stroke_linecap="round"))
    # Betonfugen + Wandtafeln rechts
    for yy in (105, 210):
        w(line(P(X1, yy, ZN), P(X1, yy, ZF), stroke="#9E9B94", stroke_width="1"))
    for z in range(ZN, ZF, 300):
        w(line(P(X1, 0, z), P(X1, Y1, z), stroke="#9E9B94", stroke_width="1"))
    for z0, z1 in ((560, 760), (960, 1160)):
        w(quad_x(X1 - 2, 100, 205, z0, z1, fill="#24282A", stroke="#B08D57", stroke_width="2"))
        for k in range(5):
            zz0 = z0 + 18 + k * 37
            for r in range(3):
                yy = 185 - r * 28
                w(quad_x(X1 - 3, yy - 14, yy, zz0, zz0 + 26, fill="#EDEBE6" if (k + r) % 3 else "#B08D57", fill_opacity="0.85"))

    # Tischinseln (hinten zuerst)
    idx = 0
    for zc in (1060, 580):
        # Agenten hinter der Insel (schauen zur Kamera)
        for x in (-300, -120, 60, 240):
            w(agent(x + 10, zc + 95, True, idx)); idx += 1
        # Tischplatten + Gestell
        w(quad_y(74, -390, 330, zc - 80, zc + 80, fill="#B88F62", stroke="#8B6A47", stroke_width="1"))
        w(quad_z(zc - 80, -390, 330, 71, 74, fill="#7E6043"))
        for lx in (-385, 325):
            w(quad_z(zc - 78, lx, lx + 5, 0, 71, fill="#2B2D2F"))
        # Monitore: Rückseiten der hinteren Reihe, Bildschirme der vorderen Reihe
        for x in (-300, -120, 60, 240):
            w(quad_z(zc + 8, x - 22, x + 42, 92, 122, fill="#2E3032"))
            w(quad_z(zc - 6, x - 50, x + 14, 90, 120, fill="#1A1C1E"))
            w(quad_z(zc - 7, x - 48, x + 12, 92, 118, fill="#9CB3BD", fill_opacity="0.9"))
            # Namensschild in Agentenfarbe
            w(quad_z(zc - 70, x - 18, x + 6, 74, 79, fill=AGENT[(idx + x // 60) % len(AGENT)], fill_opacity="0.9"))
        # Agenten vor der Insel (Rücken zur Kamera)
        for x in (-300, -120, 60, 240):
            w(agent(x - 18, zc - 115, False, idx)); idx += 1
    # Licht & Vignette
    w(f'<rect width="{SK}" height="{H}" fill="url(#sonne)"/>')
    w(f'<rect width="{SK}" height="{H}" fill="url(#vignette)"/>')
    w(f'<rect width="{SK}" height="{H}" filter="url(#korn)" opacity="0.07"/>')
    w('</g>')
    w(f'<text x="28" y="{H - 28}" font-size="13" letter-spacing="2" fill="#F4EFE6" fill-opacity="0.85">STIMMUNGSSKIZZE · KAMERA 35 MM · AUGENHÖHE 165 CM · 16:30 UHR, OKTOBER</text>')
    return "".join(o)


def panel():
    o = []
    w = o.append
    x0 = SK + 56
    w(f'<rect x="{SK}" y="0" width="{W - SK}" height="{H}" fill="#F4F2EC"/>')
    w(f'<text x="{x0}" y="78" font-size="34" font-family="Georgia, serif" fill="#1E2023">Agent Office</text>')
    w(f'<text x="{x0}" y="106" font-size="13" letter-spacing="3" fill="#6F7A7D">MOODBOARD · UNREAL ENGINE 5.8</text>')

    # Palette
    w(f'<text x="{x0}" y="160" font-size="12" letter-spacing="3" fill="#6F7A7D">FARBEN</text>')
    for i, (name, hexv) in enumerate(PALETTE):
        cx, cy = x0 + (i % 3) * 166, 176 + (i // 3) * 86
        w(f'<rect x="{cx}" y="{cy}" width="150" height="46" fill="{hexv}" stroke="#00000014"/>')
        w(f'<text x="{cx}" y="{cy + 62}" font-size="12" fill="#1E2023">{name}</text>')
        w(f'<text x="{cx + 150}" y="{cy + 62}" font-size="11" fill="#8A8F93" text-anchor="end" font-family="Consolas, monospace">{hexv}</text>')
    w(f'<text x="{x0}" y="452" font-size="12" letter-spacing="3" fill="#6F7A7D">AGENTENFARBEN (ENTSÄTTIGT, NUR AKZENT)</text>')
    for i, c in enumerate(AGENT):
        w(f'<circle cx="{x0 + 12 + i * 34}" cy="474" r="11" fill="{c}"/>')

    # Materialien
    w(f'<text x="{x0}" y="530" font-size="12" letter-spacing="3" fill="#6F7A7D">MATERIALIEN</text>')
    mats = [("Sichtbeton", "url(#beton)"), ("Eiche geölt", "url(#eiche)"), ("Rauchglas", "url(#glas)"),
            ("Wollfilz", "url(#filz)"), ("Anzug, Wolle", "url(#anzug)"), ("Messing gebürstet", "url(#messing)")]
    for i, (name, fill) in enumerate(mats):
        cx, cy = x0 + (i % 3) * 166, 546 + (i // 3) * 132
        w(f'<rect x="{cx}" y="{cy}" width="150" height="100" fill="{fill}"/>')
        w(f'<text x="{cx}" y="{cy + 118}" font-size="12" fill="#1E2023">{name}</text>')

    # Figurdetail
    fy = 830
    w(f'<text x="{x0}" y="{fy}" font-size="12" letter-spacing="3" fill="#6F7A7D">FIGUR · AGENTENFARBE ALS DETAIL</text>')
    bx, by = x0 + 70, fy + 162
    s = 0.9
    u = lambda dx, dy: (bx + dx * s, by - dy * s)
    w(poly([u(-58, 0), u(58, 0), u(52, 62), u(34, 78), u(-34, 78), u(-52, 62)], fill="#1E2023"))
    w(poly([u(-14, 78), u(14, 78), u(0, 20)], fill="#EDEBE6"))
    w(poly([u(-4, 74), u(4, 74), u(6, 28), u(0, 18), u(-6, 28)], fill="#0B0B0C"))
    w(line(u(-7, 46), u(7, 46), stroke=AGENT[1], stroke_width="3.5", stroke_linecap="round"))
    w(poly([u(-10, 76), u(10, 76), u(10, 92), u(-10, 92)], fill=SKIN[1]))
    hx, hy = u(0, 112)
    w(f'<ellipse cx="{hx}" cy="{hy}" rx="{21 * s}" ry="{27 * s}" fill="{SKIN[1]}"/>')
    w(f'<path d="M{u(-21, 116)[0]} {u(-21, 116)[1]} Q{hx} {u(0, 150)[1]} {u(21, 116)[0]} {u(21, 116)[1]} L{u(20, 124)[0]} {u(20, 124)[1]} Q{hx} {u(0, 136)[1]} {u(-20, 124)[0]} {u(-20, 124)[1]}Z" fill="{HAIR[0]}"/>')
    for sx in (-10, 10):
        ex, ey = u(sx, 112)
        w(f'<rect x="{ex - 8.5 * s}" y="{ey - 5 * s}" width="{17 * s}" height="{10 * s}" rx="3" fill="#070708"/>')
    w(line(u(-2, 113), u(2, 113), stroke="#070708", stroke_width="2"))
    notes = [(u(10, 112), "Sonnenbrille, schmal, schwarz"), (u(7, 46), "Krawattennadel in Agentenfarbe"),
             (u(40, 30), "Sakko anthrazit, Hemd weiß, Krawatte schwarz")]
    tx = x0 + 190
    for k, ((px, py), text) in enumerate(notes):
        ty = fy + 42 + k * 38
        w(line((px + 6, py), (tx - 8, ty - 4), stroke="#B08D57", stroke_width="1"))
        w(f'<circle cx="{px}" cy="{py}" r="2.5" fill="#B08D57"/>')
        w(f'<text x="{tx}" y="{ty}" font-size="12.5" fill="#1E2023">{text}</text>')
    w(f'<text x="{tx}" y="{fy + 156}" font-size="11.5" fill="#6F7A7D">Plus Namensschild am Tisch mit farbiger Kante</text>')
    return "".join(o)


DEFS = """<defs>
<filter id="korn"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3"/><feColorMatrix type="saturate" values="0"/></filter>
<filter id="betonF" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.035 0.05" numOctaves="4" seed="8" result="n"/>
<feColorMatrix in="n" type="matrix" values="0 0 0 0 0.725  0 0 0 0 0.714  0 0 0 0 0.686  0 0 0 -0.9 0.75"/></filter>
<pattern id="beton" width="300" height="300" patternUnits="userSpaceOnUse"><rect width="300" height="300" fill="#BDBAB3"/><rect width="300" height="300" filter="url(#betonF)"/>
<circle cx="40" cy="60" r="2" fill="#9E9B94"/><circle cx="220" cy="190" r="1.6" fill="#9E9B94"/><circle cx="130" cy="250" r="2.2" fill="#9E9B94"/></pattern>
<filter id="maserF"><feTurbulence type="fractalNoise" baseFrequency="0.004 0.18" numOctaves="3" seed="2"/>
<feColorMatrix type="matrix" values="0 0 0 0 0.45  0 0 0 0 0.32  0 0 0 0 0.2  0 0 0 -1.4 0.95"/></filter>
<pattern id="eiche" width="150" height="100" patternUnits="userSpaceOnUse"><rect width="150" height="100" fill="#A7825A"/><rect width="150" height="100" filter="url(#maserF)"/>
<line x1="0" y1="33" x2="150" y2="33" stroke="#7E6043" stroke-width="0.8"/><line x1="0" y1="66" x2="150" y2="66" stroke="#7E6043" stroke-width="0.8"/></pattern>
<linearGradient id="eicheP" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8A7660"/><stop offset="1" stop-color="#A48B70"/></linearGradient>
<linearGradient id="glas" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8E9A9D"/><stop offset="0.42" stop-color="#6F7A7D"/><stop offset="0.46" stop-color="#A9B5B7"/><stop offset="0.52" stop-color="#6F7A7D"/><stop offset="1" stop-color="#57605F"/></linearGradient>
<filter id="filzF"><feTurbulence type="fractalNoise" baseFrequency="1.2" numOctaves="2" seed="5"/>
<feColorMatrix type="matrix" values="0 0 0 0 0.35  0 0 0 0 0.4  0 0 0 0 0.34  0 0 0 -0.8 0.5"/></filter>
<pattern id="filz" width="150" height="100" patternUnits="userSpaceOnUse"><rect width="150" height="100" fill="#7D8B78"/><rect width="150" height="100" filter="url(#filzF)"/></pattern>
<pattern id="anzug" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#1E2023"/><line x1="0" y1="0" x2="0" y2="6" stroke="#2A2D31" stroke-width="2"/></pattern>
<linearGradient id="messing" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#8F6F3F"/><stop offset="0.35" stop-color="#C7A56B"/><stop offset="0.55" stop-color="#B08D57"/><stop offset="1" stop-color="#7E6036"/></linearGradient>
<linearGradient id="sonne" x1="0" y1="0" x2="1" y2="0.2"><stop offset="0" stop-color="#FFD9A0" stop-opacity="0.32"/><stop offset="0.45" stop-color="#FFD9A0" stop-opacity="0.05"/><stop offset="1" stop-color="#2B3A44" stop-opacity="0.10"/></linearGradient>
<radialGradient id="vignette" cx="0.5" cy="0.48" r="0.75"><stop offset="0.55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.42"/></radialGradient>
</defs>"""

if __name__ == "__main__":
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">'
           f'<title>Agent Office – Moodboard</title>{DEFS}{sketch()}{panel()}</svg>')
    (HERE / "moodboard.svg").write_text(svg, encoding="utf-8")
    print("moodboard.svg geschrieben")
