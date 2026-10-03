#!/usr/bin/env node
// Rendert die Ergebnis-Leinwand als großes PNG – das Bild, das als Display
// an der Wand im Agent Office hängt. Die GitHub Action „Leinwand-Bild“ ruft
// das bei jeder Änderung auf und legt das Bild auf den Branch leinwand-bild.
//
// Aufruf:  node leinwand/bild.mjs [ziel.png]
//
// Umgebung: GITHUB_TOKEN (sonst `gh auth token`, sonst ohne Login),
//           LEINWAND_REPO (Standard: ler0xx/mein-erstes-projekt),
//           CHROME (Pfad zu Chrome/Chromium, sonst wird gesucht).
//
// Aufträge aus dem Agent Office (agenten.js) kommen bewusst nicht ins Bild,
// weil es öffentlich im Repo liegt.

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const hier = dirname(fileURLToPath(import.meta.url));
const { laden } = createRequire(import.meta.url)("./daten.js");

const repo = process.env.LEINWAND_REPO || "ler0xx/mein-erstes-projekt";
const ziel = resolve(process.argv[2] || join(hier, "wand.png"));

function token() {
  if (process.env.GITHUB_TOKEN) return process.env.GITHUB_TOKEN;
  try {
    return execFileSync("gh", ["auth", "token"], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "";
  }
}

function chrome() {
  if (process.env.CHROME) return process.env.CHROME;
  const kandidaten = [
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ];
  const fund = kandidaten.find((p) => existsSync(p));
  if (!fund) throw new Error("Kein Chrome gefunden. Pfad bitte über CHROME angeben.");
  return fund;
}

const daten = { t: Date.now(), data: await laden(repo, token()) };

// Eine Kopie der Seite, in der die Daten schon stecken – so lädt Chrome
// nichts selbst nach und das Bild zeigt genau diesen Stand.
const seite = readFileSync(join(hier, "index.html"), "utf8")
  .replace(/\s*<script src="agenten\.js"[^>]*><\/script>/, "")
  .replace(
    '<script src="daten.js"></script>',
    `<script>window.LEINWAND_DATEN = ${JSON.stringify(daten).replace(/</g, "\\u003c")};</script>\n  <script src="daten.js"></script>`,
  );
const tmp = join(hier, ".wand.html");
writeFileSync(tmp, seite);

try {
  mkdirSync(dirname(ziel), { recursive: true });
  const url = pathToFileURL(tmp).href + `?wand&office=0&repo=${encodeURIComponent(repo)}`;
  execFileSync(chrome(), [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--hide-scrollbars",
    "--force-dark-mode",
    "--blink-settings=preferredColorScheme=0",
    "--window-size=2400,1350",
    "--force-device-scale-factor=1.5",
    "--virtual-time-budget=15000",
    `--screenshot=${ziel}`,
    url,
  ], { stdio: "ignore" });
} finally {
  rmSync(tmp, { force: true });
}

if (!existsSync(ziel)) {
  console.error("Chrome hat kein Bild erzeugt.");
  process.exit(1);
}
console.log(`${daten.data.items.length} Ergebnisse als Bild nach ${ziel} geschrieben.`);
