"""
Rechnet den Grundriss des Browser-Office (AgentSystemLabs/agent-office v0.1.206) in unser Format um.

Erzeugt (aus dem Ordner unreal/AgentOffice, mit normalem Python 3, ohne Unreal):

    python Scripts/grundriss_original.py

- Content/Data/DeskLayout.json   alle Plätze (Schreibtische, Brett-Agenten, Besprechungsstühle, Sitzsäcke)
- Content/Data/OfficeRoom.json   Raum: Wände, Fenster, Türen, Bretter, Möbel, Deko, Bereiche
- Docs/grundriss-original.svg    Draufsicht zum Vergleich mit dem Browser-Office

Außerdem prüft es: keine doppelten deskIds, keine überlappenden Tische, keine Figuren zu dicht
beieinander oder im Tisch, und jede deskId aus workers.json (nur dieses Feld wird gelesen) hat einen Platz.

Die Zahlen unten sind 1:1 aus dem Original abgeschrieben (Quelle steht jeweils dabei, Pfade relativ
zu src/ im GitHub-Repo bzw. dist/ der installierten Version). Original: Meter, Draufsicht mit +x = Osten,
+z = Süden (Straße), Nordwand bei z = -13. Ein `rotY` dreht ein Objekt so, dass seine Vorderseite
nach (sin rotY, cos rotY) zeigt; Personen an Plätzen schauen genau entgegengesetzt, also nach
(-sin rotY, -cos rotY) – sie sitzen bei (sin, cos) hinter dem Tisch und blicken auf ihn.

Unser Format: Zentimeter, Ursprung = Raummitte, +x = Osten, +y = Süden, yaw 0° = +x, 90° = +y.
Dieses Skript ändert weder build_level.py noch den C++-Code.
"""

import json
import math
import os
import sys

# 2,2 x 1,1 m (Original-Schreibtisch) -> 160 x 80 cm
SCALE = 80.0 / 1.1  # cm pro Original-Meter (= 72,73)

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)

# ---------------------------------------------------------------------------
# Original-Konstanten (shared/layout.ts, sofern nicht anders angegeben)
# ---------------------------------------------------------------------------

FLOOR = dict(minX=-18.0, maxX=18.0, minZ=-13.0, maxZ=13.0)
WALL_HEIGHT = 6.8
WALL_T = 0.3
DESK_W, DESK_D, DESK_H = 2.2, 1.1, 0.78
DESK_PERSON = 0.93          # client/world/office/seats.ts buildDesk: seatAnchor z = 0.93 (Stuhl 0.9)
KIOSK = dict(width=0.8, depth=0.5, height=0.55, stand=0.55)
MEETING_PERSON = 0.85       # client/world/office/meeting-room.ts: seatAnchor/Stuhl z = 0.85
PI = math.pi


def build_desks():
    """layout.ts buildDesks(): zwei Inseln je Tischreihe, Rücken an Rücken."""
    desks, n = [], 1
    for back, front in ((-4.55, -3.45), (3.45, 4.55)):
        for cx in (-10.5, -1.5):
            for z, rot in ((back, PI), (front, 0.0)):
                for dx in (-DESK_W / 2, DESK_W / 2):
                    desks.append(dict(id="desk-%d" % n, x=cx + dx, z=z, rotY=rot, label="Schreibtisch %d" % n))
                    n += 1
    return desks


DESKS = build_desks()
WING = dict(minX=13.4, maxX=18.0, row=4.6, rows=2)
WING_DESKS = []
for _i in range(WING["rows"]):
    _z = FLOOR["minZ"] - (_i + 0.5) * WING["row"]
    _x = (WING["minX"] + WING["maxX"]) / 2
    _n = len(DESKS) + 2 * _i + 1
    WING_DESKS += [dict(id="desk-%d" % _n, x=_x, z=_z - DESK_D / 2, rotY=PI, label="Schreibtisch %d" % _n, wing=_i + 1),
                   dict(id="desk-%d" % (_n + 1), x=_x, z=_z + DESK_D / 2, rotY=0.0, label="Schreibtisch %d" % (_n + 1), wing=_i + 1)]

BEANBAGS = [dict(id="beanbag-%d" % (i + 1), x=x, z=z, rotY=r, label="Sitzsack %d" % (i + 1)) for i, (x, z, r) in enumerate([
    (15, -9.8, 0), (5.4, -9.8, 0), (-16.1, -9, PI / 2), (-16.1, -3, PI / 2), (-8.8, 10.2, PI), (0.8, 10.2, PI),
    (12.2, -5.6, -PI / 2), (12.2, 5.6, -PI / 2), (-16.1, 3, PI / 2), (-13.2, -9.8, 0), (-12.6, 9.2, PI / 2), (-5.4, -9.8, 0),
])]

STATIONS = [  # (x, z) = Kiosk; der Agent steht KIOSK.stand dahinter (zur Wand)
    dict(id="station-issues", kind="issues", x=-15.6, z=FLOOR["minZ"] + 1.3, rotY=PI, label="Issues-Brett"),
    dict(id="station-queue", kind="queue", x=-7.8, z=FLOOR["minZ"] + 1.3, rotY=PI, label="Aufgaben-Warteschlange"),
    dict(id="station-pulls", kind="pulls", x=0.0, z=FLOOR["minZ"] + 1.3, rotY=PI, label="PR-Brett"),
]
STATION_COLOR = {"issues": "#ef476f", "pulls": "#118ab2", "queue": "#06d6a0"}

LOFT = dict(minX=9.0, maxX=18.0, minZ=8.0, maxZ=13.0, y=3.0, height=2.8)
STAIRS = dict(fromX=3.0, toX=9.0, minZ=11.2, maxZ=13.0, steps=15)
MEETING_ROOM = dict(minX=9.15, maxX=18.0, minZ=8.15, maxZ=13.0, height=2.75, door=(10.0, 11.4))
MEETING_TABLE = dict(x=13.7, z=10.5, width=4.2, depth=1.7, height=0.76)
LAPTOP_IN = 0.45
MEETING_SEATS = [dict(id="meeting-%d" % (i + 1), x=x, z=z, rotY=r, label="Kopf des Tisches" if i == 0 else "Besprechungsstuhl %d" % (i + 1))
                 for i, (x, z, r) in enumerate([
                     (MEETING_TABLE["x"] - MEETING_TABLE["width"] / 2 + LAPTOP_IN, MEETING_TABLE["z"], -PI / 2),
                     (MEETING_TABLE["x"] - 0.65, MEETING_TABLE["z"] - MEETING_TABLE["depth"] / 2 + LAPTOP_IN, PI),
                     (MEETING_TABLE["x"] - 0.65, MEETING_TABLE["z"] + MEETING_TABLE["depth"] / 2 - LAPTOP_IN, 0.0),
                     (MEETING_TABLE["x"] + 1.15, MEETING_TABLE["z"] - MEETING_TABLE["depth"] / 2 + LAPTOP_IN, PI),
                     (MEETING_TABLE["x"] + 1.15, MEETING_TABLE["z"] + MEETING_TABLE["depth"] / 2 - LAPTOP_IN, 0.0),
                 ])]

