/* All calculations and validation happen in Python. This file renders results. */
"use strict";
const $ = (id) => document.getElementById(id);
const icon = (name, className = "") =>
  `<svg class="${className}" aria-hidden="true"><use href="#i-${name}"/></svg>`;
const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const money = (value, compact = false) =>
  new Intl.NumberFormat(LOCALE, {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: compact ? 0 : 2,
    minimumFractionDigits: compact ? 0 : 2,
    ...(compact && value >= 100000
      ? { notation: "compact", maximumFractionDigits: 1 }
      : {}),
  }).format(value);
const shortDate = (value) =>
  new Date(`${value}T12:00:00`).toLocaleDateString(LOCALE, {
    day: "2-digit",
    month: "short",
  });
const state = {
  data: null,
  view: "overview",
  page: 1,
  pageSize: 15,
  filters: { q: "", category: "", severity: "", status: "", flagged: "" },
  pending: null,
  requestId: 0,
};
const pageCopy = {
  overview: [
    "Overview",
    "SEE THE SIGNAL. TAKE THE NEXT STEP.",
    "Risk, made clear",
    "A practical view of operational incidents. From source to decision.",
  ],
  incidents: [
    "Incident explorer",
    "EVERY RECORD HAS A STORY.",
    "Explore the evidence",
    "Find an incident. Follow its signals. Understand the next step.",
  ],
  pipeline: [
    "Data pipeline",
    "GOOD DECISIONS START WITH GOOD DATA.",
    "Trust the process",
    "An inspectable path from imperfect CSV to consistent, usable data.",
  ],
  project: [
    "Behind the project",
    "A SMALL TOOL. A PRACTICAL PURPOSE.",
    "Built to learn. Built to work",
    "A transparent Python portfolio project by Dmitrii Kataev.",
  ],
};

function showView(view, updateHash = true) {
  if (!pageCopy[view]) view = "overview";
  state.view = view;
  document.querySelectorAll(".view").forEach((el) => {
    el.hidden = el.id !== `view-${view}`;
    el.classList.toggle("active", !el.hidden);
  });
  document.querySelectorAll(".nav-item").forEach((el) => {
    const active = el.dataset.view === view;
    el.classList.toggle("active", active);
    if (active) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
  const [crumb, eyebrow, title, subtitle] = pageCopy[view].map((text) =>
    t(text),
  );
  $("breadcrumb-current").textContent = crumb;
  $("page-eyebrow").textContent = eyebrow;
  $("page-title").innerHTML = `${title}<span>.</span>`;
  $("page-subtitle").textContent = subtitle;
  document.title = `${crumb} · CLEAR — Dmitrii Kataev`;
  if (updateHash) history.replaceState(null, "", `#${view}`);
}

function queryString() {
  const params = new URLSearchParams();
  if (LANG !== "en") params.set("lang", LANG);
  for (const [key, value] of Object.entries(state.filters))
    if (value) params.set(key, value);
  return params.toString() ? `?${params}` : "";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content,
      ...options.headers,
    },
  });
  let body;
  try {
    body = await response.json();
  } catch {
    throw new Error(
      "The server returned an unreadable response. Please retry.",
    );
  }
  if (!response.ok)
    throw new Error(body.error || "The request could not be completed.");
  return body;
}

function toast(message) {
  $("toast").textContent = translateError(message);
  $("toast").hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => {
    $("toast").hidden = true;
  }, 4500);
}

async function refresh() {
  const id = ++state.requestId;
  $("app-error").hidden = true;
  $("main").setAttribute("aria-busy", "true");
  try {
    const data = await api(`/api/dashboard${queryString()}`);
    if (id !== state.requestId) return;
    state.data = data;
    render();
  } catch (error) {
    if (id !== state.requestId) return;
    $("app-error").textContent =
      `${translateError(error.message)} ${t("Refresh the page to retry.")}`;
    $("app-error").hidden = false;
  } finally {
    if (id === state.requestId) $("main").removeAttribute("aria-busy");
  }
}

