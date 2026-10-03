# Agent Office in Unreal Engine 5.8

Eine eigene Unreal-Anwendung, die das **Agent Office** fotorealistisch zeigt:
Die KI-Agenten sitzen als Menschen an ihren Schreibtischen, das Büro wird von
echtem Sonnenlicht durch die Fenster beleuchtet.

Die Anwendung **liest nur** den Live-Zustand des Agent Office (die Datei
`workers.json`) und stellt ihn dar. Die bestehende Browser-Ansicht des Office
wird dabei nicht verändert.

> **Stand:** Technisches Grundgerüst mit Graubox-Level. Die Figuren sind vorerst
> das Engine-Mannequin (dunkel eingefärbt), die Möbel einfache Quader. Echte
> Möbel und MetaHumans (dunkler Anzug, Sonnenbrille) folgen.

---

## Was ist schon drin?

| Teil | Datei(en) | Aufgabe |
|---|---|---|
| Render-Einstellungen | `Config/DefaultEngine.ini` | Lumen (GI + Reflexionen, Hardware-Raytracing wenn möglich), Nanite, Virtual Shadow Maps, TSR, DirectX 12 / SM6 |
| Datenschicht | `Source/AgentOffice/OfficeStateSubsystem.*` | liest alle 2 s `workers.json`, meldet „Mitarbeiter kommt / geht / ändert sich“ |
| Grundriss | `Content/Data/DeskLayout.json` | wo welcher Platz steht (Schreibtische, Stationen, Besprechungstisch) |
| Regie | `Source/AgentOffice/OfficeDirector.*` | setzt für jeden Mitarbeiter eine Figur an seinen Platz |
| Figur | `Source/AgentOffice/AgentCharacter.*` | Person mit Namensschild, Bildschirmlicht und Status „arbeitet“ / „wartet“ |
| Testlevel | `Scripts/build_level.py` | baut `/Game/Maps/Office` (Raum, Fenster, Tische, Licht, Belichtung) |

---

## Voraussetzungen

1. **Unreal Engine 5.8** (Epic Games Launcher), z. B. unter `C:/Program Files/Epic Games/UE_5.8`.
2. **Visual Studio 2022** oder die **Build Tools 2022** mit:
   - „Desktopentwicklung mit C++“ (MSVC v143)
   - **Windows SDK 10.0.22621** (ältere wie 10.0.19041 sind *nicht* nötig)
   - **.NET Framework 4.6.2 Targeting Pack** bzw. **.NET Framework 4.8 SDK**
     (in UE 5.8 die Komponente `Microsoft.Net.Component.4.6.2.TargetingPack`).
     Ohne sie bricht der Editor-Build mit
     `Could not find NetFxSDK install dir` ab.
     Nachinstallieren: *Visual Studio Installer → Ändern → Einzelne Komponenten →
     „.NET Framework 4.6.2-Zielpaket“ und „.NET Framework 4.8 SDK“*.

---

## Bauen

In einer Eingabeaufforderung im Ordner `unreal/AgentOffice`:

```bat
"C:/Program Files/Epic Games/UE_5.8/Engine/Build/BatchFiles/Build.bat" AgentOfficeEditor Win64 Development -Project="%CD%/AgentOffice.uproject" -WaitMutex
```

Alternativ: Rechtsklick auf `AgentOffice.uproject` → *Generate Visual Studio project files*,
dann in Visual Studio bauen. Oder einfach `AgentOffice.uproject` doppelklicken –
Unreal fragt dann, ob es die fehlenden Module bauen soll.

## Testlevel erzeugen

Das Level ist eine Binärdatei und wird deshalb **per Skript erzeugt**
(nicht eingecheckt). Einmal nach dem Bauen ausführen:

```bat
"C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "%CD%/AgentOffice.uproject" -run=pythonscript -script="%CD%/Scripts/build_level.py"
```

Das Skript ist wiederholbar – nach einer Änderung am Grundriss einfach erneut
ausführen. Es legt an:

- Raum 20 × 16 m, 3 m hoch, Eichenboden, Südwand mit drei großen Fensteröffnungen
- Schreibtische mit Monitor, Tastatur und Stuhl an allen `desk`-Plätzen
- Tafeln an den Stationen, Besprechungstisch aus den `meeting`-Plätzen
- Sonne (75 000 lx), Himmelslicht, Atmosphäre, Wolken, leichter Dunst
- sechs Deckenleuchten (je 2 800 lm, 4 000 K)
- Post-Process mit automatischer Belichtung (EV100 6–13) und zurückhaltenden Linseneffekten
- den `OfficeDirector` und einen Startpunkt

## Starten

- **Im Editor:** `AgentOffice.uproject` öffnen → *Play* (Alt+P).
- **Als eigenes Fenster:**
  ```bat
  "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe" "%CD%/AgentOffice.uproject" -game
  ```

Mit **W A S D** + Maus fliegt man durch das Büro.

---

## Office-Ordner einstellen

Die App liest `<Office-Ordner>/workers.json`. Standard:

```
C:/Users/info/agent-office/ler0xx/mein-erstes-projekt/.agent-office
```

Ändern – entweder dauerhaft in `Config/DefaultGame.ini`:

```ini
[/Script/AgentOffice.OfficeStateSubsystem]
OfficeDir=D:/anderer/pfad/.agent-office
PollIntervalSeconds=2.0
```

… oder beim Start (hat Vorrang):

```bat
UnrealEditor.exe "%CD%/AgentOffice.uproject" -game -OfficeDir="D:/anderer/pfad/.agent-office"
```