# Wandtafeln: rotY = Richtung, in die die Tafel schaut (0 = +z). y = Höhe der Tafelmitte.
BOARDS = [
    dict(id="issues", label="Issues", x=-11.7, y=2.1, z=FLOOR["minZ"] + 0.08, rotY=0.0, width=6, height=3, frame="Holz"),
    dict(id="queue", label="Aufgaben-Warteschlange", x=-3.9, y=2.1, z=FLOOR["minZ"] + 0.08, rotY=0.0, width=6, height=3, frame="Aluminium (Whiteboard)"),
    dict(id="pulls", label="Pull Requests", x=3.9, y=2.1, z=FLOOR["minZ"] + 0.08, rotY=0.0, width=6, height=3, frame="Holz"),
    dict(id="services", label="Dienste", x=FLOOR["maxX"] - 0.08, y=2.1, z=-8.2, rotY=-PI / 2, width=6, height=3, frame="Holz"),
    dict(id="meeting", label="Besprechungs-Protokoll", x=MEETING_TABLE["x"], y=1.95, z=FLOOR["maxZ"] - 0.08, rotY=PI, width=3.6, height=1.2, frame="weiß"),
]
SCREENS = [
    dict(id="tv", label="Fernseher (Bildschirmfreigabe)", x=FLOOR["maxX"] - 0.1, y=2.2, z=0.0, rotY=-PI / 2, width=6.4, height=3.6),
    dict(id="machine-monitor", label="Rechner-Monitor (Auslastung)", x=FLOOR["minX"], y=2.2, z=-6.0, rotY=PI / 2, width=2.3, height=1.3),
]

# Öffnungen: u = Position entlang der Wand (x bei Nord/Süd, z bei West/Ost), y0/y1 = Unter-/Oberkante
WINDOWS = ([dict(wall="south", u=u, width=3.0, y0=1.1, y1=3.3) for u in (-14, -9, 1)]
           + [dict(wall="west", u=u, width=3.0, y0=1.1, y1=3.3) for u in (-9, -3, 3)]
           + [dict(wall="south", u=LOFT["minX"] + 2, width=2.8, y0=LOFT["y"] + 0.9, y1=LOFT["y"] + 2.5, loft=True),
              dict(wall="east", u=(LOFT["minZ"] + LOFT["maxZ"]) / 2, width=2.8, y0=LOFT["y"] + 0.9, y1=LOFT["y"] + 2.5, loft=True)])
DOORS = [
    dict(id="ausgang", label="Ausgang (Treppe zur Straße)", wall="west", u=6.5, width=1.4, y0=0.0, y1=2.4),
    dict(id="balkon", label="Glasschiebetür zum Balkon", wall="south", u=-4.0, width=3.0, y0=0.0, y1=2.5),
]
BALCONY = dict(minX=-10.5, maxX=2.5, minZ=FLOOR["maxZ"] + WALL_T, maxZ=FLOOR["maxZ"] + WALL_T + 3.4)
ELEVATOR = dict(x=8.5, width=2.6, depth=2.4, doorWidth=1.4, doorHeight=2.4)
GONG = dict(x=11.8, z=FLOOR["minZ"] + 0.75, width=1.9, height=2.45)
JUKEBOX = dict(x=FLOOR["maxX"] - 0.42, z=5.4, width=1.3, depth=0.72, height=1.85)
CABINET = dict(x=FLOOR["maxX"] - 0.42, z=7.05, width=0.8, depth=0.8, height=1.9)
BOOKSHELF = dict(x=-6.5, z=FLOOR["maxZ"] - 0.21, width=1.7, depth=0.42, height=2.3)
WHITEBOARD = dict(x=5.4, z=-5.4, width=4.0, height=2.2, bottom=0.5)
PLANTS = [(-17.2, -12.2, 1.4), (17.2, -12.2, 1.5), (17.2, 12.2, 1.3), (-17.2, 8.5, 1.2),
          (14.2, -12.2, 1.1), (-6, 0, 1), (3.5, 0, 0.9), (8.5, 5, 1.1)]
POLE = dict(x=6.8, z=1.6, rail=0.9)                       # POLES[0], POLE.rail
LADDER = dict(x=FLOOR["minX"] + 0.62, z=0.0, width=0.62)
HOOP = dict(face=FLOOR["minX"] + 0.62, z=10.1, rim_x=FLOOR["minX"] + 1.02, rim_y=3.05, line=4.6)   # shared/hoop.ts
SPAWN = (8.0, 7.0)
TV_X = FLOOR["maxX"] - 0.1
# client/world/office/room.ts
RUGS = [dict(x=x, z=z, w=6.2, d=4.6) for x, z in ((-10.5, -4), (-1.5, -4), (-10.5, 4), (-1.5, 4))] + [dict(x=13.4, z=0.0, w=7.0, d=7.0, lounge=True)]
LAMPS = [(-10.5, -4), (-1.5, -4), (-10.5, 4), (-1.5, 4), (13, 0)]   # Pendelleuchten, Schirm auf 4,05 m
COUCH = dict(x=10.5, z=0.0, length=4.2, depth=1.0, rotY=PI / 2)
COFFEE_TABLE = dict(x=13.0, z=0.0, d=0.9)
POUFS = [(12.5, 3.5), (14.5, -3.4)]
# client/world/kitchen.ts
KITCHEN_COUNTER = dict(minX=-17.0, maxX=-12.0, minZ=11.7, maxZ=12.7, top=1.03)
FRIDGE = dict(minX=-11.85, maxX=-10.75, minZ=11.7, maxZ=12.7, top=2.2)
COFFEE_MACHINE_X = -15.7
# server/dog.ts: Lieblingsplätze des Hundes auf dem Lounge-Teppich (sonst läuft er herum)
DOG_LOUNGE = [(16, 1.6), (16, -1.5), (14.8, 1.9), (11.8, 2.4), (11.8, -2.6), (14.6, -1.3)]

# ---------------------------------------------------------------------------
# Umrechnung
# ---------------------------------------------------------------------------


def cm(v):
    return int(round(v * SCALE))


def cmf(v):
    return round(v * SCALE, 1)


def norm(deg):
    deg = round(deg) % 360
    return deg


def person_yaw(rot):
    """Blickrichtung einer Person an einem Platz mit Original-rotY."""
    return norm(math.degrees(math.atan2(-math.cos(rot), -math.sin(rot))))


def object_yaw(rot):
    """Richtung der Vorderseite eines Objekts mit Original-rotY."""
    return norm(math.degrees(math.atan2(math.cos(rot), math.sin(rot))))


