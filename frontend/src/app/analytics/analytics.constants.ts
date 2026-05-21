

import { ApexPlotOptions, ApexFill, ApexDataLabels, ApexStroke } from 'ng-apexcharts';

export const RISK_COLORS: Record<string, string> = {
  low: '#16a34a',
  medium: '#f59e0b',
  high: '#f97316',
  critical: '#dc2626',
};

export const RISK_BG_CLASSES: Record<string, string> = {
  low: 'risk-low',
  medium: 'risk-medium',
  high: 'risk-high',
  critical: 'risk-critical',
};

export const UNDERSTANDING_COLORS: Record<string, string> = {
  excellent: '#16a34a',
  good: '#2563eb',
  average: '#f59e0b',
  poor: '#dc2626',
};

export const UNDERSTANDING_LABELS: Record<string, string> = {
  excellent: 'Excellent',
  good: 'Good',
  average: 'Average',
  poor: 'Poor',
};

export const CHART_COLORS = [
  '#6366f1',
  '#0ea5e9',
  '#10b981',
  '#f59e0b',
  '#f97316',
  '#ec4899',
  '#8b5cf6',
  '#14b8a6',
  '#ef4444',
  '#84cc16',
];

export interface KpiCardConfig {
  key: keyof import('../models/analytics.model').OverviewKPI;
  label: string;
  icon: string;
  unit?: string;
  color: string;
  description?: string;
}

export const KPI_CARDS: KpiCardConfig[] = [
  {
    key: 'total_lesson_plans',
    label: 'Total Lesson Plans',
    icon: 'menu_book',
    color: '#6366f1',
  },
  {
    key: 'active_lesson_plans',
    label: 'Active Plans',
    icon: 'play_circle',
    color: '#0ea5e9',
  },
  {
    key: 'overall_completion_pct',
    label: 'Overall Completion',
    icon: 'task_alt',
    unit: '%',
    color: '#10b981',
  },
  {
    key: 'pending_topics',
    label: 'Pending Topics',
    icon: 'pending_actions',
    color: '#f59e0b',
  },
  {
    key: 'delayed_topics',
    label: 'Delayed Topics',
    icon: 'schedule',
    color: '#f97316',
  },
  {
    key: 'at_risk_plans',
    label: 'At-Risk Plans',
    icon: 'warning',
    color: '#ef4444',
  },
  {
    key: 'hours_delivery_pct',
    label: 'Hours Delivery',
    icon: 'timer',
    unit: '%',
    color: '#8b5cf6',
  },
  {
    key: 'avg_understanding_score',
    label: 'Avg Understanding',
    icon: 'psychology',
    unit: '/4',
    color: '#14b8a6',
  },
];

export const CHART_TOOLBAR = {
  show: true,
  tools: { download: true, selection: false, zoom: false, zoomin: false, zoomout: false, pan: false, reset: false },
};

export const SEMESTER_OPTIONS = [1, 2, 3, 4, 5, 6, 7, 8];

export const METHOD_LABELS: Record<string, string> = {
  theoretical: 'Theoretical',
  practical: 'Practical',
  ppt: 'PPT Presentation',
  seminar: 'Seminar',
  lab: 'Lab Session',
  assignment: 'Assignment',
  discussion: 'Group Discussion',
  case_study: 'Case Study',
  video_based: 'Video Based',
};
