/* ═══════════════════════════════════════════════════════════════
   VITAC Benchmark Viewer
   ═══════════════════════════════════════════════════════════════
   Views:
     #/                          Dashboard
     #/runs                      All runs
     #/run/:id                   Single run detail
     #/trace/:run/:task/:trial   Trace playback
   ═══════════════════════════════════════════════════════════════ */

const $app = document.getElementById("app");

// ── State ──────────────────────────────────────────────────────

const state = {
  runsSort: { key: "accuracy", dir: "desc" },
  runsSearch: "",
  runDetailFilter: "all",   // all | pass | fail
  expandedTrials: {},        // index -> bool
  playbackSpeed: 1,
  // activeMsg tracked locally inside setupTraceAudio
};

// ── API ────────────────────────────────────────────────────────

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ── Router ─────────────────────────────────────────────────────

function currentRoute() {
  return (window.location.hash || "#/").slice(1);
}

function route() {
  const path = currentRoute();

  document.querySelectorAll(".nav-link").forEach((el) => {
    el.classList.remove("active");
    if (el.dataset.view === "dashboard" && (path === "/" || path === "")) el.classList.add("active");
    if (el.dataset.view === "runs" && (path.startsWith("/runs") || path.startsWith("/run") || path.startsWith("/trace"))) el.classList.add("active");
  });

  // Reset per-view state
  state.runDetailFilter = "all";
  state.expandedTrials = {};
  state.activeMsg = -1;

  if (path === "/" || path === "") return viewDashboard();
  if (path === "/runs") return viewRuns();

  let m;
  if ((m = path.match(/^\/run\/([^/]+)$/))) return viewRunDetail(decodeURIComponent(m[1]));
  if ((m = path.match(/^\/trace\/([^/]+)\/([^/]+)\/(.+)$/)))
    return viewTrace(decodeURIComponent(m[1]), decodeURIComponent(m[2]), decodeURIComponent(m[3]));

  $app.innerHTML = `<div class="empty">Page not found</div>`;
}

window.addEventListener("hashchange", route);
window.addEventListener("DOMContentLoaded", route);

// ── Utilities ──────────────────────────────────────────────────

function esc(s) {
  if (s == null) return "";
  const d = document.createElement("div");
  d.textContent = String(s);
  return d.innerHTML;
}

