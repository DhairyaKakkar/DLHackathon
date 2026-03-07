"use client";

import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Loader2, Calendar, Sparkles, CheckCircle2, Clock, Camera, Upload, ImageIcon } from "lucide-react";
import { getTopics, saveStudentSchedule, parseScheduleText, parseScheduleImage } from "@/lib/api";
import type { ClassScheduleIn, Topic } from "@/lib/types";
import { cn } from "@/lib/utils";

const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
const DAY_SHORT: Record<string, string> = {
  monday: "Mon", tuesday: "Tue", wednesday: "Wed",
  thursday: "Thu", friday: "Fri", saturday: "Sat", sunday: "Sun",
};

function formatTime(t: string) {
  const [h, m] = t.split(":").map(Number);
  const ampm = h >= 12 ? "PM" : "AM";
  return `${h % 12 || 12}:${m.toString().padStart(2, "0")} ${ampm}`;
}

interface ScheduleOnboardingModalProps {
  studentId: number;
  onComplete: () => void;
}

const EMPTY_CLASS: ClassScheduleIn = {
  subject_name: "",
  topic_id: null,
  days_of_week: [],
  class_time: "09:00",
  teacher_name: null,
  room: null,
};

export default function ScheduleOnboardingModal({ studentId, onComplete }: ScheduleOnboardingModalProps) {
  const [step, setStep] = useState<"intro" | "input" | "review" | "done">("intro");
  const [inputMode, setInputMode] = useState<"manual" | "text" | "photo">("manual");
  const [freeText, setFreeText] = useState("");
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [photoB64, setPhotoB64] = useState<string>("");
  const [photoMediaType, setPhotoMediaType] = useState<string>("image/jpeg");
  const [classes, setClasses] = useState<ClassScheduleIn[]>([{ ...EMPTY_CLASS }]);
  const [isParsing, setIsParsing] = useState(false);
  const [parseError, setParseError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const qc = useQueryClient();
  const { data: topics = [] } = useQuery<Topic[]>({
    queryKey: ["topics"],
    queryFn: getTopics,
  });

  const saveMutation = useMutation({
    mutationFn: (items: ClassScheduleIn[]) => saveStudentSchedule(studentId, items),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["schedule", studentId] });
      setStep("done");
    },
  });

  function addClass() {
    setClasses(prev => [...prev, { ...EMPTY_CLASS }]);
  }

  function removeClass(i: number) {
    setClasses(prev => prev.filter((_, idx) => idx !== i));
  }

  function updateClass(i: number, patch: Partial<ClassScheduleIn>) {
    setClasses(prev => prev.map((c, idx) => idx === i ? { ...c, ...patch } : c));
  }

  function toggleDay(i: number, day: string) {
    const c = classes[i];
    const days = c.days_of_week.includes(day)
      ? c.days_of_week.filter(d => d !== day)
      : [...c.days_of_week, day];
    updateClass(i, { days_of_week: days });
  }

  async function handleParseText() {
    if (!freeText.trim()) return;
    setIsParsing(true);
    setParseError("");
    try {
      const parsed = await parseScheduleText(studentId, freeText);
      if (parsed.length === 0) {
        setParseError("Couldn't parse any classes. Try being more specific.");
      } else {
        setClasses(parsed);
        setInputMode("manual");
        setParseError("");
      }
    } catch {
      setParseError("Parse failed. Please enter classes manually.");
    } finally {
      setIsParsing(false);
    }
  }

  function handlePhotoSelect(file: File) {
    setPhotoPreview(URL.createObjectURL(file));
    setPhotoMediaType(file.type || "image/jpeg");
    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string;
      // strip the data-URI prefix to get raw base64
      setPhotoB64(dataUrl.split(",")[1] ?? "");
    };
    reader.readAsDataURL(file);
    setParseError("");
  }

  async function handleParsePhoto() {
    if (!photoB64) return;
    setIsParsing(true);
    setParseError("");
    try {
      const parsed = await parseScheduleImage(studentId, photoB64, photoMediaType);
      if (parsed.length === 0) {
        setParseError("Couldn't find any classes in the photo. Try a clearer image.");
      } else {
        setClasses(parsed);
        setInputMode("manual");
        setParseError("");
      }
    } catch {
      setParseError("Photo parse failed. Try a clearer image or use text entry.");
    } finally {
      setIsParsing(false);
    }
  }

  function isValid() {
    return classes.length > 0 && classes.every(c =>
      c.subject_name.trim() && c.days_of_week.length > 0 && c.class_time
    );
  }

  function handleSave() {
    if (isValid()) saveMutation.mutate(classes);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">

        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#111113] flex items-center justify-center">
              <Calendar className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-900">Set up your schedule</h2>
              <p className="text-xs text-gray-400">Personalises your entire EALE experience</p>
            </div>
          </div>
          {/* Steps */}
          <div className="flex items-center gap-1.5">
            {(["intro", "input", "review", "done"] as const).map((s, i) => (
              <div key={s} className={cn(
                "w-2 h-2 rounded-full transition-all",
                step === s ? "bg-[#e8325a] scale-125" : ["intro","input","review","done"].indexOf(step) > i ? "bg-gray-400" : "bg-gray-200"
              )} />
            ))}
          </div>
        </div>

        <div className="px-6 py-6">

          {/* ── Step 1: Intro ── */}
          {step === "intro" && (
            <div className="flex flex-col items-center text-center gap-6">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
                <Sparkles className="w-10 h-10 text-white" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">Meet your AI study planner</h3>
                <p className="text-sm text-gray-500 max-w-md leading-relaxed">
                  EALE learns your school timetable and builds a <span className="font-semibold text-gray-700">personalised study roadmap</span> around it.
                  You'll get <span className="font-semibold text-gray-700">pre-class prep briefs</span> the day before each class, and
                  <span className="font-semibold text-gray-700"> post-class checks</span> after to lock in what you learned.
                </p>
              </div>
              <div className="grid grid-cols-3 gap-3 w-full">
                {[
                  { icon: "📷", title: "Photo upload", desc: "Snap your timetable — GPT-4o Vision reads it for you" },
                  { icon: "⚡", title: "Pre-class briefs", desc: "GPT-4o prep packet 24h before every class" },
                  { icon: "✅", title: "Post-class checks", desc: "Lock in what you learned right after class" },
                ].map(f => (
                  <div key={f.title} className="bg-gray-50 rounded-xl p-3 text-center">
                    <div className="text-2xl mb-1">{f.icon}</div>
                    <p className="text-xs font-semibold text-gray-700">{f.title}</p>
                    <p className="text-xs text-gray-400 mt-0.5 leading-snug">{f.desc}</p>
                  </div>
                ))}
              </div>
              <div className="flex gap-3 w-full">
                <button
                  onClick={onComplete}
                  className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-500 hover:bg-gray-50 transition-colors"
                >
                  Skip for now
                </button>
                <button
                  onClick={() => setStep("input")}
                  className="flex-[2] py-2.5 bg-[#111113] text-white rounded-xl text-sm font-semibold hover:bg-[#2a2a32] transition-colors"
                >
                  Set up my schedule →
                </button>
              </div>
            </div>
          )}

          {/* ── Step 2: Input ── */}
          {step === "input" && (
            <div className="flex flex-col gap-5">
              {/* Mode toggle */}
              <div className="flex gap-1.5 bg-gray-100 rounded-xl p-1">
                {([
                  { key: "manual", label: "✏️ Manual" },
                  { key: "text", label: "✨ Paste text" },
                  { key: "photo", label: "📷 Photo" },
                ] as const).map(m => (
                  <button
                    key={m.key}
                    onClick={() => setInputMode(m.key)}
                    className={cn(
                      "flex-1 py-2 rounded-lg text-xs font-medium transition-all",
                      inputMode === m.key ? "bg-white shadow text-gray-900" : "text-gray-500"
                    )}
                  >
                    {m.label}
                  </button>
                ))}
              </div>

              {inputMode === "text" ? (
                <div className="flex flex-col gap-3">
                  <p className="text-xs text-gray-500">
                    Paste your timetable, type it out, or describe it naturally. GPT-4o will extract the classes.
                  </p>
                  <textarea
                    value={freeText}
                    onChange={e => setFreeText(e.target.value)}
                    placeholder={"Monday & Wednesday 9am Physics with Mr. Smith in Lab 3\nTuesday 11am Algorithms with Prof. Lee\nFriday 2pm Calculus"}
                    rows={6}
                    className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm font-mono text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#e8325a]/20 focus:border-[#e8325a] resize-none"
                  />
                  {parseError && <p className="text-xs text-red-500">{parseError}</p>}
                  <button
                    onClick={handleParseText}
                    disabled={isParsing || !freeText.trim()}
                    className="flex items-center justify-center gap-2 bg-indigo-600 text-white py-2.5 rounded-xl text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                  >
                    {isParsing ? <><Loader2 className="w-4 h-4 animate-spin" /> Parsing with GPT-4o…</> : <><Sparkles className="w-4 h-4" /> Parse my schedule</>}
                  </button>
                </div>
              ) : inputMode === "photo" ? (
                <div className="flex flex-col gap-3">
                  <p className="text-xs text-gray-500">
                    Take a photo or upload an image of your timetable. GPT-4o Vision will extract all classes automatically.
                  </p>

                  {/* Hidden file inputs */}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={e => { const f = e.target.files?.[0]; if (f) handlePhotoSelect(f); }}
                  />
                  <input
                    ref={cameraInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={e => { const f = e.target.files?.[0]; if (f) handlePhotoSelect(f); }}
                  />

                  {photoPreview ? (
                    <div className="relative">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={photoPreview}
                        alt="Timetable preview"
                        className="w-full rounded-xl border border-gray-200 object-contain max-h-64"
                      />
                      <button
                        onClick={() => { setPhotoPreview(null); setPhotoB64(""); setParseError(""); }}
                        className="absolute top-2 right-2 bg-white border border-gray-200 rounded-full w-7 h-7 flex items-center justify-center text-gray-500 hover:text-red-500 text-xs shadow"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <div
                      className="border-2 border-dashed border-gray-200 rounded-xl p-8 flex flex-col items-center gap-3 cursor-pointer hover:border-gray-300 transition-colors"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <ImageIcon className="w-10 h-10 text-gray-300" />
                      <p className="text-sm text-gray-400 text-center">Drop your timetable image here<br />or click to browse</p>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <button
                      onClick={() => cameraInputRef.current?.click()}
                      className="flex-1 flex items-center justify-center gap-2 border border-gray-200 rounded-xl py-2.5 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                    >
                      <Camera className="w-4 h-4" /> Camera
                    </button>
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="flex-1 flex items-center justify-center gap-2 border border-gray-200 rounded-xl py-2.5 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                    >
                      <Upload className="w-4 h-4" /> Upload
                    </button>
                  </div>

                  {parseError && <p className="text-xs text-red-500">{parseError}</p>}

                  <button
                    onClick={handleParsePhoto}
                    disabled={isParsing || !photoB64}
                    className="flex items-center justify-center gap-2 bg-indigo-600 text-white py-2.5 rounded-xl text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                  >
                    {isParsing
                      ? <><Loader2 className="w-4 h-4 animate-spin" /> Scanning with GPT-4o Vision…</>
                      : <><Sparkles className="w-4 h-4" /> Extract my schedule</>}
                  </button>
                </div>
              ) : (
                <div className="flex flex-col gap-4">
                  {classes.map((cls, i) => (
                    <div key={i} className="border border-gray-200 rounded-xl p-4 flex flex-col gap-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Class {i + 1}</span>
                        {classes.length > 1 && (
                          <button onClick={() => removeClass(i)} className="text-gray-300 hover:text-red-400 transition-colors">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>

                      {/* Subject + Teacher */}
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Subject *</label>
                          <input
                            value={cls.subject_name}
                            onChange={e => updateClass(i, { subject_name: e.target.value })}
                            placeholder="e.g. Physics"
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#e8325a]/20 focus:border-[#e8325a]"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Teacher</label>
                          <input
                            value={cls.teacher_name ?? ""}
                            onChange={e => updateClass(i, { teacher_name: e.target.value || null })}
                            placeholder="e.g. Mr. Smith"
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#e8325a]/20 focus:border-[#e8325a]"
                          />
                        </div>
                      </div>

                      {/* Time + Room + Topic */}
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Time *</label>
                          <input
                            type="time"
                            value={cls.class_time}
                            onChange={e => updateClass(i, { class_time: e.target.value })}
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#e8325a]/20 focus:border-[#e8325a]"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Room</label>
                          <input
                            value={cls.room ?? ""}
                            onChange={e => updateClass(i, { room: e.target.value || null })}
                            placeholder="e.g. Lab 3"
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#e8325a]/20 focus:border-[#e8325a]"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Link to topic</label>
                          <select
                            value={cls.topic_id ?? ""}
                            onChange={e => updateClass(i, { topic_id: e.target.value ? Number(e.target.value) : null })}
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#e8325a]/20 focus:border-[#e8325a] bg-white"
                          >
                            <option value="">No link</option>
                            {topics.map(t => (
                              <option key={t.id} value={t.id}>{t.name}</option>
                            ))}
                          </select>
                        </div>
                      </div>

                      {/* Days */}
                      <div>
                        <label className="block text-xs text-gray-500 mb-2">Days *</label>
                        <div className="flex gap-1.5 flex-wrap">
                          {DAYS.map(day => (
                            <button
                              key={day}
                              type="button"
                              onClick={() => toggleDay(i, day)}
                              className={cn(
                                "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border",
                                cls.days_of_week.includes(day)
                                  ? "bg-[#111113] text-white border-[#111113]"
                                  : "bg-white text-gray-500 border-gray-200 hover:border-gray-400"
                              )}
                            >
                              {DAY_SHORT[day]}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}

                  <button
                    onClick={addClass}
                    className="flex items-center justify-center gap-2 border-2 border-dashed border-gray-200 rounded-xl py-3 text-sm text-gray-400 hover:text-gray-600 hover:border-gray-300 transition-colors"
                  >
                    <Plus className="w-4 h-4" /> Add another class
                  </button>
                </div>
              )}

              <div className="flex gap-3">
                <button onClick={() => setStep("intro")} className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-500 hover:bg-gray-50 transition-colors">
                  Back
                </button>
                <button
                  onClick={() => setStep("review")}
                  disabled={!isValid()}
                  className="flex-[2] py-2.5 bg-[#111113] text-white rounded-xl text-sm font-semibold hover:bg-[#2a2a32] disabled:opacity-40 transition-colors"
                >
                  Review schedule →
                </button>
              </div>
            </div>
          )}

          {/* ── Step 3: Review ── */}
          {step === "review" && (
            <div className="flex flex-col gap-5">
              <div>
                <h3 className="text-base font-bold text-gray-900">Review your schedule</h3>
                <p className="text-sm text-gray-500 mt-1">EALE will personalise your roadmap and prep briefs around these classes.</p>
              </div>
              <div className="flex flex-col gap-3">
                {classes.map((cls, i) => {
                  const linkedTopic = topics.find(t => t.id === cls.topic_id);
                  return (
                    <div key={i} className="border border-gray-200 rounded-xl p-4 flex items-start gap-4">
                      <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center shrink-0">
                        <Clock className="w-5 h-5 text-indigo-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-sm font-semibold text-gray-900">{cls.subject_name}</p>
                          {linkedTopic && (
                            <span className="text-xs bg-indigo-50 text-indigo-600 border border-indigo-200 px-2 py-0.5 rounded-full font-medium">
                              → {linkedTopic.name}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {cls.days_of_week.map(d => DAY_SHORT[d]).join(", ")} at {formatTime(cls.class_time)}
                          {cls.teacher_name && ` · ${cls.teacher_name}`}
                          {cls.room && ` · ${cls.room}`}
                        </p>
                      </div>
                      <button onClick={() => { setStep("input"); }} className="text-xs text-[#e8325a] shrink-0">Edit</button>
                    </div>
                  );
                })}
              </div>
              <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4">
                <p className="text-xs text-indigo-700 font-semibold mb-1">What happens next</p>
                <ul className="text-xs text-indigo-600 space-y-1">
                  <li>• Your roadmap reorders by upcoming class urgency</li>
                  <li>• Classes within 24h show an ⚡ urgent badge</li>
                  <li>• Click any class card to generate a GPT-4o prep brief</li>
                  <li>• Post-class checks appear after your class ends</li>
                </ul>
              </div>
              <div className="flex gap-3">
                <button onClick={() => setStep("input")} className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-500 hover:bg-gray-50 transition-colors">
                  Back
                </button>
                <button
                  onClick={handleSave}
                  disabled={saveMutation.isPending}
                  className="flex-[2] py-2.5 bg-[#111113] text-white rounded-xl text-sm font-semibold hover:bg-[#2a2a32] disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                >
                  {saveMutation.isPending ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</> : "Save schedule ✓"}
                </button>
              </div>
            </div>
          )}

          {/* ── Step 4: Done ── */}
          {step === "done" && (
            <div className="flex flex-col items-center text-center gap-6 py-4">
              <div className="w-20 h-20 rounded-full bg-emerald-50 flex items-center justify-center">
                <CheckCircle2 className="w-10 h-10 text-emerald-500" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">You're all set! 🎉</h3>
                <p className="text-sm text-gray-500 max-w-sm leading-relaxed">
                  Your schedule is saved. Switch to the <span className="font-semibold text-gray-700">Roadmap tab</span> to see urgency-sorted topics, and look out for ⚡ pre-class prep alerts.
                </p>
              </div>
              <button
                onClick={onComplete}
                className="w-full py-3 bg-[#111113] text-white rounded-xl font-semibold hover:bg-[#2a2a32] transition-colors"
              >
                Go to dashboard →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
