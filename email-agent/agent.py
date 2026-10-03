#!/usr/bin/env python3
"""E-Mail-Kampagnen-Agent: macht aus einem Briefing fertige E-Mail-Entwürfe.

Der Agent versendet NICHTS. Er schreibt nur Dateien zum Prüfen nach
email-agent/out/<kampagne>/:

  - mail-01.html, mail-01.txt, ...  (HTML mit Inline-CSS + Plain-Text)
  - summary.md                      (Betreff-Varianten, Preheader, Versandplan)

Aufruf:
  python email-agent/agent.py email-agent/briefings/beispiel.yaml
  python email-agent/agent.py email-agent/briefings/beispiel.yaml --dry-run

Der API-Key kommt ausschließlich aus der Umgebungsvariable ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-5-5"
AGENT_DIR = Path(__file__).resolve().parent
DEFAULT_OUT = AGENT_DIR / "out"

# Markenpalette "Rhizome Atlas" / Rootyn: erdig, ruhig, sparsam.
FARBEN = {
    "papier": "#f6f4ef",   # Papierweiß (Seitenhintergrund)
    "karte": "#fffdf8",    # helleres Papier für den Inhaltsblock
    "wald": "#2f4a3a",     # tiefes Waldgrün (Kopf, Überschriften, Button)
    "ocker": "#b8893b",    # gedämpftes Ocker (Akzentlinie)
    "text": "#2b2a26",     # fast schwarz, warm
    "leise": "#6e6a5e",    # gedämpfter Text (Fußzeile)
    "linie": "#e4dfd3",
}

PFLICHTFELDER = ["kampagnenname", "ziel", "zielgruppe", "kernbotschaft", "call_to_action", "link"]

# JSON-Schema für die strukturierte Antwort des Modells.
MAIL_SCHEMA = {
    "type": "object",
    "properties": {
        "mails": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rolle": {"type": "string", "description": "Funktion der Mail in der Sequenz, z. B. Auftakt, Vertiefung, Erinnerung"},
                    "betreff_varianten": {"type": "array", "items": {"type": "string"}, "description": "Genau 3 Betreffzeilen für A/B-Tests"},
                    "preheader": {"type": "string"},
                    "ueberschrift": {"type": "string"},
                    "anrede": {"type": "string", "description": "Anrede, darf {{vorname}} enthalten"},
                    "absaetze": {"type": "array", "items": {"type": "string"}},
                    "cta_text": {"type": "string"},
                    "gruss": {"type": "string"},
                    "versand_tag": {"type": "integer", "description": "Tag relativ zum Start (0 = erster Versandtag)"},
                    "versand_zeit": {"type": "string", "description": "Empfohlene Uhrzeit, z. B. 'Dienstag, 9:30 Uhr'"},
                    "begruendung": {"type": "string", "description": "Kurz: warum dieser Zeitpunkt/Abstand"},
                },
                "required": [
                    "rolle", "betreff_varianten", "preheader", "ueberschrift", "anrede",
                    "absaetze", "cta_text", "gruss", "versand_tag", "versand_zeit", "begruendung",
                ],
                "additionalProperties": False,
            },
        },
        "sequenz_hinweis": {"type": "string", "description": "Gesamtempfehlung zu Rhythmus und Abständen der Sequenz"},
    },
    "required": ["mails", "sequenz_hinweis"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """Du schreibst E-Mail-Entwürfe für die Marke Rootyn (Markenwelt "Rhizome Atlas").
Stil der Marke: ruhig, klar, sparsam. Kurze Sätze, keine Superlative, keine Ausrufezeichen-Ketten,
keine Emojis, kein Marketing-Druck ("Nur heute!", "Jetzt zuschlagen!"). Lieber ein Gedanke zu wenig als einer zu viel.

Regeln:
- Schreibe in der Sprache aus dem Briefing.
- Jede Mail hat 2–4 kurze Absätze und genau einen Call-to-Action.
- Liefere pro Mail genau 3 unterschiedliche Betreffzeilen (max. ca. 50 Zeichen) und einen Preheader (max. ca. 90 Zeichen).
- Verwende {{vorname}} als Platzhalter für die persönliche Anrede. Erfinde keine Namen, Preise, Daten oder Versprechen,
  die nicht im Briefing stehen.