function fmtDur(startStr, endStr) {
  if (!startStr || !endStr) return "-";
  const ms = new Date(endStr) - new Date(startStr);
  if (isNaN(ms) || ms < 0) return "-";
  const s = Math.round(ms / 1000);
  return s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`;
}

function fmtSec(sec) {
  if (!sec || sec < 0) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function pct(n, d) {
  return d > 0 ? (100 * n / d).toFixed(1) : "0.0";
}

function diffBadge(diff) {
  const c = { easy: "badge-easy", medium: "badge-medium", hard: "badge-hard" }[diff] || "";
  return c ? `<span class="badge ${c}">${esc(diff)}</span>` : esc(diff || "-");
}

function statusBadge(resolved) {
  return resolved
    ? `<span class="badge badge-pass">PASS</span>`
    : `<span class="badge badge-fail">FAIL</span>`;
}

function failBadge(mode) {
  if (!mode || mode === "none" || mode === "unset") return "";
  const cls = (mode === "agent_timeout" || mode === "test_timeout") ? "badge-timeout" : "badge-fail";
  return `<span class="badge ${cls}">${esc(mode)}</span>`;
}

function sortArrow(currentKey, key, dir) {
  if (currentKey !== key) return "";
  return `<span class="sort-arrow">${dir === "asc" ? "\u25B2" : "\u25BC"}</span>`;
}

function barColor(ratio) {
  if (ratio >= 0.8) return "var(--green)";
  if (ratio >= 0.4) return "var(--yellow)";
  return "var(--red)";
}

// ── View: Dashboard ────────────────────────────────────────────

async function viewDashboard() {
  $app.innerHTML = `<div class="loading">Loading</div>`;
  try {
    const [agg, runs] = await Promise.all([api("/api/aggregate"), api("/api/runs")]);

    const systems = agg.systems || [];
    const tasks = agg.tasks || {};
    const meta = agg.task_meta || {};
    const taskIds = Object.keys(tasks).sort();

    // Compute totals
    let totalTrials = 0, totalPassed = 0;
    const sysStats = {}; // system -> { passed, total }
    for (const sys of systems) sysStats[sys] = { passed: 0, total: 0 };

    for (const tid of taskIds) {
      for (const sys of systems) {
        const c = (tasks[tid] || {})[sys];
        if (!c) continue;
        totalTrials += c.total;
        totalPassed += c.passed;
        sysStats[sys].total += c.total;
        sysStats[sys].passed += c.passed;
      }
    }

    // Sort systems by accuracy descending
    const sortedSystems = [...systems].sort((a, b) => {
      const ra = sysStats[a].total ? sysStats[a].passed / sysStats[a].total : 0;
      const rb = sysStats[b].total ? sysStats[b].passed / sysStats[b].total : 0;
      return rb - ra;
    });

    let html = `<h1>Dashboard</h1>`;

    // Stats row
    html += `
      <div class="stats">
        <div class="stat"><div class="stat-label">Runs</div><div class="stat-value">${runs.length}</div></div>
        <div class="stat"><div class="stat-label">Total Trials</div><div class="stat-value">${totalTrials}</div></div>
        <div class="stat"><div class="stat-label">Passed</div><div class="stat-value" style="color:var(--green)">${totalPassed}</div></div>
        <div class="stat"><div class="stat-label">Failed</div><div class="stat-value" style="color:var(--red)">${totalTrials - totalPassed}</div></div>
        <div class="stat"><div class="stat-label">Pass Rate</div><div class="stat-value">${pct(totalPassed, totalTrials)}%</div></div>
      </div>
    `;

    // System leaderboard
    if (sortedSystems.length > 0) {
      html += `<div class="card"><h2>System Leaderboard</h2><div class="leaderboard">`;
      for (const sys of sortedSystems) {
        const s = sysStats[sys];
        const ratio = s.total ? s.passed / s.total : 0;
        html += `
          <div class="lb-row">
            <div class="lb-name">${esc(sys)}</div>
            <div class="lb-bar-wrap"><div class="lb-bar" style="width:${(100 * ratio).toFixed(1)}%;background:${barColor(ratio)}"></div></div>
            <div class="lb-pct" style="color:${barColor(ratio)}">${pct(s.passed, s.total)}%</div>
            <div class="lb-count">${s.passed}/${s.total}</div>
          </div>
        `;
      }
      html += `</div></div>`;
    }

    // Matrix: tasks (rows) x systems (columns)
    if (taskIds.length > 0) {
      // Group tasks by difficulty
      const byDiff = { easy: [], medium: [], hard: [], unknown: [] };
      for (const tid of taskIds) {
        const d = (meta[tid] || {}).difficulty || "unknown";
        (byDiff[d] || byDiff.unknown).push(tid);
      }
      const orderedTasks = [...byDiff.easy, ...byDiff.medium, ...byDiff.hard, ...byDiff.unknown];

      html += `<div class="card" style="overflow-x:auto"><h2>Pass / Fail Matrix</h2><table style="width:auto;min-width:0">`;
      html += `<thead><tr><th>Task</th><th>Difficulty</th>`;
      for (const sys of sortedSystems) {
        // Shorten system name for column header
        const short = sys.replace("-voice", "");
        html += `<th style="text-align:center;min-width:80px" title="${esc(sys)}">${esc(short)}</th>`;
      }
      html += `<th style="text-align:center">Total</th></tr></thead><tbody>`;

      for (const tid of orderedTasks) {
        let rowP = 0, rowT = 0;
        html += `<tr><td><code>${esc(tid)}</code></td>`;
        html += `<td>${diffBadge((meta[tid] || {}).difficulty)}</td>`;

        for (const sys of sortedSystems) {
          const c = (tasks[tid] || {})[sys];
          if (!c) {
            html += `<td class="heatmap heatmap-na">-</td>`;
            continue;
          }
          rowP += c.passed;
          rowT += c.total;
          const cls = c.passed === c.total ? "heatmap-100" : c.passed === 0 ? "heatmap-0" : "heatmap-partial";
          html += `<td class="heatmap ${cls}">${c.passed}/${c.total}</td>`;
        }

        const totalCls = rowP === rowT ? "heatmap-100" : rowP === 0 ? "heatmap-0" : "heatmap-partial";
        html += `<td class="heatmap ${totalCls}">${rowP}/${rowT}</td></tr>`;
      }

      html += `</tbody></table></div>`;
    } else {
      html += `<div class="empty">No results data found. Run benchmarks first.</div>`;
    }

    $app.innerHTML = html;
  } catch (err) {
    $app.innerHTML = `<div class="empty">Error: ${esc(err.message)}<br><button class="filter-btn" style="margin-top:0.75rem" onclick="viewDashboard()">Retry</button></div>`;
  }
}

// ── View: Runs ─────────────────────────────────────────────────

let _runsData = null;

async function viewRuns() {
  $app.innerHTML = `<div class="loading">Loading</div>`;
  try {
    _runsData = await api("/api/runs");
    renderRuns();
  } catch (err) {
    $app.innerHTML = `<div class="empty">Error: ${esc(err.message)}<br><button class="filter-btn" style="margin-top:0.75rem" onclick="viewRuns()">Retry</button></div>`;
  }
}

function renderRuns() {
  const runs = _runsData || [];
  if (runs.length === 0) {
    $app.innerHTML = `<h1>Runs</h1><div class="empty">No benchmark runs found.</div>`;
    return;
  }

  // Filter
  const q = state.runsSearch.toLowerCase();
  let filtered = runs;
  if (q) {
    filtered = runs.filter(r =>
      r.run_id.toLowerCase().includes(q) || r.system.toLowerCase().includes(q)
    );
  }

  // Sort
  const { key, dir } = state.runsSort;
  filtered.sort((a, b) => {
    let va = a[key], vb = b[key];
    if (typeof va === "string") { va = va.toLowerCase(); vb = (vb || "").toLowerCase(); }
    if (va < vb) return dir === "asc" ? -1 : 1;
    if (va > vb) return dir === "asc" ? 1 : -1;
    return 0;
  });

  let html = `<h1>Runs</h1>`;
  html += `<div class="toolbar">
    <input class="search-input" id="runs-search" type="text" placeholder="Filter by run ID or system..." value="${esc(state.runsSearch)}">
  </div>`;

  html += `<div class="card"><table><thead><tr>
    <th class="sortable" data-sort="run_id">Run ID ${sortArrow(key, "run_id", dir)}</th>
    <th class="sortable" data-sort="system">System ${sortArrow(key, "system", dir)}</th>
    <th class="sortable" data-sort="n_total">Tasks ${sortArrow(key, "n_total", dir)}</th>
    <th class="sortable" data-sort="n_resolved">Resolved ${sortArrow(key, "n_resolved", dir)}</th>
    <th class="sortable" data-sort="accuracy">Accuracy ${sortArrow(key, "accuracy", dir)}</th>
  </tr></thead><tbody>`;

  for (const r of filtered) {
    const ratio = r.n_total ? r.n_resolved / r.n_total : 0;
    html += `
      <tr class="clickable" data-href="#/run/${encodeURIComponent(r.run_id)}">
        <td><code>${esc(r.run_id)}</code></td>
        <td><span class="badge badge-system">${esc(r.system)}</span></td>
        <td>${r.n_total}</td>
        <td>${r.n_resolved}/${r.n_total}</td>
        <td>
          <div class="accuracy-bar-wrap">
            <div class="accuracy-bar"><div class="accuracy-bar-fill" style="width:${(100 * ratio).toFixed(1)}%;background:${barColor(ratio)}"></div></div>
            <span class="accuracy-pct" style="color:${barColor(ratio)}">${pct(r.n_resolved, r.n_total)}%</span>
          </div>
        </td>
      </tr>
    `;
  }

  html += `</tbody></table></div>`;
  $app.innerHTML = html;

  // Attach events
  document.getElementById("runs-search").addEventListener("input", (e) => {
    const cursorPos = e.target.selectionStart;
    state.runsSearch = e.target.value;
    renderRuns();
    // Refocus and restore cursor to original position
    const input = document.getElementById("runs-search");
    input.focus();
    input.setSelectionRange(cursorPos, cursorPos);
  });

  $app.querySelectorAll("th.sortable").forEach(th => {
    th.addEventListener("click", () => {
      const k = th.dataset.sort;
      if (state.runsSort.key === k) {
        state.runsSort.dir = state.runsSort.dir === "asc" ? "desc" : "asc";
      } else {
        state.runsSort = { key: k, dir: k === "accuracy" || k === "n_resolved" ? "desc" : "asc" };
      }
      renderRuns();
    });
  });

  $app.querySelectorAll("tr.clickable").forEach(tr => {
    tr.addEventListener("click", () => { location.hash = tr.dataset.href; });
  });
}

// ── View: Run Detail ───────────────────────────────────────────

let _runDetailData = null;
let _runDetailId = null;

async function viewRunDetail(runId) {
  $app.innerHTML = `<div class="loading">Loading</div>`;
  try {
    _runDetailData = await api(`/api/runs/${encodeURIComponent(runId)}`);
    _runDetailId = runId;
    renderRunDetail();
  } catch (err) {
    $app.innerHTML = `<div class="empty">Error: ${esc(err.message)}<br><button class="filter-btn retry-btn" style="margin-top:0.75rem">Retry</button></div>`;
    $app.querySelector(".retry-btn").addEventListener("click", () => viewRunDetail(runId));
  }
}

function renderRunDetail() {
  const data = _runDetailData;
  const runId = _runDetailId;
  const trials = data.results || [];

  const nPass = trials.filter(t => t.is_resolved).length;
  const nFail = trials.length - nPass;
  const f = state.runDetailFilter;

  const filtered = f === "all" ? trials
    : f === "pass" ? trials.filter(t => t.is_resolved)
    : trials.filter(t => !t.is_resolved);

  let html = `
    <div class="breadcrumb">
      <a href="#/runs">Runs</a><span class="sep">/</span><span>${esc(runId)}</span>
    </div>
    <h1>${esc(runId)}</h1>
    <p style="color:var(--text-dim);margin-bottom:1rem;font-size:0.85rem">
      System: <span class="badge badge-system">${esc(data.system || "unknown")}</span>
      &mdash; ${trials.length} trial(s), ${nPass} passed, ${nFail} failed
      (${pct(nPass, trials.length)}%)
    </p>
  `;

  // Filter bar
  html += `<div class="toolbar">
    <button class="filter-btn ${f === "all" ? "active" : ""}" data-filter="all">All (${trials.length})</button>
    <button class="filter-btn ${f === "pass" ? "active" : ""}" data-filter="pass">Passed (${nPass})</button>
    <button class="filter-btn ${f === "fail" ? "active" : ""}" data-filter="fail">Failed (${nFail})</button>
  </div>`;

  html += `<div class="card"><table><thead><tr>
    <th></th>
    <th>Task</th>
    <th>Status</th>
    <th>Failure Mode</th>
    <th>Duration</th>
    <th>Trace</th>
  </tr></thead><tbody>`;

  filtered.forEach((t, i) => {
    const dur = fmtDur(t.trial_started_at, t.trial_ended_at);
    const hasTests = t.parser_results && Object.keys(t.parser_results).length > 0;
    const expanded = !!state.expandedTrials[i];
    const traceHref = t.has_trace
      ? `#/trace/${encodeURIComponent(runId)}/${encodeURIComponent(t.task_id)}/${encodeURIComponent(t.trial_name)}`
      : null;

    html += `
      <tr class="${hasTests ? "clickable" : ""}" data-expand="${i}">
        <td style="width:1.5rem;color:var(--text-dim);font-size:0.7rem">${hasTests ? (expanded ? "\u25BC" : "\u25B6") : ""}</td>
        <td><code>${esc(t.task_id)}</code></td>
        <td>${statusBadge(t.is_resolved)}</td>
        <td>${failBadge(t.failure_mode)}</td>
        <td style="font-family:var(--mono)">${dur}</td>
        <td>${traceHref
          ? `<a href="${traceHref}" onclick="event.stopPropagation()">View trace${t.has_audio ? " + audio" : ""}</a>`
          : `<span style="color:var(--text-dim)">-</span>`}</td>
      </tr>
    `;

    // Expandable test results row
    if (hasTests) {
      html += `<tr class="trial-detail-row ${expanded ? "" : "hidden"}" data-detail="${i}"><td colspan="6"><div class="trial-detail-content">`;
      html += `<ul class="test-list">`;
      for (const [name, status] of Object.entries(t.parser_results)) {
        const cls = status === "passed" ? "cell-pass" : "cell-fail";
        html += `<li><span class="test-name" title="${esc(name)}">${esc(name)}</span><span class="${cls}">${esc(status)}</span></li>`;
      }
      html += `</ul></div></td></tr>`;
    }
  });

  html += `</tbody></table></div>`;
  $app.innerHTML = html;

  // Attach events: expand/collapse
  $app.querySelectorAll("tr[data-expand]").forEach(tr => {
    tr.addEventListener("click", (e) => {
      // Don't expand if clicking a link
      if (e.target.closest("a")) return;
      const idx = tr.dataset.expand;
      state.expandedTrials[idx] = !state.expandedTrials[idx];
      renderRunDetail();
    });
  });

  // Filter buttons
  $app.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      state.runDetailFilter = btn.dataset.filter;
      state.expandedTrials = {};
      renderRunDetail();
    });
  });
}

