# mein-erstes-projekt

Eine kleine, eigenständige Landing-Page mit einem generativen Hintergrund:
über tausend Partikel folgen einem sich langsam verändernden Strömungsfeld,
ziehen leuchtende Spuren und weichen dem Mauszeiger (oder Finger) aus.

- Reines HTML, CSS und JavaScript – kein Build-Schritt, keine Abhängigkeiten
- Hell- und Dunkelmodus über `prefers-color-scheme`
- Respektiert `prefers-reduced-motion` (zeigt dann ein ruhiges, statisches Bild;
  die Animation lässt sich per Button trotzdem starten oder pausieren)
- Responsiv bis Handybreite, scharf auf High-DPI-Displays

## Öffnen

Einfach `index.html` im Browser öffnen (Doppelklick genügt).

Optional über einen lokalen Server:

```sh
python -m http.server 8000
# dann http://localhost:8000 aufrufen
```

## Dateien

| Datei        | Inhalt                                             |
| ------------ | -------------------------------------------------- |
| `index.html` | Seitenstruktur                                      |
| `style.css`  | Layout, Typografie, Farben (hell/dunkel)            |
| `main.js`    | Canvas-Animation (Strömungsfeld, Maus-Interaktion) |
| `images/blume.svg` | Blumen-Grafik                                 |
| `leinwand/`  | Ergebnis-Leinwand für alle Agenten-Ergebnisse      |
| `unreal/`    | Nachbau der Seite als Unreal-Engine-5.8-Projekt (C++) |

## Blume

Unter Titel und Untertitel zeigt die Seite eine kleine Blume
(`images/blume.svg`), die sanft hin- und herschwingt – bei
`prefers-reduced-motion` steht sie still.

![Eine Blume](images/blume.svg)

## Ergebnis-Leinwand

`leinwand/index.html` ist eine riesige, verschiebbare und zoombare Leinwand,
auf der alle Ergebnisse der Agenten zu sehen sind – erreichbar auch über den
Button auf der Startseite.

- **Jede Zeile ein Agent, jede Spalte ein Ergebnis** in zeitlicher Reihenfolge.
  Oben läuft `main`: gemergte Pull Requests münden mit einer durchgezogenen
  Linie hinein, offene mit einer gestrichelten.
- **Karten** zeigen Status (gemergt, offen, nur Branch, geschlossen, ohne PR),
  Titel, Datum, geänderte Zeilen, Dateien und eine Bildvorschau, falls ein
  Bild dazugehört.
- **Klick auf eine Karte** öffnet die Details: Auftrag, Verlauf, alle Bilder,
  Beschreibung und Dateien, mit Link zu GitHub.
- **Filter und Suche** oben, **Übersichtskarte** unten rechts.
- Bedienung: ziehen zum Verschieben, Mausrad oder zwei Finger zum Zoomen,
  Tasten `+` `−` `0` und Pfeiltasten.

Die Daten kommen live von der GitHub-API (öffentliches Repo, kein Login nötig)
und werden zehn Minuten zwischengespeichert; ↻ lädt neu. Ein anderes Repo
geht mit `leinwand/index.html?repo=besitzer/name`.

### Aufträge aus dem Agent Office einblenden

```sh
node leinwand/sammeln.mjs
```

liest `.agent-office/workers.json` und `queue.json` und schreibt
`leinwand/agenten.js`. Danach zeigt die Leinwand zu jedem Ergebnis den
ursprünglichen Auftrag, Namen und Farbe des Agenten – und auch Aufträge, zu
denen es noch keinen Pull Request gibt. Die Datei bleibt lokal (`.gitignore`).

### Als Display an der Wand im Agent Office

Die Wände im Agent Office zeigen Bilder, keine Webseiten. Deshalb rendert
`leinwand/bild.mjs` die Leinwand im Wand-Modus (`?wand`, ohne Bedienelemente)
als großes PNG. Die GitHub Action **Leinwand-Bild** macht das bei jedem neuen,
geänderten oder gemergten Pull Request und legt das Bild auf den Branch
`leinwand-bild`. Im Office hängst du es so auf: Bild aufhängen → Link einfügen:

```
https://raw.githubusercontent.com/ler0xx/mein-erstes-projekt/leinwand-bild/leinwand.png
```

Das Office lädt das Bild selbst nach (es speichert es bis zu einer Stunde
zwischen). Von Hand neu erzeugen: in GitHub unter *Actions → Leinwand-Bild →
Run workflow* oder lokal mit `node leinwand/bild.mjs`. Aufträge aus dem
Agent Office kommen nicht ins Bild, weil es öffentlich ist.

