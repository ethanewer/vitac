/* ===================================================================
   VITAC Trace Viewer — Single-Page App
   ===================================================================
   Views:
     #/            Dashboard (aggregate pass/fail table)
     #/runs        Run browser (list of all runs)
     #/run/:id     Single run detail (list of trials)
     #/trace/:run/:task/:trial   Trace detail (chat + audio)
   =================================================================== */

const $app = document.getElementById("app");

// ---- API helpers ----

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ---- Routing ----

function navigate(hash) {
  window.location.hash = hash;
}

function currentRoute() {
  const h = window.location.hash || "#/";
  return h.slice(1); // strip leading #
}

window.addEventListener("hashchange", () => route());
window.addEventListener("DOMContentLoaded", () => route());

function route() {
  const path = currentRoute();

  // Update active nav link
  document.querySelectorAll(".nav-link").forEach((el) => {
    el.classList.remove("active");
    if (el.dataset.view === "dashboard" && (path === "/" || path === ""))
      el.classList.add("active");
    if (el.dataset.view === "runs" && path.startsWith("/runs"))
      el.classList.add("active");
    if (el.dataset.view === "runs" && path.startsWith("/run"))
      el.classList.add("active");
  });

  if (path === "/" || path === "") return viewDashboard();
  if (path === "/runs") return viewRuns();

  const runMatch = path.match(/^\/run\/([^/]+)$/);
  if (runMatch) return viewRunDetail(runMatch[1]);

  const traceMatch = path.match(/^\/trace\/([^/]+)\/([^/]+)\/(.+)$/);
  if (traceMatch) return viewTrace(traceMatch[1], traceMatch[2], traceMatch[3]);

  $app.innerHTML = `<div class="empty">Page not found</div>`;
}

// ---- Utilities ----

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function formatDuration(startStr, endStr) {
  if (!startStr || !endStr) return "-";
  try {
    const ms = new Date(endStr) - new Date(startStr);
    if (isNaN(ms) || ms < 0) return "-";
    const s = Math.round(ms / 1000);
    const m = Math.floor(s / 60);
    return m > 0 ? `${m}m ${s % 60}s` : `${s}s`;
  } catch {
    return "-";
  }
}

function failureBadge(mode) {
  if (!mode || mode === "none" || mode === "unset")
    return "";
  if (mode === "agent_timeout" || mode === "test_timeout")
    return `<span class="badge badge-timeout">${esc(mode)}</span>`;
  return `<span class="badge badge-fail">${esc(mode)}</span>`;
}

function resolvedBadge(resolved) {
  return resolved
    ? `<span class="badge badge-pass">PASS</span>`
    : `<span class="badge badge-fail">FAIL</span>`;
}

// ---- Views ----