function animateNumber(
  element,
  final,
  format = (n) => Math.round(n).toLocaleString(LOCALE),
) {
  if (element._animation) cancelAnimationFrame(element._animation);
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    element.textContent = format(final);
    return;
  }
  const start = performance.now();
  const tick = (time) => {
    const progress = Math.min(1, (time - start) / 650);
    element.textContent = format(final * (1 - Math.pow(1 - progress, 3)));
    if (progress < 1) element._animation = requestAnimationFrame(tick);
  };
  element._animation = requestAnimationFrame(tick);
}

function render() {
  const { dataset, summary, options } = state.data;
  $("dataset-name").textContent = dataset.is_demo
    ? t("Operations · September 2026")
    : dataset.name;
  $("dataset-date").textContent = t("Analysis date {date}", {
    date: `${shortDate(dataset.as_of)} ${dataset.as_of.slice(0, 4)}`,
  });
  $("nav-count").textContent = dataset.quality.accepted;
  $("filter-notice").hidden = !Object.values(state.filters).some(Boolean);
  animateNumber($("metric-total"), summary.metrics.total);
  animateNumber($("metric-active"), summary.metrics.active);
  animateNumber($("metric-flagged"), summary.metrics.flagged);
  animateNumber($("metric-loss"), summary.metrics.loss, (n) => money(n, true));
  $("metric-loss").title = money(summary.metrics.loss);
  $("metric-aging").textContent = t("{n} aging", { n: summary.metrics.aging });
  $("focus-critical").textContent = summary.metrics.critical;
  $("focus-ring").style.strokeDashoffset =
    452.39 *
    (1 -
      (summary.metrics.active
        ? summary.metrics.critical / summary.metrics.active
        : 0));
  $("focus-copy").textContent = t(
    "{critical} of {active} active cases have critical severity. Start with their evidence and assigned owners.",
    summary.metrics,
  );
  $("summary-text").textContent = summary.narrative;
  $("summary-actions").innerHTML = summary.actions
    .map(
      (text, i) =>
        `<div class="action-item"><span class="action-number">${i + 1}</span><span>${escapeHtml(text)}</span></div>`,
    )
    .join("");
  renderTrend(summary.trend);
  renderCategories(summary.categories);
  renderPriorities();
  for (const key of ["category", "severity", "status"]) {
    const el = $(`filter-${key}`);
    const first = el.options[0].textContent;
    el.innerHTML =
      `<option value="">${first}</option>` +
      options[key]
        .map(
          (value) =>
            `<option value="${escapeHtml(value)}">${escapeHtml(t(value))}</option>`,
        )
        .join("");
    el.value = state.filters[key];
  }
  $("search").value = state.filters.q;
  $("filter-flagged").checked = state.filters.flagged === "1";
  renderIncidents();
  renderQuality();
  renderRules();
  const qs = queryString();
  $("export-report").href = `/report${qs}`;
  $("summary-report").href = `/report${qs}`;
  $("export-csv").href = `/api/export/clean.csv${qs}`;
  $("export-json").href = `/api/export/report.json${qs}`;
}

