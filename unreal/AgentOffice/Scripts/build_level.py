"""
Baut das Graubox-Level /Game/Maps/Office für das Agent Office.

Aufruf ohne Editor-Fenster (aus dem Ordner unreal/AgentOffice):

    "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" ^
        "%CD%/AgentOffice.uproject" -run=pythonscript -script="%CD%/Scripts/build_level.py"

Oder im offenen Editor: Werkzeuge > Python-Skript ausführen > Scripts/build_level.py

Das Skript ist wiederholbar: Existiert das Level schon, wird sein Inhalt
komplett ersetzt. Tische, Stühle usw. werden aus Content/Data/DeskLayout.json
erzeugt – derselben Datei, die der AOfficeDirector zur Laufzeit liest.

Raum, Licht und Materialien folgen dem Designkonzept
(docs/agent-office-ue5/konzept.md): offener Raum 16 x 11 m, 3,10 m hoch,
Ursprung = Raummitte, +X = Osten, +Y = Süden. Fensterfronten im Westen und
Süden, Sichtbeton im Norden (mit Eingang) und Osten, gläserner
Besprechungsraum im Osten, tiefe Nachmittagssonne aus Westen.

Alles hier ist bewusst Graubox (einfache Quader mit realistischen
Materialwerten). Echte Möbel/Assets kommen später.
"""

import json
import math
import os

import unreal

MAP_PATH = "/Game/Maps/Office"
MAT_DIR = "/Game/Graybox/Materials"

# Raum (cm, Innenmaß). Ursprung = Raummitte, Boden-Oberkante bei Z = 0.
ROOM_W = 1600.0   # entlang X (West -> Ost)
ROOM_D = 1100.0   # entlang Y (Nord -> Süd)
ROOM_H = 310.0
HX, HY = ROOM_W / 2, ROOM_D / 2
WALL_T = 25.0
SILL_H = 45.0        # Brüstung der Stahlfenster
WINDOW_TOP = 285.0
WINDOW_POSTS = 5     # Pfosten je Fensterfront (wie im Grundriss)
ENTRANCE = (160.0, 260.0, 220.0)   # Eingang Nordwand: x von, x bis, Höhe

# Besprechungsraum (Glaswände mit Stahlprofilen)
GLASS_X = 280.0
GLASS_Y = 330.0
GLASS_DOOR = (-GLASS_Y + 90.0, -GLASS_Y + 190.0)  # Türöffnung in der Westglaswand (y von, y bis)

DESK_H = 75.0
DESK_SEAT_OFFSET = 75.0     # Tischmitte -> Person (wie im Designkonzept)
STATION_STAND_OFFSET = 70.0
# Die Platzhalter-Figuren stehen noch (keine Sitz-Animation) – Stühle daher etwas zurückgerollt
CHAIR_PUSHED_BACK = 35.0

log = unreal.log
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


# ---------------------------------------------------------------------------
# Materialien
# ---------------------------------------------------------------------------

def make_master_material():
    """M_Graybox: BaseColor/Roughness/Metallic als Parameter."""
    path = MAT_DIR + "/M_Graybox"
    if eal.does_asset_exist(path):
        return eal.load_asset(path)

    mat = asset_tools.create_asset("M_Graybox", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())

    base = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -500, -100)
    base.set_editor_property("parameter_name", "BaseColor")
    base.set_editor_property("default_value", unreal.LinearColor(0.5, 0.5, 0.5, 1.0))

    rough = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -500, 150)
    rough.set_editor_property("parameter_name", "Roughness")
    rough.set_editor_property("default_value", 0.6)

    metal = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -500, 300)
    metal.set_editor_property("parameter_name", "Metallic")
    metal.set_editor_property("default_value", 0.0)

    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    return mat


