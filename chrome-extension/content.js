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
    "position:fixed;bottom:24px;right:24px;z-index:2147483647;font-family:system-ui,sans-serif;";
  document.body.appendChild(host);

  const shadow = host.attachShadow({ mode: "open" });

  // ── Inject styles into shadow root ────────────────────────────────────────
  const styleEl = document.createElement("style");
  styleEl.textContent = `
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    /* ── KEYFRAMES ──────────────────────────────────────────────────────── */
    @keyframes eale-slide-up {
      from { opacity: 0; transform: translateY(18px) scale(0.98); }
      to   { opacity: 1; transform: translateY(0)   scale(1); }
    }
    @keyframes eale-fade-in {
      from { opacity: 0; transform: translateY(5px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes eale-ring-pulse {
      0%   { transform: scale(1);    opacity: 0.7; }
      100% { transform: scale(1.65); opacity: 0; }
    }
    @keyframes eale-dot-bounce {
      0%, 80%, 100% { transform: translateY(0);    opacity: 0.3; }
      40%           { transform: translateY(-9px); opacity: 1; }
    }
    @keyframes eale-glow-breathe {
      0%,100% { box-shadow: 0 0 18px rgba(99,102,241,0.4), 0 6px 24px rgba(0,0,0,0.55); }
      50%     { box-shadow: 0 0 32px rgba(99,102,241,0.65), 0 6px 24px rgba(0,0,0,0.55); }
    }

    /* ── FLOATING BUTTON ────────────────────────────────────────────────── */
    #eale-btn-wrap {
      position: relative;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    #eale-btn-ring {
      position: absolute;
      inset: -5px;
      border-radius: 999px;
      border: 1.5px solid rgba(99,102,241,0.55);
      animation: eale-ring-pulse 2.4s ease-out infinite;
      pointer-events: none;
    }
    #eale-btn {
      position: relative;
      z-index: 1;
      background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
      color: #fff;
      border: none;
      border-radius: 999px;
      padding: 10px 20px;
      font-size: 11px;
      font-weight: 700;
      font-family: system-ui, -apple-system, sans-serif;
      cursor: pointer;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      display: flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
      animation: eale-glow-breathe 3s ease-in-out infinite;
      transition: transform 0.15s ease, filter 0.15s ease;
    }
    #eale-btn:hover  { transform: translateY(-2px); filter: brightness(1.1); }
    #eale-btn:active { transform: translateY(0);    filter: brightness(0.95); }

    /* ── PANEL ──────────────────────────────────────────────────────────── */
    #eale-panel {
      background: rgba(9, 9, 18, 0.97);
      backdrop-filter: blur(28px) saturate(180%);
      -webkit-backdrop-filter: blur(28px) saturate(180%);
      border-radius: 20px;
      border: 1px solid rgba(99,102,241,0.18);
      box-shadow:
        0 0 0 1px rgba(255,255,255,0.04) inset,
        0 0 48px rgba(99,102,241,0.14),
        0 28px 72px rgba(0,0,0,0.7);
      width: 384px;
      max-width: calc(100vw - 48px);
      overflow: hidden;
      display: none;
      flex-direction: column;
      font-family: system-ui, -apple-system, sans-serif;
      color: #f1f5f9;
    }
    #eale-panel.open {
      display: flex;
      animation: eale-slide-up 0.24s cubic-bezier(0.22,1,0.36,1) both;
    }

    /* ── PANEL HEADER ───────────────────────────────────────────────────── */
    .panel-header {
      background: rgba(255,255,255,0.025);
      padding: 13px 14px 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid rgba(99,102,241,0.1);
      gap: 8px;
    }
    .header-left {
      display: flex;
      align-items: center;
      gap: 7px;
      min-width: 0;
      flex: 1;
    }
    .header-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #6366f1;
      box-shadow: 0 0 7px rgba(99,102,241,0.9);
      flex-shrink: 0;
    }
    .header-title {
      font-size: 12px;
      font-weight: 800;
      color: #f1f5f9;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      flex-shrink: 0;
    }
    .topic-pill {
      font-size: 10px;
      font-weight: 500;
      color: #64748b;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 999px;
      padding: 2px 8px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 130px;
    }
    .header-right {
      display: flex;
      align-items: center;
      gap: 5px;
      flex-shrink: 0;
    }
    .close-btn {
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.08);
      color: #475569;
      cursor: pointer;
      width: 22px;
      height: 22px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      line-height: 1;
      transition: background 0.12s, color 0.12s, border-color 0.12s;
      padding: 0;
    }
    .close-btn:hover {
      background: rgba(244,63,94,0.14);
      color: #f43f5e;
      border-color: rgba(244,63,94,0.28);
    }

    /* ── PANEL BODY ─────────────────────────────────────────────────────── */
    .panel-body {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 11px;
      animation: eale-fade-in 0.2s ease-out both;
    }

    /* ── QUESTION TEXT ──────────────────────────────────────────────────── */
    .question-text {
      font-size: 14px;
      color: #e2e8f0;
      line-height: 1.7;
      font-weight: 500;
      letter-spacing: -0.01em;
    }

    /* ── RATIONALE ──────────────────────────────────────────────────────── */
    .rationale {
      font-size: 11px;
      color: #334155;
      font-style: italic;
      line-height: 1.5;
      padding: 7px 10px;
      background: rgba(255,255,255,0.025);
      border-radius: 7px;
      border-left: 2px solid rgba(99,102,241,0.3);
    }

    /* ── MCQ OPTIONS ────────────────────────────────────────────────────── */
    .options-list { display: flex; flex-direction: column; gap: 5px; }
    .option-label {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      background: rgba(255,255,255,0.035);
      border: 1px solid rgba(255,255,255,0.07);
      border-left: 3px solid transparent;
      border-radius: 10px;
      cursor: pointer;
      font-size: 13px;
      color: #64748b;
      transition: all 0.13s ease;
      line-height: 1.4;
      user-select: none;
    }
    .option-label:hover {
      background: rgba(99,102,241,0.07);
      border-color: rgba(99,102,241,0.22);
      border-left-color: rgba(99,102,241,0.35);
      color: #c7d2fe;
    }
    .option-label input[type=radio] { display: none; }
    .option-label.selected {
      background: rgba(99,102,241,0.12);
      border-color: rgba(99,102,241,0.28);
      border-left-color: #6366f1;
      color: #e0e7ff;
    }

    /* ── SHORT TEXT INPUT ───────────────────────────────────────────────── */
    .text-input {
      width: 100%;
      padding: 10px 12px;
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(99,102,241,0.18);
      border-radius: 10px;
      font-size: 13px;
      color: #f1f5f9;
      font-family: system-ui, -apple-system, sans-serif;
      outline: none;
      transition: border-color 0.13s, box-shadow 0.13s;
    }
    .text-input::placeholder { color: #334155; }
    .text-input:focus {
      border-color: rgba(99,102,241,0.5);
      box-shadow: 0 0 0 3px rgba(99,102,241,0.09);
    }

    /* ── CONFIDENCE SLIDER ──────────────────────────────────────────────── */
    .confidence-row { display: flex; flex-direction: column; gap: 5px; }
    .confidence-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .confidence-label {
      font-size: 10px;
      color: #334155;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.09em;
    }
    .conf-desc { font-size: 11px; color: #475569; font-style: italic; }
    .slider-row { display: flex; align-items: center; gap: 8px; }
    .slider-row input[type=range] {
      flex: 1;
      -webkit-appearance: none;
      appearance: none;
      height: 4px;
      border-radius: 999px;
      background: rgba(255,255,255,0.08);
      outline: none;
      cursor: pointer;
      transition: background 0.15s;
    }
    .slider-row input[type=range]::-webkit-slider-thumb {
      -webkit-appearance: none;
      appearance: none;
      width: 15px;
      height: 15px;
      border-radius: 50%;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      box-shadow: 0 0 8px rgba(99,102,241,0.7);
      cursor: pointer;
      transition: transform 0.1s, box-shadow 0.1s;
    }
    .slider-row input[type=range]::-webkit-slider-thumb:hover {
      transform: scale(1.25);
      box-shadow: 0 0 14px rgba(99,102,241,0.9);
    }
    .conf-value {
      font-size: 12px;
      font-weight: 800;
      color: #818cf8;
      min-width: 22px;
      text-align: center;
      background: rgba(99,102,241,0.12);
      border: 1px solid rgba(99,102,241,0.2);
      border-radius: 6px;
      padding: 2px 5px;
    }

    /* ── REASONING ──────────────────────────────────────────────────────── */
    .reasoning-toggle {
      font-size: 11px;
      color: #4f46e5;
      cursor: pointer;
      background: none;
      border: none;
      padding: 0;
      font-family: system-ui, -apple-system, sans-serif;
      transition: color 0.12s;
      opacity: 0.8;
    }
    .reasoning-toggle:hover { color: #818cf8; opacity: 1; }
    .reasoning-area {
      width: 100%;
      margin-top: 6px;
      padding: 9px 11px;
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(99,102,241,0.18);
      border-radius: 10px;
      font-size: 12px;
      color: #f1f5f9;
      font-family: system-ui, -apple-system, sans-serif;
      resize: vertical;
      min-height: 58px;
      outline: none;
      display: none;
      transition: border-color 0.13s;
    }
    .reasoning-area::placeholder { color: #334155; }
    .reasoning-area.open { display: block; }
    .reasoning-area:focus { border-color: rgba(99,102,241,0.5); }

    /* ── SUBMIT BUTTON ──────────────────────────────────────────────────── */
    .submit-btn {
      background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%);
      color: #fff;
      border: none;
      border-radius: 10px;
      padding: 12px;
      font-size: 13px;
      font-weight: 700;
      font-family: system-ui, -apple-system, sans-serif;
      letter-spacing: 0.03em;
      cursor: pointer;
      width: 100%;
      transition: transform 0.13s ease, box-shadow 0.13s ease, filter 0.13s ease;
      box-shadow: 0 4px 16px rgba(99,102,241,0.38);
    }
    .submit-btn:hover:not(:disabled) {
      transform: translateY(-1px);
      filter: brightness(1.08);
      box-shadow: 0 0 28px rgba(99,102,241,0.55), 0 8px 22px rgba(0,0,0,0.35);
    }
    .submit-btn:active:not(:disabled) { transform: translateY(0); filter: brightness(0.95); }
    .submit-btn:disabled { opacity: 0.4; cursor: not-allowed; }

    /* ── LOADING (3-dot bounce) ─────────────────────────────────────────── */
    .loading-wrap {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 36px 16px 32px;
      gap: 16px;
    }
    .loading-dots {
      display: flex;
      align-items: center;
      gap: 7px;
    }
    .loading-dots span {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      animation: eale-dot-bounce 1.2s ease-in-out infinite both;
    }
    .loading-dots span:nth-child(1) { animation-delay:   0ms; }
    .loading-dots span:nth-child(2) { animation-delay: 160ms; }
    .loading-dots span:nth-child(3) { animation-delay: 320ms; }
    .loading-text {
      font-size: 12px;
      color: #334155;
      font-weight: 500;
      letter-spacing: 0.02em;
    }

    /* ── RESULT ─────────────────────────────────────────────────────────── */
    .result-block { display: flex; flex-direction: column; gap: 11px; }
    .result-top-row { display: flex; align-items: center; gap: 12px; }
    .result-icon-wrap {
      width: 46px;
      height: 46px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      font-weight: 700;
      flex-shrink: 0;
    }
    .result-icon-wrap.correct {
      background: rgba(16,185,129,0.12);
      color: #10b981;
      box-shadow: 0 0 18px rgba(16,185,129,0.22);
    }
    .result-icon-wrap.incorrect {
      background: rgba(244,63,94,0.12);
      color: #f43f5e;
      box-shadow: 0 0 18px rgba(244,63,94,0.22);
    }
    .result-heading {
      font-size: 16px;
      font-weight: 700;
      color: #f1f5f9;
      letter-spacing: -0.01em;
    }
    .result-explanation {
      font-size: 12px;
      color: #64748b;
      line-height: 1.65;
    }
    .correct-answer-note {
      font-size: 11px;
      color: #475569;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 8px;
      padding: 8px 11px;
    }
    .correct-answer-note span { font-weight: 700; color: #f59e0b; }
    .dus-line {
      font-size: 11px;
      color: #334155;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .dus-line strong { color: #818cf8; font-weight: 800; font-size: 13px; }

    /* ── DONE / ACTION BUTTONS ──────────────────────────────────────────── */
    .done-btn {
      background: rgba(255,255,255,0.05);
      color: #475569;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 10px;
      padding: 10px;
      font-size: 12px;
      font-weight: 600;
      font-family: system-ui, -apple-system, sans-serif;
      cursor: pointer;
      width: 100%;
      transition: background 0.13s, color 0.13s, transform 0.13s;
      letter-spacing: 0.02em;
    }
    .done-btn:hover {
      background: rgba(255,255,255,0.09);
      color: #94a3b8;
      transform: translateY(-1px);
    }

    /* ── ERROR ──────────────────────────────────────────────────────────── */
    .error-msg {
      font-size: 12px;
      color: #fb7185;
      background: rgba(244,63,94,0.08);
      border: 1px solid rgba(244,63,94,0.18);
      padding: 12px 13px;
      border-radius: 10px;
      line-height: 1.6;
    }

    /* ── TASK / MODE BADGES ─────────────────────────────────────────────── */
    .task-badge {
      font-size: 9px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 999px;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      border: 1px solid;
    }
    .task-badge.retest   { color: #fbbf24; background: rgba(251,191,36,0.1);  border-color: rgba(251,191,36,0.22); }
    .task-badge.transfer { color: #a78bfa; background: rgba(167,139,250,0.1); border-color: rgba(167,139,250,0.22); }
    .task-badge.new      { color: #818cf8; background: rgba(129,140,248,0.1); border-color: rgba(129,140,248,0.22); }

    .mode-badge {
      font-size: 9px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 999px;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      border: 1px solid;
    }
    .mode-badge.due-task { color: #fbbf24; background: rgba(251,191,36,0.08);  border-color: rgba(251,191,36,0.18); }
    .mode-badge.llm      { color: #34d399; background: rgba(52,211,153,0.08);  border-color: rgba(52,211,153,0.18); }
    .mode-badge.keyword  { color: #38bdf8; background: rgba(56,189,248,0.08);  border-color: rgba(56,189,248,0.18); }
    .mode-badge.random   { color: #475569; background: rgba(71,85,105,0.08);   border-color: rgba(71,85,105,0.18); }
  `;
  shadow.appendChild(styleEl);

  // ── Render root ────────────────────────────────────────────────────────────
  const container = document.createElement("div");
  container.style.cssText = "display:flex;flex-direction:column;align-items:flex-end;gap:12px;";
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
    if (url.startsWith("file://") || url.includes("localhost")) return true;
    const { allowlist = [] } = settings;
    for (const pattern of allowlist) {
      if (url.includes(pattern)) return true;
    }
    return false;
  }

  // ── Build UI ───────────────────────────────────────────────────────────────

  // Floating button — wrapped in a ring container
  const btnWrap = document.createElement("div");
  btnWrap.id = "eale-btn-wrap";
  const ring = document.createElement("div");
  ring.id = "eale-btn-ring";
  const btn = document.createElement("button");
  btn.id = "eale-btn";
  btn.innerHTML = `⚡ EALE`;
  btnWrap.appendChild(ring);
  btnWrap.appendChild(btn);
  container.appendChild(btnWrap);

  // Panel
  const panel = document.createElement("div");
  panel.id = "eale-panel";
  container.insertBefore(panel, btnWrap);

  function renderPanel(html) {
    panel.innerHTML = html;
    panel.classList.add("open");
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
    const topicHtml = topicName
      ? `<span class="topic-pill">${escHtml(topicName)}</span>`
      : "";
    return `
      <div class="panel-header">
        <div class="header-left">
          <span class="header-dot"></span>
          <span class="header-title">EALE</span>
          ${topicHtml}
        </div>
        <div class="header-right">
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
        <div class="header-left">
          <span class="header-dot"></span>
          <span class="header-title">EALE</span>
        </div>
        <div class="header-right">
          <button class="close-btn" title="Close">✕</button>
        </div>
      </div>
      <div class="loading-wrap">
        <div class="loading-dots"><span></span><span></span><span></span></div>
        <span class="loading-text">Fetching question…</span>
      </div>
    `);
  }

  function showLoadingLLM() {
    state = "loading";
    renderPanel(`
      <div class="panel-header">
        <div class="header-left">
          <span class="header-dot"></span>
          <span class="header-title">EALE</span>
          <span class="topic-pill">AI Reading Page…</span>
        </div>
        <div class="header-right">
          <button class="close-btn" title="Close">✕</button>
        </div>
      </div>
      <div class="loading-wrap">
        <div class="loading-dots"><span></span><span></span><span></span></div>
        <span class="loading-text">Generating question with AI…</span>
      </div>
    `);
  }

  function showError(msg) {
    state = "idle";
    renderPanel(`
      <div class="panel-header">
        <div class="header-left">
          <span class="header-dot" style="background:#f43f5e;box-shadow:0 0 7px rgba(244,63,94,0.85);"></span>
          <span class="header-title">EALE</span>
        </div>
        <div class="header-right">
          <button class="close-btn" title="Close">✕</button>
        </div>
      </div>
      <div class="panel-body">
        <div class="error-msg">${msg}</div>
        <button class="done-btn" id="eale-retry-btn"
          style="background:rgba(99,102,241,0.1);color:#818cf8;border-color:rgba(99,102,241,0.22);">
          Try again
        </button>
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
        ${ctx.rationale ? `<p class="rationale">${escHtml(ctx.rationale)}</p>` : ""}
        <p class="question-text">${escHtml(q.text)}</p>

        ${optionsHtml}

        <div class="confidence-row">
          <div class="confidence-header">
            <span class="confidence-label">Confidence</span>
            <span class="conf-desc" id="eale-conf-desc">${CONF_LABELS[5]}</span>
          </div>
          <div class="slider-row">
            <input type="range" id="eale-conf" min="1" max="10" value="5" />
            <span class="conf-value" id="eale-conf-val">5</span>
          </div>
        </div>

        <div>
          <button class="reasoning-toggle" id="eale-reason-toggle">+ Add reasoning (optional)</button>
          <textarea class="reasoning-area" id="eale-reasoning" placeholder="Why do you think this is correct?"></textarea>
        </div>

        <button class="submit-btn" id="eale-submit">Submit Answer →</button>
      </div>
    `);

    // Confidence slider
    const confSlider = panel.querySelector("#eale-conf");
    const confVal    = panel.querySelector("#eale-conf-val");
    const confDesc   = panel.querySelector("#eale-conf-desc");

    function updateSlider(v) {
      confVal.textContent  = v;
      confDesc.textContent = CONF_LABELS[v] || "";
      const pct = ((v - 1) / 9) * 100;
      confSlider.style.background = `linear-gradient(to right, #6366f1 ${pct}%, rgba(255,255,255,0.08) ${pct}%)`;
    }
    updateSlider(5);
    confSlider.addEventListener("input", () => updateSlider(parseInt(confSlider.value, 10)));

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
      ? `<div class="dus-line">DUS updated → <strong>${data.updated_dus}</strong><span style="color:#334155">/100</span></div>`
      : "";
    renderPanel(`
      ${header(currentContext?.topic_name || "Result", null, currentContext?.mode)}
      <div class="panel-body">
        <div class="result-block">
          <div class="result-top-row">
            <div class="result-icon-wrap ${isCorrect ? "correct" : "incorrect"}">
              ${isCorrect ? "✓" : "✗"}
            </div>
            <div class="result-heading">${isCorrect ? "Correct!" : "Incorrect"}</div>
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
    const reasoning  = panel.querySelector("#eale-reasoning")?.value?.trim() || null;

    const submitBtn = panel.querySelector("#eale-submit");
    if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Submitting…"; }

    state = "submitting";

    try {
      const data = await apiFetch(
        `${settings.backendUrl}/api/v1/extension/submit`,
        {
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
        },
        30000
      );
      showResult(data);
    } catch (err) {
      if (err.message === "AbortError") {
        showError("Submit timed out (30 s). Please try again.");
      } else {
        showError(`Submit failed: ${err.message}`);
      }
    }
  }

  // ── Trigger quiz ───────────────────────────────────────────────────────────

  async function triggerQuiz() {
    if (state === "loading" || state === "submitting") return;

    if (!isAllowed(location.href)) {
      showError(
        "This page is not in your EALE allowlist.<br>" +
        '<code style="background:rgba(255,255,255,0.06);padding:1px 5px;border-radius:4px;font-size:11px;">' +
        escHtml(location.hostname) +
        "</code> — add it in Extension Options."
      );
      return;
    }

    if (settings.useLlmContext) {
      showLoadingLLM();
    } else {
      showLoading();
    }

    try {
      const ctx = await apiFetch(
        `${settings.backendUrl}/api/v1/extension/context`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": settings.studentApiKey,
          },
          body: JSON.stringify({
            page_url:   location.href,
            page_title: document.title || "",
            page_text:  getPageText(),
          }),
        },
        45000
      );
      showQuiz(ctx);
    } catch (err) {
      if (err.message === "AbortError") {
        showError("Request timed out (45 s). Check that the backend is running.");
      } else {
        showError(`Could not fetch question: ${err.message}`);
      }
    }
  }

  // ── API proxy helper ───────────────────────────────────────────────────────
  // Routes fetch through the background service worker so HTTPS pages (YouTube,
  // etc.) don't block the request via their Content Security Policy.

  function apiFetch(url, options, timeoutMs) {
    const ms = timeoutMs || 45000;
    return new Promise(function (resolve, reject) {
      const timer = setTimeout(function () {
        reject(new Error("AbortError"));
      }, ms);
      chrome.runtime.sendMessage(
        { type: "EALE_API_FETCH", url: url, options: options },
        function (response) {
          clearTimeout(timer);
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
            return;
          }
          if (!response) {
            reject(new Error("No response from background"));
            return;
          }
          if (response.error) {
            reject(new Error(response.error));
            return;
          }
          if (!response.ok) {
            try {
              const err = JSON.parse(response.body);
              reject(new Error(err.detail || ("HTTP " + response.status)));
            } catch (_) {
              reject(new Error("HTTP " + response.status));
            }
            return;
          }
          try {
            resolve(JSON.parse(response.body));
          } catch (_) {
            resolve(response.body);
          }
        }
      );
    });
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
        allowlist:     data.allowlist    || ["file://", "localhost", "youtube.com"],
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