- Abmeldelink und Impressum fügt das System selbst ein – schreibe sie nicht in den Text.
- Die Mails bilden eine Sequenz: jede hat eine eigene Rolle und baut auf der vorherigen auf, ohne sie zu wiederholen.
- Empfiehl für jede Mail Versandtag (relativ zum Start) und Uhrzeit mit kurzer Begründung."""


# ---------------------------------------------------------------- Briefing

def lade_briefing(pfad: Path) -> dict:
    text = pfad.read_text(encoding="utf-8")
    if pfad.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            sys.exit("Für YAML-Briefings wird PyYAML benötigt: pip install -r email-agent/requirements.txt")
        daten = yaml.safe_load(text)
    else:
        daten = json.loads(text)
    if not isinstance(daten, dict):
        sys.exit(f"Briefing {pfad} muss ein Objekt mit Feldern enthalten.")

    fehlend = [f for f in PFLICHTFELDER if not daten.get(f)]
    if fehlend:
        sys.exit(f"Im Briefing fehlen Pflichtfelder: {', '.join(fehlend)}")

    daten.setdefault("sprache", "Deutsch")
    daten.setdefault("tonalitaet", "ruhig, klar, freundlich")
    try:
        daten["anzahl_mails"] = int(daten.get("anzahl_mails", 3))
    except (TypeError, ValueError):
        sys.exit("anzahl_mails muss eine Zahl sein.")
    if not 1 <= daten["anzahl_mails"] <= 10:
        sys.exit("anzahl_mails muss zwischen 1 und 10 liegen.")
    return daten


def slug(name: str) -> str:
    name = name.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    return name or "kampagne"


# ---------------------------------------------------------------- Inhalte erzeugen

def inhalte_dry_run(b: dict) -> dict:
    """Platzhaltertexte ohne API-Aufruf – zum Testen der Pipeline."""
    rollen = ["Auftakt", "Vertiefung", "Erinnerung", "Nachfassen", "Abschluss"]
    mails = []
    for i in range(b["anzahl_mails"]):
        rolle = rollen[i] if i < len(rollen) else f"Mail {i + 1}"
        mails.append({
            "rolle": rolle,
            "betreff_varianten": [
                f"[Dry-Run] {b['kampagnenname']} – {rolle} (A)",
                f"[Dry-Run] {b['kampagnenname']} – {rolle} (B)",
                f"[Dry-Run] {b['kampagnenname']} – {rolle} (C)",
            ],
            "preheader": f"Platzhalter-Preheader für Mail {i + 1}.",
            "ueberschrift": f"{rolle}: {b['kernbotschaft']}",
            "anrede": "Hallo {{vorname}},",
            "absaetze": [
                f"Dies ist ein Platzhaltertext (Dry-Run, kein API-Aufruf). Ziel der Kampagne: {b['ziel']}",
                f"Zielgruppe: {b['zielgruppe'].rstrip('.')}. Tonalität: {b['tonalitaet']}.",
                "Im echten Lauf schreibt das Modell hier zwei bis vier kurze Absätze.",
            ],
            "cta_text": b["call_to_action"],
            "gruss": "Herzliche Grüße\nIhr Rootyn-Team",
            "versand_tag": i * 3,
            "versand_zeit": "Dienstag, 9:30 Uhr" if i % 2 == 0 else "Donnerstag, 18:00 Uhr",
            "begruendung": "Platzhalter: Abstand von drei Tagen, wechselnde Tageszeit.",
        })
    return {"mails": mails, "sequenz_hinweis": "Platzhalter (Dry-Run): 3 Tage Abstand zwischen den Mails."}


def inhalte_von_claude(b: dict, model: str, fallback: bool) -> dict:
    try:
        import anthropic
    except ImportError:
        sys.exit("Das Paket 'anthropic' fehlt: pip install -r email-agent/requirements.txt")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY ist nicht gesetzt. Key setzen oder --dry-run verwenden.")

    briefing_text = json.dumps(b, ensure_ascii=False, indent=2)
    nutzer = (
        f"Erstelle eine Sequenz aus genau {b['anzahl_mails']} E-Mails auf {b['sprache']} "
        f"für dieses Kampagnen-Briefing:\n\n<briefing>\n{briefing_text}\n</briefing>"
    )

    client = anthropic.Anthropic()
    params = dict(
        model=model,
        max_tokens=32000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": nutzer}],
        output_config={"format": {"type": "json_schema", "schema": MAIL_SCHEMA}},
    )
    try:
        if fallback:
            # Bei einer Ablehnung durch Sicherheitsfilter springt serverseitig ein anderes Modell ein.
            with client.beta.messages.stream(
                **params, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            ) as stream:
                antwort = stream.get_final_message()
        else:
            with client.messages.stream(**params) as stream:
                antwort = stream.get_final_message()
    except anthropic.AuthenticationError:
        sys.exit("API-Key ungültig (ANTHROPIC_API_KEY prüfen).")
    except anthropic.NotFoundError:
        sys.exit(f"Modell '{model}' nicht gefunden.")
    except anthropic.RateLimitError:
        sys.exit("Rate-Limit erreicht – bitte später erneut versuchen.")
    except anthropic.APIStatusError as e:
        sys.exit(f"API-Fehler {e.status_code}: {e.message}")
    except anthropic.APIConnectionError:
        sys.exit("Keine Verbindung zur Anthropic-API.")

    if antwort.stop_reason == "refusal":
        sys.exit("Das Modell hat die Anfrage abgelehnt. Briefing prüfen.")
    if antwort.stop_reason == "max_tokens":
        sys.exit("Antwort wurde abgeschnitten (max_tokens). Weniger Mails anfordern.")

    text = next(block.text for block in antwort.content if block.type == "text")
    daten = json.loads(text)
    u = antwort.usage
    print(f"Modell {antwort.model}: {u.input_tokens} Eingabe-, {u.output_tokens} Ausgabe-Tokens.")
    return daten


# ---------------------------------------------------------------- Rendern

def _absatz_html(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


def render_html(mail: dict, b: dict, nr: int, gesamt: int) -> str:
    f = FARBEN
    absaetze = "\n".join(
        f'<p style="margin:0 0 16px 0;font-size:16px;line-height:1.6;color:{f["text"]};">{_absatz_html(a)}</p>'
        for a in mail["absaetze"]
    )
    link = html.escape(str(b["link"]), quote=True)
    titel = html.escape(mail["betreff_varianten"][0])
    preheader = html.escape(mail["preheader"])
    sans = "Helvetica, Arial, sans-serif"
    serif = "Georgia, 'Times New Roman', serif"
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<title>{titel}</title>
</head>
<body style="margin:0;padding:0;background-color:{f['papier']};">
<!-- Preheader: in der Inbox-Vorschau sichtbar, in der Mail selbst versteckt -->
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:{f['papier']};">{preheader}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{f['papier']};">
  <tr>
    <td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;background-color:{f['karte']};border:1px solid {f['linie']};">
        <tr>
          <td style="background-color:{f['wald']};padding:20px 32px;font-family:{serif};font-size:20px;letter-spacing:2px;color:{f['papier']};">
            ROOTYN
          </td>
        </tr>
        <tr>
          <td style="height:4px;line-height:4px;font-size:0;background-color:{f['ocker']};">&nbsp;</td>
        </tr>
        <tr>
          <td style="padding:36px 32px 8px 32px;font-family:{sans};">
            <h1 style="margin:0 0 24px 0;font-family:{serif};font-weight:normal;font-size:26px;line-height:1.3;color:{f['wald']};">{html.escape(mail['ueberschrift'])}</h1>
            <p style="margin:0 0 16px 0;font-size:16px;line-height:1.6;color:{f['text']};">{_absatz_html(mail['anrede'])}</p>
{absaetze}
          </td>
        </tr>
        <tr>
          <td align="left" style="padding:8px 32px 32px 32px;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="background-color:{f['wald']};border-radius:2px;">
                  <a href="{link}" style="display:inline-block;padding:14px 28px;font-family:{sans};font-size:16px;color:{f['papier']};text-decoration:none;">{html.escape(mail['cta_text'])}</a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px 36px 32px;font-family:{sans};font-size:16px;line-height:1.6;color:{f['text']};">{_absatz_html(mail['gruss'])}</td>
        </tr>
        <tr>
          <td style="padding:24px 32px;border-top:1px solid {f['linie']};font-family:{sans};font-size:12px;line-height:1.6;color:{f['leise']};">
            Sie erhalten diese E-Mail, weil Sie sich für Neuigkeiten von Rootyn angemeldet haben.<br>
            <a href="{{{{unsubscribe_link}}}}" style="color:{f['wald']};">Vom Newsletter abmelden</a><br><br>
            {{{{impressum}}}}<br>
            <a href="{{{{impressum_link}}}}" style="color:{f['wald']};">Impressum</a> · <a href="{{{{datenschutz_link}}}}" style="color:{f['wald']};">Datenschutz</a>
          </td>
        </tr>
      </table>
      <p style="margin:16px 0 0 0;font-family:{sans};font-size:11px;color:{f['leise']};">Entwurf {nr}/{gesamt} · {html.escape(mail['rolle'])}</p>
    </td>
  </tr>
</table>
</body>
</html>
"""


