"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { KeyRound, GraduationCap, User } from "lucide-react";
import { setAuth, getAuth } from "@/lib/auth";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export default function LoginPage() {
  const router = useRouter();
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const auth = getAuth();
    if (auth) {
      router.replace(auth.role === "faculty" ? "/faculty" : `/student/${auth.studentId}`);
    }
  }, [router]);

  async function handleSignIn(e: React.FormEvent) {
    e.preventDefault();
    if (!apiKey.trim()) { setError("Please enter your API key."); return; }
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey.trim() }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? "Invalid API key");
      }
      const data = await res.json();
      setAuth({ role: data.role, studentId: data.student_id, name: data.name, apiKey: apiKey.trim() });
      router.replace(data.role === "faculty" ? "/faculty" : `/student/${data.student_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#fafaf8] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">

        {/* Wordmark */}
        <div className="flex flex-col items-center mb-10">
          <div className="w-10 h-10 rounded bg-[#111113] flex items-center justify-center mb-4">
            <span className="font-display italic font-bold text-xl text-white leading-none">E</span>
          </div>
          <h1 className="font-display italic font-bold text-3xl text-[#111113] tracking-tight">EALE</h1>
          <p className="text-xs text-[#9e9eae] mt-1 tracking-widest uppercase">Evidence-Aligned Learning</p>
        </div>

        <div className="bg-white rounded-xl border border-[#d0cec9] shadow-card p-8">
          <h2 className="text-base font-semibold text-[#111113] mb-0.5">Sign in</h2>
          <p className="text-sm text-[#9e9eae] mb-6">Enter your API key to continue</p>

          <form onSubmit={handleSignIn} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#5c5c6e] uppercase tracking-widest mb-1.5">
                API Key
              </label>
              <div className="relative">
                <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9e9eae]" />
                <input
                  type="text"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="student-alice-key"
                  className="w-full pl-9 pr-4 py-2.5 border border-[#d0cec9] rounded-lg text-sm font-mono text-[#111113] bg-white focus:outline-none focus:ring-2 focus:ring-[#e8325a]/20 focus:border-[#e8325a] placeholder-[#9e9eae] transition-colors"
                  autoFocus
                  autoComplete="off"
                />
              </div>
            </div>

            {error && (
              <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#111113] text-white font-semibold py-2.5 rounded-lg hover:bg-[#2a2a32] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-[#ece9e4] flex flex-col gap-2">
            <p className="text-xs text-[#9e9eae] font-semibold uppercase tracking-widest mb-1">Demo accounts</p>
            <div className="flex items-center gap-2 text-xs text-[#5c5c6e]">
              <User className="w-3.5 h-3.5 text-[#e8325a] shrink-0" />
              <span><span className="font-mono text-[#111113]">student-alice-key</span> — Student dashboard</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-[#5c5c6e]">
              <User className="w-3.5 h-3.5 text-[#e8325a] shrink-0" />
              <span><span className="font-mono text-[#111113]">student-bob-key</span> — Student dashboard</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-[#5c5c6e]">
              <GraduationCap className="w-3.5 h-3.5 text-amber-600 shrink-0" />
              <span><span className="font-mono text-[#111113]">faculty-dana-key</span> — Faculty cohort view</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