Im Log (`Saved/Logs/AgentOffice.log`) steht, welche Datei gelesen wird und
welche Mitarbeiter kommen und gehen.

### Welche Daten werden gelesen?

Pro Mitarbeiter **nur**: `id`, `name`, `deskId`, `color`, `activity`,
`midTurn` (arbeitet gerade) und `task.name`.
Alle anderen Felder – insbesondere `hookToken`, `prompt`, `sessionId`,
`tracker` – werden übersprungen und **nie** gespeichert, angezeigt oder geloggt.
Die App schreibt nichts in den Office-Ordner.

Fehlt die Datei oder ist sie gerade halb geschrieben, bleibt der letzte gültige
Stand stehen. Fehlt sie dreimal hintereinander, gilt das Büro als leer.

---

## Grundriss (`Content/Data/DeskLayout.json`)

```json
[
  {"deskId": "desk-1", "label": "Schreibtisch 1", "type": "desk", "x": 300, "y": 400, "yaw": -90},
  ...
]
```

| Feld | Bedeutung |
|---|---|
| `deskId` | muss zur `deskId` in `workers.json` passen (`desk-1` … `desk-8`, `station-pulls`, `station-queue`, `meeting-1` … `meeting-4`) |
| `label` | lesbarer Name |
| `type` | `desk` (Schreibtisch), `station` (Tafel/Brett) oder `meeting` (Platz am Besprechungstisch) |
| `x`, `y` | **Standort der Person** in cm, relativ zum `OfficeDirector` (im Testlevel = Raumecke an der Fensterwand) |
| `yaw` | **Blickrichtung der Person** in Grad: 0 = +X (Osten), 90 = +Y (weg vom Fenster), −90 = zum Fenster |

Der Tisch steht vor der Person (in Blickrichtung). `meeting-1` ist der Kopf des
Besprechungstisches; der Tisch selbst wird aus den `meeting`-Plätzen berechnet.
Mitarbeiter mit einer unbekannten `deskId` warten in einer „Lobby“ an der Nordwand.

Die aktuellen Koordinaten sind **Platzhalter**. Die finalen liefert das
Designkonzept (`docs/agent-office-ue5/`) im selben Format – Datei ersetzen,
`build_level.py` erneut ausführen, fertig.

---

## Figuren austauschen (MetaHumans)

Die Figur ist austauschbar, ohne Code zu ändern:

- **Nur das Mesh tauschen** – in `Config/DefaultGame.ini`:
  ```ini
  [/Script/AgentOffice.OfficeDirector]
  AgentMeshOverride=/Game/MetaHumans/Agent/Body/MeinMesh.MeinMesh
  ```
- **Ganze Figur als Blueprint** – im Editor eine Blueprint-Klasse von
  `AgentCharacter` anlegen (z. B. `BP_MetaHumanAgent`), dort MetaHuman-Körper,
  Kopf, Anzug und Sonnenbrille einbauen, `Tint Placeholder` ausschalten und
  in `DefaultGame.ini` eintragen:
  ```ini
  AgentClass=/Game/Agents/BP_MetaHumanAgent.BP_MetaHumanAgent_C
  ```
  Das Blueprint-Event **On Worker Updated** meldet jede Statusänderung
  (z. B. um zwischen Tipp- und Warte-Animation umzuschalten).

### „Arbeitet“ vs. „wartet“

| | arbeitet | wartet |
|---|---|---|
| Bildschirmlicht am Tisch | an (kühles Monitorlicht, 160 lm) | fast aus |
| Animation | normale Geschwindigkeit | ruhiger |
| Namensschild | „arbeitet“ mit grünem Punkt | „wartet“ mit grauem Punkt |

Das Namensschild zeigt Name und Aufgabe in dezenten Farben; die Agentenfarbe
erscheint nur als schmaler, entsättigter Streifen.

---

## Projektstruktur

```
unreal/AgentOffice/
├─ AgentOffice.uproject
├─ Config/
│  ├─ DefaultEngine.ini      Render-Einstellungen (kommentiert)
│  └─ DefaultGame.ini        Office-Ordner, Figur-Klasse, Packaging
├─ Content/Data/DeskLayout.json
├─ Scripts/build_level.py    erzeugt /Game/Maps/Office
└─ Source/AgentOffice/
   ├─ OfficeTypes.h          FOfficeWorker, FOfficeDeskSpot
   ├─ OfficeStateSubsystem.* liest workers.json
   ├─ OfficeLayout.*         liest DeskLayout.json
   ├─ OfficeDirector.*       spawnt/entfernt Figuren
   └─ AgentCharacter.*       die Figur
```

Nicht im Repo (siehe `.gitignore`): `Binaries/`, `Intermediate/`, `Saved/`,
`DerivedDataCache/`, das erzeugte Level und die Graubox-Materialien – und
natürlich niemals Dateien aus `.agent-office/`.

---

## Was noch fehlt

- **Echte Möbel und Raum-Assets** (Tische, Stühle, Monitore, Glas in den Fenstern, Pflanzen, Deckenleuchten) statt Graubox
- **MetaHumans** in dunklen Anzügen mit Sonnenbrillen (als `AgentCharacter`-Blueprint)
- **Sitz- und Tipp-Animationen** (das Mannequin steht vorerst hinter dem Stuhl)
- **Finale Koordinaten** aus dem Designkonzept
- Kamerafahrten / feste Kameraperspektiven
- Visual Studio-Komponente „.NET Framework 4.6.2 Targeting Pack“ auf diesem Rechner (siehe Voraussetzungen)