def render_text(mail: dict, b: dict) -> str:
    teile = [
        mail["ueberschrift"],
        "",
        mail["anrede"],
        "",
        *[a + "\n" for a in mail["absaetze"]],
        f"{mail['cta_text']}: {b['link']}",
        "",
        mail["gruss"],
        "",
        "-- ",
        "Sie erhalten diese E-Mail, weil Sie sich für Neuigkeiten von Rootyn angemeldet haben.",
        "Abmelden: {{unsubscribe_link}}",
        "",
        "{{impressum}}",
        "Impressum: {{impressum_link}}",
        "Datenschutz: {{datenschutz_link}}",
    ]
    return "\n".join(teile) + "\n"


def render_summary(inhalt: dict, b: dict, model: str | None) -> str:
    quelle = "Dry-Run (Platzhaltertexte, kein API-Aufruf)" if model is None else f"Modell `{model}`"
    zeilen = [
        f"# {b['kampagnenname']} – Kampagnen-Entwürfe",
        "",
        f"- **Ziel:** {b['ziel']}",
        f"- **Zielgruppe:** {b['zielgruppe']}",
        f"- **Kernbotschaft:** {b['kernbotschaft']}",
        f"- **Call-to-Action:** {b['call_to_action']} → {b['link']}",
        f"- **Erzeugt mit:** {quelle}",
        "",
        "> Nur Entwürfe – nichts wurde versendet. Vor dem Versand prüfen und die Platzhalter",
        "> `{{vorname}}`, `{{unsubscribe_link}}`, `{{impressum}}`, `{{impressum_link}}`, `{{datenschutz_link}}` im Mail-Tool belegen.",
        "",
        "## Versandplan",
        "",
        "| Mail | Rolle | Tag | Zeitpunkt | Begründung |",
        "| --- | --- | --- | --- | --- |",
    ]
    for i, m in enumerate(inhalt["mails"], 1):
        zeilen.append(f"| {i:02d} | {m['rolle']} | +{m['versand_tag']} | {m['versand_zeit']} | {m['begruendung']} |")
    zeilen += ["", inhalt["sequenz_hinweis"], ""]
    for i, m in enumerate(inhalt["mails"], 1):
        zeilen += [
            f"## Mail {i:02d} – {m['rolle']}",
            "",
            f"Dateien: [`mail-{i:02d}.html`](mail-{i:02d}.html) · [`mail-{i:02d}.txt`](mail-{i:02d}.txt)",
            "",
            "**Betreff-Varianten (A/B-Test):**",
            "",
            *[f"- **{chr(65 + k)}:** {s}" for k, s in enumerate(m["betreff_varianten"])],
            "",
            f"**Preheader:** {m['preheader']}",
            "",
        ]
    return "\n".join(zeilen)


