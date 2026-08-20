/* SAT Adaptive Drill — Chiron classroom app.
 *
 * Runs a per-skill difficulty ladder. Entry is always level 0 (real SAT
 * difficulty). A wrong answer drops a rung toward the prerequisite concept
 * underneath the skill; a right answer climbs. Skills that bottom out get
 * requeued so they come back around later in the session rather than being
 * quietly skipped.
 *
 * Data contract: see SCHEMA.md in this directory.
 */
(function () {
  "use strict";

  var STORE_KEY = "sat_drill_state_v1";
  var WEAK_SPOTS = ["advanced-math", "standard-english-conventions"];

  // ------------------------------------------------------------- math --
  // Shared with sat-test.js. Ordering matters: longer commands must be
  // replaced before their prefixes (\leq before \le), and the final
  // backslash strip must come last.
  function renderMath(str) {
    if (!str) return "";
    var s = String(str).replace(/\\begin\{aligned\}([\s\S]*?)\\end\{aligned\}/g, function (_, body) {
      var lines = body.split("\\\\").map(function (l) {
        return l.replace(/&/g, "").trim();
      }).filter(Boolean);
      return '<span class="sat-aligned">' + lines.join("<br>") + "</span>";
    });
    s = s.replace(/\\\$/g, " DOLLAR ").replace(/\$/g, "").replace(/ DOLLAR /g, "$");
    s = s.replace(/\\d?frac\{([^{}]+)\}\{([^{}]+)\}/g,
      '<span class="frac"><span class="num">$1</span><span class="den">$2</span></span>');
    s = s.replace(/\\d?frac(\d)(\d)/g,
      '<span class="frac"><span class="num">$1</span><span class="den">$2</span></span>');
    s = s.replace(/\\sqrt\{([^{}]+)\}/g, "√($1)").replace(/\\sqrt(\d)/g, "√$1");
    s = s.replace(/\^\{([^{}]+)\}/g, "<sup>$1</sup>").replace(/\^(\d)/g, "<sup>$1</sup>");
    s = s.replace(/_\{([^{}]+)\}/g, "<sub>$1</sub>").replace(/_(\d)/g, "<sub>$1</sub>");
    s = s.replace(/\\sin/g, "sin ").replace(/\\cos/g, "cos ").replace(/\\tan/g, "tan ")
      .replace(/\\theta/g, "θ").replace(/\\approx/g, "≈").replace(/\\times/g, "×")
      .replace(/\\div/g, "÷").replace(/\\to/g, "→").replace(/\\triangle/g, "△")
      .replace(/\\sim/g, "~");
    s = s.replace(/\\leq/g, "≤").replace(/\\geq/g, "≥").replace(/\\neq/g, "≠")
      .replace(/\\le/g, "≤").replace(/\\ge/g, "≥").replace(/\\ne/g, "≠")
      .replace(/\\pm/g, "±").replace(/\\cdot/g, "·").replace(/\\Rightarrow/g, "⇒")
      .replace(/\\pi/g, "π").replace(/\\/g, "");
    return s;
  }

  function esc(t) {
    return String(t == null ? "" : t)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  // Question text is authored by us, not user input — escape first, then let
  // renderMath reintroduce the small set of tags it emits.
  function fmt(t) { return renderMath(esc(t)); }

  // ------------------------------------------------------------ state --
  var DOMAINS = [];
  var state = null;
  var app = document.getElementById("app");
  var barStat = document.getElementById("bar-stat");

  function collectDomains() {
    var out = [];
    for (var k in window) {
      if (k.indexOf("SAT_DRILL_") !== 0) continue;
      var d = window[k];
      if (d && d.id && Array.isArray(d.skills) && d.skills.length) out.push(d);
    }
    // Weak spots first, then math, then R&W — matches the study priority.
    out.sort(function (a, b) {
      var aw = WEAK_SPOTS.indexOf(a.id) >= 0 ? 0 : 1;
      var bw = WEAK_SPOTS.indexOf(b.id) >= 0 ? 0 : 1;
      if (aw !== bw) return aw - bw;
      if (a.domain !== b.domain) return a.domain === "math" ? -1 : 1;
      return a.title.localeCompare(b.title);
    });
    return out;
  }

  function freshState() {
    return {
      screen: "home",
      domainId: null,
      queue: [],          // skill indexes still to do
      skillIdx: null,
      level: 0,
      attempts: 0,        // wrong attempts at the current rung
      failedSkills: {},   // skillId -> true (bottomed out at least once)
      picked: null,
      phase: "asking",    // asking | hint | revealed
      log: [],            // every answered rung, for the session doc
      mastery: {}         // "domainId:skillId" -> "mastered" | "shaky" | "gap"
    };
  }

  function load() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (raw) {
        var s = JSON.parse(raw);
        if (s && s.mastery) return s;
      }
    } catch (e) { /* corrupt or unavailable storage — start clean */ }
    return freshState();
  }
  function save() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch (e) { /* quota */ }
  }

  function domainById(id) {
    for (var i = 0; i < DOMAINS.length; i++) if (DOMAINS[i].id === id) return DOMAINS[i];
    return null;
  }
  function curDomain() { return domainById(state.domainId); }
  function curSkill() {
    var d = curDomain();
    return d && state.skillIdx != null ? d.skills[state.skillIdx] : null;
  }
  function rungAt(skill, level) {
    for (var i = 0; i < skill.rungs.length; i++) if (skill.rungs[i].level === level) return skill.rungs[i];
    return null;
  }
  function levelsOf(skill) {
    return skill.rungs.map(function (r) { return r.level; }).sort(function (a, b) { return a - b; });
  }
  function curRung() {
    var sk = curSkill();
    if (!sk) return null;
    return rungAt(sk, state.level) || rungAt(sk, 0) || sk.rungs[0];
  }

  // ------------------------------------------------------------ views --
  function render() {
    if (state.screen === "home") return renderHome();
    if (state.screen === "drill") return renderDrill();
    if (state.screen === "results") return renderResults();
    renderHome();
  }

  function domainProgress(d) {
    var total = d.skills.length, done = 0;
    for (var i = 0; i < d.skills.length; i++) {
      if (state.mastery[d.id + ":" + d.skills[i].id] === "mastered") done++;
    }
    return { done: done, total: total, pct: total ? Math.round(done / total * 100) : 0 };
  }

  function renderHome() {
    barStat.textContent = "";
    var mathCards = "", rwCards = "";
    DOMAINS.forEach(function (d) {
      var p = domainProgress(d);
      var weak = WEAK_SPOTS.indexOf(d.id) >= 0;
      var rungs = d.skills.reduce(function (n, s) { return n + s.rungs.length; }, 0);
      var html =
        '<div class="card' + (weak ? " weak" : "") + '" data-domain="' + esc(d.id) + '">' +
          '<div class="name">' + esc(d.title.replace(/^(Math|R&W) — /, "")) +
            (weak ? '<span class="weak-tag">weak spot</span>' : "") + "</div>" +
          '<div class="meta">' + d.skills.length + " skills · " + rungs + " questions · " +
            p.done + "/" + p.total + " mastered</div>" +
          '<div class="bar-track"><div class="bar-fill" style="width:' + p.pct + '%"></div></div>' +
        "</div>";
      if (d.domain === "math") mathCards += html; else rwCards += html;
    });

    var loaded = DOMAINS.length;
    app.innerHTML =
      '<h2 class="page-title">Adaptive Drill</h2>' +
      '<p class="lede">Every skill is a ladder. You start at real SAT difficulty. Get it wrong and ' +
        'you drop to a simpler version of the same skill, then to the concept underneath it — ' +
        'the drill keeps going down until it finds the rung you actually know, then climbs back up. ' +
        'Skills you bottom out on come back later in the session.</p>' +
      (loaded === 0
        ? '<div class="ladder-note">No question banks have loaded yet. If the drill was just rebuilt, ' +
          'hard-refresh this page (Ctrl+Shift+R).</div>'
        : (mathCards ? '<div class="sec-title">Math</div><div class="grid">' + mathCards + "</div>" : "") +
          (rwCards ? '<div class="sec-title">Reading &amp; Writing</div><div class="grid">' + rwCards + "</div>" : "")) +
      (state.log.length
        ? '<div class="btn-row"><button class="btn ghost" id="see-results">See this session (' +
          state.log.length + " answered)</button></div>"
        : "");

    Array.prototype.forEach.call(app.querySelectorAll(".card"), function (el) {
      el.onclick = function () { startDomain(el.getAttribute("data-domain")); };
    });
    var sr = document.getElementById("see-results");
    if (sr) sr.onclick = function () { state.screen = "results"; save(); render(); };
  }

  var LEVEL_LABEL = {
    "1": ["lv1", "Stretch — harder than the real test"],
    "0": ["lv0", "Real SAT difficulty"],
    "-1": ["lvm1", "Simplified — same skill, stripped down"],
    "-2": ["lvm2", "Foundations — the concept underneath"]
  };

  function renderDrill() {
    var d = curDomain(), sk = curSkill(), rung = curRung();
    if (!sk || !rung) { state.screen = "results"; save(); return render(); }

    var lvl = LEVEL_LABEL[String(rung.level)] || ["lv0", "Level " + rung.level];
    var doneCount = d.skills.length - state.queue.length - 1;
    barStat.textContent = d.title.replace(/^(Math|R&W) — /, "") + " · skill " +
      Math.max(1, doneCount + 1) + " of " + d.skills.length;

    // A dropped rung gets a short framing line so the change in difficulty
    // reads as deliberate rather than as the app glitching.
    var note = "";
    if (state.ladderNote) note = '<div class="ladder-note">' + esc(state.ladderNote) + "</div>";

    var body =
      '<div class="drill-head">' +
        '<span class="skill-code">' + esc(sk.id) + "</span>" +
        '<span class="skill-name">' + esc(sk.name) + "</span>" +
        '<span class="level-chip ' + lvl[0] + '">' + esc(lvl[1]) + "</span>" +
      "</div>" + note +
      '<div class="qbox">' +
        '<div class="qprompt">' + promptHtml(rung.prompt) + "</div>";

    if (rung.choices) {
      body += '<div class="choices">';
      rung.choices.forEach(function (c, i) {
        var cls = "choice";
        if (state.phase === "revealed") {
          if (i === rung.answer) cls += " correct";
          else if (i === state.picked) cls += " wrong";
        } else if (i === state.picked) cls += " sel";
        body += '<button class="' + cls + '" data-i="' + i + '"' +
          (state.phase === "revealed" ? " disabled" : "") + ">" +
          '<span class="ltr">' + "ABCD"[i] + "</span><span>" + fmt(c) + "</span></button>";
      });
      body += "</div>";
    } else {
      body += '<div class="gridin-row"><input id="gridin" placeholder="Your answer" ' +
        (state.phase === "revealed" ? "disabled " : "") +
        'value="' + esc(state.picked == null ? "" : state.picked) + '"></div>';
    }

    // feedback area
    if (state.phase === "hint") {
      body += '<div class="feedback hint"><h4>Not quite — try again</h4><div>' +
        fmt(rung.hint || "Re-read the question and check each choice against the method.") + "</div></div>";
    } else if (state.phase === "revealed") {
      var right = isCorrect(rung, state.picked);
      body += '<div class="feedback ' + (right ? "right" : "wrongfb") + '">' +
        "<h4>" + (right ? "Correct" : "Answer: " + answerLabel(rung)) + "</h4>" +
        '<div class="explain">' + fmt(rung.explain) + "</div></div>";
      if (rung.desmos) {
        body += '<div class="desmos-tip"><b>Faster in Desmos:</b> ' + fmt(rung.desmos) + "</div>";
      }
    }
    body += "</div>";

    body += '<div class="btn-row">';
    if (state.phase === "revealed") {
      body += '<button class="btn" id="next">Continue</button>';
    } else {
      body += '<button class="btn" id="submit"' +
        (state.picked == null || state.picked === "" ? " disabled" : "") + ">Submit</button>";
    }
    body += '<button class="btn ghost" id="quit">End session</button></div>';

    app.innerHTML = body;
    wireDrill(rung);
  }

  function promptHtml(p) {
    // A blank line separates an R&W passage from the question stem.
    var parts = String(p).split(/\n\s*\n/);
    if (parts.length > 1) {
      return '<span class="passage">' + fmt(parts.slice(0, -1).join("\n\n")) + "</span>" +
        fmt(parts[parts.length - 1]);
    }
    return fmt(p);
  }

  function answerLabel(rung) {
    if (!rung.choices) return String(rung.answer);
    return "ABCD"[rung.answer] || String(rung.answer);
  }

  function isCorrect(rung, picked) {
    if (picked == null) return false;
    if (rung.choices) return picked === rung.answer;
    return normGridin(picked) === normGridin(rung.answer);
  }
  function normGridin(v) {
    return String(v).trim().replace(/\s+/g, "").replace(/^\+/, "");
  }

  function wireDrill(rung) {
    Array.prototype.forEach.call(app.querySelectorAll(".choice"), function (el) {
      el.onclick = function () {
        if (state.phase === "revealed") return;
        state.picked = parseInt(el.getAttribute("data-i"), 10);
        save(); render();
      };
    });
    var gi = document.getElementById("gridin");
    if (gi) {
      gi.oninput = function () {
        state.picked = gi.value;
        var sb = document.getElementById("submit");
        if (sb) sb.disabled = !gi.value.trim();
      };
      gi.onkeydown = function (e) { if (e.key === "Enter") submitAnswer(rung); };
    }
    var sb = document.getElementById("submit");
    if (sb) sb.onclick = function () { submitAnswer(rung); };
    var nx = document.getElementById("next");
    if (nx) nx.onclick = function () { advance(rung); };
    var q = document.getElementById("quit");
    if (q) q.onclick = function () { state.screen = "results"; save(); render(); };
  }

  // ----------------------------------------------------------- engine --
  function startDomain(id) {
    var d = domainById(id);
    if (!d) return;
    state.domainId = id;
    state.queue = d.skills.map(function (_, i) { return i; });
    state.failedSkills = {};
    state.screen = "drill";
    nextSkill(true);
  }

  function nextSkill(initial) {
    if (!state.queue.length) { state.screen = "results"; save(); return render(); }
    state.skillIdx = state.queue.shift();
    state.level = 0;
    state.attempts = 0;
    state.picked = null;
    state.phase = "asking";
    state.ladderNote = initial ? "" : "";
    save(); render();
  }

  function submitAnswer(rung) {
    if (state.picked == null || state.picked === "") return;
    var right = isCorrect(rung, state.picked);
    if (!right && state.attempts === 0 && rung.hint && state.phase === "asking") {
      // One nudge before revealing — a hint often recovers the question
      // without needing to drop a rung.
      state.attempts = 1;
      state.phase = "hint";
      save(); render();
      return;
    }
    state.phase = "revealed";
    var sk = curSkill();
    state.log.push({
      domain: curDomain().title,
      skillId: sk.id,
      skillName: sk.name,
      level: rung.level,
      prompt: rung.prompt,
      picked: rung.choices ? (rung.choices[state.picked] || "(none)") : String(state.picked),
      correctAnswer: rung.choices ? rung.choices[rung.answer] : String(rung.answer),
      correct: right,
      usedHint: state.attempts > 0
    });
    save(); render();
  }

  function advance(rung) {
    var sk = curSkill();
    var key = state.domainId + ":" + sk.id;
    var right = isCorrect(rung, state.picked);
    var levels = levelsOf(sk);
    var maxL = levels[levels.length - 1];
    var minL = levels[0];

    state.picked = null;
    state.phase = "asking";
    state.attempts = 0;
    state.ladderNote = "";

    if (right) {
      if (state.level >= maxL) {
        // Cleared the top rung — skill is done for this session.
        state.mastery[key] = state.failedSkills[sk.id] ? "shaky" : "mastered";
        save();
        return nextSkill(false);
      }
      // Climb to the next level up that actually exists.
      var up = levels.filter(function (l) { return l > state.level; })[0];
      state.level = up;
      state.ladderNote = "Got it. Stepping back up — this one is harder.";
      save(); return render();
    }

    // Wrong, after the hint and the explanation.
    if (state.level > minL) {
      var down = levels.filter(function (l) { return l < state.level; }).pop();
      state.level = down;
      state.ladderNote = down <= -2
        ? "Dropping to the concept underneath this skill. If this one clicks, the gap is upstream of the question, not in the question."
        : "Dropping a rung — same skill, simpler version. Rebuild it here and we climb back.";
      save(); return render();
    }

    // Bottomed out. Requeue the skill so it comes back later this session
    // rather than being silently abandoned.
    state.mastery[key] = "gap";
    if (!state.failedSkills[sk.id]) {
      state.failedSkills[sk.id] = true;
      state.queue.push(state.skillIdx);
      state.ladderNote = "";
      save();
      return nextSkill(false);
    }
    save();
    return nextSkill(false);
  }

  // ---------------------------------------------------------- results --
  function renderResults() {
    barStat.textContent = "";
    var total = state.log.length;
    var right = state.log.filter(function (l) { return l.correct; }).length;

    var gaps = [], shaky = [], mastered = [];
    for (var k in state.mastery) {
      var parts = k.split(":");
      var d = domainById(parts[0]);
      if (!d) continue;
      var sk = null;
      for (var i = 0; i < d.skills.length; i++) if (d.skills[i].id === parts[1]) sk = d.skills[i];
      if (!sk) continue;
      var entry = sk.id + " — " + sk.name;
      if (state.mastery[k] === "gap") gaps.push(entry);
      else if (state.mastery[k] === "shaky") shaky.push(entry);
      else mastered.push(entry);
    }

    function list(title, arr, cls) {
      if (!arr.length) return "";
      return '<div class="sec-title">' + title + "</div>" +
        arr.map(function (e) {
          return '<div class="res-line"><span class="lbl">' + esc(e) +
            '</span><span class="val ' + cls + '">' + title.split(" ")[0] + "</span></div>";
        }).join("");
    }

    app.innerHTML =
      '<h2 class="page-title">Session summary</h2>' +
      '<p class="lede">' + right + " correct out of " + total + " answered" +
        (total ? " (" + Math.round(right / total * 100) + "%)" : "") +
        ". Rungs below level 0 are scaffolding, not SAT-level questions — a low percentage here " +
        "mostly means the ladder did its job and dug down.</p>" +
      list("Gaps — bottomed out", gaps, "bad") +
      list("Shaky — recovered after dropping", shaky, "") +
      list("Mastered — cleared the stretch rung", mastered, "good") +
      '<div class="qlog" id="export-status">Export this session — plus every question you asked ' +
        'the tutor — into a single review doc in your vault, so you can read it before the test.</div>' +
      '<div class="btn-row">' +
        '<button class="btn" id="export">Export review doc to vault</button>' +
        '<button class="btn ghost" id="home">Back to drills</button>' +
      "</div>";

    document.getElementById("home").onclick = function () {
      state.screen = "home"; save(); render();
    };
    document.getElementById("export").onclick = exportDoc;
  }

  function exportDoc() {
    var btn = document.getElementById("export");
    var status = document.getElementById("export-status");
    btn.disabled = true;
    status.textContent = "Writing…";
    fetch("/api/sat-drill/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ log: state.log, mastery: state.mastery })
    }).then(function (r) {
      return r.json().then(function (j) { return { ok: r.ok, j: j }; });
    }).then(function (res) {
      if (!res.ok) throw new Error(res.j.detail || "export failed");
      status.textContent = "Written to " + res.j.path + " — open it in Obsidian.";
      btn.disabled = false;
    }).catch(function (e) {
      status.textContent = "Export failed: " + e.message;
      btn.disabled = false;
    });
  }

  // ------------------------------------------------------------- boot --
  DOMAINS = collectDomains();
  state = load();
  if (state.screen === "drill" && !curDomain()) state = freshState();
  render();
})();
