(function () {
  "use strict";
  var D;
  try { D = JSON.parse(document.getElementById("data").textContent); }
  catch (e) { D = { cards: [], warnings: ["Dashboard data could not be read."], statuses: [] }; }
  var LIVE = D.live || null;
  var CARDS = D.cards || [];
  var LABEL = { TODO: "To do", IN_PROGRESS: "In progress", IN_REVIEW: "In review", DONE: "Done", BLOCKED: "Blocked" };
  var ICON = {
    TODO: '<circle cx="8" cy="8" r="5.5"/>',
    IN_PROGRESS: '<circle cx="8" cy="8" r="5.5"/><path d="M8 2.5v11" /><path d="M8 2.5a5.5 5.5 0 0 1 0 11z" fill="currentColor"/>',
    IN_REVIEW: '<rect x="2.5" y="2.5" width="11" height="11" rx="2"/><path d="M5.5 8h5M8 5.5v5"/>',
    DONE: '<circle cx="8" cy="8" r="5.5"/><path d="M5.3 8.2l2 2 3.5-4"/>',
    BLOCKED: '<circle cx="8" cy="8" r="5.5"/><path d="M4.5 11.5l7-7"/>'
  };
  var TABS = [["board", "Board"], ["now", "Now"], ["timeline", "Timeline"], ["usage", "Usage"], ["team", "Team"], ["activity", "Activity"]];
  var st = { tab: "board", q: "", status: "", owner: "" };
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

  /* ---------- header ---------- */
  function renderHeader() {
    document.getElementById("proj").textContent = D.project || "Project";
    var sp = (LIVE && LIVE.sprint) || {};
    document.getElementById("goal").textContent = sp.name ? sp.name + ": " + (sp.goal || "") : "Sprint goal: data missing";
    document.getElementById("stamp").textContent = "Page built " + fmtDate(D.generated_at) + (LIVE && LIVE.updated ? " | live data from " + fmtDate(LIVE.updated) : "");
    var u = (LIVE && LIVE.usage) || {}, b = document.getElementById("banner");
    var plan = u.weekly_cap_plan_pct == null ? 40 : u.weekly_cap_plan_pct;
    if (typeof u.weekly_pct === "number" && u.weekly_pct >= plan) {
      b.hidden = false;
      b.textContent = "Warning: weekly Claude usage is " + u.weekly_pct + "%, at or above the " + plan + "% plan line (hard stop " + (u.weekly_cap_hard_pct == null ? 50 : u.weekly_cap_hard_pct) + "%). Pause new work.";
    }
    var w = document.getElementById("warnings");
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
    var chips = [h("span", { class: "chip", text: c.owner || "Unassigned" })];
    run.forEach(function (a) { chips.push(h("span", { class: "chip run", text: "Running: " + a.name })); });
    if (!run.length && ags.length) chips.push(h("span", { class: "chip", text: ags.length + " agent" + (ags.length > 1 ? "s" : "") + " (finished)" }));
    if (c.model) chips.push(h("span", { class: "chip", text: "Model: " + c.model }));
    chips.push(h("span", { class: "chip", text: "Points: " + pts(c.estimate) + " est / " + (c.actual == null ? "no actual yet" : c.actual + " actual") }));
    if (c.depends_on && c.depends_on.length) chips.push(h("span", { class: "chip dep", text: "Needs " + c.depends_on.join(", ") }));
    var titleText = c.title && c.title !== c.id ? c.title : c.scope;
    return h("button", { class: "card s-" + c.status, type: "button", "aria-label": c.id + ", " + LABEL[c.status] + ". " + titleText, onclick: function () { openDrawer(c.id); } }, [
      h("span", { class: "id", text: c.id }), h("span", { class: "ttl", text: titleText }), h("div", { class: "chips" }, chips)
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
  function openDrawer(id) {
    var c = CARDS.filter(function (x) { return x.id === id; })[0];
    if (!c) return;
    var body = document.getElementById("drawer-body"), dr = document.getElementById("drawer");
    if (dr.hidden) lastFocus = document.activeElement;
    body.textContent = "";
    document.getElementById("drawer-title").textContent = c.id + ": " + (c.title && c.title !== c.id ? c.title : c.scope);
    var kids = [h("div", { class: "chips" }, [badge(c.status), h("span", { class: "chip", text: c.owner || "Unassigned" }),
      c.model ? h("span", { class: "chip", text: "Model: " + c.model }) : null,
      h("span", { class: "chip", text: "Points: " + pts(c.estimate) + " est / " + (c.actual == null ? "no actual yet" : c.actual + " actual") })])];
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
    document.getElementById("drawer-close").focus();
    dr.scrollTop = 0;
  }
  function closeDrawer() {
    document.getElementById("drawer").hidden = true; document.getElementById("scrim").hidden = true;
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  /* ---------- now ---------- */
  function renderNow(root) {
    var counts = h("div", { class: "counts" });
    Object.keys(LABEL).forEach(function (s) {
      var n = CARDS.filter(function (c) { return c.status === s; }).length;
      counts.appendChild(h("div", { class: "count" }, [h("b", { text: String(n) }), badge(s)]));
    });
    root.appendChild(counts);
    var grid = h("div", { class: "grid2" });
    var work = h("section", { class: "panel" }, [h("h2", { text: "Who is working on what" })]);
    if (!LIVE) work.appendChild(missing("status.json not available, so agents are unknown."));
    else {
      var ags = LIVE.agents.slice().sort(function (a, b) { return (b.status === "running") - (a.status === "running"); });
      if (!ags.length) work.appendChild(h("p", { class: "muted", text: "No agents listed." }));
      var ul = h("ul", { class: "list" });
      ags.forEach(function (a) {
        var run = a.status === "running";
        ul.appendChild(h("li", {}, [
          h("div", {}, [h("strong", { text: a.name }), " ", h("span", { class: "muted small", text: a.role + (a.model ? ", " + a.model : "") }), h("div", { class: "small", text: a.note || "" })]),
          h("div", { class: "chips" }, [h("span", { class: "chip" + (run ? " run" : ""), text: run ? "Working now" : (a.status === "done" ? "Finished" : a.status) }),
            a.ticket && a.ticket !== "—" ? h("button", { class: "linkbtn", type: "button", onclick: function () { openDrawer(a.ticket); } }, [a.ticket]) : null])
        ]));
      });
      work.appendChild(ul);
    }
    grid.appendChild(work);
    var own = h("section", { class: "panel owner" }, [h("h2", { text: "Needs the owner" })]);
    var bl = LIVE ? LIVE.owner_blockers : [];
    if (bl.length) {
      var open = bl.filter(function (b) { return b.status !== "done"; }), closed = bl.filter(function (b) { return b.status === "done"; });
      var ol = h("ul", { class: "list" });
      open.concat(closed).forEach(function (b) {
        var isDone = b.status === "done";
        ol.appendChild(h("li", {}, [h("span", { class: isDone ? "done-item" : "", text: b.item }),
          h("span", { class: "chip", text: (isDone ? "Done" : "Open") + ", needed by " + (b.needed_by || "unspecified") })]));
      });
      own.appendChild(h("p", { class: "small", text: open.length + " open, " + closed.length + " done." }));
      own.appendChild(ol);
    } else if (D.blocked_text) { own.appendChild(h("p", {}, [inline(D.blocked_text)])); }
    else own.appendChild(missing("no owner action list found."));
    grid.appendChild(own);
    root.appendChild(grid);
  }

  /* ---------- timeline ---------- */
  function renderTimeline(root) {
    var p = h("section", { class: "panel" }, [h("h2", { text: "Planned timeline" })]);
    var tl = D.timeline || [];
    if (!tl.length) { p.appendChild(missing("no work packages to plot.")); root.appendChild(p); return; }
    var basis = tl.some(function (t) { return t.basis === "spread by estimate"; });
    p.appendChild(h("p", { class: "small muted", text: basis ? "Indicative: weeks are spread by estimate points across the plan (W0 to W4). Add a timeline list to status.json to set exact weeks." : "Weeks from the plan." }));
    var axis = h("div", { class: "tl-axis", "aria-hidden": "true" }, ["W0", "W1", "W2", "W3", "W4", "After"].map(function (w) { return h("span", { text: w }); }));
    p.appendChild(axis);
    var wrap = h("div", { class: "tl" });
    tl.forEach(function (t) {
      var left = Math.min(100, t.start / 6 * 100), width = Math.max(2, (t.end - t.start) / 6 * 100);
      wrap.appendChild(h("div", { class: "tl-row s-" + t.status }, [
        h("div", { class: "nm" }, [h("strong", { text: t.id }), h("span", { text: t.label }), badge(t.status)]),
        h("div", { class: "tl-track" }, [h("div", { class: "tl-bar", style: "left:" + left + "%;width:" + width + "%" })])
      ]));
    });
    p.appendChild(wrap); root.appendChild(p);
  }

  /* ---------- usage ---------- */
  function gauge(label, pct, marks, note) {
    var cls = "fill"; var plan = marks.length ? marks[0].at : 101, hard = marks.length > 1 ? marks[1].at : 101;
    if (pct >= hard) cls += " bad"; else if (pct >= plan) cls += " warn";
    var track = h("div", { class: "track", role: "meter", "aria-label": label, "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": String(pct) }, [h("div", { class: cls, style: "width:" + Math.min(100, pct) + "%" })]);
    marks.forEach(function (m) {
      track.appendChild(h("div", { class: "mark" + (m.hard ? " hard" : ""), style: "left:" + m.at + "%" }));
      track.appendChild(h("span", { class: "marklbl" + (m.hard ? " hard" : ""), style: "left:" + m.at + "%", text: m.text }));
    });
    return h("div", { class: "gauge" }, [h("div", { class: "lbl" }, [h("strong", { text: label }), h("span", { text: pct + "%" + (note ? " | " + note : "") })]), track]);
  }
  function renderUsage(root) {
    var u = LIVE && LIVE.usage, p = h("section", { class: "panel" }, [h("h2", { text: "Claude usage" })]);
    if (!u || typeof u.weekly_pct !== "number") p.appendChild(missing("weekly usage not available in status.json."));
    else {
      var plan = u.weekly_cap_plan_pct == null ? 40 : u.weekly_cap_plan_pct, hard = u.weekly_cap_hard_pct == null ? 50 : u.weekly_cap_hard_pct;
      p.appendChild(gauge("This week", u.weekly_pct, [{ at: plan, text: "Plan " + plan + "%" }, { at: hard, text: "Hard stop " + hard + "%", hard: true }], u.weekly_resets ? "resets " + fmtDate(u.weekly_resets) : ""));
      if (typeof u.five_hour_pct === "number") p.appendChild(gauge("Last 5 hours", u.five_hour_pct, [], u.five_hour_resets ? "resets " + fmtDate(u.five_hour_resets) : ""));
      p.appendChild(h("p", { class: "small muted", text: "Dashed line is the planned limit; the solid red line is the hard stop." }));
    }
    root.appendChild(p);
    var o = h("section", { class: "panel" }, [h("h2", { text: "OpenAI spend" })]);
    if (!u || (u.openai_balance_usd == null && u.openai_spent_usd == null)) o.appendChild(missing("OpenAI figures not in status.json."));
    else o.appendChild(h("p", { text: "Spent $" + (u.openai_spent_usd == null ? "?" : u.openai_spent_usd) + " | balance $" + (u.openai_balance_usd == null ? "?" : u.openai_balance_usd) }));
    root.appendChild(o);
    var l = h("section", { class: "panel" }, [h("h2", { text: "Points: planned vs actual" })]);
    if (!(D.ledger || []).length) l.appendChild(missing("budget-ledger.md has no rows."));
    else {
      var rows = D.ledger.map(function (r) {
        return h("tr", {}, [h("td", { text: r.date }), h("td", { text: r.wp }), h("td", { text: r.estimate == null ? "-" : String(r.estimate) }), h("td", { text: r.actual == null ? "-" : String(r.actual) }),
          h("td", { text: (r.weekly_before || "-") + " to " + (r.weekly_after || "-") }), h("td", { text: r.five_hour_after || "-" }), h("td", { text: r.notes })]);
      });
      l.appendChild(h("div", { class: "tablewrap" }, [h("table", {}, [h("thead", {}, [h("tr", {}, ["Date", "Work", "Planned pts", "Actual pts", "Weekly %", "5-hour %", "Notes"].map(function (t) { return h("th", { scope: "col", text: t }); }))]), h("tbody", {}, rows)])]));
    }
    root.appendChild(l);
  }

  /* ---------- team ---------- */
  function buildTree(nodes) {
    var rootUl = h("ul", { class: "tree", role: "tree" }), stack = [{ depth: -1, ul: rootUl }];
    nodes.forEach(function (n, i) {
      while (stack.length > 1 && stack[stack.length - 1].depth >= n.depth) stack.pop();
      var parent = stack[stack.length - 1], next = nodes[i + 1], hasKids = next && next.depth > n.depth;
      var label = [h("strong", { text: n.name }), n.desc ? h("span", { class: "d", text: " - " + n.desc }) : null];
      var li = h("li", { role: "treeitem" });
      if (hasKids) {
        var ul = h("ul", { role: "group" });
        li.appendChild(h("details", { open: n.depth < 2 }, [h("summary", {}, label), ul]));
        stack.push({ depth: n.depth, ul: ul });
      } else label.forEach(function (k) { if (k) li.appendChild(k); });
      parent.ul.appendChild(li);
    });
    return rootUl;
  }
  function renderTeam(root) {
    var o = h("section", { class: "panel" }, [h("h2", { text: "Who reports to whom" })]);
    if (!(D.org || []).length) o.appendChild(missing("org-chart.md has no hierarchy.")); else o.appendChild(buildTree(D.org));
    root.appendChild(o);
    var t = h("section", { class: "panel" }, [h("h2", { text: "Roster" })]);
    if (!(D.team || []).length) t.appendChild(missing("team.md has no roster."));
    else {
      var keys = Object.keys(D.team[0]);
      t.appendChild(h("div", { class: "tablewrap" }, [h("table", {}, [h("thead", {}, [h("tr", {}, keys.map(function (k) { return h("th", { scope: "col", text: k.charAt(0).toUpperCase() + k.slice(1) }); }))]),
        h("tbody", {}, D.team.map(function (r) { return h("tr", {}, keys.map(function (k) { return h("td", { text: r[k] }); })); }))])]));
    }
    root.appendChild(t);
  }

  /* ---------- activity ---------- */
  function renderActivity(root) {
    var items = (D.feed || []).map(function (f) { return { date: f.date, kind: f.kind === "review" ? "Review" : "Standup", title: f.title, extra: f.verdict ? "Verdict: " + f.verdict : "", text: f.excerpt, file: f.file }; });
    (D.ledger || []).forEach(function (r) { items.push({ date: r.date, kind: "Usage", title: r.wp, extra: "Weekly " + (r.weekly_before || "-") + "% to " + (r.weekly_after || "-") + "%", text: r.notes, file: "budget-ledger.md" }); });
    items.sort(function (a, b) { return (b.date || "").localeCompare(a.date || ""); });
    if (!items.length) { root.appendChild(missing("no standups, reviews or ledger rows.")); return; }
    var ul = h("ul", { class: "feed" });
    items.forEach(function (it) {
      ul.appendChild(h("li", {}, [
        h("div", { class: "chips" }, [h("span", { class: "chip", text: it.kind }), h("span", { class: "small muted", text: it.date || "date unknown" }), it.extra ? h("span", { class: "chip", text: it.extra }) : null]),
        h("strong", { text: it.title }), h("pre", {}, [inline(it.text)]), h("p", { class: "small muted", text: "Source: " + it.file })
      ]));
    });
    root.appendChild(ul);
  }

  /* ---------- shell ---------- */
  var VIEWS = { board: renderBoard, now: renderNow, timeline: renderTimeline, usage: renderUsage, team: renderTeam, activity: renderActivity };
  function show(tab, focusView) {
    st.tab = VIEWS[tab] ? tab : "board";
    var root = document.getElementById("view"); root.textContent = "";
    root.setAttribute("role", "tabpanel"); root.setAttribute("aria-labelledby", "tab-" + st.tab);
    try { VIEWS[st.tab](root); } catch (e) { root.appendChild(missing("this view could not be drawn (" + e.message + ").")); }
    Array.prototype.forEach.call(document.querySelectorAll("[role=tab]"), function (t) {
      var on = t.dataset.tab === st.tab; t.setAttribute("aria-selected", on); t.tabIndex = on ? 0 : -1;
    });
    if (focusView) root.focus();
  }
  function setTab(tab) { try { history.replaceState(null, "", "#" + tab); } catch (e) { /* file:// ok */ } show(tab, false); }
  function init() {
    renderHeader();
    var tabs = document.getElementById("tabs");
    TABS.forEach(function (t) {
      tabs.appendChild(h("button", { role: "tab", id: "tab-" + t[0], "data-tab": t[0], type: "button", onclick: function () { setTab(t[0]); } }, [t[1]]));
    });
    tabs.addEventListener("keydown", function (e) {
      var ids = TABS.map(function (t) { return t[0]; }), i = ids.indexOf(st.tab);
      if (e.key === "ArrowRight") i = (i + 1) % ids.length; else if (e.key === "ArrowLeft") i = (i + ids.length - 1) % ids.length; else if (e.key === "Home") i = 0; else if (e.key === "End") i = ids.length - 1; else return;
      e.preventDefault(); setTab(ids[i]); document.getElementById("tab-" + ids[i]).focus();
    });
    document.getElementById("drawer-close").addEventListener("click", closeDrawer);
    document.getElementById("scrim").addEventListener("click", closeDrawer);
    document.addEventListener("keydown", function (e) {
      var dr = document.getElementById("drawer");
      if (dr.hidden) return;
      if (e.key === "Escape") { closeDrawer(); return; }
      if (e.key === "Tab") {
        var f = dr.querySelectorAll("button,[href],input,select"); if (!f.length) return;
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
    show((location.hash || "").replace("#", "") || "board", false);
  }
  init();
})();