def behind(x, z, rot, dist):
    """Punkt `dist` Meter hinter einem Platz (dort, wo die Person ist)."""
    return x + math.sin(rot) * dist, z + math.cos(rot) * dist


DESK_SEAT = 75.0       # OfficeDirector.DeskSeatOffset
STATION_STAND = 70.0   # OfficeDirector.StationStandOffset


def spots():
    out = []
    for d in DESKS:
        out.append(dict(deskId=d["id"], label=d["label"], type="desk", x=cm(d["x"]), y=cm(d["z"]), yaw=person_yaw(d["rotY"])))
    for s in STATIONS:
        # Der Agent steht mit dem Rücken zur Wand hinter seinem Kiosk und schaut in den Raum. Der
        # OfficeDirector stellt die Person 70 cm entgegen der Blickrichtung hinter x/y – also ist
        # x/y der Punkt 70 cm vor dem Agenten (liegt am Kiosk), nicht die Tafel (die hängt daneben).
        px, pz = behind(s["x"], s["z"], s["rotY"], KIOSK["stand"])
        yaw = person_yaw(s["rotY"])
        a = math.radians(yaw)
        out.append(dict(deskId=s["id"], label=s["label"], type="station",
                        x=int(round(px * SCALE + STATION_STAND * math.cos(a))), y=int(round(pz * SCALE + STATION_STAND * math.sin(a))), yaw=yaw))
    for m in MEETING_SEATS:
        px, pz = behind(m["x"], m["z"], m["rotY"], MEETING_PERSON)
        out.append(dict(deskId=m["id"], label=m["label"], type="meeting", x=cm(px), y=cm(pz), yaw=person_yaw(m["rotY"])))
    for b in BEANBAGS:
        out.append(dict(deskId=b["id"], label=b["label"], type="beanbag", x=cm(b["x"]), y=cm(b["z"]), yaw=person_yaw(b["rotY"])))
    return out


def person_pos(spot):
    """Wo die Figur nach unserer Konvention (OfficeDirector) landet."""
    back = {"desk": DESK_SEAT, "station": STATION_STAND}.get(spot["type"], 0.0)
    a = math.radians(spot["yaw"])
    return spot["x"] - back * math.cos(a), spot["y"] - back * math.sin(a)


def opening(o):
    """Öffnung in unserem Format: Anfangs- und Endpunkt auf der Wandinnenseite."""
    h = o["width"] / 2
    if o["wall"] in ("north", "south"):
        z = FLOOR["minZ"] if o["wall"] == "north" else FLOOR["maxZ"]
        a, b = (o["u"] - h, z), (o["u"] + h, z)
    else:
        x = FLOOR["minX"] if o["wall"] == "west" else FLOOR["maxX"]
        a, b = (x, o["u"] - h), (x, o["u"] + h)
    return dict(wand={"north": "Nord", "south": "Süd", "west": "West", "east": "Ost"}[o["wall"]],
                von=[cm(a[0]), cm(a[1])], bis=[cm(b[0]), cm(b[1])], breite=cm(o["width"]),
                unterkante=cm(o["y0"]), oberkante=cm(o["y1"]))