async function viewDashboard() {
  $app.innerHTML = `<div class="loading">Loading aggregate data</div>`;

  try {
    const [agg, runs] = await Promise.all([
      api("/api/aggregate"),
      api("/api/runs"),
    ]);

    const systems = agg.systems || [];
    const tasks = agg.tasks || {};
    const taskIds = Object.keys(tasks).sort();

    // Summary stats
    let totalTrials = 0, totalPassed = 0;
    for (const tid of taskIds) {
      for (const sys of systems) {
        const cell = (tasks[tid] || {})[sys];
        if (cell) {
          totalTrials += cell.total;
          totalPassed += cell.passed;
        }
      }
    }
    const totalRuns = runs.length;

    let html = `
      <h1 style="margin-bottom:1.5rem">Dashboard</h1>
      <div class="summary-row">
        <div class="stat-card">
          <div class="label">Runs</div>
          <div class="value">${totalRuns}</div>
        </div>
        <div class="stat-card">
          <div class="label">Total Trials</div>
          <div class="value">${totalTrials}</div>
        </div>
        <div class="stat-card">
          <div class="label">Passed</div>
          <div class="value" style="color:var(--green)">${totalPassed}</div>
        </div>
        <div class="stat-card">
          <div class="label">Overall Pass Rate</div>
          <div class="value">${totalTrials ? (100 * totalPassed / totalTrials).toFixed(1) : 0}%</div>
        </div>
      </div>
    `;

    // Aggregate table: tasks (rows) x systems (columns)
    if (taskIds.length === 0) {
      html += `<div class="empty">No results data found. Run some benchmarks first.</div>`;
    } else {
      html += `
        <div class="card">
          <h2>Pass / Fail by Task and System</h2>
          <div style="overflow-x:auto">
            <table>
              <thead>
                <tr>
                  <th>Task</th>
                  ${systems.map((s) => `<th>${esc(s)}</th>`).join("")}
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
      `;

      for (const tid of taskIds) {
        let rowTotal = 0, rowPassed = 0;
        const cells = systems.map((sys) => {
          const cell = (tasks[tid] || {})[sys];
          if (!cell) return `<td class="cell-na">-</td>`;
          rowTotal += cell.total;
          rowPassed += cell.passed;
          if (cell.passed === cell.total && cell.total > 0)
            return `<td class="cell-pass">${cell.passed}/${cell.total}</td>`;
          if (cell.passed === 0)
            return `<td class="cell-fail">${cell.passed}/${cell.total}</td>`;
          return `<td><span class="cell-pass">${cell.passed}</span>/<span class="cell-fail">${cell.total}</span></td>`;
        });

        html += `
          <tr>
            <td><code>${esc(tid)}</code></td>
            ${cells.join("")}
            <td class="${rowPassed > 0 ? "cell-pass" : "cell-fail"}">${rowPassed}/${rowTotal}</td>
          </tr>
        `;
      }

      html += `</tbody></table></div></div>`;
    }

    $app.innerHTML = html;
  } catch (err) {
    $app.innerHTML = `<div class="empty">Error loading data: ${esc(err.message)}</div>`;
  }
}

async function viewRuns() {
  $app.innerHTML = `<div class="loading">Loading runs</div>`;

  try {
    const runs = await api("/api/runs");

    if (runs.length === 0) {
      $app.innerHTML = `
        <h1 style="margin-bottom:1.5rem">Runs</h1>
        <div class="empty">No benchmark runs found in results/</div>
      `;
      return;
    }

    let html = `<h1 style="margin-bottom:1.5rem">Runs</h1>`;
    html += `
      <div class="card">
        <table>
          <thead>
            <tr>
              <th>Run ID</th>
              <th>System</th>
              <th>Tasks</th>
              <th>Resolved</th>
              <th>Accuracy</th>
            </tr>
          </thead>
          <tbody>
    `;

    for (const r of runs) {
      html += `
        <tr class="clickable" onclick="location.hash='#/run/${esc(r.run_id)}'">
          <td><code>${esc(r.run_id)}</code></td>
          <td><span class="badge badge-system">${esc(r.system)}</span></td>
          <td>${r.n_total}</td>
          <td>${r.n_resolved}/${r.n_total}</td>
          <td class="${r.accuracy > 0 ? "cell-pass" : "cell-fail"}">
            ${(100 * r.accuracy).toFixed(1)}%
          </td>
        </tr>
      `;
    }

    html += `</tbody></table></div>`;
    $app.innerHTML = html;
  } catch (err) {
    $app.innerHTML = `<div class="empty">Error: ${esc(err.message)}</div>`;
  }
}

