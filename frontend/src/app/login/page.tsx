"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { BrainCircuit, KeyRound, GraduationCap, User } from "lucide-react";
import { setAuth, getAuth } from "@/lib/auth";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export default function LoginPage() {
  const router = useRouter();
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // If already logged in, redirect immediately
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <BrainCircuit className="w-6 h-6 text-indigo-600" />
          <span className="font-extrabold text-xl text-gray-900 tracking-tight">EALE</span>
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 shadow-card p-8">
          <h1 className="text-xl font-bold text-gray-900 mb-1">Sign in to your dashboard</h1>
          <p className="text-sm text-gray-400 mb-6">Enter your API key to continue</p>

          <form onSubmit={handleSignIn} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
                API Key
              </label>
              <div className="relative">
                <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300" />
                <input
                  type="text"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="student-alice-key"
                  className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-lg text-sm font-mono text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder-gray-300"
                  autoFocus
                  autoComplete="off"
                />
              </div>
            </div>

            {error && (
              <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 text-white font-semibold py-2.5 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>

          {/* Role hints */}
          <div className="mt-6 pt-5 border-t border-gray-100 flex flex-col gap-2">
            <p className="text-xs text-gray-400 font-semibold uppercase tracking-wide mb-1">Demo accounts</p>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <User className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <span><span className="font-mono text-gray-700">student-alice-key</span> — Student dashboard</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <User className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <span><span className="font-mono text-gray-700">student-bob-key</span> — Student dashboard</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <GraduationCap className="w-3.5 h-3.5 text-amber-500 shrink-0" />
              <span><span className="font-mono text-gray-700">faculty-dana-key</span> — Faculty cohort view</span>
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">
          EALE · Evidence-Aligned Learning Engine
        </p>
      </div>
    </div>
  );
}
