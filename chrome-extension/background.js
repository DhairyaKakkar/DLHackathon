/**
 * EALE Background Service Worker (MV3)
 *
 * Responsibilities:
 *  - Set default storage values on install
 *  - Manage the auto-pop alarm (fires every N minutes to trigger a quiz)
 *  - Forward messages from popup → content script
 */

const DEFAULT_SETTINGS = {
  backendUrl: "http://localhost:8000",
  studentApiKey: "student-alice-key",
  studentId: 1,
  autoPopMinutes: 0,          // 0 = disabled
  allowlist: [
    "file://",
    "localhost",
    "blackboard.com",
    "canvas.instructure.com",
    "moodle.org",
    "notion.site",
    "khanacademy.org",
    "youtube.com",
  ],
};

// ── Install: seed defaults ─────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(({ reason }) => {
  if (reason !== "install") return;
  chrome.storage.sync.get(null, (existing) => {
    const merged = { ...DEFAULT_SETTINGS, ...existing };
    chrome.storage.sync.set(merged, () => {
      console.log("[EALE] Defaults written:", merged);
    });
  });
});

// ── Auto-pop alarm ─────────────────────────────────────────────────────────

const ALARM_NAME = "eale-auto-pop";

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "sync") return;
  if (!changes.autoPopMinutes) return;

  const minutes = changes.autoPopMinutes.newValue;
  chrome.alarms.clear(ALARM_NAME, () => {
    if (minutes > 0) {
      chrome.alarms.create(ALARM_NAME, {
        periodInMinutes: minutes,
        delayInMinutes: minutes,
      });
      console.log(`[EALE] Auto-pop alarm set for every ${minutes} min`);
    }
  });
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name !== ALARM_NAME) return;
  // Trigger quiz on the active tab
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs[0]?.id) return;
    chrome.tabs.sendMessage(tabs[0].id, { type: "EALE_AUTO_POP" }).catch(() => {
      // Content script not injected on this page — ignore
    });
  });
});

// ── Message bridge: popup → active tab ────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "EALE_TRIGGER_QUIZ") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0]?.id) {
        sendResponse({ ok: false, error: "No active tab" });
        return;
      }
      chrome.tabs.sendMessage(tabs[0].id, { type: "EALE_TRIGGER_QUIZ" })
        .then(() => sendResponse({ ok: true }))
        .catch((err) => sendResponse({ ok: false, error: String(err) }));
    });
    return true; // keep channel open for async sendResponse
  }

  if (msg.type === "EALE_CAPTURE_SCREENSHOT") {
    chrome.tabs.captureVisibleTab(null, { format: "png" }, (dataUrl) => {
      if (chrome.runtime.lastError || !dataUrl) {
        sendResponse({ ok: false });
      } else {
        sendResponse({ ok: true, dataUrl });
      }
    });
    return true; // async
  }
});
