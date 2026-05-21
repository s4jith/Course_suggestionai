import {
  Component, OnInit, OnDestroy, inject, signal,
} from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject, forkJoin, of } from 'rxjs';
import { takeUntil, catchError } from 'rxjs/operators';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatChipsModule } from '@angular/material/chips';
import { MatTableModule } from '@angular/material/table';
import { MatSortModule } from '@angular/material/sort';
import { MatBadgeModule } from '@angular/material/badge';
import { MatDividerModule } from '@angular/material/divider';
import {
  NgApexchartsModule,
  ApexChart, ApexAxisChartSeries, ApexNonAxisChartSeries,
  ApexXAxis, ApexYAxis, ApexDataLabels, ApexPlotOptions,
  ApexFill, ApexLegend, ApexTitleSubtitle, ApexTooltip,
  ApexStroke, ApexGrid, ApexResponsive,
} from 'ng-apexcharts';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { AnalyticsApiService } from '../../services/analytics-api.service';
import {
  AnalyticsFilters, OverviewKPI, SyllabusCompletionItem,
  FacultyAnalyticsItem, SubjectAnalyticsItem, DelayedTopicItem,
  RiskScoreItem, TeachingMethodItem, UnderstandingBreakdown,
  CompletionTrendPoint, HeatmapCell,
} from '../../models/analytics.model';
import {
  RISK_COLORS, UNDERSTANDING_COLORS, CHART_COLORS, KPI_CARDS,
  METHOD_LABELS, SEMESTER_OPTIONS, CHART_TOOLBAR,
} from '../analytics.constants';

@Component({
  selector: 'app-analytics-dashboard',
  standalone: true,
  imports: [
    CommonModule, FormsModule, DecimalPipe,
    MatCardModule, MatButtonModule, MatIconModule, MatSelectModule,
    MatFormFieldModule, MatInputModule, MatProgressBarModule,
    MatProgressSpinnerModule, MatTooltipModule, MatChipsModule,
    MatTableModule, MatSortModule, MatBadgeModule, MatDividerModule,
    NgApexchartsModule,
    PageHeaderComponent,
  ],
  templateUrl: './analytics-dashboard.component.html',
  styleUrl: './analytics-dashboard.component.scss',
})
export class AnalyticsDashboardComponent implements OnInit, OnDestroy {
  private readonly api = inject(AnalyticsApiService);
  private readonly destroy$ = new Subject<void>();

  loading = signal(false);
  error = signal<string | null>(null);

  filters: AnalyticsFilters = {};
  academicYearInput = '';
  semesterInput: number | null = null;
  semesterOptions = SEMESTER_OPTIONS;

  overview: OverviewKPI | null = null;
  syllabusItems: SyllabusCompletionItem[] = [];
  syllabusAvgPct = 0;
  facultyItems: FacultyAnalyticsItem[] = [];
  subjectItems: SubjectAnalyticsItem[] = [];
  delayedItems: DelayedTopicItem[] = [];
  riskItems: RiskScoreItem[] = [];
  teachingItems: TeachingMethodItem[] = [];
  understanding: UnderstandingBreakdown | null = null;
  trendPoints: CompletionTrendPoint[] = [];
  heatmapCells: HeatmapCell[] = [];

  readonly kpiCards = KPI_CARDS;
  readonly riskColors = RISK_COLORS;
  readonly understandingColors = UNDERSTANDING_COLORS;

  syllabusChart: { series: ApexAxisChartSeries; chart: ApexChart; xaxis: ApexXAxis; yaxis: ApexYAxis; plotOptions: ApexPlotOptions; dataLabels: ApexDataLabels; fill: ApexFill; colors: string[]; tooltip: ApexTooltip } = {
    series: [{ name: 'Completion %', data: [] }],
    chart: { type: 'bar', height: 300, toolbar: CHART_TOOLBAR },
    xaxis: { categories: [], labels: { rotate: -30, style: { fontSize: '11px' } } },
    yaxis: { min: 0, max: 100, labels: { formatter: (v: number) => `${v}%` } },
    plotOptions: { bar: { borderRadius: 4, columnWidth: '55%', dataLabels: { position: 'top' } } },
    dataLabels: { enabled: true, formatter: (v: number) => `${v}%`, offsetY: -20, style: { fontSize: '10px', colors: ['#374151'] } },
    fill: { type: 'gradient', gradient: { shade: 'light', type: 'vertical', shadeIntensity: 0.3, gradientToColors: ['#6366f1'], inverseColors: false, opacityFrom: 0.85, opacityTo: 1 } },
    colors: [CHART_COLORS[0]],
    tooltip: { y: { formatter: (v: number) => `${v}%` } },
  };