async function viewRunDetail(runId) {
  $app.innerHTML = `<div class="loading">Loading run</div>`;

  try {
    const data = await api(`/api/runs/${encodeURIComponent(runId)}`);
    const trials = data.results || [];

    let html = `
      <div class="breadcrumb">
        <a href="#/runs">Runs</a>
        <span class="sep">/</span>
        <span>${esc(runId)}</span>
      </div>
      <h1 style="margin-bottom:0.5rem">${esc(runId)}</h1>
      <p style="color:var(--text-dim);margin-bottom:1.5rem">
        System: <span class="badge badge-system">${esc(data.system || "unknown")}</span>
        &mdash; ${trials.length} trial(s),
        ${trials.filter((t) => t.is_resolved).length} resolved
      </p>
    `;

    html += `
      <div class="card">
        <table>
          <thead>
            <tr>
              <th>Task</th>
              <th>Status</th>
              <th>Failure Mode</th>
              <th>Duration</th>
              <th>Trace</th>
            </tr>
          </thead>
          <tbody>
    `;

    for (const t of trials) {
      const dur = formatDuration(t.trial_started_at, t.trial_ended_at);
      const traceLink = t.has_trace
        ? `<a href="#/trace/${esc(runId)}/${esc(t.task_id)}/${esc(t.trial_name)}">
            View${t.has_audio ? " (+ audio)" : ""}
           </a>`
        : `<span style="color:var(--text-dim)">-</span>`;

      html += `
        <tr class="${t.has_trace ? "clickable" : ""}"
            ${t.has_trace ? `onclick="location.hash='#/trace/${esc(runId)}/${esc(t.task_id)}/${esc(t.trial_name)}'"` : ""}>
          <td><code>${esc(t.task_id)}</code></td>
          <td>${resolvedBadge(t.is_resolved)}</td>
          <td>${failureBadge(t.failure_mode)}</td>
          <td style="font-family:var(--font-mono)">${dur}</td>
          <td>${traceLink}</td>
        </tr>
      `;
    }

    html += `</tbody></table></div>`;

    // Test results per trial
    for (const t of trials) {
      if (t.parser_results && Object.keys(t.parser_results).length > 0) {
        html += `
          <div class="card" style="margin-top:1rem">
            <h2>Test Results: ${esc(t.task_id)}</h2>
            <ul class="test-list">
        `;
        for (const [name, status] of Object.entries(t.parser_results)) {
          const cls = status === "passed" ? "cell-pass" : "cell-fail";
          html += `
            <li>
              <span class="test-name" title="${esc(name)}">${esc(name)}</span>
              <span class="${cls}">${esc(status)}</span>
            </li>
          `;
        }
        html += `</ul></div>`;
      }
    }

    $app.innerHTML = html;
  } catch (err) {
    $app.innerHTML = `<div class="empty">Error: ${esc(err.message)}</div>`;
  }
}