# ---------------------------------------------------------------- CLI

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Erzeugt E-Mail-Entwürfe aus einem Kampagnen-Briefing. Versendet nichts.")
    parser.add_argument("briefing", type=Path, help="Briefing als YAML- oder JSON-Datei")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude-Modell (Standard: {DEFAULT_MODEL})")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Ausgabeordner (Standard: email-agent/out)")
    parser.add_argument("--dry-run", action="store_true", help="Ohne API-Aufruf mit Platzhaltertexten durchlaufen")
    parser.add_argument("--no-fallback", action="store_true",
                        help="Kein serverseitiges Ausweichmodell bei Ablehnungen verwenden")
    args = parser.parse_args()

    for strom in (sys.stdout, sys.stderr):
        if hasattr(strom, "reconfigure"):
            strom.reconfigure(encoding="utf-8")

    b = lade_briefing(args.briefing)
    if args.dry_run:
        inhalt = inhalte_dry_run(b)
        model = None
    else:
        print(f"Erzeuge {b['anzahl_mails']} Entwürfe mit {args.model} …")
        inhalt = inhalte_von_claude(b, args.model, fallback=not args.no_fallback)
        model = args.model

    mails = inhalt["mails"]
    if len(mails) != b["anzahl_mails"]:
        print(f"Hinweis: {len(mails)} statt {b['anzahl_mails']} Mails erhalten.")

    ziel = args.out / slug(b["kampagnenname"])
    ziel.mkdir(parents=True, exist_ok=True)
    for alt in ziel.glob("mail-*.*"):
        alt.unlink()
    for i, mail in enumerate(mails, 1):
        (ziel / f"mail-{i:02d}.html").write_text(render_html(mail, b, i, len(mails)), encoding="utf-8")
        (ziel / f"mail-{i:02d}.txt").write_text(render_text(mail, b), encoding="utf-8")
    (ziel / "summary.md").write_text(render_summary(inhalt, b, model), encoding="utf-8")

    print(f"{len(mails)} Entwürfe + summary.md geschrieben nach {ziel}")
    print("Es wurde nichts versendet.")


if __name__ == "__main__":
    main()
