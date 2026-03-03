const AUTH_KEY = "eale_auth";

export interface EaleAuth {
  role: "student" | "faculty";
  studentId: number | null;
  name: string;
  apiKey: string;
}

export function getAuth(): EaleAuth | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    return raw ? (JSON.parse(raw) as EaleAuth) : null;
  } catch {
    return null;
  }
}

export function setAuth(auth: EaleAuth): void {
  localStorage.setItem(AUTH_KEY, JSON.stringify(auth));
}

export function clearAuth(): void {
  localStorage.removeItem(AUTH_KEY);
}
