/* Dashboard script, part 1 of 3. app.js + views.js + live.js are concatenated by render.py into
   ONE closure: this file opens it, live.js closes it. Rendering is a function of the current
   data (setData + renderAll in live.js), so it can be re-run without reloading the page. */
(function () {
  "use strict";
  var D = {}, LIVE = null, CARDS = [], ACT = null, fetchedAt = Date.now();
  function setData(d) {
    D = d || { cards: [], warnings: [], statuses: [] };
    LIVE = D.live || null; CARDS = D.cards || []; ACT = D.activity || null; fetchedAt = Date.now();
  }
  try { setData(JSON.parse(document.getElementById("data").textContent)); }
  catch (e) { setData({ cards: [], warnings: ["Dashboard data could not be read."], statuses: [] }); }
  var LABEL = { TODO: "To do", IN_PROGRESS: "In progress", IN_REVIEW: "In review", DONE: "Done", BLOCKED: "Blocked" };
  var ICON = {
    TODO: '<circle cx="8" cy="8" r="5.5"/>',
    IN_PROGRESS: '<circle cx="8" cy="8" r="5.5"/><path d="M8 2.5v11" /><path d="M8 2.5a5.5 5.5 0 0 1 0 11z" fill="currentColor"/>',
    IN_REVIEW: '<rect x="2.5" y="2.5" width="11" height="11" rx="2"/><path d="M5.5 8h5M8 5.5v5"/>',
    DONE: '<circle cx="8" cy="8" r="5.5"/><path d="M5.3 8.2l2 2 3.5-4"/>',
    BLOCKED: '<circle cx="8" cy="8" r="5.5"/><path d="M4.5 11.5l7-7"/>'
  };
  var TABS = [["board", "Board"], ["now", "Now"], ["timeline", "Timeline"], ["usage", "Usage"], ["team", "Team"], ["activity", "Activity"]];
  var st = { tab: "board", q: "", status: "", owner: "", drawer: null };
  var openSet = {};
  var lastFocus = null;

  function h(tag, attrs, kids) {
    var el = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === "class") el.className = attrs[k];
      else if (k === "text") el.textContent = attrs[k];
      else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] !== null && attrs[k] !== undefined && attrs[k] !== false) el.setAttribute(k, attrs[k] === true ? "" : attrs[k]);
    }
    (kids || []).forEach(function (c) { if (c !== null && c !== undefined && c !== false) el.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return el;
  }
  function inline(text) {
    var f = document.createDocumentFragment();
    String(text || "").split(/(`[^`]+`|\*\*[^*]+\*\*)/).forEach(function (p) {
      if (!p) return;
      if (p[0] === "`" && p.length > 2) f.appendChild(h("code", { text: p.slice(1, -1) }));
      else if (p.slice(0, 2) === "**" && p.length > 4) f.appendChild(h("strong", { text: p.slice(2, -2) }));
      else f.appendChild(document.createTextNode(p));
    });
    return f;
  }
  function badge(status) {
    var b = h("span", { class: "badge s-" + status });
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 16 16"); svg.setAttribute("aria-hidden", "true");
    svg.innerHTML = ICON[status] || ICON.TODO;
    b.appendChild(svg); b.appendChild(document.createTextNode(LABEL[status] || status));
    return b;
  }
  function pts(n) { return n === null || n === undefined ? "?" : String(n); }
  function agentsFor(id) { return ((LIVE && LIVE.agents) || []).filter(function (a) { return a.ticket === id; }); }
  function fmtDate(iso) {
    var d = new Date(iso);
    return isNaN(d) ? (iso || "unknown") : d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
  }
  function missing(msg) { return h("p", { class: "warn-box", text: "Data missing: " + msg }); }

  /* ---------- live activity helpers ---------- */
  function nowS() { return ACT ? ACT.now + (Date.now() - fetchedAt) / 1000 : Date.now() / 1000; }
  function fmtAgo(s) {
    s = Math.max(0, Math.round(s));
    return s < 60 ? s + " s ago" : s < 3600 ? Math.round(s / 60) + " min ago" : Math.round(s / 3600) + " h ago";
  }
  function agoSpan(mtime) { return h("span", { class: "ago", "data-mtime": String(mtime), text: fmtAgo(nowS() - mtime) }); }
  function ticketAct(id) {
    var files = ACT ? ACT.files.filter(function (f) { return f.ticket === id && nowS() - f.mtime <= ACT.window_s; }) : [];
    return { files: files, active: files.length > 0 && nowS() - files[0].mtime <= ACT.active_s };
  }
  function activeSig() {
    if (!ACT) return "";
    return CARDS.filter(function (c) { return ticketAct(c.id).active; }).map(function (c) { return c.id; }).join(",") +
      "|" + ACT.files.filter(function (f) { return nowS() - f.mtime <= ACT.window_s; }).length;
  }
  function unregistered(c) { return c.status === "IN_PROGRESS" && ACT && ACT.truth.no_agent.indexOf(c.id) >= 0; }
  function latestLine(c) {
    var a = c.activity && c.activity.length ? c.activity[c.activity.length - 1] : "";
    a = a.split("\n")[0].replace(/[`*]/g, "");
    return a.length > 110 ? a.slice(0, 107) + "..." : a;
  }
  function liveBadge() { return h("span", { class: "live-badge", text: "Active now" }); }

  /* ---------- header ---------- */
  function renderHeader() {
    document.getElementById("proj").textContent = D.project || "Project";
    var sp = (LIVE && LIVE.sprint) || {};
    document.getElementById("goal").textContent = sp.name ? sp.name + ": " + (sp.goal || "") : "Sprint goal: data missing";
    document.getElementById("stamp").textContent = "Data built " + fmtDate(D.generated_at) + (LIVE && LIVE.updated ? " | status.json " + fmtDate(LIVE.updated) : "");
    var g = ACT && ACT.git, gl = document.getElementById("gitline");
    gl.textContent = g ? "Git: " + g.branch + " | " + g.dirty + " uncommitted file" + (g.dirty === 1 ? "" : "s") + (g.last_commit ? " | last commit: " + g.last_commit : "") : "";
    var sn = document.getElementById("stale"), tr = ACT && ACT.truth;
    sn.hidden = !(tr && tr.status_stale);
    sn.textContent = tr && tr.status_stale ? "Status file may be stale: status.json was updated " + fmtAgo(tr.status_age_s) + " but work is in progress." : "";
    var u = (LIVE && LIVE.usage) || {}, b = document.getElementById("banner");
    var plan = u.weekly_cap_plan_pct == null ? 40 : u.weekly_cap_plan_pct;
    b.hidden = true;
    if (typeof u.weekly_pct === "number" && u.weekly_pct >= plan) {
      b.hidden = false;
      b.textContent = "Warning: weekly Claude usage is " + u.weekly_pct + "%, at or above the " + plan + "% plan line (hard stop " + (u.weekly_cap_hard_pct == null ? 50 : u.weekly_cap_hard_pct) + "%). Pause new work.";
    }
    var w = document.getElementById("warnings");
    w.textContent = ""; w.hidden = true;
    if ((D.warnings || []).length) {
      w.hidden = false;
      D.warnings.forEach(function (m) { w.appendChild(h("p", { class: "warn-box", text: m })); });
    }
  }

  /* ---------- board ---------- */
  function matches(c) {
    if (st.status && c.status !== st.status) return false;
    if (st.owner && c.owner !== st.owner) return false;
    if (st.q) {
      var hay = (c.id + " " + c.title + " " + c.scope + " " + c.owner).toLowerCase();
      if (hay.indexOf(st.q.toLowerCase()) < 0) return false;
    }
    return true;
  }
  function cardEl(c) {
    var ags = agentsFor(c.id), run = ags.filter(function (a) { return a.status === "running"; });
    var ta = ticketAct(c.id), chips = [h("span", { class: "chip", text: c.owner || "Unassigned" })];
    if (ta.active) chips.unshift(liveBadge());
    if (unregistered(c)) chips.push(h("span", { class: "chip dep", text: "Work in progress (agent not registered)" }));
    run.forEach(function (a) { chips.push(h("span", { class: "chip run", text: "Running: " + a.name })); });
    if (!run.length && ags.length) chips.push(h("span", { class: "chip", text: ags.length + " agent" + (ags.length > 1 ? "s" : "") + " (finished)" }));
    if (c.model) chips.push(h("span", { class: "chip", text: "Model: " + c.model }));
    chips.push(h("span", { class: "chip", text: "Points: " + pts(c.estimate) + " est / " + (c.actual == null ? "no actual yet" : c.actual + " actual") }));
    if (c.depends_on && c.depends_on.length) chips.push(h("span", { class: "chip dep", text: "Needs " + c.depends_on.join(", ") }));
    var titleText = c.title && c.title !== c.id ? c.title : c.scope;
    return h("button", { class: "card s-" + c.status, type: "button", "aria-label": c.id + ", " + LABEL[c.status] + (ta.active ? ", active now" : "") + ". " + titleText, onclick: function () { openDrawer(c.id); } }, [
      h("span", { class: "id", text: c.id }), h("span", { class: "ttl", text: titleText }), h("div", { class: "chips" }, chips),
      latestLine(c) ? h("span", { class: "latest", text: "Latest: " + latestLine(c) }) : null
    ]);
  }
  function renderBoard(root) {
    var owners = []; CARDS.forEach(function (c) { if (c.owner && owners.indexOf(c.owner) < 0) owners.push(c.owner); });
    var q = h("input", { type: "search", id: "f-q", value: st.q, placeholder: "ID or words", oninput: function (e) { st.q = e.target.value; refreshCols(); } });
    var sel = h("select", { id: "f-s", onchange: function (e) { st.status = e.target.value; refreshCols(); } }, [h("option", { value: "", text: "All statuses" })].concat(Object.keys(LABEL).map(function (k) { return h("option", { value: k, text: LABEL[k], selected: st.status === k }); })));
    var own = h("select", { id: "f-o", onchange: function (e) { st.owner = e.target.value; refreshCols(); } }, [h("option", { value: "", text: "Everyone" })].concat(owners.map(function (o) { return h("option", { value: o, text: o, selected: st.owner === o }); })));
    root.appendChild(h("div", { class: "filters", role: "search" }, [
      h("label", { for: "f-q" }, ["Search", q]), h("label", { for: "f-s" }, ["Status", sel]), h("label", { for: "f-o" }, ["Assignee", own])
    ]));
    if (!CARDS.length) { root.appendChild(missing("no work packages found in board.md or tickets.")); return; }
    var board = h("div", { class: "board" }); root.appendChild(board);
    function refreshCols() {
      board.textContent = "";
      Object.keys(LABEL).forEach(function (s) {
        var list = CARDS.filter(function (c) { return c.status === s && matches(c); });
        var col = h("section", { class: "col", "aria-label": LABEL[s] + ", " + list.length + " items" }, [
          h("h3", {}, [badge(s), h("span", { class: "n", text: String(list.length) })])
        ]);
        if (!list.length) col.appendChild(h("p", { class: "empty", text: "Nothing here" }));
        list.forEach(function (c) { col.appendChild(cardEl(c)); });
        board.appendChild(col);
      });
    }
    refreshCols();
  }

  /* ---------- drawer ---------- */
  function section(title, node) { return [h("h3", { text: title }), node]; }
  function openDrawer(id, keep) {
    var c = CARDS.filter(function (x) { return x.id === id; })[0];
    if (!c) return;
    var body = document.getElementById("drawer-body"), dr = document.getElementById("drawer");
    if (dr.hidden) lastFocus = document.activeElement;
    var keepTop = dr.scrollTop;
    st.drawer = id;
    body.textContent = "";
    document.getElementById("drawer-title").textContent = c.id + ": " + (c.title && c.title !== c.id ? c.title : c.scope);
    var kids = [h("div", { class: "chips" }, [badge(c.status), h("span", { class: "chip", text: c.owner || "Unassigned" }),
      c.model ? h("span", { class: "chip", text: "Model: " + c.model }) : null,
      h("span", { class: "chip", text: "Points: " + pts(c.estimate) + " est / " + (c.actual == null ? "no actual yet" : c.actual + " actual") })])];
    var ta = ticketAct(c.id);
    if (ta.active) kids.push(h("p", {}, [liveBadge()]));
    if (unregistered(c)) kids.push(h("p", { class: "warn-box", text: "Work in progress (agent not registered): no running agent is listed for this ticket in status.json." }));
    if (ta.files.length) kids = kids.concat(section("Recent file changes", h("ul", { class: "tasks" }, ta.files.slice(0, 12).map(function (f) { return h("li", {}, [h("code", { text: f.path }), " ", agoSpan(f.mtime)]); }))));
    if (c.status_note) kids.push(h("p", { class: "small muted", text: c.status_note }));
    if (c.scope && c.scope !== c.title) kids = kids.concat(section("Scope", h("p", { text: c.scope })));
    if (c.goal) kids = kids.concat(section("Goal", h("p", {}, [inline(c.goal)])));
    var ags = agentsFor(c.id);
    if (ags.length) kids = kids.concat(section("Agents", h("ul", { class: "tasks" }, ags.map(function (a) { return h("li", { text: a.name + " (" + a.role + ", " + a.model + ", " + a.status + "): " + (a.note || "") }); }))));
    if (c.depends_on && c.depends_on.length) {
      kids = kids.concat(section("Depends on", h("div", {}, c.depends_on.map(function (d) {
        var known = CARDS.some(function (x) { return x.id === d; });
        return known ? h("button", { class: "linkbtn", type: "button", onclick: function () { openDrawer(d); } }, [d]) : h("span", { class: "chip", text: d });
      }))));
    }
    if (c.tasks && c.tasks.length) {
      var tracked = c.tasks.filter(function (t) { return t.done !== null; }), done = tracked.filter(function (t) { return t.done; }).length;
      var box = h("div", {});
      if (tracked.length) {
        box.appendChild(h("p", { class: "small", text: done + " of " + tracked.length + " tasks done" }));
        box.appendChild(h("div", { class: "prog", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": String(tracked.length), "aria-valuenow": String(done), "aria-label": "Task progress" }, [h("i", { style: "width:" + Math.round(100 * done / tracked.length) + "%" })]));
      } else box.appendChild(h("p", { class: "small muted", text: c.tasks.length + " tasks listed (no checkboxes, so progress is not tracked)" }));
      box.appendChild(h("ul", { class: "tasks" }, c.tasks.map(function (t) { return h("li", {}, [t.done === null ? "" : (t.done ? "Done: " : "Open: "), inline(t.text)]); })));
      kids = kids.concat(section("Tasks", box));
    }
    if (c.acceptance) kids = kids.concat(section("Acceptance", h("div", { class: "drawer-pre" }, [inline(c.acceptance)])));
    if (c.activity && c.activity.length) kids = kids.concat(section("Activity log", h("div", {}, c.activity.map(function (a) { return h("div", { class: "entry" }, [inline(a)]); }))));
    if (c.linked && c.linked.length) kids = kids.concat(section("Related standups and reviews", h("ul", { class: "tasks" }, c.linked.map(function (l) { return h("li", { text: (l.date ? l.date + " " : "") + l.kind + ": " + l.title + " (" + l.file + ")" }); }))));
    if (!c.has_ticket) kids.push(h("p", { class: "warn-box", text: "No ticket file yet for this work package, so there are no tasks or log to show." }));
    kids.forEach(function (k) { body.appendChild(k); });
    document.getElementById("scrim").hidden = false; dr.hidden = false;
    if (keep) dr.scrollTop = keepTop;
    else { document.getElementById("drawer-close").focus(); dr.scrollTop = 0; }
  }
  function closeDrawer() {
    st.drawer = null;
    document.getElementById("drawer").hidden = true; document.getElementById("scrim").hidden = true;
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