  facultyChart: { series: ApexAxisChartSeries; chart: ApexChart; xaxis: ApexXAxis; yaxis: ApexYAxis; plotOptions: ApexPlotOptions; dataLabels: ApexDataLabels; colors: string[]; tooltip: ApexTooltip } = {
    series: [{ name: 'Completion %', data: [] }],
    chart: { type: 'bar', height: 300, toolbar: CHART_TOOLBAR },
    xaxis: { categories: [] },
    yaxis: { min: 0, max: 100, labels: { formatter: (v: number) => `${v}%` } },
    plotOptions: { bar: { borderRadius: 4, horizontal: true, barHeight: '55%' } },
    dataLabels: { enabled: true, formatter: (v: number) => `${v}%`, style: { fontSize: '11px' } },
    colors: [CHART_COLORS[1]],
    tooltip: { x: { show: true } },
  };

  subjectChart: { series: ApexAxisChartSeries; chart: ApexChart; xaxis: ApexXAxis; yaxis: ApexYAxis; plotOptions: ApexPlotOptions; dataLabels: ApexDataLabels; colors: string[] } = {
    series: [{ name: 'Completion %', data: [] }],
    chart: { type: 'bar', height: 300, toolbar: CHART_TOOLBAR },
    xaxis: { categories: [], min: 0, max: 100, labels: { formatter: (v: number) => `${v}%` } },
    yaxis: { labels: { style: { fontSize: '11px' } } },
    plotOptions: { bar: { borderRadius: 4, horizontal: true, barHeight: '55%' } },
    dataLabels: { enabled: true, formatter: (v: number) => `${v}%`, style: { fontSize: '11px' } },
    colors: [CHART_COLORS[2]],
  };

  understandingChart: { series: ApexNonAxisChartSeries; chart: ApexChart; labels: string[]; colors: string[]; legend: ApexLegend; dataLabels: ApexDataLabels; plotOptions: ApexPlotOptions; tooltip: ApexTooltip } = {
    series: [0, 0, 0, 0],
    chart: { type: 'donut', height: 280, toolbar: { show: false } },
    labels: ['Excellent', 'Good', 'Average', 'Poor'],
    colors: [UNDERSTANDING_COLORS['excellent'], UNDERSTANDING_COLORS['good'], UNDERSTANDING_COLORS['average'], UNDERSTANDING_COLORS['poor']],
    legend: { position: 'bottom' },
    dataLabels: { enabled: true, formatter: (_v: number, opts: { seriesIndex: number; w: { globals: { seriesTotals: number[] } } }) => {
      const total = opts.w.globals.seriesTotals.reduce((a: number, b: number) => a + b, 0);
      return total ? `${Math.round(opts.w.globals.seriesTotals[opts.seriesIndex] / total * 100)}%` : '0%';
    }},
    plotOptions: { pie: { donut: { size: '65%', labels: { show: true, total: { show: true, label: 'Total', formatter: (w: { globals: { seriesTotals: number[] } }) => w.globals.seriesTotals.reduce((a: number, b: number) => a + b, 0).toString() } } } } },
    tooltip: { y: { formatter: (v: number) => `${v} topics` } },
  };

  teachingChart: { series: ApexAxisChartSeries; chart: ApexChart; xaxis: ApexXAxis; yaxis: ApexYAxis; plotOptions: ApexPlotOptions; dataLabels: ApexDataLabels; colors: string[] } = {
    series: [{ name: 'Effectiveness Score', data: [] }],
    chart: { type: 'bar', height: 320, toolbar: CHART_TOOLBAR },
    xaxis: { categories: [], min: 0, max: 100, labels: { formatter: (v: number) => `${v}` } },
    yaxis: { labels: { style: { fontSize: '11px' } } },
    plotOptions: { bar: { borderRadius: 4, horizontal: true, barHeight: '55%' } },
    dataLabels: { enabled: true, formatter: (v: number) => `${v.toFixed(1)}`, style: { fontSize: '11px' } },
    colors: [CHART_COLORS[3]],
  };