def room():
    r = dict(
        _info="Erzeugt von Scripts/grundriss_original.py aus agent-office v0.1.206 (shared/layout.ts). "
              "cm, Ursprung = Raummitte, +x = Osten, +y = Süden, yaw = Richtung der Vorderseite (0 = +x, 90 = +y). "
              "Höhen (z, hoehe, unterkante, oberkante, boden, deckenhoehe) sind wie die Grundfläche mit dem Maßstab umgerechnet; "
              "für Möbel, Türen und die Empore stehen realistische Werte in Docs/grundriss-original.md (Abschnitt Höhen).",
        massstab_cm_pro_original_meter=round(SCALE, 4),
        raum=dict(minX=cm(FLOOR["minX"]), maxX=cm(FLOOR["maxX"]), minY=cm(FLOOR["minZ"]), maxY=cm(FLOOR["maxZ"]),
                  breite=cm(FLOOR["maxX"] - FLOOR["minX"]), tiefe=cm(FLOOR["maxZ"] - FLOOR["minZ"]),
                  deckenhoehe=cm(WALL_HEIGHT), wandstaerke=cm(WALL_T)),
        fenster=[dict(opening(o), **({"loft": True} if o.get("loft") else {})) for o in WINDOWS],
        tueren=[dict(id=d["id"], label=d["label"], **opening(d)) for d in DOORS],
        wandtafeln=[dict(id=b["id"], label=b["label"], x=cm(b["x"]), y=cm(b["z"]), z=cm(b["y"]), yaw=object_yaw(b["rotY"]),
                         breite=cm(b["width"]), hoehe=cm(b["height"]), rahmen=b["frame"]) for b in BOARDS],
        bildschirme=[dict(id=s["id"], label=s["label"], x=cm(s["x"]), y=cm(s["z"]), z=cm(s["y"]), yaw=object_yaw(s["rotY"]),
                          breite=cm(s["width"]), hoehe=cm(s["height"])) for s in SCREENS],
        kioske=[dict(deskId=s["id"], x=cm(s["x"]), y=cm(s["z"]), yaw=object_yaw(0.0), breite=cm(KIOSK["width"]),
                     tiefe=cm(KIOSK["depth"]), hoehe=cm(KIOSK["height"]), farbe=STATION_COLOR[s["kind"]],
                     person=[cm(behind(s["x"], s["z"], s["rotY"], KIOSK["stand"])[0]), cm(behind(s["x"], s["z"], s["rotY"], KIOSK["stand"])[1])])
                for s in STATIONS],
        besprechungstisch=dict(x=cm(MEETING_TABLE["x"]), y=cm(MEETING_TABLE["z"]), laenge=cm(MEETING_TABLE["width"]),
                               breite=cm(MEETING_TABLE["depth"]), hoehe=cm(MEETING_TABLE["height"])),
        bereiche=[
            dict(id="besprechungsraum", label="Besprechungsraum (Glaswände Nord/West, Tür in der Nordwand)",
                 minX=cm(MEETING_ROOM["minX"]), maxX=cm(MEETING_ROOM["maxX"]), minY=cm(MEETING_ROOM["minZ"]), maxY=cm(MEETING_ROOM["maxZ"]),
                 hoehe=cm(MEETING_ROOM["height"]), tuer_x=[cm(MEETING_ROOM["door"][0]), cm(MEETING_ROOM["door"][1])]),
            dict(id="loft", label="Chefbüro auf der Empore (über dem Besprechungsraum)",
                 minX=cm(LOFT["minX"]), maxX=cm(LOFT["maxX"]), minY=cm(LOFT["minZ"]), maxY=cm(LOFT["maxZ"]),
                 boden=cm(LOFT["y"]), hoehe=cm(LOFT["height"]),
                 stuetzen=[[cm(LOFT["minX"] + 0.15), cm(LOFT["minZ"] + 0.15)], [cm((LOFT["minX"] + LOFT["maxX"]) / 2), cm(LOFT["minZ"] + 0.15)]]),
            dict(id="treppe", label="Treppe zur Empore (steigt nach Osten, 15 Stufen)",
                 minX=cm(STAIRS["fromX"]), maxX=cm(STAIRS["toX"]), minY=cm(STAIRS["minZ"]), maxY=cm(STAIRS["maxZ"]), stufen=STAIRS["steps"]),
            dict(id="aufzug", label="Aufzugsschacht, Türen nach Süden",
                 minX=cm(ELEVATOR["x"] - ELEVATOR["width"] / 2), maxX=cm(ELEVATOR["x"] + ELEVATOR["width"] / 2),
                 minY=cm(FLOOR["minZ"]), maxY=cm(FLOOR["minZ"] + ELEVATOR["depth"]), tuerbreite=cm(ELEVATOR["doorWidth"])),
            dict(id="balkon", label="Raucherbalkon (draußen vor der Südwand)",
                 minX=cm(BALCONY["minX"]), maxX=cm(BALCONY["maxX"]), minY=cm(BALCONY["minZ"]), maxY=cm(BALCONY["maxZ"])),
            dict(id="kueche_theke", label="Küchenzeile mit Spüle und Espressomaschine", minX=cm(KITCHEN_COUNTER["minX"]),
                 maxX=cm(KITCHEN_COUNTER["maxX"]), minY=cm(KITCHEN_COUNTER["minZ"]), maxY=cm(KITCHEN_COUNTER["maxZ"]), hoehe=cm(KITCHEN_COUNTER["top"])),
            dict(id="kuehlschrank", label="Retro-Kühlschrank", minX=cm(FRIDGE["minX"]), maxX=cm(FRIDGE["maxX"]),
                 minY=cm(FRIDGE["minZ"]), maxY=cm(FRIDGE["maxZ"]), hoehe=cm(FRIDGE["top"])),
            dict(id="hinterzimmer", label="Hinterzimmer (Ausbau nach Norden, hier NICHT gebaut: floorplan wing = 0)",
                 minX=cm(WING["minX"]), maxX=cm(WING["maxX"]), minY=cm(FLOOR["minZ"] - WING["rows"] * WING["row"]), maxY=cm(FLOOR["minZ"]), gebaut=False),
        ] + [dict(id="teppich-%d" % (i + 1), label="Teppich Lounge" if r.get("lounge") else "Teppich unter Tischinsel",
                  minX=cm(r["x"] - r["w"] / 2), maxX=cm(r["x"] + r["w"] / 2), minY=cm(r["z"] - r["d"] / 2), maxY=cm(r["z"] + r["d"] / 2))
             for i, r in enumerate(RUGS)],
        objekte=[
            dict(id="sofa", label="Lounge-Sofa (blau)", x=cm(COUCH["x"]), y=cm(COUCH["z"]), yaw=object_yaw(COUCH["rotY"]), breite=cm(COUCH["length"]), tiefe=cm(COUCH["depth"])),
            dict(id="couchtisch", label="Runder Couchtisch", x=cm(COFFEE_TABLE["x"]), y=cm(COFFEE_TABLE["z"]), durchmesser=cm(COFFEE_TABLE["d"])),
        ] + [dict(id="pouf-%d" % (i + 1), label="Pouf (zum Fernseher gedreht)", x=cm(x), y=cm(z),
                  yaw=norm(math.degrees(math.atan2(0 - z, TV_X - x))), durchmesser=cm(1.05)) for i, (x, z) in enumerate(POUFS)] + [
            dict(id="jukebox", label="Jukebox", x=cm(JUKEBOX["x"]), y=cm(JUKEBOX["z"]), yaw=180, breite=cm(JUKEBOX["width"]), tiefe=cm(JUKEBOX["depth"]), hoehe=cm(JUKEBOX["height"])),
            dict(id="arcade", label="Arcade-Automat", x=cm(CABINET["x"]), y=cm(CABINET["z"]), yaw=180, breite=cm(CABINET["width"]), tiefe=cm(CABINET["depth"]), hoehe=cm(CABINET["height"])),
            dict(id="buecherregal", label="Bücherregal (Projekt-Doku)", x=cm(BOOKSHELF["x"]), y=cm(BOOKSHELF["z"]), yaw=270, breite=cm(BOOKSHELF["width"]), tiefe=cm(BOOKSHELF["depth"]), hoehe=cm(BOOKSHELF["height"])),
            dict(id="gong", label="Gong (läutet bei PR-Merge)", x=cm(GONG["x"]), y=cm(GONG["z"]), yaw=90, breite=cm(GONG["width"]), hoehe=cm(GONG["height"])),
            dict(id="whiteboard", label="Whiteboard auf Rollen", x=cm(WHITEBOARD["x"]), y=cm(WHITEBOARD["z"]), yaw=90, breite=cm(WHITEBOARD["width"]),
                 hoehe=cm(WHITEBOARD["height"]), unterkante=cm(WHITEBOARD["bottom"])),
            dict(id="kaffeemaschine", label="Espressomaschine (auf der Küchentheke)", x=cm(COFFEE_MACHINE_X), y=cm(12.2), yaw=270),
            dict(id="feuerwehrstange", label="Feuerwehrstange mit Geländer (unten: Matte)", x=cm(POLE["x"]), y=cm(POLE["z"]), radius_gelaender=cm(POLE["rail"])),
            dict(id="leiter", label="Leiter an der Westwand (Luke in Decke/Boden)", x=cm(LADDER["x"]), y=cm(LADDER["z"]), yaw=0, breite=cm(LADDER["width"])),
            dict(id="basketballkorb", label="Basketballkorb an der Westwand", x=cm(HOOP["face"]), y=cm(HOOP["z"]), yaw=0,
                 ring=[cm(HOOP["rim_x"]), cm(HOOP["z"])], ringhoehe=cm(HOOP["rim_y"]), freiwurflinie=cm(HOOP["line"])),
            dict(id="startpunkt", label="Startpunkt des Spielers", x=cm(SPAWN[0]), y=cm(SPAWN[1])),
        ] + [dict(id="pflanze-%d" % (i + 1), label="Topfpflanze (%s)" % ("Monstera", "Bogenhanf", "Ficus")[i % 3], x=cm(x), y=cm(z), groesse=s)
             for i, (x, z, s) in enumerate(PLANTS)] + [
            dict(id="haengeleuchte-%d" % (i + 1), label="Pendelleuchte", x=cm(x), y=cm(z), z=cm(4.05)) for i, (x, z) in enumerate(LAMPS)
        ] + [dict(id="hund-platz-%d" % (i + 1), label="Lieblingsplatz des Hundes (Lounge-Teppich)", x=cm(x), y=cm(z)) for i, (x, z) in enumerate(DOG_LOUNGE)],
        hinterzimmer_plaetze=[dict(deskId=d["id"], label=d["label"], type="desk", x=cm(d["x"]), y=cm(d["z"]), yaw=person_yaw(d["rotY"]), reihe=d["wing"])
                              for d in WING_DESKS],
    )
    return r


