import { TeachingMethod, UnderstandingLevel } from './lesson-plan.model';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface NextTopicRecommendation {
  topic_id: string;
  topic_title: string;
  chapter_title: string;
  priority_score: number;
  reason: string;
  suggested_method: TeachingMethod;
  estimated_hours: number;
  is_delayed: boolean;
  days_overdue: number;
}

export interface WeakAreaAlert {
  topic_id: string;
  topic_title: string;
  chapter_title: string;
  understanding_level: UnderstandingLevel | null;
  last_taught: string | null;
  revision_recommended: boolean;
  suggested_approach: string;
  issues: string | null;
}

export interface TimetableEntry {
  slot: number;
  date: string;
  day_of_week: string;
  topic_id: string;
  topic_title: string;
  chapter_title: string;
  suggested_hours: number;
  teaching_method: TeachingMethod;
}

export interface RiskAssessment {
  risk_score: number;
  risk_level: RiskLevel;
  completion_percentage: number;
  delayed_topics_count: number;
  hours_behind: number;
  predicted_completion_date: string | null;
  delay_days: number;
  is_on_track: boolean;
  topics_per_week: number;
  weeks_remaining: number | null;
  risk_factors: string[];
  mitigation_suggestions: string[];
}

export interface MethodEffectivenessItem {
  method: TeachingMethod;
  avg_understanding_score: number;
  usage_count: number;
  effectiveness_label: string;
}

export interface LlmInsights {
  summary?: {
    progress_narrative: string;
    teaching_style_analysis: string;
    student_performance_insight: string;
    recommendations: string[];
    motivational_note: string;
  };
  next_topic?: {
    recommendation_reason: string;
    teaching_guidance: string;
    preparation_tips: string[];
    estimated_duration_note: string;
    student_engagement_tips: string[];
  };
  weak_areas?: {
    overall_diagnosis: string;
    revision_plan: Array<{ topic: string; strategy: string; suggested_method: string }>;
    general_improvement_tips: string[];
  };
  timetable?: {
    schedule_insights: string;
    optimizations: string[];
    weekly_goal: string;
    risk_note: string;
  };
  risk?: {
    executive_summary: string;
    key_concerns: string[];
    immediate_actions: string[];
    long_term_strategy: string;
  };
}

export interface AIRecommendationResponse {
  lesson_plan_id: string;
  generated_at: string;
  next_topic: NextTopicRecommendation | null;
  weak_areas: WeakAreaAlert[];
  risk_assessment: RiskAssessment;
  timetable_suggestions: TimetableEntry[];
  method_effectiveness: MethodEffectivenessItem[];
  llm_insights: LlmInsights | null;
  ai_summary: string | null;
  fallback_mode: boolean;
}

export interface OllamaHealthStatus {
  available: boolean;
  model_loaded: boolean;
  model: string;
  base_url: string;
  available_models: string[];
  error: string | null;
}
