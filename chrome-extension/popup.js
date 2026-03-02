/**
 * EALE Popup script.
 */

const DEMO_STUDENTS = {
  "student-alice-key": { name: "Alice Chen", id: 1 },
  "student-bob-key":   { name: "Bob Martinez", id: 2 },
};

// ── Load current student ───────────────────────────────────────────────────

chrome.storage.sync.get(["studentApiKey", "studentId"], (data) => {
  const key  = data.studentApiKey || "student-alice-key";
  const name = DEMO_STUDENTS[key]?.name || `Student #${data.studentId || "?"}`;
  document.getElementById("studentName").textContent = name;
  document.getElementById("studentKey").textContent  = key;
  markActiveBtn(key);
});

function markActiveBtn(key) {
  document.querySelectorAll(".qs-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.key === key);
  });
}

// ── Quick switch ──────────────────────────────────────────────────────────

document.querySelectorAll(".qs-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const key  = btn.dataset.key;
    const name = btn.dataset.name;
    const id   = DEMO_STUDENTS[key]?.id;
    chrome.storage.sync.set({ studentApiKey: key, studentId: id }, () => {
      document.getElementById("studentName").textContent = name;
      document.getElementById("studentKey").textContent  = key;
      markActiveBtn(key);
      showStatus("Switched to " + name, "ok");
    });
  });
});

// ── Trigger quiz ──────────────────────────────────────────────────────────

document.getElementById("quizBtn").addEventListener("click", () => {
  const btn = document.getElementById("quizBtn");
  btn.disabled = true;
  showStatus("Triggering quiz…", "");

  chrome.runtime.sendMessage({ type: "EALE_TRIGGER_QUIZ" }, (res) => {
    btn.disabled = false;
    if (res?.ok) {
      showStatus("Quiz triggered!", "ok");
    } else {
      showStatus(res?.error || "Failed — is this page allowed?", "err");
    }
  });
});

// ── Options link ──────────────────────────────────────────────────────────

document.getElementById("optionsLink").addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

// ── Status helper ─────────────────────────────────────────────────────────

function showStatus(msg, cls) {
  const el = document.getElementById("statusMsg");
  el.textContent = msg;
  el.className = "status-msg " + cls;
}