// ── View: Trace ────────────────────────────────────────────────

async function viewTrace(runId, taskId, trialName) {
  $app.innerHTML = `<div class="loading">Loading trace</div>`;
  try {
    const data = await api(
      `/api/runs/${encodeURIComponent(runId)}/${encodeURIComponent(taskId)}/${encodeURIComponent(trialName)}/trace`
    );
    renderTrace(runId, taskId, trialName, data);
  } catch (err) {
    $app.innerHTML = `<div class="empty">Error: ${esc(err.message)}<br><button class="filter-btn retry-btn" style="margin-top:0.75rem">Retry</button></div>`;
    $app.querySelector(".retry-btn").addEventListener("click", () => viewTrace(runId, taskId, trialName));
  }
}

function renderTrace(runId, taskId, trialName, data) {
  const trace = data.trace || {};
  const trial = data.trial_results || {};
  const taskDef = data.task_def || {};
  const hasAudio = data.has_audio;
  const messages = trace.voiceMessages || [];
  const timeline = data.timeline || [];
  const totalDuration = data.total_audio_duration || 0;

  function audioUrl(filename) {
    if (!hasAudio || !filename) return null;
    return `/api/audio/${encodeURIComponent(runId)}/${encodeURIComponent(taskId)}/${encodeURIComponent(trialName)}/${encodeURIComponent(filename)}`;
  }

  const fullAudioUrl = `/api/audio/${encodeURIComponent(runId)}/${encodeURIComponent(taskId)}/${encodeURIComponent(trialName)}/full`;

  let html = `
    <div class="breadcrumb">
      <a href="#/runs">Runs</a><span class="sep">/</span>
      <a href="#/run/${encodeURIComponent(runId)}">${esc(runId)}</a><span class="sep">/</span>
      <span>${esc(taskId)}</span>
    </div>
  `;

  // ── Audio player (above the two-column layout) ──
  if (hasAudio && messages.some(m => m.audioFilename) && totalDuration > 0) {
    html += `
      <div class="card player-card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;flex-wrap:wrap;gap:0.4rem">
          <h2 style="margin:0">Conversation Playback</h2>
          <div class="speed-controls">
            <span class="speed-label">Speed:</span>
            <button class="speed-btn ${state.playbackSpeed === 0.5 ? "active" : ""}" data-speed="0.5">0.5x</button>
            <button class="speed-btn ${state.playbackSpeed === 1 ? "active" : ""}" data-speed="1">1x</button>
            <button class="speed-btn ${state.playbackSpeed === 1.5 ? "active" : ""}" data-speed="1.5">1.5x</button>
            <button class="speed-btn ${state.playbackSpeed === 2 ? "active" : ""}" data-speed="2">2x</button>
            <button class="speed-btn ${state.playbackSpeed === 3 ? "active" : ""}" data-speed="3">3x</button>
          </div>
        </div>
        <div class="player-controls">
          <button class="play-btn" id="play-btn" title="Play/Pause (Space)">&#9654;</button>
          <div class="timeline-bar" id="timeline-bar">
            ${timeline.map((seg, i) => {
              const left = totalDuration > 0 ? (100 * seg.start / totalDuration) : 0;
              const width = totalDuration > 0 ? (100 * seg.duration / totalDuration) : 0;
              return `<div class="timeline-segment ${seg.sender}" data-idx="${i}" style="left:${left.toFixed(2)}%;width:${Math.max(width, 0.3).toFixed(2)}%" title="Message ${i + 1} (${seg.sender})"></div>`;
            }).join("")}
            <div class="timeline-playhead" id="playhead" style="left:0"></div>
          </div>
          <div class="player-time"><span id="cur-time">0:00</span> / <span id="tot-time">${fmtSec(totalDuration)}</span></div>
        </div>
        <audio id="full-audio" preload="metadata" src="${fullAudioUrl}"></audio>
        <div class="kbd-hint"><kbd>Space</kbd> play/pause &nbsp; <kbd>\u2190</kbd><kbd>\u2192</kbd> skip 5s &nbsp; <kbd>\u2191</kbd><kbd>\u2193</kbd> prev/next message</div>
      </div>
    `;
  }

  html += `<div class="trace-layout">`;

  // ── Chat column ──
  html += `<div>`;
  html += `<h2>${esc(taskId)} &mdash; ${messages.length} message${messages.length !== 1 ? "s" : ""}</h2>`;

  if (messages.length === 0) {
    html += `<div class="empty">No voice messages recorded.</div>`;
  } else {
    html += `<div class="chat" id="chat">`;
    const t0 = messages[0].timestampMs || 0;
    messages.forEach((msg, i) => {
      const side = msg.sender === "primary" ? "primary" : "collaborator";
      const label = msg.sender === "primary" ? "Primary" : "Collaborator";
      const elapsed = msg.timestampMs ? ((msg.timestampMs - t0) / 1000).toFixed(1) : "?";
      const url = audioUrl(msg.audioFilename);

      html += `
        <div class="msg ${side}" id="msg-${i}" data-msg-idx="${i}">
          <div class="msg-header">
            <span class="msg-sender">${label}</span>
            <span class="msg-time">#${i + 1} &middot; +${elapsed}s${msg.duration_sec ? ` &middot; ${msg.duration_sec.toFixed(1)}s` : ""}</span>
          </div>
          <div class="msg-text">${esc(msg.transcript || "[no transcript]")}</div>
          ${url ? `<button class="msg-play-btn" data-msg-idx="${i}" title="Play this message">&#9654; Play</button>` : ""}
        </div>
      `;
    });
    html += `</div>`;
  }
  html += `</div>`;

  // ── Sidebar ──
  html += `<div class="sidebar">`;

  // Trial metadata
  html += `<div class="card"><h3>Trial</h3>`;
  html += metaRow("Status", statusBadge(trial.is_resolved));
  html += metaRow("Failure Mode", failBadge(trial.failure_mode) || "-");
  html += metaRow("Completed", trace.completed ? "Yes" : "No");
  html += metaRow("Messages", messages.length);
  html += metaRow("Agent Duration", fmtDur(trial.agent_started_at, trial.agent_ended_at));
  html += metaRow("Total Duration", fmtDur(trial.trial_started_at, trial.trial_ended_at));
  if (trace.error) {
    html += metaRow("Error", `<span style="color:var(--red);font-size:0.7rem">${esc(trace.error)}</span>`);
  }
  html += `</div>`;

  // Task info
  html += `<div class="card"><h3>Task</h3>`;
  html += metaRow("Difficulty", diffBadge(taskDef.difficulty));
  html += metaRow("Category", esc(taskDef.category || "-"));
  html += metaRow("Transcript", esc(taskDef.transcript_mode || "-"));
  html += `</div>`;

  // Instruction
  const instruction = trial.instruction || taskDef.instruction || "";
  if (instruction) {
    html += `<div class="card"><h3>Instruction</h3><div class="instruction-block">${esc(instruction)}</div></div>`;
  }

  // Collaborator context
  if (taskDef.collaborator_context) {
    html += `<div class="card"><h3>Collaborator Context</h3><div class="instruction-block">${esc(taskDef.collaborator_context)}</div></div>`;
  }

  // Test results
  if (trial.parser_results && Object.keys(trial.parser_results).length > 0) {
    const entries = Object.entries(trial.parser_results);
    const nPass = entries.filter(([, s]) => s === "passed").length;
    html += `<div class="card"><h3>Tests (${nPass}/${entries.length} passed)</h3><ul class="test-list">`;
    for (const [name, status] of entries) {
      const cls = status === "passed" ? "cell-pass" : "cell-fail";
      html += `<li><span class="test-name" title="${esc(name)}">${esc(name)}</span><span class="${cls}">${esc(status)}</span></li>`;
    }
    html += `</ul></div>`;
  }

  // Terminal commands
  const cmds = trace.terminalCommands || [];
  if (cmds.length > 0) {
    html += `<div class="card"><h3>Terminal Commands (${cmds.length})</h3><div class="instruction-block">${cmds.map(c => esc(c)).join("\n")}</div></div>`;
  }

  html += `</div>`; // sidebar
  html += `</div>`; // trace-layout

  $app.innerHTML = html;

  // ── Wire up audio ──
  setupTraceAudio(runId, taskId, trialName, messages, timeline, totalDuration);
}

function metaRow(label, value) {
  return `<div class="meta-row"><span class="meta-label">${label}</span><span class="meta-value">${value}</span></div>`;
}

// ── Audio Controller ───────────────────────────────────────────

function setupTraceAudio(runId, taskId, trialName, messages, timeline, totalDuration) {
  const audio = document.getElementById("full-audio");
  if (!audio) return;

  const playBtn = document.getElementById("play-btn");
  const playhead = document.getElementById("playhead");
  const curTimeEl = document.getElementById("cur-time");
  const totTimeEl = document.getElementById("tot-time");
  const timelineBar = document.getElementById("timeline-bar");
  let activeIdx = -1;

  // Use the actual audio duration when available, fall back to API estimate
  function getDuration() {
    return (audio.duration && isFinite(audio.duration)) ? audio.duration : totalDuration;
  }

  // Set initial speed
  audio.playbackRate = state.playbackSpeed;

  // Update total time display when audio metadata loads
  audio.addEventListener("loadedmetadata", () => {
    totTimeEl.textContent = fmtSec(getDuration());
  });

  // Loading/buffering feedback
  audio.addEventListener("waiting", () => {
    playBtn.classList.add("loading");
    playBtn.innerHTML = "&#8987;";
  });
  audio.addEventListener("canplay", () => {
    playBtn.classList.remove("loading");
    if (!audio.paused) {
      playBtn.innerHTML = "&#9646;&#9646;";
    } else {
      playBtn.innerHTML = "&#9654;";
    }
  });

  // Play/pause
  playBtn.addEventListener("click", togglePlay);

  function togglePlay() {
    if (audio.paused) {
      audio.play().catch(() => {});
      playBtn.innerHTML = "&#9646;&#9646;";
    } else {
      audio.pause();
      playBtn.innerHTML = "&#9654;";
    }
  }

  // Time update -> move playhead + highlight message
  audio.addEventListener("timeupdate", () => {
    const t = audio.currentTime;
    const dur = getDuration();
    if (dur > 0) {
      const pctPos = Math.min(100, 100 * t / dur).toFixed(2);
      playhead.style.left = pctPos + "%";
    }
    curTimeEl.textContent = fmtSec(t);

    // Find active message — scale timeline positions if durations differ
    const scale = (totalDuration > 0 && dur > 0) ? dur / totalDuration : 1;
    let newIdx = -1;
    for (let i = timeline.length - 1; i >= 0; i--) {
      if (t >= timeline[i].start * scale) {
        newIdx = i;
        break;
      }
    }

    if (newIdx !== activeIdx) {
      // Remove old highlight
      if (activeIdx >= 0) {
        const old = document.getElementById(`msg-${activeIdx}`);
        if (old) old.classList.remove("active");
        const oldSeg = timelineBar.querySelector(`.timeline-segment[data-idx="${activeIdx}"]`);
        if (oldSeg) oldSeg.classList.remove("active");
      }
      // Add new highlight
      activeIdx = newIdx;
      if (activeIdx >= 0) {
        const el = document.getElementById(`msg-${activeIdx}`);
        if (el) {
          el.classList.add("active");
          el.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
        const seg = timelineBar.querySelector(`.timeline-segment[data-idx="${activeIdx}"]`);
        if (seg) seg.classList.add("active");
      }
    }
  });

  audio.addEventListener("ended", () => {
    playBtn.innerHTML = "&#9654;";
  });

  // Click on timeline to seek
  timelineBar.addEventListener("click", (e) => {
    const rect = timelineBar.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const dur = getDuration();
    audio.currentTime = Math.min(ratio * dur, dur);
    if (audio.paused) {
      audio.play().catch(() => {});
      playBtn.innerHTML = "&#9646;&#9646;";
    }
  });

  // Speed buttons
  document.querySelectorAll(".speed-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const speed = parseFloat(btn.dataset.speed);
      state.playbackSpeed = speed;
      audio.playbackRate = speed;
      document.querySelectorAll(".speed-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
    });
  });

  // Helper: get scaled start time for a timeline entry
  function scaledStart(idx) {
    const dur = getDuration();
    const scale = (totalDuration > 0 && dur > 0) ? dur / totalDuration : 1;
    return timeline[idx].start * scale;
  }

  // Per-message play buttons: seek full audio to that message's start
  document.querySelectorAll(".msg-play-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const idx = parseInt(btn.dataset.msgIdx);
      if (idx >= 0 && idx < timeline.length) {
        audio.currentTime = scaledStart(idx);
        if (audio.paused) {
          audio.play().catch(() => {});
          playBtn.innerHTML = "&#9646;&#9646;";
        }
      }
    });
  });

  // Click on message to seek
  document.querySelectorAll(".msg[data-msg-idx]").forEach(el => {
    el.addEventListener("click", () => {
      const idx = parseInt(el.dataset.msgIdx);
      if (idx >= 0 && idx < timeline.length) {
        audio.currentTime = scaledStart(idx);
        if (audio.paused) {
          audio.play().catch(() => {});
          playBtn.innerHTML = "&#9646;&#9646;";
        }
      }
    });
  });

  // Keyboard shortcuts (only when trace view is active)
  function handleKey(e) {
    // Don't capture when typing in an input
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;

    const dur = getDuration();

    if (e.code === "Space") {
      e.preventDefault();
      togglePlay();
    } else if (e.code === "ArrowLeft") {
      e.preventDefault();
      audio.currentTime = Math.max(0, audio.currentTime - 5);
    } else if (e.code === "ArrowRight") {
      e.preventDefault();
      audio.currentTime = Math.min(dur, audio.currentTime + 5);
    } else if (e.code === "ArrowUp") {
      e.preventDefault();
      const prev = Math.max(0, activeIdx - 1);
      if (prev < timeline.length) {
        audio.currentTime = scaledStart(prev);
        if (audio.paused) { audio.play().catch(() => {}); playBtn.innerHTML = "&#9646;&#9646;"; }
      }
    } else if (e.code === "ArrowDown") {
      e.preventDefault();
      const next = Math.min(timeline.length - 1, activeIdx + 1);
      if (next >= 0 && next < timeline.length) {
        audio.currentTime = scaledStart(next);
        if (audio.paused) { audio.play().catch(() => {}); playBtn.innerHTML = "&#9646;&#9646;"; }
      }
    }
  }

  document.addEventListener("keydown", handleKey);

  // Clean up keyboard listener on route change
  const cleanupOnRoute = () => {
    document.removeEventListener("keydown", handleKey);
    window.removeEventListener("hashchange", cleanupOnRoute);
    audio.pause();
  };
  window.addEventListener("hashchange", cleanupOnRoute);
}
