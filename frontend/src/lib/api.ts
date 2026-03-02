import type {
  Student,
  StudentDashboard,
  ScheduledTask,
  AttemptCreate,
  AttemptOut,
  FacultyDashboard,
  Topic,
  Question,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body?.detail ?? message;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(res.status, message);
  }

  // 204 or empty body
  const text = await res.text();
  return text ? JSON.parse(text) : ({} as T);
}

// ─── Students ─────────────────────────────────────────────────────────────────

export const getStudents = (): Promise<Student[]> =>
  request("/api/v1/students/");

export const getStudent = (id: number): Promise<Student> =>
  request(`/api/v1/students/${id}`);

// ─── Topics ───────────────────────────────────────────────────────────────────

export const getTopics = (): Promise<Topic[]> => request("/api/v1/topics/");

// ─── Questions ────────────────────────────────────────────────────────────────

export const getQuestion = (id: number): Promise<Question> =>
  request(`/api/v1/questions/${id}`);

// ─── Metrics ──────────────────────────────────────────────────────────────────

export const getStudentDashboard = (studentId: number): Promise<StudentDashboard> =>
  request(`/api/v1/metrics/student/${studentId}`);

export const getFacultyDashboard = (): Promise<FacultyDashboard> =>
  request("/api/v1/metrics/faculty");

// ─── Tasks ────────────────────────────────────────────────────────────────────

export const getStudentTasks = (
  studentId: number,
  includeFuture = false,
): Promise<ScheduledTask[]> =>
  request(
    `/api/v1/tasks/student/${studentId}?include_future=${includeFuture}`,
  );

// ─── Attempts ─────────────────────────────────────────────────────────────────

export const submitAttempt = (payload: AttemptCreate): Promise<AttemptOut> =>
  request("/api/v1/attempts/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

// ─── Roadmap ──────────────────────────────────────────────────────────────────

export interface TopicRoadmapResource {
  title: string;
  url: string;
  type: "video" | "article" | "practice" | "course" | "documentation";
  description: string;
}

export interface TopicRoadmapStep {
  number: number;
  title: string;
  description: string;
  duration: string;
}

export interface TopicRoadmap {
  topic_name: string;
  diagnosis: string;
  steps: TopicRoadmapStep[];
  resources: TopicRoadmapResource[];
  concepts: string[];
  estimated_weeks: number;
}

export const getTopicRoadmap = (studentId: number, topicId: number): Promise<TopicRoadmap> =>
  request(`/api/v1/metrics/student/${studentId}/topic/${topicId}/roadmap`);

// ─── Admin ────────────────────────────────────────────────────────────────────

export const triggerScheduler = (): Promise<{ tasks_created: number }> =>
  request("/api/v1/admin/scheduler/run", { method: "POST" });

export { ApiError };
