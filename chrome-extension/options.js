/**
 * EALE Options page script.
 * Reads from / writes to chrome.storage.sync.
 */

const DEFAULTS = {
  backendUrl: "http://localhost:8000",
  studentApiKey: "student-alice-key",
  autoPopMinutes: 0,
  allowlist: [
    "file://",
    "localhost",
    "blackboard.com",
    "canvas.instructure.com",
    "moodle.org",
    "notion.site",
  ],
};

let allowlist = [];

// ── Render allowlist ──────────────────────────────────────────────────────────

function renderAllowlist() {
  const el = document.getElementById("allowlistEl");
  el.innerHTML = "";
  allowlist.forEach((pattern, idx) => {
    const item = document.createElement("div");
    item.className = "allowlist-item";
    item.innerHTML = `
      <span>${pattern}</span>
      <button class="del-btn" data-idx="${idx}" title="Remove">×</button>
    `;
    el.appendChild(item);
  });
  el.querySelectorAll(".del-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const i = parseInt(btn.dataset.idx, 10);
      allowlist.splice(i, 1);
      renderAllowlist();
    });
  });
}

// ── Load settings ─────────────────────────────────────────────────────────────

chrome.storage.sync.get(
  ["backendUrl", "studentApiKey", "autoPopMinutes", "allowlist", "useLlmContext", "useLlmGrading"],
  (data) => {
    document.getElementById("backendUrl").value =
      data.backendUrl ?? DEFAULTS.backendUrl;
    document.getElementById("studentApiKey").value =
      data.studentApiKey ?? DEFAULTS.studentApiKey;
    document.getElementById("autoPopMinutes").value =
      data.autoPopMinutes ?? DEFAULTS.autoPopMinutes;
    document.getElementById("useLlmContext").checked =
      data.useLlmContext ?? false;
    document.getElementById("useLlmGrading").checked =
      data.useLlmGrading ?? false;

    allowlist = Array.isArray(data.allowlist) ? [...data.allowlist] : [...DEFAULTS.allowlist];
    renderAllowlist();
  }
);

// ── Add pattern ───────────────────────────────────────────────────────────────

document.getElementById("addPatternBtn").addEventListener("click", () => {
  const input = document.getElementById("newPattern");
  const val = input.value.trim();
  if (val && !allowlist.includes(val)) {
    allowlist.push(val);
    renderAllowlist();
    input.value = "";
  }
});

document.getElementById("newPattern").addEventListener("keydown", (e) => {
  if (e.key === "Enter") document.getElementById("addPatternBtn").click();
});

// ── Save ──────────────────────────────────────────────────────────────────────

document.getElementById("saveBtn").addEventListener("click", () => {
  const settings = {
    backendUrl:    document.getElementById("backendUrl").value.trim()    || DEFAULTS.backendUrl,
    studentApiKey: document.getElementById("studentApiKey").value.trim() || DEFAULTS.studentApiKey,
    autoPopMinutes: parseInt(document.getElementById("autoPopMinutes").value || "0", 10),
    allowlist,
    useLlmContext: document.getElementById("useLlmContext").checked,
    useLlmGrading: document.getElementById("useLlmGrading").checked,
  };

  chrome.storage.sync.set(settings, () => {
    const status = document.getElementById("statusEl");
    status.classList.add("show");
    setTimeout(() => status.classList.remove("show"), 2000);
  });
});
