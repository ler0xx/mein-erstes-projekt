"""
Baut das Graubox-Level /Game/Maps/Office für das Agent Office.

Aufruf ohne Editor-Fenster (aus dem Ordner unreal/AgentOffice):

    "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" ^
        "%CD%/AgentOffice.uproject" -run=pythonscript -script="%CD%/Scripts/build_level.py"

Oder im offenen Editor: Werkzeuge > Python-Skript ausführen > Scripts/build_level.py

Das Skript ist wiederholbar: Existiert das Level schon, wird sein Inhalt
komplett ersetzt. Tische, Stühle usw. werden aus Content/Data/DeskLayout.json
erzeugt – derselben Datei, die der AOfficeDirector zur Laufzeit liest.

Alles hier ist bewusst Graubox (einfache Quader mit realistischen
Materialwerten). Echte Möbel/Assets kommen später.
"""

import json
import math
import os

import unreal

MAP_PATH = "/Game/Maps/Office"
MAT_DIR = "/Game/Graybox/Materials"

# Raum (cm). Ursprung = Ecke Fensterwand/Westwand, Boden-Oberkante bei Z = 0.
ROOM_W = 2000.0   # entlang X
ROOM_D = 1600.0   # entlang Y
ROOM_H = 300.0
WALL_T = 30.0
SILL_H = 80.0     # Brüstungshöhe der Fenster
WINDOW_TOP = 270.0
WINDOWS = [(200.0, 600.0), (800.0, 1200.0), (1400.0, 1800.0)]  # Fensteröffnungen in der Südwand (y = 0)

DESK_H = 75.0

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
    # Realistische Albedo-Werte: nichts ist ganz weiß oder ganz schwarz
    return {
        "floor":   make_mi(master, "MI_Floor_Oak",       (0.28, 0.17, 0.09), 0.45),
        "wall":    make_mi(master, "MI_Wall_Plaster",    (0.70, 0.69, 0.66), 0.90),
        "ceiling": make_mi(master, "MI_Ceiling",         (0.78, 0.78, 0.76), 0.95),
        "desk":    make_mi(master, "MI_Desk_Laminate",   (0.62, 0.61, 0.58), 0.40),
        "walnut":  make_mi(master, "MI_Table_Walnut",    (0.09, 0.045, 0.02), 0.35),
        "metal":   make_mi(master, "MI_Metal_Black",     (0.03, 0.03, 0.03), 0.35, 1.0),
        "alu":     make_mi(master, "MI_Metal_Alu",       (0.60, 0.60, 0.62), 0.30, 1.0),
        "fabric":  make_mi(master, "MI_Chair_Fabric",    (0.018, 0.018, 0.02), 0.90),
        "screen":  make_mi(master, "MI_Screen_Off",      (0.004, 0.004, 0.005), 0.12),
        "board":   make_mi(master, "MI_Whiteboard",      (0.80, 0.80, 0.79), 0.20),
        "panel":   make_mi(master, "MI_LightPanel",      (0.85, 0.85, 0.85), 0.60),
        "ground":  make_mi(master, "MI_Ground_Outside",  (0.12, 0.12, 0.11), 0.90),
    }


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

CUBE = None


def box(label, center, size, mat, yaw=0.0, folder="Graybox"):
    """Quader mit Mittelpunkt `center` und Kantenlängen `size` (cm)."""
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