# ---------------------------------------------------------------------------
# Prüfung
# ---------------------------------------------------------------------------

def rect_corners(cx, cy, w, d, yaw):
    """Rechteck: w quer zur Blickrichtung, d entlang der Blickrichtung."""
    a = math.radians(yaw)
    fx, fy = math.cos(a), math.sin(a)
    sx, sy = -fy, fx
    return [(cx + fx * dd + sx * ww, cy + fy * dd + sy * ww) for dd, ww in ((-d / 2, -w / 2), (-d / 2, w / 2), (d / 2, w / 2), (d / 2, -w / 2))]


def overlap(a, b, tol=1.0):
    """Trennende-Achsen-Test für zwei konvexe Vierecke; Berührung (bis tol cm) zählt nicht."""
    for poly in (a, b):
        for i in range(4):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % 4]
            nx, ny = y2 - y1, x1 - x2
            ln = math.hypot(nx, ny)
            nx, ny = nx / ln, ny / ln
            pa = [nx * x + ny * y for x, y in a]
            pb = [nx * x + ny * y for x, y in b]
            if max(pa) <= min(pb) + tol or max(pb) <= min(pa) + tol:
                return False
    return True


def check(spots_list, rm, worker_ids):
    problems = []
    ids = [s["deskId"] for s in spots_list]
    if len(ids) != len(set(ids)):
        problems.append("doppelte deskIds")
    desks = [(s["deskId"], rect_corners(s["x"], s["y"], 160, 80, s["yaw"])) for s in spots_list if s["type"] == "desk"]
    for i in range(len(desks)):
        for j in range(i + 1, len(desks)):
            if overlap(desks[i][1], desks[j][1]):
                problems.append("Tische überlappen: %s / %s" % (desks[i][0], desks[j][0]))
    people = [(s["deskId"], person_pos(s)) for s in spots_list]
    kiosks = [(k["deskId"], rect_corners(k["x"], k["y"], k["breite"], k["tiefe"], k["yaw"])) for k in rm["kioske"]]
    for i in range(len(people)):
        for j in range(i + 1, len(people)):
            dist = math.hypot(people[i][1][0] - people[j][1][0], people[i][1][1] - people[j][1][1])
            if dist < 60:
                problems.append("Personen zu dicht (%d cm): %s / %s" % (dist, people[i][0], people[j][0]))
    for pid, (px, py) in people:
        for did, corners in desks + kiosks:
            if overlap([(px - 20, py - 20), (px + 20, py - 20), (px + 20, py + 20), (px - 20, py + 20)], corners):
                problems.append("Person %s steht im Tisch %s" % (pid, did))
        R = rm["raum"]
        if not (R["minX"] + 20 <= px <= R["maxX"] - 20 and R["minY"] + 20 <= py <= R["maxY"] - 20):
            problems.append("Person %s außerhalb des Raums" % pid)
    for wid in worker_ids:
        if wid not in ids:
            problems.append("deskId aus workers.json fehlt: %s" % wid)
    return problems


# ---------------------------------------------------------------------------
# Draufsicht (SVG)
# ---------------------------------------------------------------------------

