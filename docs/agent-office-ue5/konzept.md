# Agent Office in Unreal Engine 5.8 – Art Direction

Das Agent Office soll aussehen wie ein echtes Büro, nicht wie ein Spiel. Fotorealistisch, ruhig, etwas filmisch.
Die Agenten sind Menschen in dunklen Anzügen mit Sonnenbrille, die konzentriert an ihren Tischen arbeiten.
Die Wirkung entsteht aus dem Kontrast: ein nüchternes, helles Architekturbüro und darin eine Gruppe
sehr einheitlich gekleideter, leicht rätselhafter Gestalten.

![Moodboard](moodboard.svg)

| Datei | Inhalt |
| --- | --- |
| `konzept.md` | Art Direction (dieses Dokument) |
| `figuren.md` | Agenten als MetaHumans: Kleidung, Vielfalt, Agentenfarbe, Haltungen |
| `grundriss.svg` | Plan von oben mit allen Plätzen, Maßen und Blickrichtungen |
| `DeskLayout.json` | Plätze für die Engine (x/y in cm, yaw in Grad) |
| `assets.md` | Kostenlose Assets und Schritt-für-Schritt-Anleitung |
| `moodboard.svg` | Stimmungsskizze, Palette, Materialien, Figurdetail |
| `grundriss_erzeugen.py` | prüft `DeskLayout.json` und zeichnet `grundriss.svg` neu |
| `moodboard_erzeugen.py` | zeichnet `moodboard.svg` neu |

## 1. Stimmung

- **Ort:** Zentrale einer kleinen, sehr guten Agentur im obersten Geschoss eines umgebauten Gewerbebaus.
  Ein offener Raum, 16 × 11 m, 3,10 m hoch. Keine Trennwände außer dem gläsernen Besprechungsraum.
- **Tageszeit:** später Nachmittag im Oktober, ca. 16:30 Uhr. Die Sonne steht tief im Westen und
  wirft lange, warme Lichtbahnen durch die Fensterfront über den Holzboden. Der Rest des Raums
  liegt im kühlen, weichen Himmelslicht.
- **Gefühl:** konzentrierte Stille. Nichts ist unordentlich, aber auch nicht steril. Eine Tasse,
  ein Notizbuch, ein Kabel, das nicht ganz gerade liegt. Glaubwürdige Gebrauchsspuren.
- **Leitsatz:** *Ein Architekturfoto, in das zufällig eine Spezialeinheit eingezogen ist.*

## 2. Licht

| Element | Einstellung (Richtwert) |
| --- | --- |
| Sonne (Directional Light) | ca. 5200 K, Höhe 18–22°, aus Westen (−x) durch die Fensterfront, harte Schatten mit leicht weicher Kante (Source Angle ~1°) |
| Himmel (Sky Light + Sky Atmosphere) | echtzeitbasiert, leicht kühler als die Sonne; sorgt für das blaue Fülllicht in den Schatten |
| Deckenleuchten | drei lange Linienleuchten, 4000 K, **gedimmt** (sie sollen sichtbar an sein, aber nicht dominieren) |
| Monitore | schwach emissiv, kühles Blaugrau; geben den Gesichtern mit Sonnenbrille einen feinen Reflex |
| Globale Beleuchtung | Lumen (Standard in UE 5.8), Reflexionen über Lumen; für Standbilder optional Path Tracer |
| Belichtung | manuell fixieren (keine Auto-Exposure-Sprünge beim Kameraflug) |

Atmosphäre: ein Hauch Exponential Height Fog mit Volumetric Fog, damit die Lichtbahnen der Sonne leicht
sichtbar werden. Sehr zurückhaltend, eher spürbar als sichtbar.

## 3. Materialien

| Material | Wo | Hinweise |
| --- | --- | --- |
| Sichtbeton | Nord- und Ostwand, Decke | glatt geschalt, Ankerlöcher, feine Farbschwankungen; Rauheit hoch (0.7–0.85) |
| Eiche geölt | Boden (Dielen 20 cm breit), Tischplatten | warm, matt mit leichtem Glanz in Laufwegen |
| Glas | Fensterfront West/Süd, Besprechungsraum | klar bzw. leicht rauchgrau, schwarze Stahlprofile |
| Stahl schwarz, pulverbeschichtet | Tischgestelle, Fensterprofile, Leuchten | matt, kaum Reflexion |
| Wollfilz salbeigrün | Akustikpaneele, Sofa, Stuhlpolster | einzige „Farbe“ im Raum neben Holz |
| Messing gebürstet | Rahmen der Wandtafeln, Krawattennadeln, Türgriffe | sparsam, verbindet Raum und Figuren |
| Anzugstoff Wolle | Agenten | anthrazit, sehr feines Fischgrat; kein Glanz |

## 4. Farbpalette

Gedeckt und realistisch, wenig Sättigung. Die Werte sind Richtwerte für Albedo und Licht, keine Logo-Farben.