def make_mi(master, name, color, roughness, metallic=0.0):
    """Materialinstanz anlegen bzw. aktualisieren. Farben linear (nicht sRGB)."""
    path = "{}/{}".format(MAT_DIR, name)
    if eal.does_asset_exist(path):
        mi = eal.load_asset(path)
    else:
        mi = asset_tools.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant,
                                      unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, master)
    mel.set_material_instance_vector_parameter_value(mi, "BaseColor", unreal.LinearColor(color[0], color[1], color[2], 1.0))
    mel.set_material_instance_scalar_parameter_value(mi, "Roughness", roughness)
    mel.set_material_instance_scalar_parameter_value(mi, "Metallic", metallic)
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    return mi


def make_materials():
    master = make_master_material()
    # Palette aus dem Designkonzept; realistische Albedo-Werte (nichts ganz weiß oder schwarz)
    return {
        "oak":      make_mi(master, "MI_Oak_Oiled",        (0.30, 0.19, 0.10), 0.50),
        "concrete": make_mi(master, "MI_Concrete",         (0.33, 0.32, 0.30), 0.80),
        "ceiling":  make_mi(master, "MI_Concrete_Ceiling", (0.38, 0.37, 0.35), 0.85),
        "steel":    make_mi(master, "MI_Steel_Black",      (0.025, 0.025, 0.025), 0.55, 1.0),
        "brass":    make_mi(master, "MI_Brass_Brushed",    (0.62, 0.45, 0.20), 0.35, 1.0),
        "felt":     make_mi(master, "MI_Felt_Sage",        (0.10, 0.13, 0.09), 0.95),
        "screen":   make_mi(master, "MI_Screen_Off",       (0.004, 0.004, 0.005), 0.12),
        "board":    make_mi(master, "MI_Board",            (0.70, 0.69, 0.66), 0.35),
        "walnut":   make_mi(master, "MI_Table_Walnut",     (0.09, 0.045, 0.02), 0.35),
        "ground":   make_mi(master, "MI_Roof_Outside",     (0.12, 0.12, 0.11), 0.90),
    }


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

CUBE = None


def box(label, center, size, mat, yaw=0.0, folder="Graybox"):
    """Quader mit Mittelpunkt `center` und Kantenlängen `size` (cm, vor der Drehung um `yaw`)."""
    actor = eas.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(center[0], center[1], center[2]),
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw))
    comp = actor.static_mesh_component
    comp.set_static_mesh(CUBE)
    comp.set_material(0, mat)
    actor.set_actor_scale3d(unreal.Vector(size[0] / 100.0, size[1] / 100.0, size[2] / 100.0))
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    return actor


