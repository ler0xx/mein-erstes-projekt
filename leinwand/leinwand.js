// Ergebnis-Leinwand: holt alle Pull Requests und Agenten-Branches des Repos
// von GitHub und legt sie als Karten auf eine große, verschiebbare und
// zoombare Fläche. Jede Zeile gehört einem Agenten, jede Spalte ist ein
// Ergebnis in zeitlicher Reihenfolge; oben läuft main, in das gemergte
// Ergebnisse münden. Optional ergänzt agenten.js (von sammeln.mjs) die
// Aufträge aus dem Agent Office.
(() => {
  "use strict";

  const params = new URLSearchParams(location.search);
  // ?wand: nur die Leinwand, ohne Bedienelemente – für das Bild an der
  // Office-Wand (siehe bild.mjs).
  const WALL = params.has("wand");
  if (WALL) document.body.classList.add("wand");
  const REPO = params.get("repo") || "ler0xx/mein-erstes-projekt";
  const CACHE_KEY = "leinwand:" + REPO;
  const CACHE_MS = 10 * 60 * 1000;
  const IMG_RE = /\.(png|jpe?g|gif|webp|svg|avif)$/i;

  // Raster der Leinwand (in Welt-Pixeln).
  const X0 = 300;
  const COL_W = 400;
  const CARD_W = 340;
  const MAIN_Y = 0;
  const LANE_TOP = 200;
  const LANE_MIN_H = 240;
  const LANE_GAP = 110;
  const MIN_K = 0.08;
  const MAX_K = 2.5;

  const PALETTE = ["#ef476f", "#ffb400", "#06d6a0", "#118ab2", "#b388eb", "#f78c6b", "#4cc9f0", "#90be6d"];

  const STATES = {
    merged: { label: "Gemergt", filter: "merged" },
    open: { label: "Offen", filter: "open" },
    draft: { label: "Entwurf", filter: "open" },
    closed: { label: "Geschlossen", filter: "closed" },
    branch: { label: "Nur Branch", filter: "branch" },
    working: { label: "Arbeitet", filter: "task" },
    queued: { label: "Wartet", filter: "task" },
    task: { label: "Ohne PR", filter: "task" },
  };

  const FILTERS = [
    { id: "all", label: "Alle" },
    { id: "merged", label: "Gemergt", color: "var(--merged)" },
    { id: "open", label: "Offen", color: "var(--open)" },
    { id: "branch", label: "Nur Branch", color: "var(--branch)" },
    { id: "closed", label: "Geschlossen", color: "var(--closed)" },
    { id: "task", label: "Ohne PR", color: "var(--task)" },
  ];

  const $ = (id) => document.getElementById(id);
  const viewport = $("viewport");
  const world = $("world");
  const links = $("links");
  const notice = $("notice");
  const sub = $("sub");
  const chips = $("chips");
  const search = $("search");
  const minimap = $("minimap");
  const detail = $("detail");
  const detailBody = $("detail-body");
  const reloadBtn = $("reload");

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const fmt = new Intl.DateTimeFormat("de-DE", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
  const fmtLong = new Intl.DateTimeFormat("de-DE", { dateStyle: "medium", timeStyle: "short" });

  let items = [];
  let bounds = { x: 0, y: -100, w: 1000, h: 800 };
  let filter = "all";
  let query = "";
  let activeCard = null;
  const view = { x: 0, y: 0, k: 1 };

  // ---------- Hilfsfunktionen ----------

  function h(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value == null || value === false) continue;
      if (key === "class") node.className = value;
      else if (key === "style") node.style.cssText = value;
      else node.setAttribute(key, value);
    }
    for (const child of children.flat()) {
      if (child == null || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  }

  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const date = (iso) => (iso ? fmt.format(new Date(iso)) : "");

  function hashColor(name) {
    let n = 0;
    for (const ch of name) n = (n * 31 + ch.codePointAt(0)) >>> 0;
    return PALETTE[n % PALETTE.length];
  }

  function rawUrl(sha, path) {
    return `https://raw.githubusercontent.com/${REPO}/${sha}/${path.split("/").map(encodeURIComponent).join("/")}`;
  }

  // "office/pixel-93bf" -> "Pixel", "office/meeting-es-geht-um-x-10ac" -> "Meeting".
  function agentFromBranch(branch) {
    const m = /^office\/(.+?)-[0-9a-f]{4}$/i.exec(branch || "");
    const raw = m ? m[1] : (branch || "Unbekannt").replace(/^.*\//, "");
    const word = raw.split("-")[0];
    return word.charAt(0).toUpperCase() + word.slice(1);
  }

  function bodyImages(body) {
    const out = [];
    const re = /!\[[^\]]*\]\((https:\/\/[^)\s]+)\)|<img[^>]+src="(https:\/\/[^"]+)"/g;
    let m;
    while ((m = re.exec(body || ""))) out.push(m[1] || m[2]);
    return out;
  }

  // ---------- Kleiner Markdown-Renderer für PR-Beschreibungen ----------

  function inline(s) {
    return esc(s)
      .replace(/!\[([^\]]*)\]\((https:\/\/[^)\s]+)\)/g, '<img src="$2" alt="$1" loading="lazy">')
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
  }

  function markdown(src) {
    const lines = String(src || "").replace(/\r/g, "").split("\n");
    let html = "";
    let list = null;
    let code = null;
    let table = [];
    let para = [];

    const flushPara = () => {
      if (para.length) html += `<p>${para.map(inline).join("<br>")}</p>`;
      para = [];
    };
    const flushList = () => {
      if (list) html += `</${list}>`;
      list = null;
    };
    const flushTable = () => {
      if (!table.length) return;
      const rows = table
        .filter((row) => !/^[\s|:-]+$/.test(row))
        .map((row) => row.trim().replace(/^\||\|$/g, "").split("|"));
      html += "<table>" + rows.map((cells, i) => {
        const tag = i === 0 ? "th" : "td";
        return "<tr>" + cells.map((c) => `<${tag}>${inline(c.trim())}</${tag}>`).join("") + "</tr>";
      }).join("") + "</table>";
      table = [];
    };
    const flushAll = () => { flushPara(); flushList(); flushTable(); };

    for (const line of lines) {
      if (code) {
        if (/^\s*```/.test(line)) {
          html += `<pre><code>${esc(code.join("\n"))}</code></pre>`;
          code = null;
        } else code.push(line);
        continue;
      }
      if (/^\s*```/.test(line)) { flushAll(); code = []; continue; }
      if (/^\s*\|.*\|\s*$/.test(line)) { flushPara(); flushList(); table.push(line); continue; }
      flushTable();
      let m;
      if ((m = /^(#{1,6})\s+(.*)$/.exec(line))) {
        flushPara(); flushList();
        const level = Math.min(6, m[1].length + 2);
        html += `<h${level}>${inline(m[2])}</h${level}>`;
      } else if ((m = /^\s*([-*]|\d+\.)\s+(.*)$/.exec(line))) {
        flushPara();
        const kind = /\d/.test(m[1]) ? "ol" : "ul";
        if (list !== kind) { flushList(); html += `<${kind}>`; list = kind; }
        html += `<li>${inline(m[2])}</li>`;
      } else if (!line.trim()) {
        flushPara(); flushList();
      } else {
        flushList();
        para.push(line);
      }
    }
    if (code) html += `<pre><code>${esc(code.join("\n"))}</code></pre>`;
    flushAll();
    return html;
  }

  // ---------- Daten laden ----------

  const loadGithub = () => window.LeinwandDaten.laden(REPO);

  function readCache() {
    try {
      return JSON.parse(localStorage.getItem(CACHE_KEY));
    } catch {
      return null;
    }
  }

  function writeCache(data) {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({ t: Date.now(), data }));
    } catch {
      /* Ohne Speicher geht es auch. */
    }
  }

  // Verknüpft GitHub-Ergebnisse mit den Aufträgen aus dem Agent Office und
  // ergänzt Aufträge, zu denen es (noch) keinen Pull Request gibt.
  function withOffice(ghItems) {
    const office = params.get("office") === "0" ? null : window.AGENT_OFFICE;
    const agents = (office && office.agenten) || [];
    const tasks = (office && office.auftraege) || [];
    const byName = new Map(agents.map((a) => [a.name.toLowerCase(), a]));
    const byBranch = new Map();
    for (const t of tasks) if (t.branch) byBranch.set(t.branch, { name: t.agent, auftrag: t.auftrag, titel: t.titel });
    for (const a of agents) if (a.branch) byBranch.set(a.branch, a);

    const out = ghItems.map((it) => {
      const hit = byBranch.get(it.branch);
      const name = (hit && hit.name) || agentFromBranch(it.branch);
      const known = byName.get(name.toLowerCase());
      return {
        ...it,
        agent: {
          name,
          color: (known && known.color) || hashColor(name),
          auftrag: hit && hit.auftrag,
          titel: hit && hit.titel,
          zusammenfassung: hit && hit.zusammenfassung,
          provider: hit && hit.provider,
          model: hit && hit.model,
        },
      };
    });

    const seenBranches = new Set(ghItems.map((it) => it.branch));
    const seenAgents = new Set();
    for (const a of agents) {
      if (a.branch && seenBranches.has(a.branch)) continue;
      seenAgents.add(a.id);
      out.push({
        kind: "task",
        id: "agent-" + a.id,
        state: a.arbeitet ? "working" : "task",
        title: a.titel || "Auftrag",
        body: a.zusammenfassung || "",
        branch: a.branch,
        created: a.erstellt,
        files: [],
        agent: { ...a, color: a.color || hashColor(a.name) },
      });
    }
    for (const t of tasks) {
      if (t.status !== "queued" || (t.agentId && seenAgents.has(t.agentId))) continue;
      out.push({
        kind: "task",
        id: "queue-" + t.id,
        state: "queued",
        title: t.titel || "Auftrag in der Warteschlange",
        body: "",
        created: t.erstellt,
        files: [],
        agent: { name: "Warteschlange", color: "#7a7a8c", auftrag: t.auftrag },
      });
    }
    return out;
  }

  // ---------- Leinwand aufbauen ----------

  function cardPreview(it) {
    const imgs = it.files.filter((f) => IMG_RE.test(f.name) && f.status !== "removed");
    const img = imgs.find((f) => !/screenshot/i.test(f.name)) || imgs[0];
    if (img && it.sha) return rawUrl(it.sha, img.name);
    return bodyImages(it.body)[0] || null;
  }

  function renderCard(it) {
    const st = STATES[it.state];
    const preview = cardPreview(it);
    const shown = it.files.slice(0, 5);
    const card = h("article", {
      class: `card s-${it.state}`,
      style: `left:${it.x}px;top:0;--agent:${it.agent.color}`,
      tabindex: "0",
      "data-id": it.id,
      "aria-label": `${it.title} – ${it.agent.name}, ${st.label}`,
    },
      h("div", { class: "card-head" },
        h("span", { class: "avatar" }, it.agent.name.charAt(0)),
        h("span", { class: "agent" }, it.agent.name),
        h("span", { class: "badge" }, st.label)),
      h("h3", null, it.title),
      h("p", { class: "meta" },
        it.number ? h("span", null, "#" + it.number) : null,
        it.kind === "branch" ? h("span", null, `${it.commits} Commit${it.commits === 1 ? "" : "s"}`) : null,
        h("span", null, date(it.created)),
        it.files.length ? h("span", null,
          h("span", { class: "add" }, "+" + it.additions), " ",
          h("span", { class: "del" }, "−" + it.deletions)) : null,
        it.files.length ? h("span", null, `${it.files.length} Datei${it.files.length === 1 ? "" : "en"}`) : null),
      preview ? h("figure", { class: "preview" }, h("img", { src: preview, alt: "", loading: "lazy", decoding: "async" })) : null,
      it.agent.auftrag ? h("p", { class: "auftrag" }, `„${it.agent.auftrag}“`) : null,
      !it.agent.auftrag && it.kind === "task" && it.body ? h("p", { class: "summary" }, it.body) : null,
      shown.length ? h("ul", { class: "files" },
        shown.map((f) => h("li", null,
          h("span", { class: `fs fs-${f.status}` }, { added: "+", removed: "−", renamed: "→" }[f.status] || "~"),
          h("span", { class: "fname", title: f.name }, f.name))),
        it.files.length > shown.length ? h("li", { class: "more" }, `… und ${it.files.length - shown.length} weitere`) : null) : null,
    );
    return card;
  }

  function layout() {
    items.sort((a, b) => new Date(a.created || 0) - new Date(b.created || 0));
    const lanes = [];
    for (const it of items) if (!lanes.includes(it.agent.name)) lanes.push(it.agent.name);

    items.forEach((it, i) => {
      it.lane = lanes.indexOf(it.agent.name);
      it.x = X0 + i * COL_W;
    });
    return lanes;
  }

  // Jede Zeile ist so hoch wie ihre höchste Karte; dafür werden die Karten
  // erst eingefügt, dann gemessen und dann senkrecht platziert.
  function placeLanes(lanes) {
    const heights = lanes.map(() => LANE_MIN_H);
    for (const it of items) heights[it.lane] = Math.max(heights[it.lane], it.node.offsetHeight);
    const tops = [];
    let y = LANE_TOP;
    for (const hgt of heights) {
      tops.push(y);
      y += hgt + LANE_GAP;
    }
    for (const it of items) {
      it.y = tops[it.lane];
      it.node.style.top = it.y + "px";
    }
    const right = X0 + Math.max(1, items.length) * COL_W;
    const bottom = y - LANE_GAP;
    bounds = { x: 0, y: MAIN_Y - 120, w: right + 60, h: bottom + 40 - (MAIN_Y - 120) };
    return { tops, right };
  }

  function render() {
    for (const node of [...world.children]) if (node !== links) node.remove();
    links.replaceChildren();
    const lanes = layout();
    for (const it of items) {
      it.node = renderCard(it);
      world.append(it.node);
    }
    const { tops, right } = placeLanes(lanes);

    const NS = "http://www.w3.org/2000/svg";
    const svg = (tag, attrs) => {
      const node = document.createElementNS(NS, tag);
      for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
      links.append(node);
      return node;
    };

    // main als Hauptlinie oben.
    const merges = items.filter((it) => it.state === "merged").length;
    world.append(h("div", { class: "main-label", style: `left:40px;top:${MAIN_Y}px` },
      "main", h("span", { style: "opacity:.65;font-weight:500" }, `· ${merges} gemergt`)));
    svg("line", { x1: 150, y1: MAIN_Y, x2: right, y2: MAIN_Y, stroke: "var(--main-line)", "stroke-width": 4, "stroke-linecap": "round" });

    // Agenten-Zeilen.
    lanes.forEach((name, i) => {
      const y = tops[i];
      const own = items.filter((it) => it.agent.name === name);
      world.append(h("div", { class: "lane-rule", style: `left:30px;top:${y - LANE_GAP / 2}px;width:${right - 30}px` }));
      world.append(h("div", { class: "lane-label sticky", style: `left:40px;top:${y - LANE_GAP / 2}px;--agent:${own[0].agent.color}` },
        h("span", { class: "avatar" }, name.charAt(0)),
        h("div", null, h("strong", null, name), h("span", null, `${own.length} Ergebnis${own.length === 1 ? "" : "se"}`))));
    });

    for (const it of items) {
      const cx = it.x + CARD_W / 2;
      world.append(h("div", { class: "tick", style: `left:${it.x}px;top:${MAIN_Y - 52}px` }, date(it.merged || it.created)));
      if (it.state === "merged" || it.state === "open" || it.state === "draft" || it.state === "branch") {
        const color = { merged: "var(--merged)", open: "var(--open)", draft: "var(--open)", branch: "var(--branch)" }[it.state];
        const top = MAIN_Y + 10;
        const path = `M ${cx} ${it.y} C ${cx} ${it.y - 90}, ${cx - 60} ${top + 70}, ${cx - 60} ${top + 26} L ${cx - 60} ${top}`;
        svg("path", {
          d: path, fill: "none", stroke: color, "stroke-width": 3,
          "stroke-dasharray": it.state === "merged" ? "" : "8 8", "data-id": it.id, class: "link",
        });
        svg("circle", {
          cx: cx - 60, cy: MAIN_Y, r: it.state === "merged" ? 9 : 7,
          fill: it.state === "merged" ? color : "var(--bg)", stroke: color, "stroke-width": 3, "data-id": it.id,
        });
      }
    }

    applyFilter();
    renderChips();
    stickLabels();
    drawMinimap();
  }

  // Namen der Agenten und "main" bleiben am linken Bildrand sichtbar.
  function stickLabels() {
    const left = Math.max(40, (16 - view.x) / view.k);
    for (const node of world.querySelectorAll(".sticky")) node.style.left = left + "px";
  }

  // ---------- Filter und Suche ----------

  function matches(it) {
    if (filter !== "all" && STATES[it.state].filter !== filter) return false;
    if (!query) return true;
    const hay = [it.title, it.body, it.branch, it.agent.name, it.agent.auftrag, ...it.files.map((f) => f.name)]
      .join(" ").toLowerCase();
    return query.split(/\s+/).every((w) => hay.includes(w));
  }

  function applyFilter() {
    for (const it of items) {
      const ok = matches(it);
      it.node.classList.toggle("dim", !ok);
      for (const n of links.querySelectorAll(`[data-id="${CSS.escape(it.id)}"]`)) n.style.opacity = ok ? "" : "0.12";
    }
    drawMinimap();
  }

  function renderChips() {
    chips.replaceChildren(...FILTERS.map((f) => {
      const n = f.id === "all" ? items.length : items.filter((it) => STATES[it.state].filter === f.id).length;
      if (f.id !== "all" && !n) return null;
      const chip = h("button", { type: "button", class: "chip", "aria-pressed": String(filter === f.id), style: f.color ? `--c:${f.color}` : null },
        f.color ? h("span", { class: "dot" }) : null, f.label, h("span", { class: "n" }, n));
      chip.addEventListener("click", () => {
        filter = f.id;
        renderChips();
        applyFilter();
      });
      return chip;
    }).filter(Boolean));
  }

  search.addEventListener("input", () => {
    query = search.value.trim().toLowerCase();
    applyFilter();
  });

  // ---------- Detail-Ansicht ----------

  function openDetail(it) {
    if (activeCard) activeCard.classList.remove("active");
    activeCard = it.node;
    activeCard.classList.add("active");
    const st = STATES[it.state];
    const images = [
      ...it.files.filter((f) => IMG_RE.test(f.name) && f.status !== "removed" && it.sha)
        .map((f) => ({ src: rawUrl(it.sha, f.name), name: f.name })),
    ];

    const events = [
      it.created && { s: "var(--task)", text: it.kind === "pr" ? "Pull Request geöffnet" : it.kind === "branch" ? "Erster Commit" : "Auftrag erteilt", at: it.created },
      it.updated && { s: "var(--branch)", text: "Letzter Commit", at: it.updated },
      it.merged && { s: "var(--merged)", text: "In main gemergt", at: it.merged },
      !it.merged && it.closed && { s: "var(--closed)", text: "Ohne Merge geschlossen", at: it.closed },
    ].filter(Boolean);

    const md = h("div", { class: "md" });
    md.innerHTML = markdown(it.body);

    detailBody.replaceChildren(...[
      h("div", { class: `card-head s-${it.state}`, style: `--agent:${it.agent.color}` },
        h("span", { class: "avatar" }, it.agent.name.charAt(0)),
        h("span", { class: "agent" }, it.agent.name,
          it.agent.model ? h("span", { style: "color:var(--muted);font-weight:500" }, ` · ${it.agent.provider || ""} ${it.agent.model}`) : null),
        h("span", { class: "badge" }, st.label)),
      h("h2", { id: "detail-title" }, it.title),
      h("p", { class: "meta" },
        it.number ? h("span", null, "#" + it.number) : null,
        it.branch ? h("span", null, it.branch) : null,
        it.files.length ? h("span", null, h("span", { class: "add" }, "+" + it.additions), " ", h("span", { class: "del" }, "−" + it.deletions)) : null),
      it.url ? h("a", { class: "gh-link", href: it.url, target: "_blank", rel: "noopener" }, "Auf GitHub ansehen ↗") : null,
      it.agent.auftrag ? [h("h4", null, "Auftrag"), h("p", { class: "auftrag", style: `--agent:${it.agent.color}` }, it.agent.auftrag)] : null,
      events.length ? [h("h4", null, "Verlauf"), h("ul", { class: "timeline" },
        events.map((e) => h("li", { style: `--s:${e.s}` }, e.text, h("br"), h("time", { datetime: e.at }, fmtLong.format(new Date(e.at))))))] : null,
      images.length ? [h("h4", null, "Bilder"), h("div", { class: "gallery" },
        images.map((img) => h("figure", null,
          h("a", { href: img.src, target: "_blank", rel: "noopener", class: "preview" }, h("img", { src: img.src, alt: img.name, loading: "lazy" })),
          h("figcaption", { title: img.name }, img.name))))] : null,
      it.body ? [h("h4", null, it.kind === "branch" ? "Commits" : "Beschreibung"), md] : null,
      it.files.length ? [h("h4", null, `Dateien (${it.files.length})`), h("ul", { class: "files" },
        it.files.map((f) => h("li", null,
          h("span", { class: `fs fs-${f.status}` }, { added: "+", removed: "−", renamed: "→" }[f.status] || "~"),
          h("span", { class: "fname", title: f.name }, f.name),
          h("span", { class: "add" }, "+" + f.add), h("span", { class: "del" }, "−" + f.del))))] : null,
    ].flat().filter(Boolean));
    detail.classList.add("open");
    detail.setAttribute("aria-hidden", "false");
    detail.scrollTop = 0;
    $("detail-close").focus({ preventScroll: true });
  }

  function closeDetail() {
    detail.classList.remove("open");
    detail.setAttribute("aria-hidden", "true");
    if (activeCard) {
      activeCard.classList.remove("active");
      activeCard.focus({ preventScroll: true });
      activeCard = null;
    }
  }

  $("detail-close").addEventListener("click", closeDetail);

  function itemFor(node) {
    const card = node && node.closest && node.closest(".card");
    return card ? items.find((it) => it.id === card.dataset.id) : null;
  }

  // ---------- Verschieben und Zoomen ----------

  function apply() {
    world.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.k})`;
    let grid = 28 * view.k;
    while (grid < 12) grid *= 4;
    viewport.style.backgroundSize = `${grid}px ${grid}px`;
    viewport.style.backgroundPosition = `${view.x}px ${view.y}px`;
    stickLabels();
    drawMinimap();
  }

  function zoomAt(px, py, factor) {
    const k = clamp(view.k * factor, MIN_K, MAX_K);
    const f = k / view.k;
    view.x = px - (px - view.x) * f;
    view.y = py - (py - view.y) * f;
    view.k = k;
    apply();
  }

  let anim = 0;
  function animateTo(target) {
    cancelAnimationFrame(anim);
    if (reducedMotion.matches) {
      Object.assign(view, target);
      apply();
      return;
    }
    const from = { ...view };
    const start = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - start) / 380);
      const e = 1 - Math.pow(1 - t, 3);
      view.x = from.x + (target.x - from.x) * e;
      view.y = from.y + (target.y - from.y) * e;
      view.k = from.k + (target.k - from.k) * e;
      apply();
      if (t < 1) anim = requestAnimationFrame(step);
    };
    anim = requestAnimationFrame(step);
  }

  // Sichtbarer Bereich unterhalb der Kopfleiste.
  function screenArea() {
    const top = document.querySelector(".bar").getBoundingClientRect().bottom + 12;
    return { x: 16, y: top, w: innerWidth - 32, h: innerHeight - top - 16 };
  }

  function fitTarget(b, maxK = 1) {
    const area = screenArea();
    const k = clamp(Math.min(area.w / b.w, area.h / b.h), MIN_K, maxK);
    return { k, x: area.x + (area.w - b.w * k) / 2 - b.x * k, y: area.y + (area.h - b.h * k) / 2 - b.y * k };
  }

  function centerOn(wx, wy, k = view.k) {
    const area = screenArea();
    return { k, x: area.x + area.w / 2 - wx * k, y: area.y + area.h / 2 - wy * k };
  }

  function fitAll(animate = true) {
    const target = fitTarget(bounds, WALL ? MAX_K : 1);
    if (animate) animateTo(target);
    else {
      Object.assign(view, target);
      apply();
    }
  }

  // Beim Start: alles zeigen, solange es lesbar bleibt, sonst die neuesten
  // Ergebnisse groß zeigen.
  function initialView() {
    const target = fitTarget(bounds, WALL ? MAX_K : 1);
    if (WALL || target.k >= 0.42 || !items.length) {
      Object.assign(view, target);
    } else {
      const last = items[items.length - 1];
      const area = screenArea();
      const k = 0.6;
      Object.assign(view, { k, x: area.x + area.w - (last.x + CARD_W + 60) * k, y: area.y - (MAIN_Y - 90) * k });
    }
    apply();
  }

  const pointers = new Map();
  let drag = null;
  let pinch = null;

  viewport.addEventListener("pointerdown", (e) => {
    if (e.button !== 0 || e.target.closest("a, button, input, .notice")) return;
    cancelAnimationFrame(anim);
    viewport.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 1) {
      drag = { sx: e.clientX, sy: e.clientY, vx: view.x, vy: view.y, moved: false, target: e.target };
    } else if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), k: view.k, mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2, vx: view.x, vy: view.y };
      drag = null;
    }
  });

  viewport.addEventListener("pointermove", (e) => {
    if (!pointers.has(e.pointerId)) return;
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pinch && pointers.size >= 2) {
      const [a, b] = [...pointers.values()];
      const k = clamp(pinch.k * Math.hypot(a.x - b.x, a.y - b.y) / pinch.d, MIN_K, MAX_K);
      const mx = (a.x + b.x) / 2;
      const my = (a.y + b.y) / 2;
      view.x = mx - (pinch.mx - pinch.vx) * (k / pinch.k);
      view.y = my - (pinch.my - pinch.vy) * (k / pinch.k);
      view.k = k;
      apply();
    } else if (drag) {
      const dx = e.clientX - drag.sx;
      const dy = e.clientY - drag.sy;
      if (!drag.moved && Math.hypot(dx, dy) > 5) {
        drag.moved = true;
        viewport.classList.add("dragging");
      }
      if (drag.moved) {
        view.x = drag.vx + dx;
        view.y = drag.vy + dy;
        apply();
      }
    }
  });

  function endPointer(e) {
    if (!pointers.has(e.pointerId)) return;
    pointers.delete(e.pointerId);
    if (drag && !drag.moved && e.type === "pointerup") {
      const it = itemFor(drag.target);
      if (it) openDetail(it);
    }
    if (pointers.size < 2) pinch = null;
    if (!pointers.size) {
      drag = null;
      viewport.classList.remove("dragging");
    }
  }

  viewport.addEventListener("pointerup", endPointer);
  viewport.addEventListener("pointercancel", endPointer);

  viewport.addEventListener("wheel", (e) => {
    e.preventDefault();
    cancelAnimationFrame(anim);
    const delta = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
    zoomAt(e.clientX, e.clientY, Math.exp(-delta * (e.ctrlKey ? 0.01 : 0.0015)));
  }, { passive: false });

  viewport.addEventListener("keydown", (e) => {
    if (e.target.closest("input")) return;
    if (e.key === "Enter" || e.key === " ") {
      const it = itemFor(e.target);
      if (it) {
        e.preventDefault();
        openDetail(it);
      }
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.target.closest && e.target.closest("input")) return;
    if (e.key === "Escape" && detail.classList.contains("open")) return closeDetail();
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    const cx = innerWidth / 2;
    const cy = innerHeight / 2;
    const pan = { ArrowLeft: [80, 0], ArrowRight: [-80, 0], ArrowUp: [0, 80], ArrowDown: [0, -80] }[e.key];
    if (e.key === "+" || e.key === "=") zoomAt(cx, cy, 1.25);
    else if (e.key === "-") zoomAt(cx, cy, 0.8);
    else if (e.key === "0") fitAll();
    else if (pan && !e.target.closest(".detail")) {
      view.x += pan[0];
      view.y += pan[1];
      apply();
    } else return;
    e.preventDefault();
  });

  $("zoom-in").addEventListener("click", () => zoomAt(innerWidth / 2, innerHeight / 2, 1.3));
  $("zoom-out").addEventListener("click", () => zoomAt(innerWidth / 2, innerHeight / 2, 1 / 1.3));
  $("fit").addEventListener("click", () => fitAll());
  reloadBtn.addEventListener("click", () => load(true));
  addEventListener("resize", () => drawMinimap());

  // ---------- Übersichtskarte ----------

  let mmFrame = 0;
  function drawMinimap() {
    if (mmFrame) return;
    mmFrame = requestAnimationFrame(() => {
      mmFrame = 0;
      const dpr = Math.min(2, devicePixelRatio || 1);
      const w = minimap.clientWidth;
      const hgt = minimap.clientHeight;
      if (minimap.width !== Math.round(w * dpr)) minimap.width = Math.round(w * dpr);
      if (minimap.height !== Math.round(hgt * dpr)) minimap.height = Math.round(hgt * dpr);
      const ctx = minimap.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, hgt);
      const m = minimapScale();
      const css = getComputedStyle(document.documentElement);
      const color = (name) => css.getPropertyValue(name).trim();

      ctx.strokeStyle = color("--main-line");
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(m.ox + (150 - bounds.x) * m.s, m.oy + (MAIN_Y - bounds.y) * m.s);
      ctx.lineTo(m.ox + bounds.w * m.s, m.oy + (MAIN_Y - bounds.y) * m.s);
      ctx.stroke();

      for (const it of items) {
        const filterId = STATES[it.state].filter;
        ctx.globalAlpha = it.node && it.node.classList.contains("dim") ? 0.2 : 1;
        ctx.fillStyle = color({ merged: "--merged", open: "--open", closed: "--closed", branch: "--branch", task: "--task" }[filterId]);
        const hgtCard = (it.node && it.node.offsetHeight) || 400;
        ctx.fillRect(m.ox + (it.x - bounds.x) * m.s, m.oy + (it.y - bounds.y) * m.s, Math.max(2, CARD_W * m.s), Math.max(2, hgtCard * m.s));
      }
      ctx.globalAlpha = 1;

      const vx = (-view.x / view.k - bounds.x) * m.s + m.ox;
      const vy = (-view.y / view.k - bounds.y) * m.s + m.oy;
      ctx.strokeStyle = color("--accent-2");
      ctx.lineWidth = 1.5;
      ctx.strokeRect(vx, vy, (innerWidth / view.k) * m.s, (innerHeight / view.k) * m.s);
    });
  }

  function minimapScale() {
    const pad = 10;
    const w = minimap.clientWidth - pad * 2;
    const hgt = minimap.clientHeight - pad * 2;
    const s = Math.min(w / bounds.w, hgt / bounds.h);
    return { s, ox: pad + (w - bounds.w * s) / 2, oy: pad + (hgt - bounds.h * s) / 2 };
  }

  let mmDrag = false;
  function jumpFromMinimap(e) {
    const r = minimap.getBoundingClientRect();
    const m = minimapScale();
    const wx = (e.clientX - r.left - m.ox) / m.s + bounds.x;
    const wy = (e.clientY - r.top - m.oy) / m.s + bounds.y;
    const t = centerOn(wx, wy);
    Object.assign(view, t);
    apply();
  }
  minimap.addEventListener("pointerdown", (e) => {
    mmDrag = true;
    minimap.setPointerCapture(e.pointerId);
    cancelAnimationFrame(anim);
    jumpFromMinimap(e);
  });
  minimap.addEventListener("pointermove", (e) => mmDrag && jumpFromMinimap(e));
  minimap.addEventListener("pointerup", () => { mmDrag = false; });

  // ---------- Start ----------

  function showNotice(text, corner) {
    notice.textContent = text;
    notice.classList.toggle("corner", Boolean(corner));
    notice.hidden = !text;
  }

  function updateSub(when) {
    const agents = new Set(items.map((it) => it.agent.name)).size;
    const parts = [`${items.length} Ergebnis${items.length === 1 ? "" : "se"} von ${agents} Agent${agents === 1 ? "" : "en"}`, REPO];
    if (when) parts.push(`Stand ${fmt.format(new Date(when))}`);
    sub.textContent = parts.join(" · ");
  }

  async function load(force) {
    reloadBtn.classList.add("spin");
    reloadBtn.disabled = true;
    const cache = readCache();
    let data = null;
    let when = null;
    let problem = "";

    if (window.LEINWAND_DATEN) {
      data = window.LEINWAND_DATEN.data;
      when = window.LEINWAND_DATEN.t;
    } else if (!force && cache && Date.now() - cache.t < CACHE_MS) {
      data = cache.data;
      when = cache.t;
    } else {
      try {
        data = await loadGithub();
        when = Date.now();
        writeCache(data);
      } catch (err) {
        problem = err.message;
        if (cache) {
          data = cache.data;
          when = cache.t;
        }
      }
    }

    const first = !items.length;
    items = withOffice(data ? data.items : []);
    render();
    updateSub(when);
    if (first || force) initialView();

    if (problem && data) showNotice(`GitHub ist gerade nicht erreichbar (${problem}) – du siehst den Stand vom ${fmtLong.format(new Date(when))}.`, true);
    else if (problem) showNotice(`Die Ergebnisse konnten nicht von GitHub geladen werden. ${problem} Später mit ↻ erneut versuchen.`);
    else if (!items.length) showNotice("Noch keine Ergebnisse – sobald ein Agent einen Pull Request öffnet, erscheint er hier.");
    else showNotice("");

    reloadBtn.classList.remove("spin");
    reloadBtn.disabled = false;
  }

  load(false);
})();