def build_room(m):
    W, D, H, T = ROOM_W, ROOM_D, ROOM_H, WALL_T
    f = "Graybox/Raum"

    box("Boden", (W / 2, D / 2, -5), (W + 2 * T, D + 2 * T, 10), m["floor"], folder=f)
    box("Decke", (W / 2, D / 2, H + 15), (W + 2 * T, D + 2 * T, 30), m["ceiling"], folder=f)
    box("Aussengelaende", (W / 2, D / 2, -20), (30000, 30000, 10), m["ground"], folder=f)

    box("Wand_Nord", (W / 2, D + T / 2, H / 2), (W + 2 * T, T, H), m["wall"], folder=f)
    box("Wand_Ost", (W + T / 2, D / 2, H / 2), (T, D, H), m["wall"], folder=f)
    box("Wand_West", (-T / 2, D / 2, H / 2), (T, D, H), m["wall"], folder=f)

    # Südwand mit Fensteröffnungen: Brüstung + Sturz + Pfeiler
    y = -T / 2
    box("Wand_Sued_Bruestung", (W / 2, y, SILL_H / 2), (W + 2 * T, T, SILL_H), m["wall"], folder=f)
    box("Wand_Sued_Sturz", (W / 2, y, (WINDOW_TOP + H) / 2), (W + 2 * T, T, H - WINDOW_TOP), m["wall"], folder=f)
    edges = [-T] + [e for win in WINDOWS for e in win] + [W + T]
    for i in range(0, len(edges), 2):
        x0, x1 = edges[i], edges[i + 1]
        box("Wand_Sued_Pfeiler_{}".format(i // 2 + 1), ((x0 + x1) / 2, y, (SILL_H + WINDOW_TOP) / 2),
            (x1 - x0, T, WINDOW_TOP - SILL_H), m["wall"], folder=f)

    # Schmale Fensterrahmen (dunkles Metall), Glas folgt mit echten Assets
    fw = "Graybox/Fenster"
    win_h = WINDOW_TOP - SILL_H
    for n, (x0, x1) in enumerate(WINDOWS, start=1):
        cx = (x0 + x1) / 2
        box("Fenster{}_Rahmen_Unten".format(n), (cx, y, SILL_H + 2.5), (x1 - x0, 8, 5), m["metal"], folder=fw)
        box("Fenster{}_Rahmen_Oben".format(n), (cx, y, WINDOW_TOP - 2.5), (x1 - x0, 8, 5), m["metal"], folder=fw)
        box("Fenster{}_Rahmen_Links".format(n), (x0 + 2.5, y, SILL_H + win_h / 2), (5, 8, win_h), m["metal"], folder=fw)
        box("Fenster{}_Rahmen_Rechts".format(n), (x1 - 2.5, y, SILL_H + win_h / 2), (5, 8, win_h), m["metal"], folder=fw)
        box("Fenster{}_Sprosse".format(n), (cx, y, SILL_H + win_h / 2), (4, 6, win_h), m["metal"], folder=fw)
        box("Fenster{}_Fensterbank".format(n), (cx, 12, SILL_H + 1.5), (x1 - x0 + 10, 26, 3), m["desk"], folder=fw)


# ---------------------------------------------------------------------------
# Möbel aus dem Grundriss
# ---------------------------------------------------------------------------

def build_chair(name, spot, m, folder, back_offset=-45.0):
    yaw = spot["yaw"]
    box(name + "_Sitz", local(spot, back_offset, 0, 46), (48, 48, 7), m["fabric"], yaw, folder)
    box(name + "_Lehne", local(spot, back_offset - 24, 0, 80), (6, 46, 56), m["fabric"], yaw, folder)
    box(name + "_Saeule", local(spot, back_offset, 0, 23), (5, 5, 40), m["metal"], yaw, folder)
    box(name + "_Fuss", local(spot, back_offset, 0, 2), (56, 56, 4), m["metal"], yaw, folder)


def build_desk(spot, m):
    d = spot["deskId"]
    yaw = spot["yaw"]
    f = "Graybox/Arbeitsplaetze/" + d
    box(d + "_Platte", local(spot, 75, 0, DESK_H - 1.5), (80, 160, 3), m["desk"], yaw, f)
    for side, sign in (("L", -1), ("R", 1)):
        box(d + "_Wange_" + side, local(spot, 75, sign * 77, (DESK_H - 3) / 2), (70, 3, DESK_H - 3), m["metal"], yaw, f)
    box(d + "_Monitor", local(spot, 98, 0, 104), (2.5, 62, 37), m["screen"], yaw, f)
    box(d + "_Monitor_Arm", local(spot, 102, 0, 83), (3, 6, 18), m["alu"], yaw, f)
    box(d + "_Monitor_Fuss", local(spot, 100, 0, DESK_H + 0.5), (18, 22, 1), m["alu"], yaw, f)
    box(d + "_Tastatur", local(spot, 55, 0, DESK_H + 0.8), (14, 44, 1.6), m["metal"], yaw, f)
    build_chair(d + "_Stuhl", spot, m, f)


def build_station(spot, m):
    d = spot["deskId"]
    yaw = spot["yaw"]
    f = "Graybox/Stationen/" + d
    # Tafel an der Wand vor der Person
    box(d + "_Tafel", local(spot, 172, 0, 150), (2, 180, 110), m["board"], yaw, f)
    box(d + "_Tafel_Rahmen", local(spot, 174, 0, 150), (2, 186, 116), m["alu"], yaw, f)


def build_meeting(spots, m):
    if not spots:
        return
    f = "Graybox/Besprechung"
    xs = [s["x"] for s in spots]
    ys = [s["y"] for s in spots]
    inset = 60.0  # Abstand Person -> Tischkante
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    length = max(120.0, (max(xs) - min(xs)) - 2 * inset)
    width = max(90.0, (max(ys) - min(ys)) - 2 * inset)

    box("Besprechungstisch_Platte", (cx, cy, DESK_H - 2), (length, width, 4), m["walnut"], folder=f)
    for n, dx in enumerate((-length / 4, length / 4), start=1):
        box("Besprechungstisch_Fuss_{}".format(n), (cx + dx, cy, (DESK_H - 4) / 2), (10, width * 0.5, DESK_H - 4), m["metal"], folder=f)
    for spot in spots:
        build_chair(spot["deskId"] + "_Stuhl", spot, m, f, back_offset=-30.0)


# ---------------------------------------------------------------------------
# Licht, Atmosphäre, Belichtung
# ---------------------------------------------------------------------------

def build_lighting(m):
    f = "Licht"

    # Sonne: nachmittags, fällt schräg durch die Südfenster
    sun = eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 800),
                                     unreal.Rotator(roll=0.0, pitch=-32.0, yaw=62.0))
    sun.set_actor_label("Sonne")
    sun.set_folder_path(f)
    sun.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun_c = sun.get_component_by_class(unreal.DirectionalLightComponent)
    set_prop(sun_c, "intensity", 75000.0)            # Lux – echtes Sonnenlicht
    set_prop(sun_c, "atmosphere_sun_light", True)
    set_prop(sun_c, "light_source_angle", 0.5357)

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

    fog = eas.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, -100))
    fog.set_actor_label("Dunst")
    fog.set_folder_path(f)
    fog_c = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    if fog_c:
        set_prop(fog_c, "fog_density", 0.004)

    # Deckenleuchten: 6 Flächenleuchten, zusammen ~500 lx auf den Tischen
    for ix, x in enumerate((500.0, 1000.0, 1500.0)):
        for iy, y in enumerate((450.0, 1050.0)):
            name = "Deckenleuchte_{}_{}".format(ix + 1, iy + 1)
            box(name + "_Panel", (x, y, ROOM_H - 1.5), (62, 122, 3), m["panel"], folder=f + "/Decke")
            light = eas.spawn_actor_from_class(unreal.RectLight, unreal.Vector(x, y, ROOM_H - 4),
                                               unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0))
            light.set_actor_label(name)
            light.set_folder_path(f + "/Decke")
            light.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
            lc = light.get_component_by_class(unreal.RectLightComponent)
            set_prop(lc, "intensity_units", enum_value(unreal.LightUnits, "LUMENS"))
            set_prop(lc, "intensity", 2800.0)
            set_prop(lc, "source_width", 60.0)
            set_prop(lc, "source_height", 120.0)
            set_prop(lc, "use_temperature", True)
            set_prop(lc, "temperature", 4000.0)
            set_prop(lc, "attenuation_radius", 1200.0)
            set_prop(lc, "barn_door_angle", 80.0)