def box_span(label, a, b, z0, z1, depth, mat, folder):
    """Quader zwischen zwei Bodenpunkten a und b (Wand-/Profilstück)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    yaw = math.degrees(math.atan2(dy, dx))
    center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (z0 + z1) / 2)
    return box(label, center, (length, depth, z1 - z0), mat, yaw, folder)


def local(spot, forward, side, z):
    """Punkt relativ zu einem Platz: forward = Blickrichtung der Person, side = nach rechts."""
    yaw = math.radians(spot["yaw"])
    c, s = math.cos(yaw), math.sin(yaw)
    return (spot["x"] + forward * c - side * s, spot["y"] + forward * s + side * c, z)


def set_prop(obj, name, value):
    try:
        obj.set_editor_property(name, value)
    except Exception as exc:  # Eigenschaft in dieser Engine-Version anders benannt
        unreal.log_warning("build_level: {} nicht gesetzt ({})".format(name, exc))


def enum_value(enum_cls, *names):
    """Enum-Wert über mehrere mögliche Python-Namen suchen (Namen ändern sich gelegentlich)."""
    for name in names:
        if hasattr(enum_cls, name):
            return getattr(enum_cls, name)
    raise AttributeError("{} hat keinen der Werte {}".format(enum_cls, names))


def load_layout():
    content_dir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
    path = os.path.join(content_dir, "Data", "DeskLayout.json")
    with open(path, "r", encoding="utf-8") as handle:
        spots = json.load(handle)
    log("build_level: {} Plätze aus {}".format(len(spots), path))
    return spots


# ---------------------------------------------------------------------------
# Raum
# ---------------------------------------------------------------------------

def window_front(name, a, b, m, folder):
    """Stahlfensterfront zwischen a und b: Brüstung, Sturz, Pfosten. (Glas folgt mit echten Assets.)"""
    box_span(name + "_Bruestung", a, b, 0.0, SILL_H, WALL_T, m["concrete"], folder)
    box_span(name + "_Sturz", a, b, WINDOW_TOP, ROOM_H, WALL_T, m["concrete"], folder)
    box_span(name + "_Profil_Unten", a, b, SILL_H, SILL_H + 6.0, 8.0, m["steel"], folder)
    box_span(name + "_Profil_Oben", a, b, WINDOW_TOP - 6.0, WINDOW_TOP, 8.0, m["steel"], folder)
    box_span(name + "_Riegel", a, b, 210.0, 214.0, 6.0, m["steel"], folder)
    for i in range(WINDOW_POSTS + 2):
        t = i / float(WINDOW_POSTS + 1)
        p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        width = 12.0 if i in (0, WINDOW_POSTS + 1) else 6.0
        along_x = a[1] == b[1]
        size = (width, 8.0, WINDOW_TOP - SILL_H) if along_x else (8.0, width, WINDOW_TOP - SILL_H)
        box("{}_Pfosten_{}".format(name, i), (p[0], p[1], (SILL_H + WINDOW_TOP) / 2), size, m["steel"], folder=folder)


def build_room(m):
    T = WALL_T
    f = "Graybox/Raum"

    box("Boden_Eiche", (0, 0, -5), (ROOM_W + 2 * T, ROOM_D + 2 * T, 10), m["oak"], folder=f)
    box("Decke_Beton", (0, 0, ROOM_H + 15), (ROOM_W + 2 * T, ROOM_D + 2 * T, 30), m["ceiling"], folder=f)
    box("Dach_Umgebung", (0, 0, -20), (30000, 30000, 10), m["ground"], folder=f)

    # Nordwand (Sichtbeton) mit Eingang
    y = -HY - T / 2
    x0, x1, door_h = ENTRANCE
    box_span("Wand_Nord_West", (-HX - T, y), (x0, y), 0, ROOM_H, T, m["concrete"], f)
    box_span("Wand_Nord_Ost", (x1, y), (HX + T, y), 0, ROOM_H, T, m["concrete"], f)
    box_span("Wand_Nord_Tuersturz", (x0, y), (x1, y), door_h, ROOM_H, T, m["concrete"], f)

    # Ostwand (Sichtbeton)
    x = HX + T / 2
    box_span("Wand_Ost", (x, -HY), (x, HY), 0, ROOM_H, T, m["concrete"], f)

    # Fensterfronten West und Süd
    fw = "Graybox/Fenster"
    window_front("Fenster_West", (-HX - T / 2, -HY), (-HX - T / 2, HY + T), m, fw)
    window_front("Fenster_Sued", (-HX, HY + T / 2), (HX + T, HY + T / 2), m, fw)


def build_meeting_room_frame(m):
    """Gläserner Besprechungsraum – vorerst nur die Stahlprofile am Boden, an der Decke und als Pfosten."""
    f = "Graybox/Besprechungsraum"
    segments = [
        ("Nord", (GLASS_X, -GLASS_Y), (HX, -GLASS_Y)),
        ("Sued", (GLASS_X, GLASS_Y), (HX, GLASS_Y)),
        ("West_1", (GLASS_X, -GLASS_Y), (GLASS_X, GLASS_DOOR[0])),
        ("West_2", (GLASS_X, GLASS_DOOR[1]), (GLASS_X, GLASS_Y)),
    ]
    for name, a, b in segments:
        box_span("Glaswand_{}_Profil_Boden".format(name), a, b, 0, 5, 6, m["steel"], f)
        box_span("Glaswand_{}_Profil_Decke".format(name), a, b, ROOM_H - 5, ROOM_H, 6, m["steel"], f)
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        posts = max(1, int(length // 130))
        for i in range(posts + 1):
            t = i / float(posts)
            p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            box("Glaswand_{}_Pfosten_{}".format(name, i), (p[0], p[1], ROOM_H / 2), (5, 5, ROOM_H), m["steel"], folder=f)


# ---------------------------------------------------------------------------
# Möbel aus dem Grundriss
# ---------------------------------------------------------------------------

def build_chair(name, spot, seat_forward, m, folder):
    """Stuhl, dessen Sitzmitte `seat_forward` cm vor dem Platz liegt (negativ = dahinter)."""
    yaw = spot["yaw"]
    box(name + "_Sitz", local(spot, seat_forward, 0, 46), (48, 48, 7), m["felt"], yaw, folder)
    box(name + "_Lehne", local(spot, seat_forward - 24, 0, 80), (6, 46, 56), m["felt"], yaw, folder)
    box(name + "_Saeule", local(spot, seat_forward, 0, 23), (5, 5, 40), m["steel"], yaw, folder)
    box(name + "_Fuss", local(spot, seat_forward, 0, 2), (56, 56, 4), m["steel"], yaw, folder)


def build_desk(spot, m):
    """x/y = Mitte der Tischplatte (160 x 80 cm); die Person sitzt 75 cm dahinter."""
    d = spot["deskId"]
    yaw = spot["yaw"]
    f = "Graybox/Arbeitsplaetze/" + d
    box(d + "_Platte", local(spot, 0, 0, DESK_H - 1.5), (80, 160, 3), m["oak"], yaw, f)
    for side, sign in (("L", -1), ("R", 1)):
        box(d + "_Kufe_" + side, local(spot, 0, sign * 76, (DESK_H - 3) / 2), (70, 4, DESK_H - 3), m["steel"], yaw, f)
    box(d + "_Monitor", local(spot, 28, 0, 104), (2.5, 62, 37), m["screen"], yaw, f)
    box(d + "_Monitor_Arm", local(spot, 31, 0, 83), (3, 6, 18), m["steel"], yaw, f)
    box(d + "_Monitor_Fuss", local(spot, 30, 0, DESK_H + 0.5), (18, 22, 1), m["steel"], yaw, f)
    box(d + "_Tastatur", local(spot, -15, 0, DESK_H + 0.8), (14, 44, 1.6), m["steel"], yaw, f)
    build_chair(d + "_Stuhl", spot, -DESK_SEAT_OFFSET - CHAIR_PUSHED_BACK, m, f)


def build_station(spot, m):
    """x/y = Mitte der Wandtafel; die Person steht 70 cm davor."""
    d = spot["deskId"]
    yaw = spot["yaw"]
    f = "Graybox/Stationen/" + d
    box(d + "_Tafel", local(spot, 0, 0, 150), (4, 200, 120), m["board"], yaw, f)
    box(d + "_Tafel_Rahmen", local(spot, 3, 0, 150), (2, 206, 126), m["brass"], yaw, f)


def build_meeting(spots, m):
    """x/y = Stuhlmitte. Der Tisch umschließt die Punkte 45 cm vor jedem Platz (±40 cm seitlich)."""
    if not spots:
        return
    f = "Graybox/Besprechungsraum"
    edge = [local(s, 45, side, 0) for s in spots for side in (-40, 40)]
    xs = [p[0] for p in edge]
    ys = [p[1] for p in edge]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    length = max(120.0, max(xs) - min(xs))
    width = max(90.0, max(ys) - min(ys))

    box("Besprechungstisch_Platte", (cx, cy, DESK_H - 2), (length, width, 4), m["walnut"], folder=f)
    for n, dx in enumerate((-length / 4, length / 4), start=1):
        box("Besprechungstisch_Fuss_{}".format(n), (cx + dx, cy, (DESK_H - 4) / 2), (10, width * 0.5, DESK_H - 4), m["steel"], folder=f)
    for spot in spots:
        build_chair(spot["deskId"] + "_Stuhl", spot, -CHAIR_PUSHED_BACK, m, f)


# ---------------------------------------------------------------------------
# Licht, Atmosphäre, Belichtung
# ---------------------------------------------------------------------------

def build_lighting(m):
    f = "Licht"

    # Sonne: später Nachmittag im Oktober, tief aus Westen (leicht Süd), 5200 K
    sun = eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 800),
                                     unreal.Rotator(roll=0.0, pitch=-20.0, yaw=-12.0))
    sun.set_actor_label("Sonne")
    sun.set_folder_path(f)
    sun.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun_c = sun.get_component_by_class(unreal.DirectionalLightComponent)
    set_prop(sun_c, "intensity", 40000.0)            # Lux – tief stehende Nachmittagssonne
    set_prop(sun_c, "use_temperature", True)
    set_prop(sun_c, "temperature", 5200.0)
    set_prop(sun_c, "atmosphere_sun_light", True)
    set_prop(sun_c, "light_source_angle", 1.0)

    sky = eas.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 900))
    sky.set_actor_label("Himmelslicht")
    sky.set_folder_path(f)
    sky.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    set_prop(sky.get_component_by_class(unreal.SkyLightComponent), "real_time_capture", True)

    atmo = eas.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    atmo.set_actor_label("Atmosphaere")
    atmo.set_folder_path(f)

    clouds = eas.spawn_actor_from_class(unreal.VolumetricCloud, unreal.Vector(0, 0, 0))
    clouds.set_actor_label("Wolken")
    clouds.set_folder_path(f)

    # Ein Hauch Dunst mit volumetrischem Nebel, damit die Lichtbahnen der Sonne spürbar werden
    fog = eas.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, -100))
    fog.set_actor_label("Dunst")
    fog.set_folder_path(f)
    fog_c = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    if fog_c:
        set_prop(fog_c, "fog_density", 0.003)
        set_prop(fog_c, "enable_volumetric_fog", True)

    # Drei lange Linienleuchten über den Tischinseln, 4000 K, gedimmt
    for n, y in enumerate((-170.0, 0.0, 170.0), start=1):
        name = "Linienleuchte_{}".format(n)
        cx, length = -250.0, 900.0
        box(name + "_Gehaeuse", (cx, y, ROOM_H - 30), (length, 8, 6), m["steel"], folder=f + "/Decke")
        box(name + "_Abhaengung_1", (cx - length / 2 + 40, y, ROOM_H - 13), (1, 1, 28), m["steel"], folder=f + "/Decke")
        box(name + "_Abhaengung_2", (cx + length / 2 - 40, y, ROOM_H - 13), (1, 1, 28), m["steel"], folder=f + "/Decke")
        light = eas.spawn_actor_from_class(unreal.RectLight, unreal.Vector(cx, y, ROOM_H - 34),
                                           unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0))
        light.set_actor_label(name)
        light.set_folder_path(f + "/Decke")
        light.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        lc = light.get_component_by_class(unreal.RectLightComponent)
        set_prop(lc, "intensity_units", enum_value(unreal.LightUnits, "LUMENS"))
        set_prop(lc, "intensity", 2500.0)
        # Rect Light strahlt entlang seiner X-Achse (nach unten) – Breite/Höhe liegen in der Deckenebene
        set_prop(lc, "source_width", 6.0)
        set_prop(lc, "source_height", length - 20.0)
        set_prop(lc, "use_temperature", True)
        set_prop(lc, "temperature", 4000.0)
        set_prop(lc, "attenuation_radius", 1000.0)
        set_prop(lc, "barn_door_angle", 70.0)


def pp(settings, name, value):
    """Post-Process-Wert setzen inkl. override_-Schalter."""
    set_prop(settings, "override_" + name, True)
    set_prop(settings, name, value)


def build_post_process():
    ppv = eas.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, ROOM_H / 2))
    ppv.set_actor_label("Belichtung")
    ppv.set_folder_path("Licht")
    set_prop(ppv, "unbound", True)

    s = ppv.get_editor_property("settings")
    # Belichtung wie eine Kamera im Innenraum bei Tageslicht. Bewusst enger Bereich und träge,
    # damit beim Kameraflug nichts springt. Ist das Licht final abgestimmt, min = max setzen
    # (= feste Belichtung, wie im Designkonzept vorgesehen).
    pp(s, "auto_exposure_method", enum_value(unreal.AutoExposureMethod, "AEM_HISTOGRAM", "HISTOGRAM"))
    pp(s, "auto_exposure_min_brightness", 8.5)
    pp(s, "auto_exposure_max_brightness", 10.5)
    pp(s, "auto_exposure_bias", 0.0)
    pp(s, "auto_exposure_speed_up", 0.5)
    pp(s, "auto_exposure_speed_down", 0.5)
    # Zurückhaltende Linseneffekte – nichts, was nach Spiel aussieht
    pp(s, "bloom_intensity", 0.2)
    pp(s, "vignette_intensity", 0.25)
    pp(s, "scene_fringe_intensity", 0.0)
    pp(s, "film_grain_intensity", 0.0)
    # Lumen ausdrücklich, falls die Projekt-Defaults einmal geändert werden
    pp(s, "dynamic_global_illumination_method", enum_value(unreal.DynamicGlobalIlluminationMethod, "LUMEN"))
    pp(s, "reflection_method", enum_value(unreal.ReflectionMethod, "LUMEN"))
    pp(s, "lumen_final_gather_quality", 2.0)
    ppv.set_editor_property("settings", s)


def build_cameras():
    # Startpunkt: Südost-Ecke, Blick nach Nordwest über die Tischinseln (wie die Hauptkamera im Konzept)
    start = eas.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(700, 470, 100),
                                       unreal.Rotator(roll=0.0, pitch=0.0, yaw=-150.0))
    start.set_actor_label("Startpunkt")

    cam = eas.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(740, 500, 240),
                                     unreal.Rotator(roll=0.0, pitch=-17.0, yaw=-150.0))
    cam.set_actor_label("Kamera_Uebersicht")
    cam.set_folder_path("Kameras")
    cam_c = cam.get_cine_camera_component()
    set_prop(cam_c, "current_focal_length", 24.0)
    set_prop(cam_c, "current_aperture", 5.6)
    focus = cam_c.get_editor_property("focus_settings")
    set_prop(focus, "manual_focus_distance", 900.0)
    set_prop(cam_c, "focus_settings", focus)


# ---------------------------------------------------------------------------
# Ablauf
# ---------------------------------------------------------------------------

def open_or_create_level():
    if eal.does_asset_exist(MAP_PATH):
        if not les.load_level(MAP_PATH):
            raise RuntimeError("Level {} konnte nicht geladen werden".format(MAP_PATH))
        for actor in eas.get_all_level_actors():
            if isinstance(actor, unreal.WorldSettings):
                continue
            eas.destroy_actor(actor)
        log("build_level: bestehendes Level geleert")
    else:
        if not les.new_level(MAP_PATH):
            raise RuntimeError("Level {} konnte nicht angelegt werden".format(MAP_PATH))
        log("build_level: neues Level angelegt")


def main():
    global CUBE
    CUBE = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")

    if not hasattr(unreal, "OfficeDirector"):
        raise RuntimeError("Klasse OfficeDirector fehlt – zuerst das C++-Modul AgentOffice bauen.")

    spots = load_layout()
    materials = make_materials()
    open_or_create_level()

    build_room(materials)
    build_meeting_room_frame(materials)
    for spot in spots:
        kind = spot.get("type", "desk")
        if kind == "desk":
            build_desk(spot, materials)
        elif kind == "station":
            build_station(spot, materials)
    build_meeting([s for s in spots if s.get("type") == "meeting"], materials)

    build_lighting(materials)
    build_post_process()
    build_cameras()

    # Regie in der Raummitte = Ursprung der Koordinaten aus DeskLayout.json
    director = eas.spawn_actor_from_class(unreal.OfficeDirector, unreal.Vector(0, 0, 0))
    director.set_actor_label("OfficeDirector")

    if not les.save_current_level():
        raise RuntimeError("Level konnte nicht gespeichert werden")
    log("build_level: {} gespeichert".format(MAP_PATH))


main()