function renderTrend(trend) {
  const width =
    window.innerWidth < 740
      ? Math.max(290, $("trend-chart").clientWidth - 29)
      : 640;
  const height = 240,
    left = 40,
    right = 20,
    top = 22,
    bottom = 37;
  const maximum = Math.max(4, ...trend.map((d) => d.count));
  const scale = Math.ceil(maximum / 4) * 4;
  const chartHeight = height - top - bottom;
  const x = (i) => left + (i * (width - left - right)) / 7;
  const y = (v) => top + chartHeight - (v / scale) * chartHeight;
  const line = (key) =>
    trend
      .map(
        (d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(d[key]).toFixed(1)}`,
      )
      .join(" ");
  const grid = [0, 1, 2, 3, 4]
    .map(
      (i) =>
        `<line x1="${left}" x2="${width - right}" y1="${y((scale * i) / 4)}" y2="${y((scale * i) / 4)}" class="chart-grid"/><text x="${left - 13}" y="${y((scale * i) / 4) + 4}" text-anchor="end" class="chart-axis">${(scale * i) / 4}</text>`,
    )
    .join("");
  const labels = trend
    .map(
      (d, i) =>
        `<text x="${x(i)}" y="${height - 10}" text-anchor="middle" class="chart-axis">${shortDate(d.start)}</text>`,
    )
    .join("");
  const points = trend
    .map(
      (d, i) =>
        `<circle class="chart-point" cx="${x(i)}" cy="${y(d.count)}" r="3.5"><title>${shortDate(d.start)}–${shortDate(d.end)}: ${t("{n} incidents, {flagged} flagged", { n: d.count, flagged: d.flagged })}${d.partial ? ` (${t("partial week")})` : ""}</title></circle>`,
    )
    .join("");
  const accessible = trend
    .map(
      (d) =>
        `${shortDate(d.start)}: ${t("{n} incidents, {flagged} flagged", { n: d.count, flagged: d.flagged })}`,
    )
    .join("; ");
  $("trend-chart").innerHTML =
    `<svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="trend-title trend-desc"><title id="trend-title">${t("Weekly incidents and review flags")}</title><desc id="trend-desc">${accessible}. ${t("The current week is partial.")}</desc><defs><linearGradient id="area-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#c4d4a4" stop-opacity=".4"/><stop offset="100%" stop-color="#f7faf2" stop-opacity=".05"/></linearGradient></defs>${grid}<path d="${line("count")} L${x(7)},${y(0)} L${x(0)},${y(0)} Z" class="chart-area"/><path d="${line("count")}" class="chart-line"/><path d="${line("flagged")}" class="chart-flag-line"/>${points}${labels}</svg>`;
}

function renderCategories(categories) {
  const maximum = Math.max(1, ...categories.map((c) => c.loss));
  $("category-bars").innerHTML = categories.length
    ? categories
        .map(
          (c, i) =>
            `<div class="category-row"><div class="category-label"><span>${escapeHtml(t(c.name))}</span><strong>${money(c.loss, true)}</strong></div><div class="bar-track" title="${escapeHtml(t(c.name))}: ${t("{amount} from {n} incidents", { amount: money(c.loss), n: c.count })}"><div class="bar-fill" style="width:${(c.loss / maximum) * 100}%;animation-delay:${i * 65}ms"></div></div></div>`,
        )
        .join("")
    : `<p class="empty-state">${t("No data in this selection.")}</p>`;
}

function badge(value) {
  const classes = {
    Critical: "critical",
    High: "high",
    Medium: "medium",
    Low: "low",
    Resolved: "resolved",
    Open: "open",
    "In progress": "in-progress",
  };
  return `<span class="badge ${classes[value] || ""}">${escapeHtml(t(value))}</span>`;
}

function renderPriorities() {
  const records = state.data.records.filter((r) => r.flags.length).slice(0, 5);
  $("priority-body").innerHTML = records.length
    ? records
        .map(
          (r) =>
            `<tr class="interactive-row" data-incident="${escapeHtml(r.incident_id)}"><td><button class="id-link" data-incident="${escapeHtml(r.incident_id)}" aria-label="${escapeHtml(t("Inspect {id}", { id: r.incident_id }))}">${escapeHtml(r.incident_id)}</button><span class="cell-sub">${escapeHtml(r.business_unit)}</span></td><td>${escapeHtml(t(r.category))}</td><td>${badge(r.severity)}</td><td class="amount">${money(r.loss_eur, true)}</td><td class="signal-cell">${escapeHtml(t(r.flag_labels[0]))}${r.flags.length > 1 ? `<span class="cell-sub">${t("+ {n} more signals", { n: r.flags.length - 1 })}</span>` : ""}</td><td>${icon("arrow", "row-arrow")}</td></tr>`,
        )
        .join("")
    : `<tr><td colspan="6" class="empty-state"><strong>${t("No review flags in this selection.")}</strong>${t("Explore all incidents or broaden your filters.")}</td></tr>`;
}

function renderIncidents() {
  const records = state.data.records;
  const pages = Math.max(1, Math.ceil(records.length / state.pageSize));
  state.page = Math.max(1, Math.min(state.page, pages));
  const start = (state.page - 1) * state.pageSize;
  const rows = records.slice(start, start + state.pageSize);
  $("result-count").textContent = records.length;
  $("incidents-body").innerHTML = rows.length
    ? rows
        .map(
          (r) =>
            `<tr class="interactive-row" data-incident="${escapeHtml(r.incident_id)}"><td><button class="id-link" data-incident="${escapeHtml(r.incident_id)}" aria-label="${escapeHtml(t("Inspect {id}", { id: r.incident_id }))}">${escapeHtml(r.incident_id)}</button><span class="cell-sub">${shortDate(r.occurred_on)} ${r.occurred_on.slice(0, 4)}</span></td><td>${escapeHtml(t(r.category))}<span class="cell-sub">${escapeHtml(r.business_unit)}</span></td><td>${badge(r.severity)}</td><td>${badge(r.status)}</td><td class="amount">${money(r.loss_eur, true)}</td><td><span class="score-pill" title="${t("{n} review rules triggered", { n: r.flags.length })}">${r.score}</span></td><td>${icon("arrow", "row-arrow")}</td></tr>`,
        )
        .join("")
    : `<tr><td colspan="7" class="empty-state"><strong>${t("No matching incidents.")}</strong>${t("Try a broader search or reset the filters.")}</td></tr>`;
  $("page-status").textContent = records.length
    ? t("{start}–{end} of {total} incidents", {
        start: start + 1,
        end: Math.min(start + state.pageSize, records.length),
        total: records.length,
      })
    : t("0 incidents");
  $("previous-page").disabled = state.page <= 1;
  $("next-page").disabled = state.page >= pages;
}

function renderQuality() {
  const q = state.data.dataset.quality;
  $("quality-metrics").innerHTML = [
    ["Source rows", q.total, ""],
    ["Accepted", q.accepted, "green"],
    ["Duplicates", q.duplicates, ""],
    ["Rejected", q.rejected, "red"],
  ]
    .map(
      ([label, n, c]) =>
        `<div class="quality-stat ${c}"><strong>${n}</strong><span>${t(label)}</span></div>`,
    )
    .join("");
  $("quality-bar").innerHTML = [
    [q.accepted, "#a4c368"],
    [q.duplicates, "#e4ca83"],
    [q.rejected, "#cf907b"],
  ]
    .map(
      ([n, color]) =>
        `<span style="width:${(n / q.total) * 100}%;background:${color}"></span>`,
    )
    .join("");
  $("quality-changes").innerHTML =
    `<div class="change-row"><span>${t("Row acceptance rate")}</span><strong>${q.acceptance_rate.toLocaleString(LOCALE)}%</strong></div><div class="change-row"><span>${t("Accepted rows normalized")}</span><strong>${q.cleaned}</strong></div>` +
    Object.entries(q.changes)
      .map(
        ([label, n]) =>
          `<div class="change-row"><span>${escapeHtml(t(label))}</span><strong>${n}</strong></div>`,
      )
      .join("") +
    `<p class="subtle-note">${t("A row can have several changes. Missing amounts are rejected, never guessed.")} ${q.ignored_columns.length ? escapeHtml(t("Ignored columns: {columns}.", { columns: q.ignored_columns.join(", ") })) : ""} ${q.blank ? t("{n} blank rows skipped.", { n: q.blank }) : ""} ${q.headers_normalized ? t("Column names normalized.") : ""}</p>`;
  $("issues-body").innerHTML = q.issues.length
    ? q.issues
        .slice(0, 100)
        .map(
          (issue) =>
            `<tr><td>${issue.row}</td><td><span class="badge ${issue.type}">${t(issue.type === "duplicate" ? "Duplicate removed" : "Rejected")}</span></td><td class="issues-message">${escapeHtml(translateError(issue.message))}</td></tr>`,
        )
        .join("")
    : `<tr><td colspan="3" class="empty-state"><strong>${t("All records passed validation.")}</strong>${t("No duplicates or rejected rows were found.")}</td></tr>`;
  $("issues-footer").textContent =
    `${t("{n} excluded rows.", { n: q.issues.length })} ${t(q.issues.length > 100 ? "Showing the first 100; download the log for every issue." : "Source rows count CSV records including the header at row 1.")} ${t("Dataset quality uses the full input, regardless of dashboard filters.")}`;
}

function renderRules() {
  $("rules-list").innerHTML = state.data.rules
    .map(
      (rule, i) =>
        `<div class="rule-row"><span>0${i + 1}</span><strong>${escapeHtml(t(rule.label))}</strong><p>${escapeHtml(t(rule.description))}</p><span class="rule-weight">+${rule.weight}</span></div>`,
    )
    .join("");
}

function openDetails(id) {
  const r = state.data.records.find((record) => record.incident_id === id);
  if (!r) return;
  $("detail-title").textContent = r.incident_id;
  const fields = [
    ["Category", t(r.category)],
    ["Company / unit", r.business_unit],
    ["Severity", t(r.severity)],
    ["Status", t(r.status)],
    ["Recorded loss", money(r.loss_eur)],
    ["Owner", state.data.dataset.is_demo ? t(r.owner) : r.owner],
    [
      "Occurrence date",
      new Date(`${r.occurred_on}T12:00:00`).toLocaleDateString(LOCALE),
    ],
    ["Age at analysis", t("{n} days", { n: r.age_days })],
  ];
  $("detail-content").className = "detail-content";
  const description = r.description
    ? state.data.dataset.is_demo
      ? t(r.description)
      : r.description
    : t("No description provided.");
  $("detail-content").innerHTML =
    `<p class="detail-description">${escapeHtml(description)}</p><div class="detail-grid">${fields.map(([label, value]) => `<div class="detail-field"><span>${t(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}</div><h3>${t("Review score {score} / 100", { score: r.score })}</h3>${
      r.flags.length
        ? r.flags
            .map((id) => {
              const rule = state.data.rules.find((rule) => rule.id === id);
              return `<div class="detail-rule">${icon("alert")}<div><strong>${escapeHtml(t(rule.label))} · +${rule.weight}</strong><p>${escapeHtml(t(rule.description))} ${id === "outlier" ? t("Category threshold: {amount}.", { amount: money(r.outlier_threshold_eur) }) : ""}</p></div></div>`;
            })
            .join("")
        : `<p class="subtle-note">${t("No rules triggered. This does not establish that an incident is risk-free.")}</p>`
    }<p class="provenance">${t("Source row {row} · Analysis date {date}", { row: r.source_row, date: state.data.dataset.as_of })}<br>${t("A score is a review order, not a probability.")}</p>`;
  $("detail-dialog").showModal();
}

function resetUpload() {
  state.pending = null;
  $("upload-form").reset();
  $("file-label").textContent = t("Choose a CSV or drop it here");
  $("upload-error").hidden = true;
  $("upload-input-stage").hidden = false;
  $("upload-preview-stage").hidden = true;
  $("validate-button").hidden = false;
  $("apply-button").hidden = true;
  $("upload-footnote").textContent = t(
    "Your current dataset stays active until you apply this upload.",
  );
}

function showUploadError(message) {
  $("upload-error").textContent = translateError(message);
  $("upload-error").hidden = false;
}

$("upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.pending) return;
  const file = $("csv-file").files[0];
  if (!file) return showUploadError("Choose a CSV file.");
  if (file.size > 2 * 1024 * 1024 - 8192)
    return showUploadError(
      "The upload must fit within 2 MB, including the form. Choose a smaller CSV.",
    );
  if (!file.name.toLowerCase().endsWith(".csv"))
    return showUploadError("Choose a file with the .csv extension.");
  const form = new FormData();
  form.append("file", file);
  form.append("as_of", $("as-of").value);
  form.append("synthetic", "true");
  const button = $("validate-button");
  button.disabled = true;
  button.innerHTML = `<span class="spinner"></span> ${t("Validating…")}`;
  $("upload-error").hidden = true;
  try {
    const preview = await api("/api/uploads/preview", {
      method: "POST",
      body: form,
    });
    state.pending = preview.id;
    const q = preview.quality;
    $("upload-input-stage").hidden = true;
    $("upload-preview-stage").hidden = false;
    $("upload-preview-stage").innerHTML =
      `<div class="preview-success">${icon("check")}<div><h3>${t("Validation complete.")}</h3><p>${escapeHtml(preview.name)}</p></div></div><div class="preview-stats"><div><strong>${q.accepted}</strong><span>${t("Accepted")}</span></div><div><strong>${q.duplicates}</strong><span>${t("Duplicates removed")}</span></div><div><strong>${q.rejected}</strong><span>${t("Rejected")}</span></div></div><p class="preview-note">${t("{cleaned} accepted rows normalized. {rate}% of source rows accepted. Analysis date: {date}.", { cleaned: q.cleaned, rate: q.acceptance_rate.toLocaleString(LOCALE), date: preview.as_of })} ${q.ignored_columns.length ? escapeHtml(t("Ignored columns: {columns}.", { columns: q.ignored_columns.join(", ") })) : ""}</p>${
        q.issues.length
          ? `<div class="preview-log">${q.issues
              .slice(0, 12)
              .map(
                (issue) =>
                  `<p><strong>${t("Row {n}", { n: issue.row })}</strong> — ${escapeHtml(translateError(issue.message))}</p>`,
              )
              .join(
                "",
              )}${q.issues.length > 12 ? `<p>${t("+ {n} more. The full log will be available in Data pipeline after applying.", { n: q.issues.length - 12 })}</p>` : ""}</div>`
          : ""
      }<p class="preview-note">${t("Only accepted records will be included in the dashboard. Your previous data is still active.")}</p>`;
    $("validate-button").hidden = true;
    $("apply-button").hidden = false;
    $("upload-footnote").textContent = t(
      "Inspect the excluded rows before applying. Close this dialog to cancel.",
    );
    $("apply-button").focus();
  } catch (error) {
    showUploadError(error.message);
  } finally {
    button.disabled = false;
    button.innerHTML = `${t("Validate CSV")} ${icon("arrow")}`;
  }
});

$("apply-button").addEventListener("click", async () => {
  if (!state.pending) return;
  const button = $("apply-button");
  button.disabled = true;
  try {
    await api(`/api/uploads/${state.pending}/activate`, { method: "POST" });
    clearFilters(false);
    await refresh();
    $("upload-dialog").close();
    showView("pipeline");
    toast("Dataset applied. Your data quality report is ready.");
  } catch (error) {
    showUploadError(error.message);
  } finally {
    button.disabled = false;
  }
});

function clearFilters(fetchData = true) {
  state.filters = {
    q: "",
    category: "",
    severity: "",
    status: "",
    flagged: "",
  };
  state.page = 1;
  if (fetchData) refresh();
}

document.addEventListener("click", async (event) => {
  const target = event.target.closest(
    "[data-view],[data-action],[data-close],[data-incident]",
  );
  if (!target) return;
  if (target.dataset.view) {
    showView(target.dataset.view);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  if (target.dataset.close) $(target.dataset.close).close();
  if (target.dataset.incident) openDetails(target.dataset.incident);
  if (target.dataset.action === "upload") {
    resetUpload();
    $("upload-dialog").showModal();
  }
  if (target.dataset.action === "clear-filters") clearFilters();
  if (target.dataset.action === "show-flagged") {
    clearFilters(false);
    state.filters.flagged = "1";
    showView("incidents");
    await refresh();
  }
  if (target.dataset.action === "show-critical") {
    clearFilters(false);
    state.filters.severity = "Critical";
    state.filters.status = "Active";
    showView("incidents");
    await refresh();
  }
  if (target.dataset.action === "load-demo") {
    target.disabled = true;
    try {
      await api("/api/demo", { method: "POST" });
      clearFilters(false);
      await refresh();
      toast("Sample data restored.");
    } catch (error) {
      toast(error.message);
    } finally {
      target.disabled = false;
    }
  }
});

let searchTimer;
$("filter-form").addEventListener("submit", (event) => event.preventDefault());
$("filter-form").addEventListener("input", (event) => {
  clearTimeout(searchTimer);
  const update = () => {
    state.filters = {
      q: $("search").value,
      category: $("filter-category").value,
      severity: $("filter-severity").value,
      status: $("filter-status").value,
      flagged: $("filter-flagged").checked ? "1" : "",
    };
    state.page = 1;
    refresh();
  };
  if (event.target === $("search")) searchTimer = setTimeout(update, 220);
  else update();
});
$("previous-page").addEventListener("click", () => {
  state.page--;
  renderIncidents();
});
$("next-page").addEventListener("click", () => {
  state.page++;
  renderIncidents();
});
$("csv-file").addEventListener("change", () => {
  $("file-label").textContent =
    $("csv-file").files[0]?.name || t("Choose a CSV or drop it here");
});
for (const type of ["dragenter", "dragover"])
  $("dropzone").addEventListener(type, (event) => {
    event.preventDefault();
    $("dropzone").classList.add("drag-over");
  });
for (const type of ["dragleave", "drop"])
  $("dropzone").addEventListener(type, (event) => {
    event.preventDefault();
    $("dropzone").classList.remove("drag-over");
  });
$("dropzone").addEventListener("drop", (event) => {
  if (event.dataTransfer.files.length) {
    $("csv-file").files = event.dataTransfer.files;
    $("csv-file").dispatchEvent(new Event("change"));
  }
});
document.querySelectorAll("dialog").forEach((dialog) =>
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      const rect = dialog.getBoundingClientRect();
      if (
        event.clientX < rect.left ||
        event.clientX > rect.right ||
        event.clientY < rect.top ||
        event.clientY > rect.bottom
      )
        dialog.close();
    }
  }),
);
document.addEventListener("click", (event) => {
  if (!event.target.closest(".export-menu"))
    document.querySelector(".export-menu").open = false;
});
window.addEventListener("hashchange", () =>
  showView(location.hash.slice(1), false),
);
let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (state.data) renderTrend(state.data.summary.trend);
  }, 150);
});

// Language is a display preference. Preserve the current working selection across reload.
try {
  const saved = JSON.parse(
    sessionStorage.getItem("clear_language_switch") || "null",
  );
  sessionStorage.removeItem("clear_language_switch");
  if (saved) {
    for (const key of Object.keys(state.filters))
      if (typeof saved.filters?.[key] === "string")
        state.filters[key] = saved.filters[key];
    if (Number.isInteger(saved.page) && saved.page > 0) state.page = saved.page;
  }
} catch {
  /* Storage can be disabled without preventing normal application use. */
}
$("language-select").addEventListener("change", (event) => {
  const lang = ["en", "ru", "de"].includes(event.target.value)
    ? event.target.value : "en";
  try {
    sessionStorage.setItem(
      "clear_language_switch",
      JSON.stringify({ filters: state.filters, page: state.page }),
    );
  } catch {}
  document.cookie = `clear_language=${lang}; Path=/; Max-Age=31536000; SameSite=Lax`;
  const url = new URL(location.href);
  if (url.searchParams.has("lang")) {
    url.searchParams.set("lang", lang);
    location.assign(url.href);
  } else {
    location.reload();
  }
});

showView(location.hash.slice(1) || "overview", false);
refresh();
