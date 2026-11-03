/* Dashboard script, part 3 of 3: shell, in-place re-rendering and live polling. Closes the
   closure opened in app.js. */

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

  /* Re-render everything from the current data, keeping tab, drawer, filters, focus and scroll. */
  function renderAll() {
    var ae = document.activeElement, main = document.getElementById("view");
    var fid = ae && ae.id && main.contains(ae) ? ae.id : null;
    var sel = fid && typeof ae.selectionStart === "number" ? [ae.selectionStart, ae.selectionEnd] : null;
    var y = window.scrollY;
    renderHeader(); show(st.tab, false);
    if (st.drawer) openDrawer(st.drawer, true);
    if (fid) {
      var el = document.getElementById(fid);
      if (el) { el.focus(); if (sel && el.setSelectionRange) { try { el.setSelectionRange(sel[0], sel[1]); } catch (e) { /* not text */ } } }
    }
    window.scrollTo(0, y);
  }

  /* ---------- pure poll logic (unit-tested under node) ---------- */
  // PURE-BEGIN
  var POLL_MS = 3000, REFRESH_MS = 30000, OFFLINE_AFTER = 2;
  function needsFetch(prevStamp, stamp, lastFetchMs, nowMs, refreshMs) {
    return prevStamp === null || stamp !== prevStamp || nowMs - lastFetchMs >= refreshMs;
  }
  function stateSig(d) {
    var c = {}, k;
    for (k in d) c[k] = d[k];
    c.generated_at = "";
    if (c.activity) { var a = {}; for (k in c.activity) a[k] = c.activity[k]; a.now = 0; c.activity = a; }
    return JSON.stringify(c);
  }
  function liveText(online, sinceOkS) {
    return online ? "Live, updated " + sinceOkS + " s ago" : "Offline, retrying";
  }
  // PURE-END

  /* ---------- live polling ---------- */
  var P = { stamp: null, lastFetch: 0, lastOk: Date.now(), fails: 0, sig: "", busy: false, online: true, shownSig: "" };
  function setLive(mode) {
    var el = document.getElementById("live");
    el.className = "live " + mode;
    if (mode === "static") el.textContent = "Static copy (reloads every 10 s)";
    else el.textContent = liveText(mode === "on", Math.round((Date.now() - P.lastOk) / 1000));
  }
  function getJSON(url) {
    var ctl = typeof AbortController === "function" ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, 2500);
    return fetch(url, { cache: "no-store", signal: ctl ? ctl.signal : undefined }).then(function (r) {
      clearTimeout(timer);
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }, function (e) { clearTimeout(timer); throw e; });
  }
  function pollOnce() {
    if (P.busy) return;
    P.busy = true;
    getJSON("/api/stamp").then(function (s) {
      P.fails = 0; P.lastOk = Date.now(); P.online = true; setLive("on");
      if (!needsFetch(P.stamp, s.stamp, P.lastFetch, Date.now(), REFRESH_MS)) return null;
      P.stamp = s.stamp;
      return getJSON("/api/state").then(function (d) {
        P.lastFetch = Date.now();
        var sig = stateSig(d), changed = sig !== P.sig;
        P.sig = sig; setData(d);
        if (changed || activeSig() !== P.shownSig) { renderAll(); P.shownSig = activeSig(); }
      });
    }).catch(function () {
      P.fails += 1;
      if (P.fails >= OFFLINE_AFTER) { P.online = false; setLive("off"); }
    }).then(function () { P.busy = false; });
  }
  function tick() {
    if (P.online) setLive("on");
    Array.prototype.forEach.call(document.querySelectorAll(".ago"), function (el) {
      el.textContent = fmtAgo(nowS() - Number(el.getAttribute("data-mtime")));
    });
    if (ACT && activeSig() !== P.shownSig) { renderAll(); P.shownSig = activeSig(); }  // badges expire on their own
  }
  function startLive() {
    P.sig = stateSig(D); P.shownSig = activeSig();
    if (location.protocol.indexOf("http") !== 0) {  // opened as a file: no server to poll
      setLive("static");
      setTimeout(function () { location.reload(); }, 10000);
      return;
    }
    setLive("on");
    setInterval(pollOnce, POLL_MS);
    setInterval(tick, 1000);
    pollOnce();
  }

  /* ---------- init ---------- */
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
    startLive();
  }
  init();
})();
