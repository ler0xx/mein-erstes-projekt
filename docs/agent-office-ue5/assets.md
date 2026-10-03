# Assets für das Agent Office: was es kostenlos gibt und wie du es bekommst

Diese Liste ist für Einsteiger geschrieben. Alles hier ist kostenlos oder lässt sich kostenlos filtern.

**Zu den Links:** Mit ✔ markierte Links habe ich im Oktober 2026 aufgerufen und geprüft.
Die Hauptseiten `fab.com`, `unrealengine.com` und `epicgames.com` blockieren automatische Abrufe.
Sie sind die offiziellen Adressen von Epic, die Unterseiten dort konnte ich aber nicht prüfen.
Bei einzelnen Fab-Angeboten steht deshalb ein **Suchbegriff** statt eines Links.
Ob ein Angebot gerade kostenlos ist, siehst du in Fab direkt am Preis.
Prüfe zusätzlich vor dem Download die Lizenz.

---

## Schritt 0: Was du einmalig brauchst

1. **Epic-Games-Konto anlegen** auf <https://www.epicgames.com> (oben rechts „Anmelden“ → „Registrieren“). Kostenlos.
2. **Epic Games Launcher installieren** und **Unreal Engine 5.8** installieren.
   Anleitung: ✔ [Install Unreal Engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/install-unreal-engine)
3. Beim Installieren der Engine unter **Optionen** das Häkchen **„MetaHuman Creator Core Data“** setzen
   (siehe Schritt 2). Falls vergessen: im Launcher bei der Engine-Version auf den kleinen Pfeil → **Optionen** → Häkchen setzen → **Anwenden**.
4. Speicherplatz einplanen: Engine plus MetaHumans plus Megascans brauchen schnell **150 GB oder mehr**.

---

## Schritt 1: Fab, der Marktplatz für Assets

Fab ist der Marktplatz von Epic. Seit 2024 gehören dort der frühere Unreal Marketplace und Quixel Megascans dazu.
Hauptseite: <https://www.fab.com>

**Assets kostenlos finden:**
1. Auf fab.com mit deinem Epic-Konto anmelden.
2. Suchbegriff eingeben (siehe Tabelle unten), dann links im Filter **Preis → Kostenlos** wählen.
   Achte zusätzlich darauf, dass das Format **Unreal Engine** angeboten wird.
3. Beim Asset auf **„Zur Bibliothek hinzufügen“** (Add to My Library) klicken. Bei kostenlosen Assets kostet das nichts,
   das Asset gehört dann dauerhaft zu deinem Konto.

