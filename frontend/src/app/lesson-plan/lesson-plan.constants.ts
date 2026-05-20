import { TeachingMethod, TopicStatus, LessonPlanStatus, UnderstandingLevel } from '../models/lesson-plan.model';

export const TEACHING_METHODS: Array<{ value: TeachingMethod; label: string; icon: string }> = [
  { value: 'theoretical',  label: 'Theoretical',       icon: 'auto_stories' },
  { value: 'practical',    label: 'Practical',          icon: 'science' },
  { value: 'ppt',          label: 'PPT Presentation',   icon: 'slideshow' },
  { value: 'seminar',      label: 'Seminar',            icon: 'record_voice_over' },
  { value: 'lab',          label: 'Lab Session',        icon: 'biotech' },
  { value: 'assignment',   label: 'Assignment',         icon: 'assignment' },
  { value: 'discussion',   label: 'Group Discussion',   icon: 'forum' },
  { value: 'case_study',   label: 'Case Study',         icon: 'cases' },
  { value: 'video_based',  label: 'Video Based',        icon: 'play_circle' },
];

export const TOPIC_STATUSES: Array<{ value: TopicStatus; label: string; color: string }> = [
  { value: 'pending',     label: 'Pending',      color: '#64748b' },
  { value: 'in_progress', label: 'In Progress',  color: '#2563eb' },
  { value: 'completed',   label: 'Completed',    color: '#16a34a' },
  { value: 'skipped',     label: 'Skipped',      color: '#dc2626' },
];

export const UNDERSTANDING_LEVELS: Array<{ value: UnderstandingLevel; label: string }> = [
  { value: 'excellent', label: 'Excellent' },
  { value: 'good',      label: 'Good' },
  { value: 'average',   label: 'Average' },
  { value: 'poor',      label: 'Poor' },
];

export const LESSON_PLAN_STATUSES: Array<{ value: LessonPlanStatus; label: string }> = [
  { value: 'draft',     label: 'Draft' },
  { value: 'active',    label: 'Active' },
  { value: 'completed', label: 'Completed' },
  { value: 'archived',  label: 'Archived' },
];

export function getAcademicYearOptions(): string[] {
  const current = new Date().getFullYear();
  return [current - 1, current, current + 1].map(y => `${y}-${y + 1}`);
}