  trendChart: { series: ApexAxisChartSeries; chart: ApexChart; xaxis: ApexXAxis; yaxis: ApexYAxis; stroke: ApexStroke; fill: ApexFill; dataLabels: ApexDataLabels; grid: ApexGrid; tooltip: ApexTooltip; colors: string[] } = {
    series: [{ name: 'Cumulative Completed', data: [] }],
    chart: { type: 'area', height: 260, toolbar: CHART_TOOLBAR },
    xaxis: { categories: [], type: 'datetime', labels: { format: 'dd MMM' } },
    yaxis: { min: 0, labels: { formatter: (v: number) => `${Math.round(v)}` } },
    stroke: { curve: 'smooth', width: 2 },
    fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.6, opacityTo: 0.1 } },
    dataLabels: { enabled: false },
    grid: { borderColor: '#f1f1f1' },
    tooltip: { x: { format: 'dd MMM yyyy' } },
    colors: [CHART_COLORS[0]],
  };

  readonly delayedCols = ['topic_title', 'subject_name', 'teacher_name', 'planned_date', 'days_overdue', 'status'];

  ngOnInit(): void {
    this.loadAll();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  applyFilters(): void {
    this.filters = {
      ...(this.academicYearInput ? { academic_year: this.academicYearInput } : {}),
      ...(this.semesterInput != null ? { semester: this.semesterInput } : {}),
    };
    this.loadAll();
  }

  clearFilters(): void {
    this.filters = {};
    this.academicYearInput = '';
    this.semesterInput = null;
    this.loadAll();
  }

  private loadAll(): void {
    this.loading.set(true);
    this.error.set(null);

    forkJoin({
      overview: this.api.getOverview(this.filters).pipe(catchError(() => of(null))),
      syllabus: this.api.getSyllabusCompletion(this.filters).pipe(catchError(() => of(null))),
      faculty: this.api.getFacultyAnalytics(this.filters).pipe(catchError(() => of(null))),
      subjects: this.api.getSubjectAnalytics(this.filters).pipe(catchError(() => of(null))),
      delayed: this.api.getDelayedTopics(this.filters).pipe(catchError(() => of(null))),
      risks: this.api.getRiskScores(this.filters).pipe(catchError(() => of(null))),
      methods: this.api.getTeachingMethodEffectiveness(this.filters).pipe(catchError(() => of(null))),
      understanding: this.api.getUnderstandingAnalytics(this.filters).pipe(catchError(() => of(null))),
      trend: this.api.getCompletionTrend(30).pipe(catchError(() => of(null))),
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe(({ overview, syllabus, faculty, subjects, delayed, risks, methods, understanding, trend }) => {
        this.loading.set(false);

        this.overview = overview;

        if (syllabus) {
          this.syllabusItems = syllabus.items.slice(0, 15);
          this.syllabusAvgPct = syllabus.avg_completion_pct;
          this.syllabusChart = {
            ...this.syllabusChart,
            series: [{ name: 'Completion %', data: this.syllabusItems.map(i => i.completion_pct) }],
            xaxis: { ...this.syllabusChart.xaxis, categories: this.syllabusItems.map(i => this.truncate(i.title, 20)) },
          };
        }

        if (faculty) {
          this.facultyItems = faculty.items.slice(0, 10);
          this.facultyChart = {
            ...this.facultyChart,
            series: [{ name: 'Completion %', data: this.facultyItems.map(i => i.completion_pct) }],
            xaxis: { ...this.facultyChart.xaxis, categories: this.facultyItems.map(i => this.truncate(i.teacher_name, 20)) },
          };
        }

        if (subjects) {
          this.subjectItems = subjects.items.slice(0, 10);
          this.subjectChart = {
            ...this.subjectChart,
            series: [{ name: 'Completion %', data: this.subjectItems.map(i => i.avg_completion_pct) }],
            yaxis: { ...this.subjectChart.yaxis, categories: this.subjectItems.map(i => `${i.subject_code || i.subject_name}`) },
          } as typeof this.subjectChart;
          this.subjectChart.xaxis.categories = this.subjectItems.map(i => `${i.subject_code || i.subject_name}`);
        }

        if (delayed) {
          this.delayedItems = delayed.items.slice(0, 20);
        }

        if (risks) {
          this.riskItems = risks.items.slice(0, 10);
        }

        if (methods) {
          this.teachingItems = methods.items;
          this.teachingChart = {
            ...this.teachingChart,
            series: [{ name: 'Effectiveness Score', data: this.teachingItems.map(i => i.effectiveness_score) }],
            xaxis: { ...this.teachingChart.xaxis, categories: this.teachingItems.map(i => i.label) },
          };
        }

        if (understanding) {
          this.understanding = understanding.overall;
          this.understandingChart = {
            ...this.understandingChart,
            series: [
              understanding.overall.excellent,
              understanding.overall.good,
              understanding.overall.average,
              understanding.overall.poor,
            ],
          };
        }

        if (trend) {
          this.trendPoints = trend.points;
          this.trendChart = {
            ...this.trendChart,
            series: [{ name: 'Cumulative Completed', data: this.trendPoints.map(p => p.cumulative_completed) }],
            xaxis: { ...this.trendChart.xaxis, categories: this.trendPoints.map(p => p.date) },
          };
        }
      });
  }

  private truncate(s: string, max: number): string {
    return s.length > max ? s.substring(0, max) + '…' : s;
  }

  getRiskClass(level: string): string {
    const map: Record<string, string> = {
      low: 'risk-badge-low',
      medium: 'risk-badge-medium',
      high: 'risk-badge-high',
      critical: 'risk-badge-critical',
    };
    return map[level] ?? 'risk-badge-low';
  }

  getKpiValue(key: string): number | null {
    if (!this.overview) return null;
    const v = (this.overview as unknown as Record<string, unknown>)[key];
    return typeof v === 'number' ? v : null;
  }
}
