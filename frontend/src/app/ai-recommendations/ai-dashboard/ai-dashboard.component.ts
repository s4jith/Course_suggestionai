import { Component, OnInit, OnDestroy, inject, signal, computed } from '@angular/core';
import { FormControl, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { TitleCasePipe, DatePipe, DecimalPipe } from '@angular/common';
import { Subject, catchError, of, takeUntil } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTableModule } from '@angular/material/table';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatBadgeModule } from '@angular/material/badge';
import { MatTabsModule } from '@angular/material/tabs';
import {
  NgApexchartsModule,
  ApexChart, ApexAxisChartSeries, ApexXAxis, ApexYAxis,
  ApexDataLabels, ApexPlotOptions, ApexFill, ApexLegend,
  ApexTooltip, ApexStroke,
} from 'ng-apexcharts';
import { AiApiService } from '../../services/ai-api.service';
import { LessonPlanApiService } from '../../services/lesson-plan-api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { RiskBadgeComponent } from '../../shared/components/risk-badge/risk-badge.component';
import {
  AIRecommendationResponse, TimetableEntry, OllamaHealthStatus,
  MethodEffectivenessItem,
} from '../../models/ai.model';
import { LessonPlanSummary } from '../../models/lesson-plan.model';

const RISK_GAUGE_COLORS: Record<string, string> = {
  low: '#16a34a',
  medium: '#f59e0b',
  high: '#f97316',
  critical: '#dc2626',
};

const METHOD_COLORS = ['#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#f97316', '#ec4899', '#8b5cf6', '#14b8a6'];

export interface TimetableWeek {
  label: string;
  weekStart: string;
  entries: TimetableEntry[];
}

@Component({
  selector: 'app-ai-dashboard',
  standalone: true,
  imports: [
    ReactiveFormsModule, FormsModule, TitleCasePipe, DatePipe, DecimalPipe,
    MatCardModule, MatButtonModule, MatIconModule, MatProgressBarModule,
    MatTableModule, MatSelectModule, MatTooltipModule, MatProgressSpinnerModule,
    MatExpansionModule, MatChipsModule, MatDividerModule, MatSlideToggleModule,
    MatBadgeModule, MatTabsModule,
    NgApexchartsModule, PageHeaderComponent, RiskBadgeComponent,
  ],
  templateUrl: './ai-dashboard.component.html',
  styleUrl: './ai-dashboard.component.scss',
})
export class AiDashboardComponent implements OnInit, OnDestroy {
  private readonly aiApi = inject(AiApiService);
  private readonly planApi = inject(LessonPlanApiService);
  private readonly destroy$ = new Subject<void>();

  plans: LessonPlanSummary[] = [];
  selectedPlanId = new FormControl<string>('');
  aiData: AIRecommendationResponse | null = null;
  loading = signal(false);
  healthLoading = signal(false);
  aiHealth: OllamaHealthStatus | null = null;
  useAI = true;
  weeksAhead = 4;
  lastGenerated: Date | null = null;
  loadError: string | null = null;

  timetableByWeek: TimetableWeek[] = [];
  timetableCols = ['slot', 'date', 'topic_title', 'chapter_title', 'teaching_method', 'hours'];

  delayWarnings: string[] = [];

  riskGaugeOptions: {
    series: number[];
    chart: ApexChart;
    plotOptions: ApexPlotOptions;
    fill: ApexFill;
    labels: string[];
    colors: string[];
  } = this._buildRiskGauge(0, 'low');

  completionRadial: {
    series: number[];
    chart: ApexChart;
    plotOptions: ApexPlotOptions;
    labels: string[];
    legend: ApexLegend;
    fill: ApexFill;
  } = {
    series: [0, 0, 0],
    chart: { type: 'radialBar', height: 220 },
    plotOptions: {
      radialBar: {
        offsetY: 0,
        startAngle: 0,
        endAngle: 270,
        hollow: { margin: 5, size: '30%', background: 'transparent' },
        track: { show: false },
        dataLabels: { name: { show: false }, value: { show: false } },
      },
    },
    labels: ['Completion', 'Hours Del.', 'On-Track'],
    legend: { show: true, floating: true, fontSize: '11px', position: 'left', offsetX: -4, offsetY: 12,
      labels: { useSeriesColors: true },
      markers: { size: 7 },
    },
    fill: { type: 'gradient', gradient: { shade: 'dark', type: 'horizontal', shadeIntensity: 0.5,
      gradientToColors: ['#ABE5A1', '#64ACFF', '#5AD8E6'], inverseColors: false, opacityFrom: 1, opacityTo: 1, stops: [0, 100] } },
  };

