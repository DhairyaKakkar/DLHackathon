// ─── Shared ───────────────────────────────────────────────────────────────────

export type QuestionType = "MCQ" | "SHORT_TEXT";
export type TaskType = "RETEST" | "TRANSFER";
export type UserRole = "student" | "faculty";

// ─── Student ──────────────────────────────────────────────────────────────────

export interface Student {
  id: number;
  name: string;
  email: string;
  api_key: string;
  role: UserRole;
  created_at: string;
}

// ─── Topic ────────────────────────────────────────────────────────────────────

export interface Topic {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
}

// ─── Question ─────────────────────────────────────────────────────────────────

export interface Question {
  id: number;
  topic_id: number;
  text: string;
  question_type: QuestionType;
  difficulty: number;
  correct_answer: string;
  options: string[] | null;
  is_variant: boolean;
  original_question_id: number | null;
  variant_template: string | null;
  created_at: string;
}

// ─── Attempt ──────────────────────────────────────────────────────────────────

export interface AttemptCreate {
  student_id: number;
  question_id: number;
  answer: string;
  confidence: number;
  reasoning?: string;
}

export interface AttemptOut {
  id: number;
  student_id: number;
  question_id: number;
  answer: string;
  confidence: number;
  reasoning: string | null;
  is_correct: boolean;
  created_at: string;
}

// ─── Scheduled Task ───────────────────────────────────────────────────────────

export interface ScheduledTask {
  id: number;
  student_id: number;
  question_id: number;
  due_at: string;
  task_type: TaskType;
  completed_at: string | null;
  created_at: string;
  question: Question;
}

// ─── Metrics ──────────────────────────────────────────────────────────────────

export interface CalibrationBin {
  bin: string;
  count: number;
  mean_confidence: number;
  accuracy: number;
  error: number;
}

export interface TopicMetrics {
  topic_id: number;
  topic_name: string;
  total_attempts: number;
  original_attempts: number;
  variant_attempts: number;
  mastery: number;
  mastery_explanation: string;
  retention: number;
  retention_bins: Record<string, number>;
  retention_explanation: string;
  transfer_robustness: number;
  transfer_explanation: string;
  calibration: number;
  overconfidence_gap: number;
  calibration_explanation: string;
  calibration_bins: CalibrationBin[];
  durable_understanding_score: number;
  dus_formula: string;
  dus_explanation: string;
}

export interface StudentDashboard {
  student_id: number;
  student_name: string;
  topics: TopicMetrics[];
  overall_dus: number;
  overall_explanation: string;
}

// ─── Faculty ──────────────────────────────────────────────────────────────────

export interface HistogramBucket {
  label: string;
  count: number;
  avg_value: number;
}

export interface FacultyTopicSummary {
  topic_id: number;
  topic_name: string;
  num_students: number;
  avg_mastery: number;
  avg_retention: number;
  avg_transfer: number;
  avg_calibration: number;
  avg_dus: number;
  avg_overconfidence_gap: number;
  low_retention_flag: boolean;
  transfer_failure_flag: boolean;
  overconfidence_flag: boolean;
}

export interface FacultyDashboard {
  num_students: number;
  num_topics: number;
  topic_summaries: FacultyTopicSummary[];
  low_retention_topics: string[];
  transfer_failure_topics: string[];
  overconfidence_hotspots: string[];
  dus_distribution: HistogramBucket[];
  explanation: string;
}