def pp(settings, name, value):
    """Post-Process-Wert setzen inkl. override_-Schalter."""
    set_prop(settings, "override_" + name, True)
    set_prop(settings, name, value)


def build_post_process():
    ppv = eas.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(ROOM_W / 2, ROOM_D / 2, ROOM_H / 2))
    ppv.set_actor_label("Belichtung")
    ppv.set_folder_path("Licht")
    set_prop(ppv, "unbound", True)

    s = ppv.get_editor_property("settings")
    # Automatische Belichtung wie eine Kamera, Bereich passend für Innenräume mit Tageslicht (EV100)
    pp(s, "auto_exposure_method", enum_value(unreal.AutoExposureMethod, "AEM_HISTOGRAM", "HISTOGRAM"))
    pp(s, "auto_exposure_min_brightness", 6.0)
    pp(s, "auto_exposure_max_brightness", 13.0)
    pp(s, "auto_exposure_bias", 0.0)
    pp(s, "auto_exposure_speed_up", 2.0)
    pp(s, "auto_exposure_speed_down", 1.0)
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
    for spot in spots:
        kind = spot.get("type", "desk")
        if kind == "desk":
            build_desk(spot, materials)
        elif kind == "station":
            build_station(spot, materials)
    build_meeting([s for s in spots if s.get("type") == "meeting"], materials)

    build_lighting(materials)
    build_post_process()

    director = eas.spawn_actor_from_class(unreal.OfficeDirector, unreal.Vector(0, 0, 0))
    director.set_actor_label("OfficeDirector")

    start = eas.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(150, 160, 100),
                                       unreal.Rotator(roll=0.0, pitch=0.0, yaw=40.0))
    start.set_actor_label("Startpunkt")

    if not les.save_current_level():
        raise RuntimeError("Level konnte nicht gespeichert werden")
    log("build_level: {} gespeichert".format(MAP_PATH))


main()