  methodChartOptions: {
    series: ApexAxisChartSeries;
    chart: ApexChart;
    xaxis: ApexXAxis;
    yaxis: ApexYAxis;
    dataLabels: ApexDataLabels;
    plotOptions: ApexPlotOptions;
    tooltip: ApexTooltip;
    fill: ApexFill;
    colors: string[];
  } = {
    series: [{ name: 'Understanding Score', data: [] }],
    chart: { type: 'bar', height: 280, toolbar: { show: false } },
    xaxis: { categories: [], labels: { style: { fontSize: '11px' } } },
    yaxis: { min: 0, max: 4, tickAmount: 4, labels: { formatter: (v: number) => `${v.toFixed(1)}` } },
    dataLabels: { enabled: true, formatter: (v: number) => v.toFixed(2), style: { fontSize: '10px' } },
    plotOptions: { bar: { horizontal: true, barHeight: '55%', borderRadius: 4 } },
    tooltip: { y: { formatter: (v: number) => `${v.toFixed(2)} avg understanding` } },
    fill: { type: 'gradient', gradient: { shade: 'light', type: 'vertical', shadeIntensity: 0.3,
      gradientToColors: ['#6366f1'], inverseColors: false, opacityFrom: 0.85, opacityTo: 1 } },
    colors: [METHOD_COLORS[0]],
  };

