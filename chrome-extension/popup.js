const API_BASE = "http://localhost:8000";

// ── Init: check if already logged in ─────────────────────────────────────────

chrome.storage.sync.get(["studentApiKey", "studentId", "studentName"], (data) => {
  if (data.studentApiKey && data.studentId) {
    showMainView(data.studentName || `Student #${data.studentId}`, data.studentApiKey, data.studentId);
  } else {
    showAuthView();
  }
});

// ── View switchers ────────────────────────────────────────────────────────────

function showAuthView() {
  document.getElementById("authView").classList.add("active");
  document.getElementById("mainView").classList.remove("active");
}

function showMainView(name, key, id) {
  document.getElementById("studentName").textContent = name;
  document.getElementById("studentKey").textContent  = key;
  document.getElementById("authView").classList.remove("active");
  document.getElementById("mainView").classList.add("active");

  // wire dashboard btn
  document.getElementById("dashboardBtn").onclick = () => {
    chrome.tabs.create({ url: `http://localhost:3000/student/${id}` });
  };
}

// ── Auth tabs ─────────────────────────────────────────────────────────────────

document.querySelectorAll(".auth-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".auth-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".auth-form").forEach(f => f.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(tab.dataset.tab + "Form").classList.add("active");
  });
});

// ── Login ─────────────────────────────────────────────────────────────────────

document.getElementById("loginBtn").addEventListener("click", async () => {
  const key = document.getElementById("loginKey").value.trim();
  if (!key) return;

  const btn = document.getElementById("loginBtn");
  btn.disabled = true;
  setStatus("loginStatus", "Checking...", "");

  try {
    const res = await fetch(`${API_BASE}/api/v1/students/me`, {
      headers: { "X-API-Key": key },
    });
    if (!res.ok) throw new Error("Invalid API key");
    const student = await res.json();
    chrome.storage.sync.set(
      { studentApiKey: key, studentId: student.id, studentName: student.name },
      () => showMainView(student.name, key, student.id)
    );
  } catch (e) {
    setStatus("loginStatus", e.message || "Login failed", "err");
  } finally {
    btn.disabled = false;
  }
});

// ── Sign Up ───────────────────────────────────────────────────────────────────

document.getElementById("signupBtn").addEventListener("click", async () => {
  const name  = document.getElementById("signupName").value.trim();
  const email = document.getElementById("signupEmail").value.trim();
  if (!name || !email) {
    setStatus("signupStatus", "Please fill in all fields", "err");
    return;
  }

  const btn = document.getElementById("signupBtn");
  btn.disabled = true;
  setStatus("signupStatus", "Creating account...", "");

  try {
    const res = await fetch(`${API_BASE}/api/v1/students/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, role: "student" }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Error ${res.status}`);
    }
    const student = await res.json();

    // show key reveal panel
    document.getElementById("newApiKey").textContent = student.api_key;
    document.getElementById("keyReveal").style.display = "flex";
    document.getElementById("keyReveal").style.flexDirection = "column";
    document.getElementById("keyReveal").style.gap = "8px";
    btn.style.display = "none";
    setStatus("signupStatus", "", "");

    // store immediately
    chrome.storage.sync.set({
      studentApiKey: student.api_key,
      studentId:    student.id,
      studentName:  student.name,
    });

    document.getElementById("continueBtn").onclick = () => {
      showMainView(student.name, student.api_key, student.id);
    };
  } catch (e) {
    setStatus("signupStatus", e.message || "Sign up failed", "err");
  } finally {
    btn.disabled = false;
  }
});

// ── Switch / Logout ───────────────────────────────────────────────────────────

document.getElementById("switchBtn").addEventListener("click", () => {
  chrome.storage.sync.remove(["studentApiKey", "studentId", "studentName"], () => {
    // reset signup form
    document.getElementById("signupName").value  = "";
    document.getElementById("signupEmail").value = "";
    document.getElementById("keyReveal").style.display = "none";
    document.getElementById("signupBtn").style.display = "";
    document.getElementById("loginKey").value = "";
    setStatus("loginStatus", "", "");
    setStatus("signupStatus", "", "");
    showAuthView();
  });
});

// ── Quiz trigger ──────────────────────────────────────────────────────────────

document.getElementById("quizBtn").addEventListener("click", () => {
  const btn = document.getElementById("quizBtn");
  btn.disabled = true;
  setStatus("quizStatus", "Triggering quiz...", "");

  chrome.runtime.sendMessage({ type: "EALE_TRIGGER_QUIZ" }, (res) => {
    btn.disabled = false;
    if (res?.ok) {
      setStatus("quizStatus", "Quiz triggered!", "ok");
    } else {
      setStatus("quizStatus", res?.error || "Failed — is this page allowed?", "err");
    }
  });
});

// ── Options ───────────────────────────────────────────────────────────────────

document.getElementById("optionsLink").addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

// ── Helpers ───────────────────────────────────────────────────────────────────

function setStatus(id, msg, cls) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.className = "status-msg " + cls;
}