**Asset ins Projekt holen**, entweder im Launcher oder in der Engine:
- **Im Launcher:** Reiter **Unreal Engine → Bibliothek → Fab-Bibliothek**, beim Asset **„Zum Projekt hinzufügen“** und dein Projekt wählen.
- **Direkt in der Engine** (empfohlen, vor allem für Megascans): Menü **Window → Fab** oder im **Content Drawer** auf den
  **Fab**-Knopf neben **Add+**. Beim Asset unten rechts auf **+** klicken, dann landet es im aktuellen Projekt.
  Anleitung: ✔ [Fab Window in Unreal Engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/fab-window-in-unreal-engine),
  ✔ [Purchasing and Downloading Assets in Fab](https://dev.epicgames.com/documentation/fab/purchasing-and-downloading-assets-in-fab)

**Zu Megascans:** Bis Ende 2024 waren alle Megascans kostenlos. Seit 2025 kosten sie in der Regel etwas.
Laut Epic gibt es aber weiterhin eine Auswahl von **über 1.500 kostenlosen Megascans**.
Was du 2024 bereits zur Bibliothek hinzugefügt hast, darfst du dauerhaft nutzen.
Hintergrund: ✔ [Quixel to Fab Transition FAQs](https://support.fab.com/s/article/Fab-Transition-FAQs)
Tipp: In der Engine kannst du unter **Fab-Einstellungen → Megascans → Preferred Quality Tier** die Qualität wählen.
Für den Anfang reicht **Medium**, das spart viel Speicher.

### Was wir aus Fab brauchen (Suchbegriffe, Filter „Kostenlos“)

| Wofür | Suchbegriff in Fab | Hinweis |
| --- | --- | --- |
| Betonwände, Decke | `concrete wall surface` | Megascans-Oberfläche (Material), für Nord-/Ostwand und Decke |
| Holzboden | `oak floor planks` / `wood floor` | Megascans-Oberfläche, Eiche hell bis mittel |
| Tische, Bürostühle, Monitore | `office furniture` / `office props` | auf Format „Unreal Engine“ achten |
| Kleinkram (Tassen, Bücher, Pflanzen) | `mug`, `books`, `potted plant` | Megascans-3D-Assets wirken am echtesten |
| Sofa, Lounge | `sofa` / `lounge furniture` | Polster später auf Salbei-Filz umfärben |
| Küchenzeile | `kitchen counter` | einfache Arbeitsplatte reicht |
| Sonnenbrille | `sunglasses` | schmale, schwarze Form (siehe `figuren.md`) |
| Ganze Büro-Umgebung (Abkürzung) | `office interior` / `modern office` | ab und zu kostenlos, oft kostenpflichtig: **Preis prüfen** |

Fab hat außerdem jeden Monat Angebote, die **für begrenzte Zeit kostenlos** sind.
Es lohnt sich, dort regelmäßig nach Büro-Assets zu schauen.

---

## Schritt 2: MetaHumans, die Agenten

Seit Unreal Engine 5.6 ist der **MetaHuman Creator direkt in der Engine** eingebaut.
Die frühere Web-Version brauchst du nicht mehr. MetaHumans sind für die Nutzung in Unreal-Engine-Projekten kostenlos.
Es gilt die Unreal-Engine-Lizenz, die erst bei hohem Jahresumsatz (über 1 Mio. US-Dollar) Gebühren vorsieht.

1. **Core Data installieren:** Launcher → bei Unreal Engine 5.8 **Starten ▾ → Optionen** →
   **„MetaHuman Creator Core Data“** anhaken → **Anwenden**. Vorher alle Projekte schließen.
2. **Plugin aktivieren:** Im Projekt **Edit → Plugins**, nach „MetaHuman“ suchen, **MetaHuman Creator** aktivieren,
   **Restart Now** klicken.
3. **Figur anlegen:** Im Content Browser per Rechtsklick ein neues **MetaHuman Character**-Asset erstellen und
   per Doppelklick öffnen. Damit startet der MetaHuman Creator.
4. Acht unterschiedliche Figuren nach der Tabelle in `figuren.md` gestalten. Anzug, Hemd und Krawatte gemäß Uniform wählen,
   soweit die Kleidungsauswahl das hergibt. Sonst unter dem Suchbegriff `MetaHuman suit` in Fab suchen und den **Preis prüfen**.
5. Für den Creator braucht die Engine eine Internetverbindung (Texturen und Rig werden auf Epic-Servern berechnet).

Anleitungen:
✔ [Getting Started with MetaHuman Creator in Unreal Engine](https://dev.epicgames.com/documentation/metahuman/getting-started-with-metahuman-creator-in-unreal-engine),
✔ [MetaHuman Creator in Unreal Engine](https://dev.epicgames.com/documentation/metahuman/metahuman-creator-in-unreal-engine),
✔ [MetaHuman Documentation](https://dev.epicgames.com/documentation/metahuman)

---

## Schritt 3: Animationen (tippen, zurücklehnen, gehen)

| Animation | Quelle | Kosten |
| --- | --- | --- |
| Gehen, Stehen, Drehen | **Game Animation Sample Project** von Epic (im Launcher unter **Unreal Engine → Beispiele** bzw. auf Fab). ✔ [Doku](https://dev.epicgames.com/documentation/en-us/unreal-engine/game-animation-sample-project-in-unreal-engine) | kostenlos |
| Tippen, sitzend warten, zurücklehnen, sitzend reden | **Mixamo** von Adobe, ✔ <https://www.mixamo.com>. Suchbegriffe: `Typing`, `Sitting Idle`, `Sitting`, `Sitting Talking` | kostenlos mit Adobe-Konto |

**So kommen Mixamo-Animationen auf die MetaHumans:**
1. Auf mixamo.com anmelden, Animation suchen, **Download** mit Format **FBX Binary (.fbx)** und **With Skin**.
2. In Unreal die FBX-Datei per Drag-and-drop in den Content Browser ziehen (importieren).
3. Mit dem **IK Retargeter** von diesem Skelett auf das MetaHuman-Skelett übertragen.
   Anleitung: ✔ [IK Rig Animation Retargeting](https://dev.epicgames.com/documentation/en-us/unreal-engine/ik-rig-animation-retargeting-in-unreal-engine)

---

## Schritt 4: Licht und Kamera (nur Doku, keine Downloads)

- ✔ [Lumen Global Illumination and Reflections](https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-global-illumination-and-reflections-in-unreal-engine)
- ✔ [Cinematic Depth of Field](https://dev.epicgames.com/documentation/en-us/unreal-engine/cinematic-depth-of-field-in-unreal-engine)

---

## Kurz-Checkliste

- [ ] Epic-Konto angelegt, Launcher installiert
- [ ] Unreal Engine 5.8 mit **MetaHuman Creator Core Data** installiert
- [ ] Plugin **MetaHuman Creator** im Projekt aktiviert
- [ ] Beton- und Eichen-Oberfläche aus Fab im Projekt
- [ ] Büromöbel, Monitore, Kleinkram aus Fab im Projekt (Filter „Kostenlos“)
- [ ] 8 MetaHumans erstellt (siehe `figuren.md`)
- [ ] Sonnenbrillen-Mesh im Projekt
- [ ] Animationen „tippen“ und „zurücklehnen“ von Mixamo, auf MetaHuman retargetet
- [ ] Game Animation Sample für Gehen
