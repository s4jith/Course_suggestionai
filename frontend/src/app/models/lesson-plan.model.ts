export type LessonPlanStatus = 'draft' | 'active' | 'completed' | 'archived';
export type TeachingMethod =
  | 'theoretical' | 'practical' | 'ppt' | 'seminar'
  | 'lab' | 'assignment' | 'discussion' | 'case_study' | 'video_based';
export type TopicStatus = 'pending' | 'in_progress' | 'completed' | 'skipped';
export type UnderstandingLevel = 'excellent' | 'good' | 'average' | 'poor';

export interface Subject {
  id: string;
  name: string;
  code: string;
  description: string | null;
  department: string;
  semester: number;
  total_hours: number;
  is_active: boolean;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
}

export interface SubjectCreate {
  name: string;
  code: string;
  description?: string;
  department: string;
  semester: number;
  total_hours?: number;
}

export interface Subtopic {
  subtopic_id: string;
  title: string;
  order: number;
}

export interface Topic {
  topic_id: string;
  title: string;
  description: string | null;
  order: number;
  planned_date: string | null;
  planned_hours: number;
  subtopics: Subtopic[];
}

export interface Chapter {
  chapter_id: string;
  title: string;
  description: string | null;
  order: number;
  topics: Topic[];
}

export interface LessonPlan {
  id: string;
  subject_id: string;
  teacher_id: string;
  academic_year: string;
  semester: number;
  title: string;
  description: string | null;
  status: LessonPlanStatus;
  chapters: Chapter[];
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
}

export interface LessonPlanSummary {
  id: string;
  subject_id: string;
  teacher_id: string;
  academic_year: string;
  semester: number;
  title: string;
  status: LessonPlanStatus;
  created_at: string;
  updated_at: string;
}

export interface LessonPlanCreate {
  subject_id: string;
  academic_year: string;
  semester: number;
  title: string;
  description?: string;
  chapters?: Chapter[];
}

export interface TopicProgress {
  id: string;
  lesson_plan_id: string;
  chapter_id: string;
  topic_id: string;
  subtopic_id: string | null;
  teacher_id: string;
  subject_id: string;
  status: TopicStatus;
  completion_percentage: number;
  teaching_method: TeachingMethod | null;
  actual_date: string | null;
  duration_taken: number | null;
  student_understanding_level: UnderstandingLevel | null;
  remarks: string | null;
  issues: string | null;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;

  topic_title?: string;
  chapter_title?: string;
  lesson_plan_title?: string;
}

export interface CompletionStats {
  lesson_plan_id: string;
  total_topics: number;
  completed_topics: number;
  in_progress_topics: number;
  pending_topics: number;
  skipped_topics: number;
  overall_completion_percentage: number;
  total_hours_planned: number;
  total_hours_delivered: number;
}
