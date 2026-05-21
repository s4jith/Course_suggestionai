

export interface OverviewKPI {
  total_lesson_plans: number;
  active_lesson_plans: number;
  total_topics: number;
  completed_topics: number;
  in_progress_topics: number;
  pending_topics: number;
  skipped_topics: number;
  overall_completion_pct: number;
  total_hours_planned: number;
  total_hours_delivered: number;
  hours_delivery_pct: number;
  at_risk_plans: number;
  delayed_topics: number;
  avg_understanding_score: number | null;
}

export interface SyllabusCompletionItem {
  lesson_plan_id: string;
  title: string;
  subject_name: string;
  academic_year: string;
  semester: number;
  status: string;
  total_topics: number;
  completed_topics: number;
  completion_pct: number;
  hours_planned: number;
  hours_delivered: number;
  risk_score: number;
}

export interface SyllabusCompletionResponse {
  items: SyllabusCompletionItem[];
  avg_completion_pct: number;
}

export interface FacultyAnalyticsItem {
  teacher_id: string;
  teacher_name: string;
  email: string;
  total_topics_assigned: number;
  completed_topics: number;
  in_progress_topics: number;
  pending_topics: number;
  skipped_topics: number;
  completion_pct: number;
  total_hours_delivered: number;
  avg_understanding_score: number | null;
  lesson_plans_count: number;
}

export interface FacultyAnalyticsResponse {
  items: FacultyAnalyticsItem[];
}

export interface SubjectAnalyticsItem {
  subject_id: string;
  subject_name: string;
  subject_code: string;
  department: string;
  semester: number;
  total_lesson_plans: number;
  avg_completion_pct: number;
  total_topics: number;
  completed_topics: number;
  pending_topics: number;
  total_hours_planned: number;
  total_hours_delivered: number;
}

export interface SubjectAnalyticsResponse {
  items: SubjectAnalyticsItem[];
}

export interface DelayedTopicItem {
  topic_id: string;
  topic_title: string;
  chapter_title: string;
  lesson_plan_id: string;
  lesson_plan_title: string;
  subject_name: string;
  teacher_name: string;
  planned_date: string | null;
  days_overdue: number;
  status: string;
  completion_pct: number;
}

export interface DelayedTopicsResponse {
  items: DelayedTopicItem[];
  total_delayed: number;
}

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface RiskScoreItem {
  lesson_plan_id: string;
  title: string;
  subject_name: string;
  teacher_name: string;
  risk_score: number;
  risk_level: RiskLevel;
  completion_pct: number;
  pending_topics: number;
  delayed_topics: number;
  days_remaining: number | null;
  recommendation: string;
}

export interface RiskScoresResponse {
  items: RiskScoreItem[];
  avg_risk_score: number;
}

export interface TeachingMethodItem {
  method: string;
  label: string;
  total_uses: number;
  avg_completion_pct: number;
  avg_understanding_score: number;
  excellent_count: number;
  good_count: number;
  average_count: number;
  poor_count: number;
  avg_duration_hours: number | null;
  effectiveness_score: number;
}

export interface TeachingMethodResponse {
  items: TeachingMethodItem[];
}

export interface UnderstandingBreakdown {
  excellent: number;
  good: number;
  average: number;
  poor: number;
  total: number;
  excellent_pct: number;
  good_pct: number;
  average_pct: number;
  poor_pct: number;
  avg_score: number;
}

export interface UnderstandingBySubject {
  subject_name: string;
  subject_code: string;
  breakdown: UnderstandingBreakdown;
}

export interface UnderstandingAnalyticsResponse {
  overall: UnderstandingBreakdown;
  by_subject: UnderstandingBySubject[];
}

export interface CompletionTrendPoint {
  date: string;
  completed_count: number;
  cumulative_completed: number;
}

export interface CompletionTrendResponse {
  points: CompletionTrendPoint[];
  period_days: number;
}

export interface HeatmapCell {
  date: string;
  count: number;
  intensity: number;
}

export interface HeatmapResponse {
  cells: HeatmapCell[];
  max_count: number;
}

export interface AnalyticsFilters {
  academic_year?: string;
  semester?: number;
  department?: string;
  teacher_id?: string;
  subject_id?: string;
}