def svg(spots_list, rm):
    R = rm["raum"]
    T = rm["raum"]["wandstaerke"]
    pad = 70
    x0, y0 = R["minX"] - T - pad, R["minY"] - T - pad - 40
    x1, y1 = R["maxX"] + T + pad, cm(BALCONY["maxZ"]) + pad + 150
    W, H = x1 - x0, y1 - y0
    o = []
    add = o.append
    add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%d %d %d %d" width="%d" height="%d" font-family="Segoe UI, Arial, sans-serif">'
        % (x0, y0, W, H, int(W * 0.5), int(H * 0.5)))
    add('<title>Agent Office – Grundriss des Browser-Office (v0.1.206) in UE-Koordinaten</title>')
    add('<rect x="%d" y="%d" width="%d" height="%d" fill="#ffffff"/>' % (x0, y0, W, H))
    # Raster alle 100 cm
    for gx in range((x0 // 100) * 100, x1, 100):
        add('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="%s"/>' % (gx, y0, gx, y1, "#c9d3df" if gx % 500 == 0 else "#eef2f6", 2 if gx % 500 == 0 else 1))
    for gy in range((y0 // 100) * 100, y1, 100):
        add('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="%s"/>' % (x0, gy, x1, gy, "#c9d3df" if gy % 500 == 0 else "#eef2f6", 2 if gy % 500 == 0 else 1))
    # Balkon
    b = [a for a in rm["bereiche"] if a["id"] == "balkon"][0]
    add('<rect x="%d" y="%d" width="%d" height="%d" fill="#e9ecef" stroke="#adb5bd" stroke-width="4" stroke-dasharray="12 8"/>' % (b["minX"], b["minY"], b["maxX"] - b["minX"], b["maxY"] - b["minY"]))
    add('<text x="%d" y="%d" font-size="30" fill="#6c757d" text-anchor="middle">Balkon (draußen)</text>' % ((b["minX"] + b["maxX"]) / 2, (b["minY"] + b["maxY"]) / 2 + 10))
    # Boden
    add('<rect x="%d" y="%d" width="%d" height="%d" fill="#f6efe4"/>' % (R["minX"], R["minY"], R["breite"], R["tiefe"]))
    for a in rm["bereiche"]:
        if a["id"].startswith("teppich"):
            add('<rect x="%d" y="%d" width="%d" height="%d" rx="30" fill="%s"/>' % (a["minX"], a["minY"], a["maxX"] - a["minX"], a["maxY"] - a["minY"], "#f7d9f7" if "Lounge" in a["label"] else "#ece3d3"))
    # Besprechungsraum + Empore
    m = [a for a in rm["bereiche"] if a["id"] == "besprechungsraum"][0]
    add('<rect x="%d" y="%d" width="%d" height="%d" fill="#e7f5fb"/>' % (m["minX"], m["minY"], m["maxX"] - m["minX"], m["maxY"] - m["minY"]))
    glass = 'stroke="#4cc9f0" stroke-width="8"'
    add('<line x1="%d" y1="%d" x2="%d" y2="%d" %s/>' % (m["minX"], m["minY"], m["tuer_x"][0], m["minY"], glass))
    add('<line x1="%d" y1="%d" x2="%d" y2="%d" %s/>' % (m["tuer_x"][1], m["minY"], m["maxX"], m["minY"], glass))
    add('<line x1="%d" y1="%d" x2="%d" y2="%d" %s/>' % (m["minX"], m["minY"], m["minX"], m["maxY"], glass))
    add('<text x="%d" y="%d" font-size="24" fill="#0077b6" text-anchor="middle">Tür</text>' % (sum(m["tuer_x"]) / 2, m["minY"] - 10))
    lo = [a for a in rm["bereiche"] if a["id"] == "loft"][0]
    add('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="#7b2cbf" stroke-width="4" stroke-dasharray="20 10"/>' % (lo["minX"], lo["minY"], lo["maxX"] - lo["minX"], lo["maxY"] - lo["minY"]))
    add('<text x="%d" y="%d" font-size="24" fill="#7b2cbf" text-anchor="end">Empore/Chefbüro darüber (+%d cm)</text>' % (lo["maxX"] - 12, lo["minY"] + 30, lo["boden"]))
    for sx, sy in lo["stuetzen"]:
        add('<circle cx="%d" cy="%d" r="9" fill="#7b2cbf"/>' % (sx, sy))
    tr = [a for a in rm["bereiche"] if a["id"] == "treppe"][0]
    add('<rect x="%d" y="%d" width="%d" height="%d" fill="#ffffff" stroke="#6c757d" stroke-width="3"/>' % (tr["minX"], tr["minY"], tr["maxX"] - tr["minX"], tr["maxY"] - tr["minY"]))
    step = (tr["maxX"] - tr["minX"]) / tr["stufen"]
    for i in range(1, tr["stufen"]):
        add('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#adb5bd" stroke-width="2"/>' % (tr["minX"] + i * step, tr["minY"], tr["minX"] + i * step, tr["maxY"]))
    add('<text x="%d" y="%d" font-size="22" fill="#495057" text-anchor="middle">Treppe ↗ Empore</text>' % ((tr["minX"] + tr["maxX"]) / 2, (tr["minY"] + tr["maxY"]) / 2 + 8))
    # Hinterzimmer (nicht gebaut)
    hz = [a for a in rm["bereiche"] if a["id"] == "hinterzimmer"][0]
    # Wände (mit Öffnungen)
    wall = "#2b2d42"
    open_n, open_s, open_w, open_e = [], [], [], []
    for f in rm["fenster"] + rm["tueren"]:
        if f.get("loft"):
            continue
        lst = {"Nord": open_n, "Süd": open_s, "West": open_w, "Ost": open_e}[f["wand"]]
        if f["wand"] in ("Nord", "Süd"):
            lst.append((f["von"][0], f["bis"][0]))
        else:
            lst.append((f["von"][1], f["bis"][1]))

    def wall_run(fixed, a, b, holes, horizontal, out):
        u = a
        pos = fixed + out * T / 2
        for h0, h1 in sorted(holes):
            if horizontal:
                add('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="%d"/>' % (u, pos, h0, pos, wall, T))
            else:
                add('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="%d"/>' % (pos, u, pos, h0, wall, T))
            u = h1
        if horizontal:
            add('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="%d"/>' % (u, pos, b, pos, wall, T))
        else:
            add('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="%d"/>' % (pos, u, pos, b, wall, T))

    wall_run(R["minY"], R["minX"] - T, R["maxX"] + T, open_n, True, -1)
    wall_run(R["maxY"], R["minX"] - T, R["maxX"] + T, open_s, True, 1)
    wall_run(R["minX"], R["minY"], R["maxY"], open_w, False, -1)
    wall_run(R["maxX"], R["minY"], R["maxY"], open_e, False, 1)
    for f in rm["fenster"]:
        horiz = f["wand"] in ("Nord", "Süd")
        out = -1 if f["wand"] in ("Nord", "West") else 1
        if horiz:
            yy = f["von"][1] + out * T / 2
            add('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="%d" %s/>' % (f["von"][0], yy, f["bis"][0], yy, "#90e0ef", T if not f.get("loft") else 8, 'stroke-dasharray="14 8"' if f.get("loft") else ""))
        else:
            xx = f["von"][0] + out * T / 2
            add('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="%d" %s/>' % (xx, f["von"][1], xx, f["bis"][1], "#90e0ef", T if not f.get("loft") else 8, 'stroke-dasharray="14 8"' if f.get("loft") else ""))
    for d in rm["tueren"]:
        if d["wand"] == "West":
            add('<path d="M %d %d A %d %d 0 0 0 %d %d" fill="none" stroke="#2a9d8f" stroke-width="4"/>' % (d["von"][0] - T, d["von"][1], d["breite"], d["breite"], d["von"][0] - T - d["breite"], d["bis"][1]))
            add('<text x="%d" y="%d" font-size="24" fill="#2a9d8f" text-anchor="start">← Ausgang</text>' % (d["von"][0] + 12, (d["von"][1] + d["bis"][1]) / 2 + 8))
        else:
            yy = d["von"][1] + T / 2
            add('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#2a9d8f" stroke-width="8"/>' % (d["von"][0], yy, d["bis"][0], yy))
            add('<text x="%d" y="%d" font-size="24" fill="#2a9d8f" text-anchor="middle">Balkontür</text>' % ((d["von"][0] + d["bis"][0]) / 2, d["von"][1] - 14))
    add('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#adb5bd" stroke-width="6" stroke-dasharray="10 8"/>' % (hz["minX"], hz["maxY"] - T - 12, hz["maxX"], hz["maxY"] - T - 12))
    add('<text x="%d" y="%d" font-size="22" fill="#868e96" text-anchor="middle">Durchbruch Hinterzimmer (nicht ausgebaut)</text>' % ((hz["minX"] + hz["maxX"]) / 2, hz["maxY"] - T - 24))

    # Wandtafeln und Bildschirme
    def wall_thing(t, color, width=10, label_out=30):
        a = math.radians(t["yaw"])
        sx, sy = -math.sin(a), math.cos(a)
        hw = t["breite"] / 2
        add('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%d" stroke-linecap="round"/>' % (t["x"] - sx * hw, t["y"] - sy * hw, t["x"] + sx * hw, t["y"] + sy * hw, color, width))
        tx, ty = t["x"] + math.cos(a) * label_out, t["y"] + math.sin(a) * label_out
        rot = 0 if abs(sy) < 0.5 else -90
        add('<text x="%.1f" y="%.1f" font-size="24" fill="%s" text-anchor="middle" transform="rotate(%d %.1f %.1f)" dominant-baseline="middle">%s</text>' % (tx, ty, color, rot, tx, ty, t["label"]))

    for t in rm["wandtafeln"]:
        wall_thing(t, "#9c6644" if t["id"] != "queue" else "#5c677d", label_out=-50 if t["id"] == "meeting" else 30)
    for t in rm["bildschirme"]:
        wall_thing(t, "#212529")

    # Aufzug, Küche, Möbel
    el = [a for a in rm["bereiche"] if a["id"] == "aufzug"][0]
    add('<rect x="%d" y="%d" width="%d" height="%d" fill="#ced4da" stroke="#495057" stroke-width="4"/>' % (el["minX"], el["minY"], el["maxX"] - el["minX"], el["maxY"] - el["minY"]))
    add('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#495057" stroke-width="2"/><line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#495057" stroke-width="2"/>'
        % (el["minX"], el["minY"], el["maxX"], el["maxY"], el["maxX"], el["minY"], el["minX"], el["maxY"]))
    add('<text x="%d" y="%d" font-size="24" fill="#212529" text-anchor="middle">Aufzug</text>' % ((el["minX"] + el["maxX"]) / 2, el["maxY"] + 28))
    for kid, col in (("kueche_theke", "#8ecae6"), ("kuehlschrank", "#f8f9fa")):
        k = [a for a in rm["bereiche"] if a["id"] == kid][0]
        add('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" stroke="#495057" stroke-width="3"/>' % (k["minX"], k["minY"], k["maxX"] - k["minX"], k["maxY"] - k["minY"], col))
    add('<text x="%d" y="%d" font-size="22" fill="#212529" text-anchor="middle">Küche · Kaffee</text>' % (cm(-14.5), cm(11.7) - 12))
    add('<text x="%d" y="%d" font-size="22" fill="#212529" text-anchor="middle">Kühlschrank</text>' % (cm(-11.3), cm(11.7) - 12))

    objs = {x["id"]: x for x in rm["objekte"]}

    def box_obj(oid, color, label=None, label_dy=0):
        ob = objs[oid]
        w, d = ob.get("breite", 40), ob.get("tiefe", 16)
        pts = rect_corners(ob["x"], ob["y"], w, d, ob.get("yaw", 0))
        add('<polygon points="%s" fill="%s" stroke="#343a40" stroke-width="3"/>' % (" ".join("%.1f,%.1f" % p for p in pts), color))
        if label:
            add('<text x="%d" y="%d" font-size="22" fill="#212529" text-anchor="middle">%s</text>' % (ob["x"], ob["y"] + label_dy, label))

    box_obj("sofa", "#5b8def", None)
    add('<text x="%d" y="%d" font-size="22" fill="#ffffff" text-anchor="middle" transform="rotate(-90 %d %d)">Sofa</text>' % (objs["sofa"]["x"], objs["sofa"]["y"] + 8, objs["sofa"]["x"], objs["sofa"]["y"]))
    add('<circle cx="%d" cy="%d" r="%d" fill="#c98b5a" stroke="#343a40" stroke-width="3"/>' % (objs["couchtisch"]["x"], objs["couchtisch"]["y"], objs["couchtisch"]["durchmesser"] / 2))
    for pid, col in (("pouf-1", "#06d6a0"), ("pouf-2", "#ffd166")):
        add('<circle cx="%d" cy="%d" r="%d" fill="%s" stroke="#343a40" stroke-width="3"/>' % (objs[pid]["x"], objs[pid]["y"], objs[pid]["durchmesser"] / 2, col))
    box_obj("jukebox", "#e63946")
    add('<text x="%d" y="%d" font-size="22" fill="#212529" text-anchor="end">Jukebox</text>' % (objs["jukebox"]["x"] - 40, objs["jukebox"]["y"] + 8))
    box_obj("arcade", "#9b5de5")
    add('<text x="%d" y="%d" font-size="22" fill="#212529" text-anchor="end">Arcade</text>' % (objs["arcade"]["x"] - 40, objs["arcade"]["y"] + 8))
    box_obj("buecherregal", "#8a5a3b", "Bücherregal", -30)
    gg = objs["gong"]
    add('<rect x="%d" y="%d" width="%d" height="14" fill="#e9b949" stroke="#343a40" stroke-width="3"/>' % (gg["x"] - gg["breite"] / 2, gg["y"] - 7, gg["breite"]))
    add('<text x="%d" y="%d" font-size="22" fill="#212529" text-anchor="middle">Gong</text>' % (gg["x"], gg["y"] + 34))
    wb = objs["whiteboard"]
    add('<rect x="%d" y="%d" width="%d" height="12" fill="#ffffff" stroke="#343a40" stroke-width="4"/>' % (wb["x"] - wb["breite"] / 2, wb["y"] - 6, wb["breite"]))
    add('<text x="%d" y="%d" font-size="22" fill="#212529" text-anchor="middle">Whiteboard (Rollen)</text>' % (wb["x"], wb["y"] + 34))
    fp = objs["feuerwehrstange"]
    add('<circle cx="%d" cy="%d" r="%d" fill="none" stroke="#e85d04" stroke-width="4"/><circle cx="%d" cy="%d" r="6" fill="#e85d04"/>' % (fp["x"], fp["y"], fp["radius_gelaender"], fp["x"], fp["y"]))
    add('<text x="%d" y="%d" font-size="22" fill="#e85d04" text-anchor="middle">Stange</text>' % (fp["x"], fp["y"] + fp["radius_gelaender"] + 26))
    la = objs["leiter"]
    add('<rect x="%d" y="%d" width="16" height="%d" fill="#adb5bd" stroke="#343a40" stroke-width="2"/>' % (R["minX"], la["y"] - la["breite"] / 2, la["breite"]))
    add('<text x="%d" y="%d" font-size="22" fill="#212529">Leiter</text>' % (R["minX"] + 24, la["y"] + 8))
    hp = objs["basketballkorb"]
    add('<rect x="%d" y="%d" width="6" height="%d" fill="#343a40"/>' % (hp["x"] - 3, hp["y"] - cm(0.7), cm(1.4)))
    add('<circle cx="%d" cy="%d" r="%d" fill="none" stroke="#f77f00" stroke-width="4"/>' % (hp["ring"][0], hp["ring"][1], cm(0.25)))
    add('<text x="%d" y="%d" font-size="22" fill="#f77f00">Korb</text>' % (hp["ring"][0] + 26, hp["ring"][1] + 8))
    for oid, ob in objs.items():
        if oid.startswith("pflanze"):
            r = 0.3 * ob["groesse"] * SCALE
            add('<circle cx="%d" cy="%d" r="%.1f" fill="#52b788" stroke="#2d6a4f" stroke-width="3"/>' % (ob["x"], ob["y"], r))
        elif oid.startswith("haengeleuchte"):
            add('<circle cx="%d" cy="%d" r="18" fill="none" stroke="#f4a261" stroke-width="3" stroke-dasharray="4 4"/>' % (ob["x"], ob["y"]))
        elif oid.startswith("hund-platz"):
            add('<text x="%d" y="%d" font-size="22" text-anchor="middle" fill="#8a5a3b">🐾</text>' % (ob["x"], ob["y"] + 8))
    add('<text x="%d" y="%d" font-size="22" fill="#8a5a3b" text-anchor="middle">Hund (Lieblingsplätze)</text>' % (cm(14.4), cm(3.5) + 60))
    sp = objs["startpunkt"]
    add('<path d="M %d %d l 14 24 l -28 0 z" fill="#adb5bd"/>' % (sp["x"], sp["y"] - 14))

    # Besprechungstisch
    mt = rm["besprechungstisch"]
    add('<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="20" fill="#7f5539" stroke="#343a40" stroke-width="3"/>' % (mt["x"] - mt["laenge"] / 2, mt["y"] - mt["breite"] / 2, mt["laenge"], mt["breite"]))
    add('<text x="%d" y="%d" font-size="22" fill="#ffffff" text-anchor="middle">Besprechungstisch</text>' % (mt["x"], mt["y"] + 8))

    # Kioske
    for k in rm["kioske"]:
        pts = rect_corners(k["x"], k["y"], k["breite"], k["tiefe"], k["yaw"])
        add('<polygon points="%s" fill="%s" stroke="#343a40" stroke-width="3"/>' % (" ".join("%.1f,%.1f" % p for p in pts), k["farbe"]))

    # Plätze
    colors = {"desk": "#ef476f", "station": "#118ab2", "meeting": "#06d6a0", "beanbag": "#9b5de5"}
    for s in spots_list:
        px, py = person_pos(s)
        a = math.radians(s["yaw"])
        c = colors[s["type"]]
        if s["type"] == "desk":
            pts = rect_corners(s["x"], s["y"], 160, 80, s["yaw"])
            add('<polygon points="%s" fill="#e9c46a" stroke="#6c584c" stroke-width="3"/>' % " ".join("%.1f,%.1f" % p for p in pts))
            add('<text x="%d" y="%d" font-size="30" font-weight="bold" fill="#3d2c1e" text-anchor="middle" dominant-baseline="middle">%s</text>' % (s["x"], s["y"], s["deskId"].split("-")[1]))
        dashed = ' stroke-dasharray="6 5"' if s["type"] == "beanbag" else ""
        fill = "#ffffff" if s["type"] == "beanbag" else c
        add('<circle cx="%.1f" cy="%.1f" r="22" fill="%s" stroke="%s" stroke-width="4"%s/>' % (px, py, fill, c, dashed))
        add('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#212529" stroke-width="5" stroke-linecap="round"/>' % (px, py, px + 36 * math.cos(a), py + 36 * math.sin(a)))
        if s["type"] == "station":
            add('<text x="%.1f" y="%.1f" font-size="22" fill="%s" text-anchor="middle">%s</text>' % (px, py + 105, c, s["deskId"]))
        elif s["type"] == "meeting":
            off = -34 if math.sin(a) > 0.5 else 46
            if abs(math.sin(a)) < 0.5:
                add('<text x="%.1f" y="%.1f" font-size="22" fill="#0b6e4f" text-anchor="end">%s</text>' % (px - 30, py + 8, s["deskId"] + " (Kopf)"))
            else:
                add('<text x="%.1f" y="%.1f" font-size="22" fill="#0b6e4f" text-anchor="middle">%s</text>' % (px, py + off, s["deskId"]))
        elif s["type"] == "beanbag":
            add('<text x="%.1f" y="%.1f" font-size="20" fill="#7b2cbf" text-anchor="middle">%s</text>' % (px, py + 46, "S" + s["deskId"].split("-")[1]))

    # Kompass, Achsen, Maßstab, Legende
    lx, ly = R["minX"], cm(BALCONY["maxZ"]) + 60
    add('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#212529" stroke-width="6"/>' % (lx, ly, lx + 500, ly))
    for i in range(6):
        add('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#212529" stroke-width="3"/>' % (lx + i * 100, ly - 10, lx + i * 100, ly + 10))
    add('<text x="%d" y="%d" font-size="26" fill="#212529">0</text><text x="%d" y="%d" font-size="26" fill="#212529" text-anchor="middle">5 m (UE)</text>' % (lx - 6, ly + 40, lx + 500, ly + 40))
    add('<text x="%d" y="%d" font-size="24" fill="#495057">Maßstab: 1 m Original = %.2f cm · Raster 1 m, dick alle 5 m · Ursprung = Raummitte</text>' % (lx + 620, ly + 8, SCALE))
    leg = [("desk", "Schreibtisch (Person 75 cm hinter Tischmitte)"), ("station", "Brett-Agent am Kiosk"), ("meeting", "Besprechungsstuhl"), ("beanbag", "Sitzsack (nur wenn alle Tische belegt)")]
    for i, (t, txt) in enumerate(leg):
        add('<circle cx="%d" cy="%d" r="16" fill="%s" stroke="%s" stroke-width="4"/>' % (lx + 20 + i * 520, ly + 90, "#ffffff" if t == "beanbag" else colors[t], colors[t]))
        add('<text x="%d" y="%d" font-size="24" fill="#212529">%s</text>' % (lx + 46 + i * 520, ly + 98, txt))
    add('<text x="0" y="0" font-size="44" font-weight="bold" fill="#adb5bd" text-anchor="middle" opacity="0.8">+</text>')
    nx, ny = R["maxX"] - 40, R["minY"] - T - 75
    add('<text x="%d" y="%d" font-size="30" font-weight="bold" fill="#212529" text-anchor="middle">N ↑</text>' % (nx, ny))
    add('<text x="%d" y="%d" font-size="34" font-weight="bold" fill="#212529">Agent Office – Grundriss des Browser-Office (v0.1.206), umgerechnet in cm</text>' % (R["minX"], R["minY"] - T - 50))
    add('</svg>')
    return "\n".join(o)


# ---------------------------------------------------------------------------

def read_worker_desk_ids():
    """Nur das Feld deskId aus workers.json – alles andere wird nicht angefasst."""
    path = os.environ.get("AGENT_OFFICE_WORKERS", "C:/Users/info/agent-office/ler0xx/mein-erstes-projekt/.agent-office/workers.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    items = data if isinstance(data, list) else data.get("workers", list(data.values()) if isinstance(data, dict) else [])
    return sorted({w.get("deskId") for w in items if isinstance(w, dict) and w.get("deskId")})


def write_layout(path, spots_list):
    lines = []
    for s in spots_list:
        lines.append('  {"deskId": %s, "label": %s, "type": %s, "x": %d, "y": %d, "yaw": %d}'
                     % (json.dumps(s["deskId"]), json.dumps(s["label"], ensure_ascii=False), json.dumps(s["type"]), s["x"], s["y"], s["yaw"]))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("[\n" + ",\n".join(lines) + "\n]\n")


def main():
    spots_list = spots()
    rm = room()
    problems = check(spots_list, rm, read_worker_desk_ids())
    for p in problems:
        print("PROBLEM:", p)
    write_layout(os.path.join(PROJECT, "Content", "Data", "DeskLayout.json"), spots_list)
    with open(os.path.join(PROJECT, "Content", "Data", "OfficeRoom.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rm, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.makedirs(os.path.join(PROJECT, "Docs"), exist_ok=True)
    with open(os.path.join(PROJECT, "Docs", "grundriss-original.svg"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(svg(spots_list, rm) + "\n")
    print("%d Plätze, %d Probleme" % (len(spots_list), len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
