#!/usr/bin/env node
// Liest die Aufträge aus dem Agent Office (.agent-office/workers.json und
// queue.json) und schreibt sie nach leinwand/agenten.js. Die Leinwand lädt
// diese Datei optional und zeigt dann zu jedem Ergebnis den Auftrag, den
// Namen und die Farbe des Agenten – und auch Aufträge ohne Pull Request.
//
// Aufruf:  node leinwand/sammeln.mjs [pfad/zu/.agent-office]
//
// Es werden nur unkritische Felder übernommen (keine Tokens, keine Kosten).
// agenten.js steht in .gitignore und bleibt auf deinem Rechner.

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const hier = dirname(fileURLToPath(import.meta.url));

function findeOffice(start) {
  let dir = resolve(start);
  for (;;) {
    const kandidat = join(dir, ".agent-office");
    if (existsSync(join(kandidat, "workers.json"))) return kandidat;
    if (existsSync(join(dir, "workers.json")) && dir.endsWith(".agent-office")) return dir;
    const oben = dirname(dir);
    if (oben === dir) return null;
    dir = oben;
  }
}

function lies(pfad, fallback) {
  try {
    return JSON.parse(readFileSync(pfad, "utf8"));
  } catch {
    return fallback;
  }
}

// Der Standard-Zusatz, den das Office an jeden Auftrag hängt, ist für die
// Leinwand uninteressant.
function kuerze(prompt) {
  if (!prompt) return "";
  return prompt.split(/\n\nDu bist in deinem eigenen Git-Worktree/)[0].trim();
}

const office = process.argv[2] ? resolve(process.argv[2]) : findeOffice(hier);
if (!office) {
  console.error("Kein .agent-office-Ordner gefunden. Pfad bitte als Argument angeben.");
  process.exit(1);
}

const workers = lies(join(office, "workers.json"), []);
const queue = lies(join(office, "queue.json"), { tasks: [] });

const agenten = workers
  .filter((w) => w.kind === "agent")
  .map((w) => ({
    id: w.id,
    name: w.name,
    color: w.color,
    provider: w.provider,
    model: w.model || null,
    titel: w.task?.name || w.title || "",
    zusammenfassung: w.task?.summary || "",
    auftrag: kuerze(w.prompt),
    branch: w.worktree?.branch || null,
    erstellt: new Date(w.createdAt).toISOString(),
    von: w.createdBy || null,
    arbeitet: Boolean(w.midTurn),
  }));

const auftraege = (queue.tasks || []).map((t) => ({
  id: t.id,
  titel: t.title,
  auftrag: kuerze(t.prompt),
  status: t.status,
  agent: t.workerName || null,
  agentId: t.workerId || null,
  branch: t.branch || null,
  erstellt: t.addedAt ? new Date(t.addedAt).toISOString() : null,
  von: t.addedBy || null,
}));

const daten = { erzeugt: new Date().toISOString(), agenten, auftraege };
const ziel = join(hier, "agenten.js");
writeFileSync(
  ziel,
  "// Erzeugt von leinwand/sammeln.mjs – nicht von Hand bearbeiten.\n" +
    "window.AGENT_OFFICE = " + JSON.stringify(daten, null, 2) + ";\n",
);
console.log(`${agenten.length} Agenten und ${auftraege.length} Aufträge nach ${ziel} geschrieben.`);