  ngOnInit(): void {
    this._loadHealth();
    this.planApi.getPlans(0, 100).pipe(catchError(() => of(null)), takeUntil(this.destroy$))
      .subscribe(res => {
        this.plans = res?.data ?? [];
        if (this.plans.length > 0) {
          this.selectedPlanId.setValue(this.plans[0].id);
          this._loadRecommendations(this.plans[0].id);
        }
      });

    this.selectedPlanId.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(id => {
      if (id) this._loadRecommendations(id);
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  refresh(): void {
    const id = this.selectedPlanId.value;
    if (id) this._loadRecommendations(id);
  }

  toggleAI(): void {
    const id = this.selectedPlanId.value;
    if (id) this._loadRecommendations(id);
  }

  get healthStatusClass(): string {
    if (!this.aiHealth) return 'status-unknown';
    if (this.aiHealth.model_loaded) return 'status-ready';
    if (this.aiHealth.available) return 'status-degraded';
    return 'status-offline';
  }

  get healthStatusLabel(): string {
    if (this.healthLoading()) return 'Checking…';
    if (!this.aiHealth) return 'Unknown';
    if (this.aiHealth.model_loaded) return 'AI Ready';
    if (this.aiHealth.available) return 'No Model';
    return 'Offline';
  }

  get healthStatusIcon(): string {
    if (!this.aiHealth) return 'help_outline';
    if (this.aiHealth.model_loaded) return 'auto_awesome';
    if (this.aiHealth.available) return 'warning_amber';
    return 'cloud_off';
  }

  getRiskColor(level: string): string {
    return RISK_GAUGE_COLORS[level] ?? '#6b7280';
  }

  getMethodColor(i: number): string {
    return METHOD_COLORS[i % METHOD_COLORS.length];
  }

  getEffectivenessLabel(score: number): string {
    if (score >= 3.5) return 'Excellent';
    if (score >= 2.8) return 'Good';
    if (score >= 2.0) return 'Fair';
    return 'Poor';
  }

  getEffectivenessClass(item: MethodEffectivenessItem): string {
    const label = item.effectiveness_label?.toLowerCase() ?? '';
    if (label.includes('high') || label.includes('excellent')) return 'eff-high';
    if (label.includes('good') || label.includes('moderate')) return 'eff-medium';
    return 'eff-low';
  }

  getMitigationIcon(s: string): string {
    if (s.toLowerCase().includes('hour') || s.toLowerCase().includes('schedul')) return 'schedule';
    if (s.toLowerCase().includes('review') || s.toLowerCase().includes('revis')) return 'rate_review';
    if (s.toLowerCase().includes('priorit')) return 'priority_high';
    return 'tips_and_updates';
  }

  formatMethod(m: string): string {
    return m.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  private _loadHealth(): void {
    this.healthLoading.set(true);
    this.aiApi.getHealth().pipe(catchError(() => of(null)), takeUntil(this.destroy$))
      .subscribe(res => {
        this.healthLoading.set(false);
        this.aiHealth = res?.data ?? null;
      });
  }

  private _loadRecommendations(planId: string): void {
    this.loading.set(true);
    this.aiData = null;
    this.loadError = null;
    this.delayWarnings = [];

    this.aiApi.getFullRecommendations(planId, this.useAI)
      .pipe(catchError(err => {
        this.loadError = err?.error?.message ?? 'Failed to load AI recommendations.';
        return of(null);
      }), takeUntil(this.destroy$))
      .subscribe(res => {
        this.loading.set(false);
        this.aiData = res?.data ?? null;
        if (this.aiData) {
          this.lastGenerated = new Date();
          this._buildCharts();
          this._buildDelayWarnings();
          this._buildTimetableWeeks();
        }
      });
  }

  private _buildCharts(): void {
    if (!this.aiData) return;
    const risk = this.aiData.risk_assessment;

    this.riskGaugeOptions = this._buildRiskGauge(risk.risk_score, risk.risk_level);

    this.completionRadial = {
      ...this.completionRadial,
      series: [
        Math.round(risk.completion_percentage),
        Math.min(100, Math.round((1 - (risk.hours_behind > 0 ? risk.hours_behind / Math.max(1, risk.hours_behind + 1) : 0)) * 100)),
        risk.is_on_track ? 100 : Math.round(risk.completion_percentage * 0.7),
      ],
    };

    if (this.aiData.method_effectiveness.length) {
      const methods = this.aiData.method_effectiveness;
      const barColors = methods.map((_m, i) => METHOD_COLORS[i % METHOD_COLORS.length]);
      this.methodChartOptions = {
        ...this.methodChartOptions,
        series: [{ name: 'Understanding Score', data: methods.map(m => +(m.avg_understanding_score).toFixed(2)) }],
        xaxis: { ...this.methodChartOptions.xaxis, categories: methods.map(m => this.formatMethod(m.method)) },
        colors: barColors,
        fill: { type: 'solid' },
      };
    }
  }

  private _buildDelayWarnings(): void {
    if (!this.aiData) return;
    const w: string[] = [];
    const r = this.aiData.risk_assessment;
    if (r.delayed_topics_count > 0)
      w.push(`${r.delayed_topics_count} topic${r.delayed_topics_count > 1 ? 's are' : ' is'} past planned date`);
    if (r.hours_behind > 0)
      w.push(`${r.hours_behind.toFixed(1)} hours behind schedule`);
    if (this.aiData.next_topic?.is_delayed)
      w.push(`Next topic is ${this.aiData.next_topic.days_overdue} day${this.aiData.next_topic.days_overdue !== 1 ? 's' : ''} overdue`);
    if (!r.is_on_track && r.risk_level !== 'low')
      w.push('Plan is off-track — acceleration needed');
    this.delayWarnings = w;
  }

  private _buildTimetableWeeks(): void {
    if (!this.aiData?.timetable_suggestions.length) { this.timetableByWeek = []; return; }
    const map = new Map<string, TimetableEntry[]>();
    for (const e of this.aiData.timetable_suggestions) {
      const d = new Date(e.date);
      const day = d.getDay();
      const diff = d.getDate() - day + (day === 0 ? -6 : 1);
      const monday = new Date(d);
      monday.setDate(diff);
      const key = monday.toISOString().slice(0, 10);
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(e);
    }
    let i = 0;
    this.timetableByWeek = Array.from(map.entries()).map(([key, entries]) => ({
      weekStart: key,
      label: `Week ${++i}`,
      entries,
    }));
  }

  private _buildRiskGauge(score: number, level: string): {
    series: number[];
    chart: ApexChart;
    plotOptions: ApexPlotOptions;
    fill: ApexFill;
    labels: string[];
    colors: string[];
  } {
    const color = RISK_GAUGE_COLORS[level] ?? '#6b7280';
    return {
      series: [Math.round(score)],
      chart: { type: 'radialBar', height: 200, sparkline: { enabled: true } } as ApexChart,
      plotOptions: {
        radialBar: {
          startAngle: -90, endAngle: 90,
          hollow: { margin: 4, size: '60%' },
          track: { background: '#f1f5f9' },
          dataLabels: {
            name: { show: true, offsetY: -5, color: '#94a3b8', fontSize: '11px' },
            value: { show: true, fontSize: '32px', fontWeight: '800', color: '#0f172a',
              formatter: (v: number) => `${v}` },
          },
        },
      },
      fill: { type: 'solid', colors: [color] } as ApexFill,
      labels: ['Risk Score'],
      colors: [color],
    };
  }
}
