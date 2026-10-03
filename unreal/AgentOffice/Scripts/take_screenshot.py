"""
Automatischer Screenshot des laufenden Büros (inkl. Namensschilder).

Aufruf (aus dem Ordner unreal/AgentOffice):

    "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe" ^
        "%CD%/AgentOffice.uproject" /Game/Maps/Office -game -windowed -ResX=1600 -ResY=900 -log ^
        -ExecCmds="DisableAllScreenMessages, py %CD%/Scripts/take_screenshot.py"

Mit -RenderOffscreen statt -windowed läuft das Ganze ohne sichtbares Fenster.

Ablauf: stellt die Kamera an die Südfenster (Blick nach Norden), wartet, bis
Shader, Lumen und Belichtung eingeschwungen sind, macht `shot showui`
(HighResShot würde die Namensschilder weglassen) und beendet das Spiel.
Das Bild landet in Saved/Screenshots/<Plattform>/.

Wartezeiten über Umgebungsvariablen änderbar:
AGENT_OFFICE_SHOT_DELAY (Sekunden bis zum Bild, Standard 45),
AGENT_OFFICE_SHOT_COUNT (Anzahl Bilder im Abstand von 15 s, Standard 1).
"""

import os
import time

import unreal

SHOT_DELAY = float(os.environ.get("AGENT_OFFICE_SHOT_DELAY", "45"))
SHOT_COUNT = int(os.environ.get("AGENT_OFFICE_SHOT_COUNT", "1"))
SHOT_SPACING = 15.0
# Blick von der Südfensterfront nach Norden über beide Tischreihen bis zu den Stationen
SHOT_LOCATION = unreal.Vector(-330.0, 530.0, 285.0)
SHOT_ROTATION = unreal.Rotator(roll=0.0, pitch=-18.0, yaw=-90.0)
SHOT_FOCAL_LENGTH = 16.0  # mm – weitwinklig, damit alle Tische aufs Bild passen

_start = time.time()
_state = {"camera": False, "shots": 0, "quit": False, "handle": None}


def _game_world():
    for world in unreal.ObjectIterator(unreal.World):
        if unreal.GameplayStatics.get_player_controller(world, 0):
            return world
    return None


def _use_shot_camera(world):
    controller = unreal.GameplayStatics.get_player_controller(world, 0)
    pawn = controller.get_controlled_pawn()
    if pawn:
        pawn.set_actor_hidden_in_game(True)  # die Kugel des Standard-Pawns nicht mit aufs Bild
    for cam in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CineCameraActor):
        # Im Spiel gibt es keine Actor-Labels; die Übersichtskamera ist die einzige CineCamera im Level.
        # Sie wird für das Bild versetzt: Von ihrem Platz in der Südost-Ecke schneidet sie die
        # Namensschilder oben ab und schaut durch die Profile des Besprechungsraums.
        cam.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        cam.set_actor_location_and_rotation(SHOT_LOCATION, SHOT_ROTATION, False, True)
        cam.get_cine_camera_component().set_editor_property("current_focal_length", SHOT_FOCAL_LENGTH)
        controller.set_view_target_with_blend(cam, 0.0)
        unreal.log("take_screenshot: Ansicht = Kamera bei {}".format(SHOT_LOCATION))
        return True
    unreal.log_warning("take_screenshot: keine CineCamera gefunden – nehme Spieler-Ansicht")
    return True


def _tick(delta_seconds):
    elapsed = time.time() - _start
    world = _game_world()
    if not world:
        return

    if not _state["camera"] and elapsed > 2.0:
        _state["camera"] = _use_shot_camera(world)

    next_shot = SHOT_DELAY + _state["shots"] * SHOT_SPACING
    if _state["shots"] < SHOT_COUNT and elapsed > next_shot:
        unreal.SystemLibrary.execute_console_command(world, "shot showui")
        _state["shots"] += 1
        unreal.log("take_screenshot: Bild {} von {} nach {:.0f} s".format(_state["shots"], SHOT_COUNT, elapsed))

    if _state["shots"] >= SHOT_COUNT and not _state["quit"] and elapsed > next_shot + 5.0:
        _state["quit"] = True
        unreal.unregister_slate_post_tick_callback(_state["handle"])
        unreal.log("take_screenshot: fertig, beende Spiel")
        # quit_game beendet das Spiel mit -RenderOffscreen nicht – der Konsolenbefehl schon
        unreal.SystemLibrary.execute_console_command(world, "quit")


_state["handle"] = unreal.register_slate_post_tick_callback(_tick)
unreal.log("take_screenshot: Bild in {:.0f} s".format(SHOT_DELAY))