async function viewTrace(runId, taskId, trialName) {
  $app.innerHTML = `<div class="loading">Loading trace</div>`;

  try {
    const data = await api(
      `/api/runs/${encodeURIComponent(runId)}/${encodeURIComponent(taskId)}/${encodeURIComponent(trialName)}/trace`
    );

    const trace = data.trace || {};
    const trial = data.trial_results || {};
    const taskDef = data.task_def || {};
    const hasAudio = data.has_audio;
    const messages = trace.voiceMessages || [];

    // Build audio URL helper
    function audioUrl(msg) {
      if (!hasAudio || !msg.audioFilename) return null;
      return `/api/audio/${encodeURIComponent(runId)}/${encodeURIComponent(taskId)}/${encodeURIComponent(trialName)}/${encodeURIComponent(msg.audioFilename)}`;
    }

    // Breadcrumb
    let html = `
      <div class="breadcrumb">
        <a href="#/runs">Runs</a>
        <span class="sep">/</span>
        <a href="#/run/${esc(runId)}">${esc(runId)}</a>
        <span class="sep">/</span>
        <span>${esc(taskId)}</span>
      </div>
    `;

    html += `<div class="trace-layout">`;

    // ---- Chat column ----
    html += `<div>`;
    html += `<h1 style="margin-bottom:1rem">${esc(taskId)}</h1>`;

    if (messages.length === 0) {
      html += `<div class="empty">No voice messages recorded for this trial.</div>`;
    } else {
      html += `<div class="chat-container">`;

      // Determine relative timestamps
      const t0 = messages[0].timestampMs || 0;

      for (const msg of messages) {
        const side = msg.sender === "primary" ? "primary" : "collaborator";
        const label = msg.sender === "primary" ? "Primary Agent" : "Collaborator";
        const elapsed = msg.timestampMs ? ((msg.timestampMs - t0) / 1000).toFixed(1) : "?";
        const url = audioUrl(msg);

        html += `
          <div class="chat-msg ${side}">
            <div class="chat-sender">${label}</div>
            <div class="chat-text">${esc(msg.transcript || "[no transcript]")}</div>
            ${url
              ? `<div class="chat-audio"><audio controls preload="none" src="${url}"></audio></div>`
              : `<div class="no-audio">audio not available</div>`
            }
            <div class="chat-time">+${elapsed}s</div>
          </div>
        `;
      }

      html += `</div>`; // chat-container
    }

    // Terminal commands
    const cmds = trace.terminalCommands || [];
    if (cmds.length > 0) {
      html += `
        <div class="card" style="margin-top:1.5rem">
          <h2>Terminal Commands (${cmds.length})</h2>
          <div class="instruction-block">${cmds.map((c) => esc(c)).join("\n")}</div>
        </div>
      `;
    }

    html += `</div>`; // end chat column

    // ---- Sidebar ----
    html += `<div class="sidebar">`;

    // Trial metadata
    html += `
      <div class="card">
        <h3>Trial</h3>
        <div class="meta-row">
          <span class="meta-label">Status</span>
          <span class="meta-value">${resolvedBadge(trial.is_resolved)}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Failure Mode</span>
          <span class="meta-value">${failureBadge(trial.failure_mode) || "-"}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">TS Completed</span>
          <span class="meta-value">${trace.completed ? "Yes" : "No"}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Voice Messages</span>
          <span class="meta-value">${messages.length}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Agent Duration</span>
          <span class="meta-value">${formatDuration(trial.agent_started_at, trial.agent_ended_at)}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Total Duration</span>
          <span class="meta-value">${formatDuration(trial.trial_started_at, trial.trial_ended_at)}</span>
        </div>
        ${trace.error ? `
          <div class="meta-row">
            <span class="meta-label">Error</span>
            <span class="meta-value" style="color:var(--red);font-size:0.75rem;max-width:180px;text-align:right">${esc(trace.error)}</span>
          </div>
        ` : ""}
      </div>
    `;

    // Task info
    html += `
      <div class="card">
        <h3>Task</h3>
        <div class="meta-row">
          <span class="meta-label">Difficulty</span>
          <span class="meta-value">${esc(taskDef.difficulty || "-")}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Category</span>
          <span class="meta-value">${esc(taskDef.category || "-")}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Transcript Mode</span>
          <span class="meta-value" style="font-size:0.75rem">${esc(taskDef.transcript_mode || "-")}</span>
        </div>
      </div>
    `;

    // Instruction
    const instruction = trial.instruction || taskDef.instruction || "";
    if (instruction) {
      html += `
        <div class="card">
          <h3>Instruction</h3>
          <div class="instruction-block">${esc(instruction)}</div>
        </div>
      `;
    }

    // Test results
    if (trial.parser_results && Object.keys(trial.parser_results).length > 0) {
      html += `
        <div class="card">
          <h3>Test Results</h3>
          <ul class="test-list">
      `;
      for (const [name, status] of Object.entries(trial.parser_results)) {
        const cls = status === "passed" ? "cell-pass" : "cell-fail";
        // Shorten long test names for sidebar
        const short = name.length > 50 ? "..." + name.slice(-47) : name;
        html += `
          <li>
            <span class="test-name" title="${esc(name)}">${esc(short)}</span>
            <span class="${cls}">${esc(status)}</span>
          </li>
        `;
      }
      html += `</ul></div>`;
    }

    html += `</div>`; // sidebar
    html += `</div>`; // trace-layout

    $app.innerHTML = html;
  } catch (err) {
    $app.innerHTML = `<div class="empty">Error: ${esc(err.message)}</div>`;
  }
}
