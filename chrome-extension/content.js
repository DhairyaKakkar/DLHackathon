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
  let _handwrittenB64 = null; // base64 image from handwriting upload
  let _answerPasted = false;

  // ── Learn It state ─────────────────────────────────────────────────────────
  let _lessonQuizQueue = [];
  let _activeAudio = null;  // TTS narration Audio object

  // ── Attention monitoring state ─────────────────────────────────────────────
  let _attentionStream = null, _attentionVideo = null;
  let _attentionTimer = null, _faceAbsentSince = null;
  const CV_URL = "http://localhost:8001";
  const ABSENT_QUIZ_MS = 20000;

  // ── Video quiz state ───────────────────────────────────────────────────────
  let _activeVideo = null;         // video element currently being quizzed on
  let _ealePausingVideo = false;   // true while EALE itself triggers .pause()
  let _videoDifficultyTimer = null;
  let _videoPrevTime = 0;
  const VIDEO_DIFFICULTY_INTERVAL_MS = 3 * 60 * 1000; // 3 min passive scan
  const VIDEO_REWIND_THRESHOLD_S = 5;                  // >5s backward = rewind

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

    /* Handwriting upload */
    .upload-btn {
      display: inline-block; padding: 7px 12px; border: 1.5px solid #4f46e5;
      border-radius: 8px; font-size: 12px; font-weight: 600; color: #4f46e5;
      cursor: pointer; text-align: center; transition: background .12s;
    }
    .upload-btn:hover { background: #eef2ff; }
    .remove-img-btn { display: block; }

    /* Video quiz mode badge */
    .video-hint {
      font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 12px;
      background: #fce7f3; color: #9d174d;
      text-transform: uppercase; letter-spacing: .04em;
    }

    /* ── Learn It — Video ── */
    #eale-panel.lesson-mode { width: 480px; }
    .lesson-nav { background:none; border:1.5px solid #e5e7eb; border-radius:7px; padding:5px 12px; font-size:12px; font-weight:600; color:#4b5563; cursor:pointer; transition:background .1s; }
    .lesson-nav:hover { background:#f3f4f6; }
    .lesson-nav.primary { background:#4f46e5; color:#fff; border-color:#4f46e5; }
    .lesson-nav.primary:hover { background:#4338ca; }
    .learn-it-btn { background:#f0fdf4; color:#15803d; border:1.5px solid #86efac; border-radius:8px; padding:9px; font-size:12px; font-weight:600; cursor:pointer; transition:background .1s; width:100%; margin-top:4px; }
    .learn-it-btn:hover { background:#dcfce7; }
    .mode-badge.learn-it { background:#fce7f3; color:#9d174d; }
    #eale-audio-btn { background:none; border:1.5px solid #e5e7eb; border-radius:7px; padding:5px 12px; font-size:12px; font-weight:600; color:#4b5563; cursor:pointer; transition:background .1s; }
    #eale-audio-btn:hover { background:#f3f4f6; }

    /* Attention button states */
    #eale-btn.attention-absent {
      background: #dc2626;
      box-shadow: 0 4px 14px rgba(220,38,38,.5);
      animation: pulse-red 1s infinite;
    }
    @keyframes pulse-red {
      0%,100% { opacity:1; } 50% { opacity:.7; }
    }
  `;
  shadow.appendChild(styleEl);

  // ── Render root ────────────────────────────────────────────────────────────
  const container = document.createElement("div");
  container.style.cssText = "display:flex;flex-direction:column;align-items:flex-end;gap:10px;";
  shadow.appendChild(container);

  // Stop ALL keyboard events from leaking out of the shadow DOM to the host
  // page — prevents YouTube/video player shortcuts (space, m, k, arrows, etc.)
  // firing while the student is typing or interacting with the quiz panel
  shadow.addEventListener("keydown",  (e) => e.stopPropagation(), true);
  shadow.addEventListener("keyup",    (e) => e.stopPropagation(), true);
  shadow.addEventListener("keypress", (e) => e.stopPropagation(), true);

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

  // Floating buttons row
  const btnRow = document.createElement("div");
  btnRow.style.cssText = "display:flex;gap:6px;align-items:center;justify-content:flex-end;";

  const btn = document.createElement("button");
  btn.id = "eale-btn";
  btn.innerHTML = `<span class="dot"></span> EALE Check`;

  const learnBtn = document.createElement("button");
  learnBtn.id = "eale-learn-floating";
  learnBtn.innerHTML = `📚`;
  learnBtn.title = "Learn this topic";
  learnBtn.style.cssText = `
    background:#059669;color:#fff;border:none;border-radius:24px;
    padding:10px 13px;font-size:14px;cursor:pointer;
    box-shadow:0 4px 14px rgba(5,150,105,.4);
    transition:background .15s,transform .1s;
  `;
  learnBtn.onmouseenter = () => { learnBtn.style.background = "#047857"; learnBtn.style.transform = "translateY(-1px)"; };
  learnBtn.onmouseleave = () => { learnBtn.style.background = "#059669"; learnBtn.style.transform = ""; };

  btnRow.appendChild(learnBtn);
  btnRow.appendChild(btn);
  container.appendChild(btnRow);

  // Panel
  const panel = document.createElement("div");
  panel.id = "eale-panel";
  container.insertBefore(panel, btnRow);

  function renderPanel(html) {
    panel.innerHTML = html;
    panel.classList.add("open");
    // Re-attach close button listener
    const closeBtn = panel.querySelector(".close-btn");
    if (closeBtn) closeBtn.addEventListener("click", closePanel);
  }

  function closePanel() {
    panel.classList.remove("open");
    panel.classList.remove("lesson-mode");
    panel.innerHTML = "";
    state = "idle";
    currentContext = null;
    // Resume video if EALE paused it for a quiz
    if (_activeVideo && !_activeVideo.ended) {
      _activeVideo.play().catch(() => {});
    }
    _activeVideo = null;
    // Clean up lesson state
    if (_activeAudio) { _activeAudio.pause(); _activeAudio = null; }
    _lessonQuizQueue = [];
  }

  const MODE_META = {
    DUE_TASK: { cls: "due-task", label: "Due Task" },
    LLM:      { cls: "llm",      label: "AI Generated" },
    KEYWORD:  { cls: "keyword",  label: "Keyword Match" },
    RANDOM:   { cls: "random",   label: "Random" },
    LEARN_IT: { cls: "learn-it", label: "Learn It" },
  };

  const VIDEO_HINT_LABEL = {
    REWIND:           "⏪ Rewound",
    MANUAL_PAUSE:     "⏸ Paused",
    DIFFICULTY:       "🧠 Dense Concept",
    ATTENTION_RETURN: "👀 Welcome Back",
  };

  function header(topicName, taskType, mode, contextHint) {
    const badgeClass = taskType
      ? (taskType.toLowerCase() === "retest" ? "retest" : "transfer")
      : "new";
    const badgeLabel = taskType || "New";
    const modeMeta = MODE_META[mode] || MODE_META.RANDOM;
    const videoHint = contextHint && VIDEO_HINT_LABEL[contextHint]
      ? `<span class="video-hint">${VIDEO_HINT_LABEL[contextHint]}</span>`
      : "";
    return `
      <div class="panel-header">
        <div>
          <div class="title">EALE Learning Check</div>
          <div class="meta">${topicName}</div>
        </div>
        <div style="display:flex;align-items:center;gap:6px;">
          ${videoHint}
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
    _handwrittenB64 = null; // reset on each new quiz
    _answerPasted = false;
    const q = ctx.question;
    const isMcq = q.question_type === "MCQ";
    const mode = ctx.mode || "RANDOM";

    const handwritingHtml = !isMcq ? `
      <div style="text-align:center;font-size:11px;color:#9ca3af;margin:2px 0">— or —</div>
      <label class="upload-btn" for="eale-file-input" id="eale-upload-label">
        📷 Upload handwritten answer
      </label>
      <input type="file" id="eale-file-input" accept="image/*" style="display:none" />
      <div id="eale-img-preview" style="display:none;margin-top:6px;">
        <img id="eale-preview-img" style="max-width:100%;border-radius:6px;" />
        <button class="remove-img-btn" id="eale-remove-img"
                style="font-size:11px;color:#ef4444;background:none;border:none;cursor:pointer;margin-top:4px;">
          ✕ Remove image
        </button>
      </div>
    ` : "";

    const optionsHtml = isMcq
      ? `<div class="options-list" id="eale-options">
          ${q.options.map((opt) => `
            <label class="option-label">
              <input type="radio" name="eale-ans" value="${escHtml(opt)}" />
              ${escHtml(opt)}
            </label>
          `).join("")}
        </div>`
      : `<input class="text-input" id="eale-text-ans" type="text" placeholder="Type your answer…" autocomplete="off" />
         ${handwritingHtml}`;

    renderPanel(`
      ${header(ctx.topic_name, ctx.task_type, mode, ctx.context_hint)}
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

    // Handwriting upload
    panel.querySelector("#eale-file-input")?.addEventListener("change", (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        const dataUrl = ev.target.result;
        _handwrittenB64 = dataUrl.replace(/^data:[^;]+;base64,/, "");
        const preview = panel.querySelector("#eale-img-preview");
        const img = panel.querySelector("#eale-preview-img");
        if (preview && img) { img.src = dataUrl; preview.style.display = "block"; }
        // Clear text input when image is used
        const textInput = panel.querySelector("#eale-text-ans");
        if (textInput) textInput.value = "";
      };
      reader.readAsDataURL(file);
    });

    panel.querySelector("#eale-remove-img")?.addEventListener("click", () => {
      _handwrittenB64 = null;
      const preview = panel.querySelector("#eale-img-preview");
      const fileInput = panel.querySelector("#eale-file-input");
      if (preview) preview.style.display = "none";
      if (fileInput) fileInput.value = "";
    });

    // Paste detection
    const textInput = panel.querySelector("#eale-text-ans");
    if (textInput) {
      textInput.addEventListener("paste", () => { _answerPasted = true; });
    }

    // Submit
    panel.querySelector("#eale-submit")?.addEventListener("click", handleSubmit);
  }

  function showResult(data) {
    state = "idle";
    const isCorrect = data.correct;
    const dusLine = data.updated_dus != null
      ? `<p style="font-size:11px;color:#6b7280;margin-top:8px;">Updated DUS: <strong style="color:#4f46e5">${data.updated_dus}</strong>/100</p>`
      : "";
    const proveItHtml = data.prove_it_question ? `
      <div style="margin-top:10px;padding:10px 12px;background:#fff7ed;border:1.5px solid #fed7aa;border-radius:8px;">
        <p style="font-size:11px;font-weight:700;color:#c2410c;margin-bottom:4px;">🔍 Prove It</p>
        <p style="font-size:12px;color:#431407;line-height:1.5;">${escHtml(data.prove_it_question)}</p>
        <p style="font-size:10px;color:#9a3412;margin-top:4px;font-style:italic;">Answer this verbally to confirm your understanding.</p>
      </div>
    ` : "";
    // If there are more LEARN_IT quiz questions queued, show "Next" instead of "Done"
    const hasNextLesson = _lessonQuizQueue.length > 0;
    const bottomBtns = `
      ${!isCorrect && !hasNextLesson ? `<button class="learn-it-btn" id="eale-learn-btn">📚 Explain this to me</button>` : ""}
      ${hasNextLesson
        ? `<button class="submit-btn" id="eale-next-q-btn" style="margin-top:4px;">Next question →</button>`
        : `<button class="done-btn" id="eale-done-btn">Done</button>`}
    `;

    renderPanel(`
      ${header(currentContext?.topic_name || "Result", null, currentContext?.mode, currentContext?.context_hint)}
      <div class="panel-body">
        <div class="result-block">
          <div class="result-badge ${isCorrect ? "correct" : "incorrect"}">
            ${isCorrect ? "✓ Correct" : "✗ Incorrect"}
          </div>
          <p class="result-explanation">${escHtml(data.explanation)}</p>
          ${!isCorrect ? `<p class="correct-answer-note">Correct answer: <span>${escHtml(data.correct_answer)}</span></p>` : ""}
          ${dusLine}
          ${proveItHtml}
        </div>
        ${bottomBtns}
      </div>
    `);

    panel.querySelector("#eale-done-btn")?.addEventListener("click", closePanel);
    panel.querySelector("#eale-next-q-btn")?.addEventListener("click", () => {
      showQuiz(_lessonQuizQueue.shift());
    });
    panel.querySelector("#eale-learn-btn")?.addEventListener("click", () => {
      const q = currentContext?.question;
      triggerLearn(q?.text, currentContext?.topic_name);
    });
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
      if (!answer && !_handwrittenB64) { alert("Please type an answer or upload a handwritten one."); return; }
    }

    const confidence = parseInt(panel.querySelector("#eale-conf")?.value || "5", 10);
    const reasoning = panel.querySelector("#eale-reasoning")?.value?.trim() || null;
    const answerPasted = _answerPasted;
    _answerPasted = false;

    const submitBtn = panel.querySelector("#eale-submit");
    if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Submitting…"; }

    state = "submitting";

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 30000);

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
          answer: _handwrittenB64 ? "[handwritten]" : answer,
          confidence,
          reasoning,
          handwritten_image: _handwrittenB64 ?? null,
          answer_pasted: answerPasted,
        }),
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      showResult(data);
    } catch (err) {
      clearTimeout(timer);
      if (err.name === "AbortError") {
        showError("Submit timed out (30 s). Please try again.");
      } else {
        showError(`Submit failed: ${err.message}`);
      }
    }
  }

  // ── Screenshot capture ─────────────────────────────────────────────────────

  async function captureScreenshot() {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: "EALE_CAPTURE_SCREENSHOT" }, (resp) => {
        resolve(resp?.ok ? resp.dataUrl.replace(/^data:image\/[a-z]+;base64,/, "") : null);
      });
    });
  }

  // ── Video helpers ──────────────────────────────────────────────────────────

  function detectVideo() {
    // Find a playing video first; fall back to any video present
    const all = Array.from(document.querySelectorAll("video"));
    return all.find((v) => !v.paused && !v.ended)
        || all.find((v) => v.readyState >= 2)
        || null;
  }

  function getVideoFrame(video) {
    try {
      const canvas = document.createElement("canvas");
      canvas.width  = video.videoWidth  || 640;
      canvas.height = video.videoHeight || 360;
      canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
      return canvas.toDataURL("image/jpeg", 0.75).replace(/^data:[^;]+;base64,/, "");
    } catch (e) {
      return null; // cross-origin or tainted canvas — fall back gracefully
    }
  }

  function getVideoCaptions() {
    // YouTube live captions
    const ytCaps = Array.from(document.querySelectorAll(".ytp-caption-segment"))
      .map((el) => el.textContent).join(" ").trim();
    if (ytCaps) return ytCaps;

    // Generic WebVTT text tracks
    const video = detectVideo();
    if (video) {
      for (const track of Array.from(video.textTracks || [])) {
        if (track.mode === "showing" && track.activeCues?.length) {
          return Array.from(track.activeCues).map((c) => c.text).join(" ").trim();
        }
      }
    }
    return "";
  }

  // ── Attention monitoring (YOLOv8 via CompVis) ──────────────────────────────

  async function startAttentionMonitoring() {
    if (_attentionStream) return; // already running
    try {
      _attentionStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
    } catch (e) {
      console.warn("[EALE] Webcam access denied:", e);
      return;
    }

    // Hidden video element
    _attentionVideo = document.createElement("video");
    _attentionVideo.srcObject = _attentionStream;
    _attentionVideo.autoplay = true;
    _attentionVideo.playsInline = true;
    _attentionVideo.style.cssText = "position:fixed;width:1px;height:1px;opacity:0;pointer-events:none;top:-9999px;left:-9999px;";
    document.documentElement.appendChild(_attentionVideo);

    // Switch CompVis to yolov8n detection mode once
    fetch(`${CV_URL}/switch-model`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_name: "yolov8n", config_overrides: { task: "detection" } }),
    }).catch(() => {});

    const canvas = document.createElement("canvas");
    const ctx2d = canvas.getContext("2d");

    _attentionTimer = setInterval(async () => {
      if (!_attentionVideo || _attentionVideo.readyState < 2) return;

      canvas.width  = _attentionVideo.videoWidth  || 320;
      canvas.height = _attentionVideo.videoHeight || 240;
      ctx2d.drawImage(_attentionVideo, 0, 0, canvas.width, canvas.height);

      canvas.toBlob(async (blob) => {
        if (!blob) return;
        const form = new FormData();
        form.append("file", blob, "frame.jpg");
        try {
          const res = await fetch(`${CV_URL}/predict`, { method: "POST", body: form });
          if (!res.ok) return;
          const data = await res.json();
          const personVisible = Array.isArray(data.boxes) &&
            data.boxes.some((b) => b.class_name === "person");

          if (personVisible) {
            // Face present
            if (_faceAbsentSince !== null) {
              _faceAbsentSince = null;
              btn.classList.remove("attention-absent");
              // Only quiz on return if a video was playing — looking away
              // during note-taking or reading is normal and should not interrupt
              if (state === "idle" && settings.videoQuizEnabled) {
                const vid = detectVideo();
                if (vid && !vid.paused) triggerVideoQuiz(vid, "ATTENTION_RETURN");
              }
            }
          } else {
            // Face absent
            if (_faceAbsentSince === null) {
              _faceAbsentSince = Date.now();
            } else {
              const absentMs = Date.now() - _faceAbsentSince;
              const vid = detectVideo();
              const videoPlaying = vid && !vid.paused && !vid.ended;

              if (videoPlaying) {
                // Watching a video — flash red after 20s
                if (absentMs >= ABSENT_QUIZ_MS) btn.classList.add("attention-absent");
              } else {
                // Reading / taking notes — quiz directly after 60s (no question on screen)
                if (absentMs >= 60000 && state === "idle") {
                  _faceAbsentSince = null; // reset so it doesn't re-fire immediately
                  triggerQuiz();
                }
              }
            }
          }
        } catch (e) {
          // CompVis not running — ignore silently
        }
      }, "image/jpeg", 0.7);
    }, 3000);
  }

  function stopAttentionMonitoring() {
    if (_attentionTimer) { clearInterval(_attentionTimer); _attentionTimer = null; }
    if (_attentionStream) { _attentionStream.getTracks().forEach((t) => t.stop()); _attentionStream = null; }
    if (_attentionVideo) { _attentionVideo.remove(); _attentionVideo = null; }
    _faceAbsentSince = null;
    btn.classList.remove("attention-absent");
  }

  // ── Video monitoring ───────────────────────────────────────────────────────

  // Bound event handlers stored so we can removeEventListener cleanly
  let _videoHandlers = null;

  function startVideoMonitoring() {
    if (_videoHandlers) return; // already attached

    // Find or wait for a video element (covers SPAs that load video late)
    function attachToVideo(video) {
      if (_videoHandlers) return; // race guard

      function onPause() {
        if (_ealePausingVideo) return; // EALE itself paused — ignore
        if (state !== "idle") return;
        triggerVideoQuiz(video, "MANUAL_PAUSE");
      }

      function onSeeked() {
        const now = video.currentTime;
        if (_videoPrevTime - now > VIDEO_REWIND_THRESHOLD_S) {
          // Rewound significantly
          if (state === "idle") triggerVideoQuiz(video, "REWIND");
        }
        _videoPrevTime = now;
      }

      function onTimeUpdate() {
        _videoPrevTime = video.currentTime;
      }

      video.addEventListener("pause",      onPause);
      video.addEventListener("seeked",     onSeeked);
      video.addEventListener("timeupdate", onTimeUpdate);

      _videoHandlers = { video, onPause, onSeeked, onTimeUpdate };

      // Passive difficulty scan every 3 min
      _videoDifficultyTimer = setInterval(async () => {
        if (state !== "idle" || video.paused || video.ended) return;
        const frame = getVideoFrame(video);
        if (!frame) return;
        const captions = getVideoCaptions();
        try {
          const res = await fetch(`${settings.backendUrl}/api/v1/extension/assess-video`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-API-Key": settings.studentApiKey,
            },
            body: JSON.stringify({ frame_b64: frame, caption_text: captions }),
          });
          if (!res.ok) return;
          const data = await res.json();
          if (data.should_quiz && state === "idle") {
            triggerVideoQuiz(video, "DIFFICULTY");
          }
        } catch (e) {
          // Backend not running or endpoint missing — fail silently
        }
      }, VIDEO_DIFFICULTY_INTERVAL_MS);
    }

    // Try immediately, then watch for dynamically loaded video (SPA)
    const vid = detectVideo();
    if (vid) {
      attachToVideo(vid);
    } else {
      const observer = new MutationObserver(() => {
        const v = detectVideo();
        if (v) { observer.disconnect(); attachToVideo(v); }
      });
      observer.observe(document.body, { childList: true, subtree: true });
    }
  }

  function stopVideoMonitoring() {
    if (_videoHandlers) {
      const { video, onPause, onSeeked, onTimeUpdate } = _videoHandlers;
      video.removeEventListener("pause",      onPause);
      video.removeEventListener("seeked",     onSeeked);
      video.removeEventListener("timeupdate", onTimeUpdate);
      _videoHandlers = null;
    }
    if (_videoDifficultyTimer) { clearInterval(_videoDifficultyTimer); _videoDifficultyTimer = null; }
    _videoPrevTime = 0;
  }

  async function triggerVideoQuiz(video, reason) {
    if (state !== "idle") return;
    _activeVideo = video;

    // Pause the video (set flag so our own pause handler ignores this)
    if (!video.paused) {
      _ealePausingVideo = true;
      video.pause();
      _ealePausingVideo = false;
    }

    const frame    = getVideoFrame(video);
    const captions = getVideoCaptions();

    // Build context hint label shown in loading screen
    const hintLabel = {
      REWIND:           "You rewound — checking understanding",
      MANUAL_PAUSE:     "You paused — quick check",
      DIFFICULTY:       "Dense concept detected",
      ATTENTION_RETURN: "Welcome back — what did you miss?",
    }[reason] || "Video learning check";

    await triggerQuiz({
      // frame is null when canvas is cross-origin (YouTube, Khan Academy) —
      // passing undefined lets triggerQuiz fall back to captureScreenshot()
      // which captures the full visible tab including the video player
      page_screenshot:    frame || undefined,
      page_text_override: captions || null,
      context_hint:       reason,
      loading_msg:        hintLabel,
    });
  }

  // ── Trigger quiz ───────────────────────────────────────────────────────────

  // overrides: { page_screenshot, page_text_override, context_hint, loading_msg }
  async function triggerQuiz(overrides = {}) {
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

    if (overrides.loading_msg) {
      // Video-specific loading message
      state = "loading";
      renderPanel(`
        <div class="panel-header">
          <div>
            <div class="title">EALE Learning Check</div>
            <div class="meta" style="opacity:.7">${escHtml(overrides.loading_msg)}</div>
          </div>
          <button class="close-btn" title="Close">✕</button>
        </div>
        <div class="spinner"><div class="spin"></div> Generating question…</div>
      `);
    } else if (settings.useLlmContext) {
      showLoadingLLM();
    } else {
      showLoading();
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 45000);

    // Use override screenshot (video frame) or capture tab screenshot
    const screenshot = overrides.page_screenshot !== undefined
      ? overrides.page_screenshot
      : await captureScreenshot();

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
          page_text: overrides.page_text_override || getPageText(),
          page_screenshot: screenshot,
          context_hint: overrides.context_hint || null,
        }),
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const ctx = await res.json();
      showQuiz(ctx);
    } catch (err) {
      clearTimeout(timer);
      if (err.name === "AbortError") {
        showError("Request timed out (45 s). Check that the backend is running.");
      } else {
        showError(`Could not fetch question: ${err.message}`);
      }
    }
  }

  // ── Learn It ───────────────────────────────────────────────────────────────

  async function triggerLearn(questionText, topicHint) {
    if (state === "loading" || state === "submitting") return;
    if (!isAllowed(location.href)) { showError("This page is not in your EALE allowlist."); return; }

    state = "loading";
    renderPanel(`
      <div class="panel-header">
        <div>
          <div class="title">📚 EALE Learn It</div>
          <div class="meta" style="opacity:.7">Building your lesson…</div>
        </div>
        <button class="close-btn" title="Close">✕</button>
      </div>
      <div class="spinner"><div class="spin"></div> Generating animated video lesson…</div>
    `);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 90000);

    try {
      const res = await fetch(`${settings.backendUrl}/api/v1/extension/learn`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": settings.studentApiKey },
        body: JSON.stringify({
          topic: topicHint || document.title || "",
          page_url: location.href,
          page_context: getPageText(),
          question_text: questionText || null,
        }),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      showVideoLesson(data);
    } catch (err) {
      clearTimeout(timer);
      showError(err.name === "AbortError"
        ? "Lesson generation timed out (60s). Check backend."
        : `Could not generate lesson: ${err.message}`);
    }
  }

  function showVideoLesson(lessonData) {
    state = "lesson";
    _lessonQuizQueue = (lessonData.quiz_questions || []).map((q) => ({
      task_id: null,
      task_type: null,
      topic_name: lessonData.topic,
      question: q,
      rationale: "Quiz from your AI video lesson — testing what you just watched.",
      mode: "LEARN_IT",
      context_hint: null,
    }));
    panel.classList.add("lesson-mode");

    // Build iframe with the GPT-generated animation HTML
    const iframe = document.createElement("iframe");
    iframe.setAttribute("sandbox", "allow-scripts");
    iframe.style.cssText = "width:444px;height:300px;border:none;border-radius:10px;display:block;margin:0 auto;";
    iframe.srcdoc = lessonData.html;

    // TTS narration audio
    if (_activeAudio) { _activeAudio.pause(); _activeAudio = null; }
    if (lessonData.audio_b64) {
      _activeAudio = new Audio(`data:audio/mp3;base64,${lessonData.audio_b64}`);
      _activeAudio.volume = 0.9;
    }

    // Store html for fullscreen
    const _lessonHtml = lessonData.html;

    renderPanel(`
      <div class="panel-header">
        <div>
          <div class="title">📚 ${escHtml(lessonData.topic)}</div>
          <div class="meta" style="opacity:.7">AI-generated video · with narration</div>
        </div>
        <button class="close-btn" title="Close">✕</button>
      </div>
      <div id="eale-video-wrap" style="padding:4px 16px 6px;"></div>
      <div style="display:flex;align-items:center;justify-content:space-between;padding:6px 16px 14px;gap:8px;">
        <div style="display:flex;gap:6px;">
          <button id="eale-audio-btn">🔊 Narration</button>
          <button id="eale-fullscreen-btn" title="Open fullscreen" style="background:none;border:1.5px solid #e5e7eb;border-radius:7px;padding:5px 10px;font-size:12px;font-weight:600;color:#4b5563;cursor:pointer;">⛶ Fullscreen</button>
        </div>
        <button class="lesson-nav primary" id="ls-quiz-btn">Quiz me →</button>
      </div>
    `);

    panel.querySelector("#eale-video-wrap").appendChild(iframe);

    // Start audio slightly after iframe loads
    setTimeout(() => _activeAudio?.play().catch(() => {}), 900);

    // Audio toggle
    const audioBtnEl = panel.querySelector("#eale-audio-btn");
    audioBtnEl?.addEventListener("click", () => {
      if (!_activeAudio) return;
      if (_activeAudio.paused) {
        _activeAudio.play().catch(() => {});
        audioBtnEl.textContent = "🔊 Narration";
      } else {
        _activeAudio.pause();
        audioBtnEl.textContent = "🔇 Paused";
      }
    });

    // Fullscreen — open in new tab
    panel.querySelector("#eale-fullscreen-btn")?.addEventListener("click", () => {
      const blob = new Blob([_lessonHtml], { type: "text/html" });
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
      // Revoke after a short delay (tab has had time to load it)
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    });

    // Quiz button
    panel.querySelector("#ls-quiz-btn")?.addEventListener("click", () => {
      if (_activeAudio) { _activeAudio.pause(); _activeAudio = null; }
      panel.classList.remove("lesson-mode");
      if (_lessonQuizQueue.length > 0) {
        showQuiz(_lessonQuizQueue.shift());
      } else {
        closePanel();
      }
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

  // ── Button clicks ──────────────────────────────────────────────────────────

  learnBtn.addEventListener("click", () => {
    if (panel.classList.contains("open")) {
      closePanel();
    } else {
      triggerLearn(null, document.title || "");
    }
  });

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
    ["backendUrl", "studentApiKey", "studentId", "allowlist", "useLlmContext", "useLlmGrading", "attentionMonitoring", "videoQuizEnabled"],
    (data) => {
      settings = {
        backendUrl:          data.backendUrl          || "http://localhost:8000",
        studentApiKey:       data.studentApiKey       || "student-alice-key",
        studentId:           data.studentId           || 1,
        allowlist:           data.allowlist           || ["file://", "localhost"],
        useLlmContext:       data.useLlmContext       || false,
        useLlmGrading:       data.useLlmGrading       || false,
        attentionMonitoring: data.attentionMonitoring || false,
        videoQuizEnabled:    data.videoQuizEnabled    || false,
      };
      if (settings.attentionMonitoring) startAttentionMonitoring();
      if (settings.videoQuizEnabled)    startVideoMonitoring();
    }
  );

  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "sync") return;
    if (changes.backendUrl)          settings.backendUrl          = changes.backendUrl.newValue;
    if (changes.studentApiKey)       settings.studentApiKey       = changes.studentApiKey.newValue;
    if (changes.studentId)           settings.studentId           = changes.studentId.newValue;
    if (changes.allowlist)           settings.allowlist           = changes.allowlist.newValue;
    if (changes.useLlmContext)       settings.useLlmContext       = changes.useLlmContext.newValue;
    if (changes.useLlmGrading)       settings.useLlmGrading       = changes.useLlmGrading.newValue;
    if (changes.attentionMonitoring) {
      settings.attentionMonitoring = changes.attentionMonitoring.newValue;
      if (settings.attentionMonitoring) startAttentionMonitoring();
      else stopAttentionMonitoring();
    }
    if (changes.videoQuizEnabled) {
      settings.videoQuizEnabled = changes.videoQuizEnabled.newValue;
      if (settings.videoQuizEnabled) startVideoMonitoring();
      else stopVideoMonitoring();
    }
  });

})();
