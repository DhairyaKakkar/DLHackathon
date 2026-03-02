/**
 * EALE Content Script
 *
 * Injects a Shadow-DOM overlay widget onto the page.
 * All styles are encapsulated — zero risk of colliding with host-page CSS.
 *
 * State machine:
 *   idle ──► loading ──► quiz ──► submitting ──► result
 *              │                                    │
 *              └──────────── error ◄────────────────┘
 */

(function () {
  "use strict";

  // ── Guard: don't inject twice ──────────────────────────────────────────────
  if (document.getElementById("eale-shadow-host")) return;

  // ── State ─────────────────────────────────────────────────────────────────
  let state = "idle";
  let settings = {};
  let currentContext = null; // ExtensionContextOut from backend

  // ── Create Shadow DOM host ─────────────────────────────────────────────────
  const host = document.createElement("div");
  host.id = "eale-shadow-host";
  host.style.cssText =
    "position:fixed;bottom:20px;right:20px;z-index:2147483647;font-family:sans-serif;";
  document.body.appendChild(host);

  const shadow = host.attachShadow({ mode: "open" });

  // ── Inject styles into shadow root ────────────────────────────────────────
  const styleEl = document.createElement("style");
  styleEl.textContent = `
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    #eale-btn {
      background: #4f46e5;
      color: #fff;
      border: none;
      border-radius: 24px;
      padding: 10px 18px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(79,70,229,.45);
      display: flex;
      align-items: center;
      gap: 6px;
      transition: background .15s, transform .1s;
      white-space: nowrap;
    }
    #eale-btn:hover { background: #4338ca; transform: translateY(-1px); }
    #eale-btn .dot {
      width: 8px; height: 8px; border-radius: 50%; background: #a5f3fc;
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%,100% { opacity:1; } 50% { opacity:.4; }
    }

    #eale-panel {
      background: #fff;
      border-radius: 16px;
      box-shadow: 0 8px 30px rgba(0,0,0,.18);
      width: 360px;
      max-width: calc(100vw - 40px);
      overflow: hidden;
      display: none;
      flex-direction: column;
      animation: slideUp .2s ease;
    }
    #eale-panel.open { display: flex; }
    @keyframes slideUp {
      from { opacity:0; transform:translateY(12px); }
      to   { opacity:1; transform:translateY(0); }
    }

    .panel-header {
      background: #4f46e5;
      color: #fff;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .panel-header .title { font-size: 13px; font-weight: 700; }
    .panel-header .meta  { font-size: 11px; opacity: .75; margin-top: 1px; }
    .close-btn {
      background: none; border: none; color: rgba(255,255,255,.7);
      cursor: pointer; font-size: 18px; line-height: 1;
      padding: 0 2px;
    }
    .close-btn:hover { color: #fff; }

    .panel-body { padding: 16px; display: flex; flex-direction: column; gap: 12px; }

    .question-text {
      font-size: 13px; color: #1e1b4b; line-height: 1.55; font-weight: 500;
    }

    /* MCQ */
    .options-list { display: flex; flex-direction: column; gap: 6px; }
    .option-label {
      display: flex; align-items: center; gap: 8px;
      padding: 8px 10px; border: 1.5px solid #e5e7eb; border-radius: 8px;
      cursor: pointer; font-size: 12px; color: #374151;
      transition: border-color .12s, background .12s;
    }
    .option-label:hover { border-color: #a5b4fc; background: #f5f3ff; }
    .option-label input[type=radio] { accent-color: #4f46e5; }
    .option-label.selected { border-color: #4f46e5; background: #eef2ff; color: #3730a3; }

    /* Short text */
    .text-input {
      width: 100%; padding: 8px 10px; border: 1.5px solid #e5e7eb;
      border-radius: 8px; font-size: 13px; outline: none;
      transition: border-color .12s;
    }
    .text-input:focus { border-color: #4f46e5; }

    /* Confidence slider */
    .confidence-row { display: flex; flex-direction: column; gap: 4px; }
    .confidence-label { font-size: 11px; color: #6b7280; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
    .slider-row { display: flex; align-items: center; gap: 8px; }
    .slider-row input[type=range] {
      flex: 1; accent-color: #4f46e5; height: 4px;
    }
    .conf-value { font-size: 12px; font-weight: 700; color: #4f46e5; min-width: 28px; text-align: right; }
    .conf-desc { font-size: 11px; color: #9ca3af; margin-top: 1px; }

    /* Reasoning */
    .reasoning-toggle {
      font-size: 11px; color: #6b7280; cursor: pointer;
      background: none; border: none; padding: 0; text-decoration: underline;
    }
    .reasoning-area {
      width: 100%; padding: 7px 10px; border: 1.5px solid #e5e7eb;
      border-radius: 8px; font-size: 12px; resize: vertical; min-height: 56px;
      outline: none; display: none;
    }
    .reasoning-area.open { display: block; }

    /* Submit */
    .submit-btn {
      background: #4f46e5; color: #fff; border: none; border-radius: 8px;
      padding: 10px; font-size: 13px; font-weight: 600; cursor: pointer;
      transition: background .12s;
    }
    .submit-btn:hover:not(:disabled) { background: #4338ca; }
    .submit-btn:disabled { opacity: .55; cursor: not-allowed; }

    /* Loading */
    .spinner {
      display: flex; align-items: center; justify-content: center; padding: 24px;
      color: #6b7280; font-size: 13px; gap: 8px;
    }
    .spin { width: 18px; height: 18px; border: 2px solid #e5e7eb; border-top-color: #4f46e5; border-radius: 50%; animation: spin .6s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* Result */
    .result-block { padding: 4px 0; }
    .result-badge {
      display: inline-flex; align-items: center; gap: 5px;
      padding: 5px 10px; border-radius: 20px; font-size: 12px; font-weight: 700;
      margin-bottom: 8px;
    }
    .result-badge.correct   { background: #dcfce7; color: #15803d; }
    .result-badge.incorrect { background: #fee2e2; color: #b91c1c; }
    .result-explanation { font-size: 12px; color: #4b5563; line-height: 1.55; }
    .correct-answer-note { margin-top: 8px; font-size: 11px; color: #6b7280; }
    .correct-answer-note span { font-weight: 700; color: #374151; }

    .done-btn {
      background: #f3f4f6; color: #374151; border: none; border-radius: 8px;
      padding: 9px; font-size: 12px; font-weight: 600; cursor: pointer;
      transition: background .12s; margin-top: 4px;
    }
    .done-btn:hover { background: #e5e7eb; }

    /* Error */
    .error-msg {
      font-size: 12px; color: #b91c1c; background: #fee2e2; padding: 10px 12px;
      border-radius: 8px; line-height: 1.5;
    }

    /* Task + mode badges */
    .task-badge {
      font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 12px;
      text-transform: uppercase; letter-spacing: .04em;
    }
    .task-badge.retest   { background: #fef3c7; color: #92400e; }
    .task-badge.transfer { background: #ede9fe; color: #5b21b6; }
    .task-badge.new      { background: #dbeafe; color: #1d4ed8; }

    .mode-badge {
      font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 10px;
      text-transform: uppercase; letter-spacing: .04em; opacity: .85;
    }
    .mode-badge.due-task { background: #fde68a; color: #78350f; }
    .mode-badge.llm      { background: #a7f3d0; color: #065f46; }
    .mode-badge.keyword  { background: #bfdbfe; color: #1e40af; }
    .mode-badge.random   { background: #e5e7eb; color: #4b5563; }

    .rationale { font-size: 11px; color: #6b7280; font-style: italic; }
  `;
  shadow.appendChild(styleEl);

  // ── Render root ────────────────────────────────────────────────────────────
  const container = document.createElement("div");
  container.style.cssText = "display:flex;flex-direction:column;align-items:flex-end;gap:10px;";
  shadow.appendChild(container);

  // ── Helpers ────────────────────────────────────────────────────────────────

  const CONF_LABELS = {
    1: "Guessing", 2: "Very unsure", 3: "Unsure", 4: "Somewhat unsure",
    5: "Neutral", 6: "Somewhat sure", 7: "Fairly sure", 8: "Confident",
    9: "Very confident", 10: "Certain",
  };

  function getPageText() {
    const el = document.body;
    if (!el) return "";
    return (el.innerText || el.textContent || "").slice(0, 2000);
  }

  function isAllowed(url) {
    // Always allow local files and localhost
    if (url.startsWith("file://") || url.includes("localhost")) return true;
    const { allowlist = [] } = settings;
    for (const pattern of allowlist) {
      if (url.includes(pattern)) return true;
    }
    return false;
  }

  // ── Build UI ───────────────────────────────────────────────────────────────

  // Floating button
  const btn = document.createElement("button");
  btn.id = "eale-btn";
  btn.innerHTML = `<span class="dot"></span> EALE Check`;
  container.appendChild(btn);

  // Panel
  const panel = document.createElement("div");
  panel.id = "eale-panel";
  container.insertBefore(panel, btn);

  function renderPanel(html) {
    panel.innerHTML = html;
    panel.classList.add("open");
    // Re-attach close button listener
    const closeBtn = panel.querySelector(".close-btn");
    if (closeBtn) closeBtn.addEventListener("click", closePanel);
  }

  function closePanel() {
    panel.classList.remove("open");
    panel.innerHTML = "";
    state = "idle";
    currentContext = null;
  }

  const MODE_META = {
    DUE_TASK: { cls: "due-task", label: "Due Task" },
    LLM:      { cls: "llm",      label: "AI Generated" },
    KEYWORD:  { cls: "keyword",  label: "Keyword Match" },
    RANDOM:   { cls: "random",   label: "Random" },
  };

  function header(topicName, taskType, mode) {
    const badgeClass = taskType
      ? (taskType.toLowerCase() === "retest" ? "retest" : "transfer")
      : "new";
    const badgeLabel = taskType || "New";
    const modeMeta = MODE_META[mode] || MODE_META.RANDOM;
    return `
      <div class="panel-header">
        <div>
          <div class="title">EALE Learning Check</div>
          <div class="meta">${topicName}</div>
        </div>
        <div style="display:flex;align-items:center;gap:6px;">
          <span class="mode-badge ${modeMeta.cls}">${modeMeta.label}</span>
          <span class="task-badge ${badgeClass}">${badgeLabel}</span>
          <button class="close-btn" title="Close">✕</button>
        </div>
      </div>
    `;
  }

  // ── Screens ────────────────────────────────────────────────────────────────

  function showLoading() {
    state = "loading";
    renderPanel(`
      <div class="panel-header">
        <div><div class="title">EALE Learning Check</div></div>
        <button class="close-btn" title="Close">✕</button>
      </div>
      <div class="spinner">
        <div class="spin"></div> Fetching question…
      </div>
    `);
  }

  function showLoadingLLM() {
    state = "loading";
    renderPanel(`
      <div class="panel-header">
        <div>
          <div class="title">EALE Learning Check</div>
          <div class="meta" style="opacity:.7">Asking AI to read the page…</div>
        </div>
        <button class="close-btn" title="Close">✕</button>
      </div>
      <div class="spinner">
        <div class="spin"></div> Generating question with AI…
      </div>
    `);
  }

  function showError(msg) {
    state = "idle";
    renderPanel(`
      <div class="panel-header">
        <div><div class="title">EALE</div></div>
        <button class="close-btn" title="Close">✕</button>
      </div>
      <div class="panel-body">
        <div class="error-msg">${msg}</div>
        <button class="done-btn" id="eale-retry-btn">Try again</button>
      </div>
    `);
    panel.querySelector("#eale-retry-btn")?.addEventListener("click", triggerQuiz);
  }

  function showQuiz(ctx) {
    state = "quiz";
    currentContext = ctx;
    const q = ctx.question;
    const isMcq = q.question_type === "MCQ";
    const mode = ctx.mode || "RANDOM";

    const optionsHtml = isMcq
      ? `<div class="options-list" id="eale-options">
          ${q.options.map((opt) => `
            <label class="option-label">
              <input type="radio" name="eale-ans" value="${escHtml(opt)}" />
              ${escHtml(opt)}
            </label>
          `).join("")}
        </div>`
      : `<input class="text-input" id="eale-text-ans" type="text" placeholder="Type your answer…" autocomplete="off" />`;

    renderPanel(`
      ${header(ctx.topic_name, ctx.task_type, mode)}
      <div class="panel-body">
        <p class="rationale">${escHtml(ctx.rationale)}</p>
        <p class="question-text">${escHtml(q.text)}</p>

        ${optionsHtml}

        <div class="confidence-row">
          <span class="confidence-label">Confidence</span>
          <div class="slider-row">
            <input type="range" id="eale-conf" min="1" max="10" value="5" />
            <span class="conf-value" id="eale-conf-val">5</span>
          </div>
          <span class="conf-desc" id="eale-conf-desc">${CONF_LABELS[5]}</span>
        </div>

        <div>
          <button class="reasoning-toggle" id="eale-reason-toggle">+ Add reasoning (optional)</button>
          <textarea class="reasoning-area" id="eale-reasoning" placeholder="Why do you think this is correct?"></textarea>
        </div>

        <button class="submit-btn" id="eale-submit">Submit Answer</button>
      </div>
    `);

    // Confidence slider
    const confSlider = panel.querySelector("#eale-conf");
    const confVal = panel.querySelector("#eale-conf-val");
    const confDesc = panel.querySelector("#eale-conf-desc");
    confSlider.addEventListener("input", () => {
      const v = parseInt(confSlider.value, 10);
      confVal.textContent = v;
      confDesc.textContent = CONF_LABELS[v] || "";
    });

    // MCQ radio highlight
    if (isMcq) {
      panel.querySelectorAll(".option-label").forEach((label) => {
        label.querySelector("input").addEventListener("change", () => {
          panel.querySelectorAll(".option-label").forEach((l) => l.classList.remove("selected"));
          label.classList.add("selected");
        });
      });
    }

    // Reasoning toggle
    panel.querySelector("#eale-reason-toggle")?.addEventListener("click", () => {
      const area = panel.querySelector("#eale-reasoning");
      area.classList.toggle("open");
      if (area.classList.contains("open")) area.focus();
    });

    // Submit
    panel.querySelector("#eale-submit")?.addEventListener("click", handleSubmit);
  }

  function showResult(data) {
    state = "idle";
    const isCorrect = data.correct;
    const dusLine = data.updated_dus != null
      ? `<p style="font-size:11px;color:#6b7280;margin-top:8px;">Updated DUS: <strong style="color:#4f46e5">${data.updated_dus}</strong>/100</p>`
      : "";
    renderPanel(`
      ${header(currentContext?.topic_name || "Result", null, currentContext?.mode)}
      <div class="panel-body">
        <div class="result-block">
          <div class="result-badge ${isCorrect ? "correct" : "incorrect"}">
            ${isCorrect ? "✓ Correct" : "✗ Incorrect"}
          </div>
          <p class="result-explanation">${escHtml(data.explanation)}</p>
          ${!isCorrect ? `<p class="correct-answer-note">Correct answer: <span>${escHtml(data.correct_answer)}</span></p>` : ""}
          ${dusLine}
        </div>
        <button class="done-btn" id="eale-done-btn">Done</button>
      </div>
    `);
    panel.querySelector("#eale-done-btn")?.addEventListener("click", closePanel);
  }

  // ── Submit handler ─────────────────────────────────────────────────────────

  async function handleSubmit() {
    if (state !== "quiz" || !currentContext) return;

    const q = currentContext.question;
    const isMcq = q.question_type === "MCQ";

    let answer = "";
    if (isMcq) {
      const checked = panel.querySelector("input[name='eale-ans']:checked");
      if (!checked) { alert("Please select an answer."); return; }
      answer = checked.value;
    } else {
      answer = (panel.querySelector("#eale-text-ans")?.value || "").trim();
      if (!answer) { alert("Please type an answer."); return; }
    }

    const confidence = parseInt(panel.querySelector("#eale-conf")?.value || "5", 10);
    const reasoning = panel.querySelector("#eale-reasoning")?.value?.trim() || null;

    const submitBtn = panel.querySelector("#eale-submit");
    if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Submitting…"; }

    state = "submitting";

    try {
      const res = await fetch(`${settings.backendUrl}/api/v1/extension/submit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": settings.studentApiKey,
        },
        body: JSON.stringify({
          question_id: q.id,
          task_id: currentContext.task_id,
          answer,
          confidence,
          reasoning,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      showResult(data);
    } catch (err) {
      showError(`Submit failed: ${err.message}`);
    }
  }

  // ── Trigger quiz ───────────────────────────────────────────────────────────

  async function triggerQuiz() {
    if (state === "loading" || state === "submitting") return;

    if (!isAllowed(location.href)) {
      showError(
        "This page is not in your EALE allowlist.<br>" +
        'Add <code style="background:#f3f4f6;padding:1px 4px;border-radius:3px">' +
        escHtml(location.hostname) +
        "</code> in Extension Options."
      );
      return;
    }

    if (settings.useLlmContext) {
      showLoadingLLM();
    } else {
      showLoading();
    }

    try {
      const res = await fetch(`${settings.backendUrl}/api/v1/extension/context`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": settings.studentApiKey,
        },
        body: JSON.stringify({
          page_url: location.href,
          page_title: document.title || "",
          page_text: getPageText(),
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const ctx = await res.json();
      showQuiz(ctx);
    } catch (err) {
      showError(`Could not fetch question: ${err.message}`);
    }
  }

  // ── HTML escaping ──────────────────────────────────────────────────────────

  function escHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ── Button click ───────────────────────────────────────────────────────────

  btn.addEventListener("click", () => {
    if (panel.classList.contains("open")) {
      closePanel();
    } else {
      triggerQuiz();
    }
  });

  // ── Listen for messages from background / popup ───────────────────────────

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === "EALE_TRIGGER_QUIZ" || msg.type === "EALE_AUTO_POP") {
      triggerQuiz();
    }
  });

  // ── Load settings from storage ────────────────────────────────────────────

  chrome.storage.sync.get(
    ["backendUrl", "studentApiKey", "studentId", "allowlist", "useLlmContext", "useLlmGrading"],
    (data) => {
      settings = {
        backendUrl:    data.backendUrl    || "http://localhost:8000",
        studentApiKey: data.studentApiKey || "student-alice-key",
        studentId:     data.studentId    || 1,
        allowlist:     data.allowlist    || ["file://", "localhost"],
        useLlmContext: data.useLlmContext || false,
        useLlmGrading: data.useLlmGrading || false,
      };
    }
  );

  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "sync") return;
    if (changes.backendUrl)    settings.backendUrl    = changes.backendUrl.newValue;
    if (changes.studentApiKey) settings.studentApiKey = changes.studentApiKey.newValue;
    if (changes.studentId)     settings.studentId     = changes.studentId.newValue;
    if (changes.allowlist)     settings.allowlist     = changes.allowlist.newValue;
    if (changes.useLlmContext) settings.useLlmContext = changes.useLlmContext.newValue;
    if (changes.useLlmGrading) settings.useLlmGrading = changes.useLlmGrading.newValue;
  });

})();
