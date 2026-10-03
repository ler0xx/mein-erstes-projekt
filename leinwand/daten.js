// Holt die Ergebnisse eines Repos von der GitHub-API: alle Pull Requests mit
// ihren Dateien und dazu Branches ohne Pull Request, die Commits vor dem
// Haupt-Branch haben. Läuft im Browser (window.LeinwandDaten) und in Node
// (require), damit Leinwand und bild.mjs dieselben Daten sehen.
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.LeinwandDaten = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const mapFile = (f) => ({ name: f.filename, status: f.status, add: f.additions, del: f.deletions });

  function summarize(files) {
    return {
      additions: files.reduce((n, f) => n + (f.add || 0), 0),
      deletions: files.reduce((n, f) => n + (f.del || 0), 0),
    };
  }

  async function laden(repo, token) {
    const api = "https://api.github.com/repos/" + repo;
    const headers = { Accept: "application/vnd.github+json" };
    if (token) headers.Authorization = "Bearer " + token;

    async function gh(path) {
      const res = await fetch(api + path, { headers });
      if (!res.ok) {
        const limited = res.status === 403 || res.status === 429;
        throw new Error(limited ? "Das stündliche GitHub-Limit ist erreicht." : `GitHub antwortet mit Status ${res.status}.`);
      }
      return res.json();
    }

    const info = await gh("");
    const base = info.default_branch;
    const [pulls, branches] = await Promise.all([
      gh("/pulls?state=all&per_page=100"),
      gh("/branches?per_page=100"),
    ]);

    const prItems = await Promise.all(pulls.map(async (p) => {
      const files = (await gh(`/pulls/${p.number}/files?per_page=100`).catch(() => [])).map(mapFile);
      return {
        kind: "pr",
        id: "pr-" + p.number,
        number: p.number,
        state: p.merged_at ? "merged" : p.state === "open" ? (p.draft ? "draft" : "open") : "closed",
        title: p.title,
        body: p.body || "",
        url: p.html_url,
        branch: p.head.ref,
        sha: p.head.sha,
        created: p.created_at,
        merged: p.merged_at,
        closed: p.closed_at,
        author: p.user && p.user.login,
        files,
        ...summarize(files),
      };
    }));

    const prBranches = new Set(pulls.map((p) => p.head.ref));
    const loose = branches.filter((b) => b.name !== base && !prBranches.has(b.name));
    const branchItems = await Promise.all(loose.map(async (b) => {
      const ref = b.name.split("/").map(encodeURIComponent).join("/");
      const cmp = await gh(`/compare/${encodeURIComponent(base)}...${ref}`).catch(() => null);
      if (!cmp || !cmp.ahead_by) return null;
      const commits = cmp.commits || [];
      const files = (cmp.files || []).map(mapFile);
      const first = commits[0];
      const last = commits[commits.length - 1];
      return {
        kind: "branch",
        id: "branch-" + b.name,
        state: "branch",
        title: last ? last.commit.message.split("\n")[0] : b.name,
        body: commits.map((c) => `- ${c.commit.message.split("\n")[0]}`).join("\n"),
        url: `https://github.com/${repo}/compare/${ref}`,
        branch: b.name,
        sha: b.commit.sha,
        created: first ? first.commit.author.date : null,
        updated: last ? last.commit.author.date : null,
        commits: commits.length,
        files,
        ...summarize(files),
      };
    }));

    return { base, items: [...prItems, ...branchItems.filter(Boolean)] };
  }

  return { laden };
});
