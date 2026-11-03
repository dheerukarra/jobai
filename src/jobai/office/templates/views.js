/* Dashboard script, part 2 of 3: the Now / Timeline / Usage / Team / Activity views. */
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
    root.appendChild(recentPanel());
  }
  function recentPanel() {
    var p = h("section", { class: "panel" }, [h("h2", { text: "Recent file activity" })]);
    if (!ACT) { p.appendChild(missing("live activity is not available.")); return p; }
    var g = ACT.git;
    p.appendChild(h("p", { class: "small", text: g ? "Git: branch " + g.branch + ", " + g.dirty + " uncommitted file" + (g.dirty === 1 ? "" : "s") + (g.last_commit ? ", last commit: " + g.last_commit : "") : "Git: not a repository or git unavailable." }));
    var recent = ACT.files.filter(function (f) { return nowS() - f.mtime <= ACT.window_s; });
    if (!recent.length) { p.appendChild(h("p", { class: "muted", text: "No file changes in the last " + Math.round(ACT.window_s / 60) + " minutes." })); return p; }
    var ul = h("ul", { class: "list" });
    recent.forEach(function (f) {
      ul.appendChild(h("li", {}, [h("code", { text: f.path }),
        h("div", { class: "chips" }, [f.ticket ? h("button", { class: "linkbtn", type: "button", onclick: function () { openDrawer(f.ticket); } }, [f.ticket]) : h("span", { class: "chip", text: "no ticket" }), agoSpan(f.mtime)])]));
    });
    p.appendChild(ul);
    return p;
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
        var key = n.name, det = h("details", { open: key in openSet ? openSet[key] : n.depth < 2, ontoggle: function () { openSet[key] = det.open; } }, [h("summary", {}, label), ul]);
        li.appendChild(det);
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
