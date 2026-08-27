const api = "/api/v1";

const state = {
  organizations: [],
  procurements: [],
  signals: [],
  selectedOrganizationId: null,
  signalFilter: "all",
};

const elements = {
  healthBadge: document.querySelector("#healthBadge"),
  syncButton: document.querySelector("#syncButton"),
  refreshButton: document.querySelector("#refreshButton"),
  organizationCount: document.querySelector("#organizationCount"),
  procurementCount: document.querySelector("#procurementCount"),
  signalCount: document.querySelector("#signalCount"),
  syncStatus: document.querySelector("#syncStatus"),
  syncDetails: document.querySelector("#syncDetails"),
  organizationSearch: document.querySelector("#organizationSearch"),
  organizationList: document.querySelector("#organizationList"),
  relationshipTitle: document.querySelector("#relationshipTitle"),
  relationshipSummary: document.querySelector("#relationshipSummary"),
  signalFilters: document.querySelector("#signalFilters"),
  signalList: document.querySelector("#signalList"),
  procurementRows: document.querySelector("#procurementRows"),
  toast: document.querySelector("#toast"),
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showToast(message, isError = false) {
  elements.toast.textContent = message;
  elements.toast.classList.toggle("error", isError);
  elements.toast.classList.add("visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => elements.toast.classList.remove("visible"), 3400);
}

async function request(path, options = {}) {
  const response = await fetch(`${api}${path}`, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed with ${response.status}`);
  }
  return response.json();
}

function formatMoney(value, currency = "UAH") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function formatDate(value) {
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" })
    .format(new Date(value));
}

async function checkHealth() {
  try {
    await request("/health");
    elements.healthBadge.className = "health-badge health-ok";
    elements.healthBadge.querySelector("span").textContent = "API online";
  } catch (error) {
    elements.healthBadge.className = "health-badge health-error";
    elements.healthBadge.querySelector("span").textContent = "API offline";
  }
}

async function loadDashboard({ quiet = false } = {}) {
  try {
    const [organizations, procurements, signals] = await Promise.all([
      request("/organizations?limit=200"),
      request("/procurements?limit=200"),
      request("/risk-signals"),
    ]);
    state.organizations = organizations;
    state.procurements = procurements;
    state.signals = signals;
    renderAll();
    if (!quiet) showToast("Dashboard refreshed.");
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderAll() {
  elements.organizationCount.textContent = state.organizations.length;
  elements.procurementCount.textContent = state.procurements.length;
  elements.signalCount.textContent = state.signals.length;
  renderOrganizations();
  renderSignals();
  renderProcurements();
}

function renderOrganizations() {
  const query = elements.organizationSearch.value.trim().toLowerCase();
  const filtered = state.organizations.filter((organization) =>
    `${organization.name} ${organization.registration_code}`.toLowerCase().includes(query)
  );

  if (!filtered.length) {
    elements.organizationList.className = "organization-list empty-state";
    elements.organizationList.innerHTML = `<div><b>No organizations found</b><span>${
      state.organizations.length ? "Try another search." : "Run the demo synchronization first."
    }</span></div>`;
    return;
  }

  elements.organizationList.className = "organization-list";
  elements.organizationList.innerHTML = filtered.map((organization) => `
    <button class="organization-row ${state.selectedOrganizationId === organization.id ? "active" : ""}"
            data-organization-id="${organization.id}">
      <span class="entity-icon">${escapeHtml(organization.name.slice(0, 2).toUpperCase())}</span>
      <span><b>${escapeHtml(organization.name)}</b><small>${escapeHtml(organization.registration_code)}</small></span>
      <span class="row-arrow">›</span>
    </button>
  `).join("");
}

async function selectOrganization(id) {
  state.selectedOrganizationId = id;
  renderOrganizations();
  const organization = state.organizations.find((item) => item.id === id);
  if (!organization) return;

  elements.relationshipTitle.textContent = organization.name;
  elements.relationshipSummary.className = "relationship-summary";
  elements.relationshipSummary.innerHTML = `<div class="empty-state compact"><div><b>Loading relationships</b><span>Aggregating counterparties…</span></div></div>`;

  try {
    const [details, relationships] = await Promise.all([
      request(`/organizations/${id}`),
      request(`/organizations/${id}/relationships`),
    ]);
    const rows = relationships.length
      ? relationships.map((relationship) => `
          <div class="relationship-row">
            <div><b>${escapeHtml(relationship.counterparty_name)}</b><small>${
              relationship.relation_type === "buys_from" ? "Buyer → supplier" : "Supplier → buyer"
            } · ${relationship.procurements_count} record(s)</small></div>
            <span class="relationship-amount">${formatMoney(relationship.total_amount)}</span>
          </div>`).join("")
      : `<div class="empty-state compact"><div><b>No relationships</b><span>This entity has no procurement edges.</span></div></div>`;

    elements.relationshipSummary.innerHTML = `
      <div class="relationship-overview">
        <div><strong>${details.purchases_count}</strong><span>Purchases</span></div>
        <div><strong>${details.sales_count}</strong><span>Sales</span></div>
      </div>
      ${rows}
    `;
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderSignals() {
  const signals = state.signalFilter === "all"
    ? state.signals
    : state.signals.filter((signal) => signal.severity === state.signalFilter);

  if (!signals.length) {
    elements.signalList.className = "signal-grid empty-state";
    elements.signalList.innerHTML = `<div><b>No matching signals</b><span>${
      state.signals.length ? "Change the severity filter." : "Signals will appear after ingestion."
    }</span></div>`;
    return;
  }

  elements.signalList.className = "signal-grid";
  elements.signalList.innerHTML = signals.map((signal) => `
    <article class="signal-card">
      <div class="signal-top">
        <span class="signal-type">${escapeHtml(signal.signal_type.replaceAll("_", " "))}</span>
        <span class="severity severity-${escapeHtml(signal.severity)}">${escapeHtml(signal.severity)}</span>
      </div>
      <p>${escapeHtml(signal.description)}</p>
    </article>
  `).join("");
}

function renderProcurements() {
  if (!state.procurements.length) {
    elements.procurementRows.innerHTML = `<tr><td colspan="6" class="table-empty">No procurement records loaded.</td></tr>`;
    return;
  }
  elements.procurementRows.innerHTML = state.procurements.map((item) => `
    <tr>
      <td>${escapeHtml(item.external_id)}</td>
      <td>${escapeHtml(item.title)}</td>
      <td>${escapeHtml(item.buyer.name)}</td>
      <td>${escapeHtml(item.supplier.name)}</td>
      <td class="amount">${formatMoney(item.amount, item.currency)}</td>
      <td>${formatDate(item.deadline_at)}</td>
    </tr>
  `).join("");
}

async function runSync() {
  const originalLabel = elements.syncButton.querySelector("span").textContent;
  elements.syncButton.disabled = true;
  elements.syncButton.querySelector("span").textContent = "Processing…";
  elements.syncStatus.textContent = "Running";
  elements.syncDetails.textContent = "validating and resolving entities";

  try {
    const result = await request("/sync-runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: "fixtures" }),
    });
    elements.syncStatus.textContent = result.status;
    elements.syncDetails.textContent = `${result.records_created} created · ${result.records_updated} updated`;
    elements.syncButton.querySelector("span").textContent = "Run sync again";
    await loadDashboard({ quiet: true });
    showToast(`Sync completed: ${result.records_created} created, ${result.records_updated} updated.`);
  } catch (error) {
    elements.syncStatus.textContent = "Failed";
    elements.syncDetails.textContent = error.message;
    elements.syncButton.querySelector("span").textContent = originalLabel;
    showToast(error.message, true);
  } finally {
    elements.syncButton.disabled = false;
  }
}

elements.syncButton.addEventListener("click", runSync);
elements.refreshButton.addEventListener("click", () => loadDashboard());
elements.organizationSearch.addEventListener("input", renderOrganizations);
elements.organizationList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-organization-id]");
  if (button) selectOrganization(Number(button.dataset.organizationId));
});
elements.signalFilters.addEventListener("click", (event) => {
  const button = event.target.closest("[data-filter]");
  if (!button) return;
  state.signalFilter = button.dataset.filter;
  elements.signalFilters.querySelectorAll("button").forEach((item) => item.classList.toggle("active", item === button));
  renderSignals();
});

checkHealth();
loadDashboard({ quiet: true });