## Unreal-Version

Unter `unreal/MeinErstesProjekt/` liegt ein Nachbau der Seite als C++-Projekt
für **Unreal Engine 5.8**. Es enthält keine `.uasset`-Dateien: Kamera, Hintergrund,
Partikel, Blume, UI und sogar das Material werden beim Start im Code aufgebaut.
Als Map dient die leere `Entry`-Map der Engine.

### Was nachgebaut ist

| Website                                   | Unreal                                                                 |
| ----------------------------------------- | ---------------------------------------------------------------------- |
| Canvas mit Strömungsfeld (`main.js`)      | `AMEPFlowFieldActor`: bis zu 1400 Partikel als Instanced Static Mesh, folgen einem Perlin-Noise-Feld und weichen der Maus aus |
| Hintergrund mit radialem Verlauf          | `AMEPBackdropActor`: Fläche plus gestapelte Scheiben als Verlauf        |
| Titel, Untertitel, „Hallo, Welt“          | `UMEPHeroWidget`: UMG-Widget, komplett in C++ aufgebaut, Titel mit wanderndem Farbverlauf |
| Blume (`images/blume.svg`)                | `AMEPFlowerActor`: Blume aus Kugeln, Zylindern und Würfeln, wächst beim Start und schwingt |
| Button „Animation pausieren/abspielen“    | Button im Widget, hält die Partikel an (sie werden dann zu ruhigen Punkten) |
| Hell/Dunkel (`prefers-color-scheme`)      | Windows-App-Modus, wird laufend nachgeprüft                            |
| `prefers-reduced-motion`                  | Windows-Einstellung „Animationen in Windows anzeigen“                   |

Zum Ausprobieren lassen sich beide Einstellungen per Kommandozeile festlegen:
`-Farbschema=hell|dunkel` und `-ReduzierteBewegung=0|1`.

### Voraussetzungen

- Unreal Engine 5.8
- Visual Studio 2022 mit der Workload „Spieleentwicklung mit C++“
  (MSVC-Toolchain und Windows 10/11 SDK ab 10.0.19041)

### Bauen

```bat
"C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" MeinErstesProjektEditor Win64 Development -Project="<Pfad>\unreal\MeinErstesProjekt\MeinErstesProjekt.uproject" -WaitMutex
```

Alternativ: Rechtsklick auf `MeinErstesProjekt.uproject` → „Generate Visual Studio
project files“, dann die `.sln` in Visual Studio öffnen und bauen.

### Öffnen und starten

- Doppelklick auf `MeinErstesProjekt.uproject` öffnet den Editor (beim ersten Mal
  wird das Modul gebaut) – dann auf „Play“ klicken.
- Ohne Editor-Oberfläche direkt als Spiel:

  ```bat
  "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" "<Pfad>\MeinErstesProjekt.uproject" -game -windowed -ResX=1280 -ResY=720
  ```

Beim allerersten Start werden die Shader für das Laufzeit-Material kompiliert; die
Formen erscheinen dann für einen Moment im grauen Standard-Material.

Hinweis: Das unbeleuchtete Material wird im Code erzeugt, das geht nur mit
Editor-Daten (Editor, „Play“, `-game`). In einem gepackten Spiel fällt das Projekt
auf das beleuchtete Grundformen-Material der Engine und ein Frontallicht zurück;
die Farben weichen dann etwas ab.

### Dateien

| Datei                                   | Inhalt                                             |
| --------------------------------------- | -------------------------------------------------- |
| `MeinErstesProjekt.uproject`            | Projektdatei                                        |
| `Config/DefaultEngine.ini`              | Start-Map, GameMode, Render-Einstellungen           |
| `Source/MeinErstesProjekt/MEPGameMode.*` | baut die Szene auf                                 |
| `Source/MeinErstesProjekt/MEPPlayerController.*` | Kamera, Mauszeiger, Widget                 |
| `Source/MeinErstesProjekt/MEPThemeSubsystem.*` | Farben, Systemeinstellungen, Laufzeit-Material |
| `Source/MeinErstesProjekt/MEPFlowFieldActor.*` | Strömungsfeld                               |
| `Source/MeinErstesProjekt/MEPBackdropActor.*` | Hintergrund                                  |
| `Source/MeinErstesProjekt/MEPFlowerActor.*` | Blume                                          |
| `Source/MeinErstesProjekt/MEPHeroWidget.*` | Titel, Untertitel, Button                       |
