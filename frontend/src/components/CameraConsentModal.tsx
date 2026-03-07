"use client";

import { useState } from "react";
import { Camera, Shield, Eye, EyeOff, X, CheckCircle2, ChevronDown, ChevronUp } from "lucide-react";

interface CameraConsentModalProps {
  onAccept: () => void;
  onDecline: () => void;
}

export default function CameraConsentModal({ onAccept, onDecline }: CameraConsentModalProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-gray-100">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-11 h-11 rounded-xl bg-blue-50 flex items-center justify-center">
              <Shield className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-900">Camera & Privacy</h2>
              <p className="text-xs text-gray-400">Responsible AI feature — your consent matters</p>
            </div>
          </div>
        </div>

        <div className="px-6 py-5 flex flex-col gap-4">
          {/* What it does */}
          <div>
            <p className="text-sm font-semibold text-gray-800 mb-2">What EALE's attention monitor does</p>
            <div className="flex flex-col gap-2">
              {[
                { icon: <Eye className="w-4 h-4 text-blue-500" />, text: "Detects whether you're looking at your screen (engagement score)" },
                { icon: <EyeOff className="w-4 h-4 text-emerald-500" />, text: "No video is ever recorded, saved, or transmitted" },
                { icon: <Shield className="w-4 h-4 text-purple-500" />, text: "Processing is session-only — clears when you close the tab" },
                { icon: <Camera className="w-4 h-4 text-amber-500" />, text: "Only an anonymised engagement score (0–100%) reaches EALE" },
              ].map(({ icon, text }, i) => (
                <div key={i} className="flex items-start gap-3 text-sm text-gray-600">
                  <span className="shrink-0 mt-0.5">{icon}</span>
                  {text}
                </div>
              ))}
            </div>
          </div>

          {/* Data statement */}
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-3">
            <p className="text-xs font-semibold text-blue-800 mb-1.5">📋 Data statement</p>
            <p className="text-xs text-blue-700 leading-relaxed">
              EALE processes your camera feed <strong>locally in your browser</strong> using YOLOv8.
              No frames, images, or biometric data leave your device.
              The only value sent to EALE is a single number: your attention percentage for the current session.
            </p>
          </div>

          {/* Expandable technical detail */}
          <button
            onClick={() => setExpanded(e => !e)}
            className="flex items-center gap-2 text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            {expanded ? "Hide" : "Show"} technical details
          </button>
          {expanded && (
            <div className="bg-gray-50 rounded-xl p-3 text-xs text-gray-500 leading-relaxed border border-gray-100">
              <p className="font-semibold text-gray-600 mb-1">How it works</p>
              <p>YOLOv8 (object detection model) runs on the CompVis server and analyses your camera feed at 1 frame per second. It detects face presence and approximate gaze direction. This produces a binary "attentive / not attentive" signal each second, averaged into an engagement percentage over your study session.</p>
              <p className="mt-2 font-semibold text-gray-600">What is NOT done</p>
              <ul className="mt-1 space-y-1 list-disc list-inside">
                <li>No face recognition or identity matching</li>
                <li>No emotion analysis</li>
                <li>No storage of video frames</li>
                <li>No third-party data sharing</li>
              </ul>
            </div>
          )}

          {/* Controls */}
          <div className="flex items-center gap-2 text-xs text-gray-400 bg-gray-50 rounded-xl px-3 py-2.5 border border-gray-100">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
            You can disable the camera at any time from the dashboard header.
          </div>

          {/* Buttons */}
          <div className="flex gap-3">
            <button
              onClick={onDecline}
              className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-500 hover:bg-gray-50 transition-colors"
            >
              Decline
            </button>
            <button
              onClick={onAccept}
              className="flex-[2] py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
            >
              <Camera className="w-4 h-4" />
              Enable attention monitor
            </button>
          </div>
          <p className="text-xs text-center text-gray-400">
            This consent is stored locally and can be changed in settings at any time.
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Camera status indicator (for Navbar) ────────────────────────────────────

export function CameraIndicator({
  active,
  onToggle,
}: {
  active: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      title={active ? "Camera: Active (session only) — click to disable" : "Camera: Off — click to enable"}
      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all border ${
        active
          ? "bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100"
          : "bg-gray-50 border-gray-200 text-gray-400 hover:bg-gray-100"
      }`}
    >
      <span className={`w-2 h-2 rounded-full ${active ? "bg-blue-500 animate-pulse" : "bg-gray-300"}`} />
      {active ? "Camera: on" : "Camera: off"}
    </button>
  );
}