| Name | Hex |
| --- | --- |
| Sichtbeton | `#B9B6AF` |
| Eiche geölt | `#A7825A` |
| Rauchglas | `#6F7A7D` |
| Anzug Anthrazit | `#1E2023` |
| Hemd Weiß | `#EDEBE6` |
| Stahl Schwarz | `#2B2D2F` |
| Wollfilz Salbei | `#7D8B78` |
| Messing | `#B08D57` |
| Tageslicht | `#F4EFE6` |

**Agentenfarben:** Die Farbe, die jeder Agent in der App hat, wird **entsättigt** übernommen
(Sättigung höchstens ca. 45 %, Helligkeit 40–60 %) und nur in sehr kleinen Flächen gezeigt. Details siehe `figuren.md`.

## 5. Kamera

- **Hauptkamera (Übersicht):** Cine Camera, 35 mm (Full Frame), Höhe 240 cm, Neigung −15° bis −20°,
  aus der Südost-Ecke Richtung Nordwest. So sind Tischinseln, Wandtafeln und Besprechungsraum gleichzeitig zu sehen.
- **Kamerafahrt:** sehr langsamer Dolly (ca. 3–5 cm/s) oder ein langsamer Bogen um die Tischinseln,
  60–90 s pro Durchgang, als Schleife. Keine schnellen Schwenke.
- **Nahansicht (wenn ein Agent ausgewählt wird):** 50–85 mm, Augenhöhe sitzend (~120 cm), Blende f/2.8,
  Fokus auf die Sonnenbrille, Hintergrund weich (Cinematic Depth of Field).
- **Moodboard-Skizze:** 35 mm aus Augenhöhe 165 cm, nur zur Stimmung.
- **Post-Process:** filmischer Tonemapper (Standard), leichte Vignette, feines Filmkorn,
  dezentes Bloom. Keine Chromatic Aberration, kein Lens Flare, keine Farbfilter.

## 6. Raumaufteilung

Den genauen Plan zeigt `grundriss.svg`, die Plätze stehen in `DeskLayout.json`. Kurzfassung:

- **Zwei Tischinseln** mit je 4 Tischen (160 × 80 cm), jeweils zwei Tische Rücken an Rücken.
  `desk-1` bis `desk-4` schauen nach Süden, `desk-5` bis `desk-8` nach Norden.
- **Wandtafeln an der Nordwand (Sichtbeton):** links `station-pulls` (Pull-Request-Brett),
  rechts `station-queue` (Aufgaben-Warteschlange). Beide 200 cm breit, Messingrahmen, Kärtchen darauf.
- **Besprechungsraum aus Glas** im Osten mit Tisch 220 × 100 cm; `meeting-1` ist das Kopfende.
- **Lounge** (Sofa, Beistelltisch) vor der Fensterecke im Südwesten, **Küchenzeile** an der Südwand.
- **Gänge:** 158 cm (Fenster ↔ Insel 1), 136 cm (zwischen den Inseln), 138 cm (Insel 2 ↔ Glaswand).

### Koordinaten

- Einheit Zentimeter, Ursprung (0,0) = Raummitte auf Bodenhöhe.
- +x = Osten (im Plan rechts), +y = Süden (im Plan unten). Das entspricht der UE-Draufsicht (X rechts, Y unten).
- **yaw** = Blickrichtung der Person, die den Platz benutzt (0° = +x, 90° = +y, 180° = −x, 270° = −y).
- **Bezugspunkt:**
  - `desk`: Mitte der Tischplatte. Der Stuhl bzw. die sitzende Person steht 75 cm entgegen der Blickrichtung.
  - `station`: Mitte der Wandtafel. Die Person steht ca. 70 cm davor.
  - `meeting`: Mitte des Stuhls.

## 7. Referenzen in Worten

- Architekturfotografie von Büro-Lofts in umgebauten Gewerbebauten: Sichtbeton, Eichendielen, große Stahlfenster.
- Skandinavische Arbeitsplatzgestaltung: wenig Dinge, gute Materialien, viel Tageslicht.
- Die Ästhetik von „Agenten in schwarzen Anzügen“ aus Science-Fiction-Filmen der späten 90er-Jahre,
  aber ohne Comic-Überzeichnung: echte Stoffe, echte Gesichter, normale Körperhaltung.
- Filmisches Nachmittagslicht wie in ruhigen Arthouse-Dramen: tiefe Sonne, lange Schatten, Staub im Licht.

## 8. Was wir vermeiden

- Comic- oder Spielzeugoptik, gesättigte Farben, Neon.
- Leere, aufgeräumte „Render-Büros“ ohne Spuren von Benutzung.
- Gleiche Gesichter (Klonarmee). Die Uniform ist gleich, die Menschen nicht.
- Agentenfarbe als großflächige Fläche (z. B. farbige Anzüge oder Monitore).
