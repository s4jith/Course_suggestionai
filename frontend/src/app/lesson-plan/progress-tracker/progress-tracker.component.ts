import { Component, inject, OnInit } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog } from '@angular/material/dialog';
import { NgApexchartsModule } from 'ng-apexcharts';
import { DatePipe } from '@angular/common';
import { TopicProgressApiService } from '../../services/topic-progress-api.service';
import { LessonPlanApiService } from '../../services/lesson-plan-api.service';
import { TopicProgress, LessonPlanSummary, CompletionStats } from '../../models/lesson-plan.model';
import { TopicStatusChipComponent } from '../../shared/components/topic-status-chip/topic-status-chip.component';
import { LoadingSkeletonComponent } from '../../shared/components/loading-skeleton/loading-skeleton.component';

@Component({
  selector: 'app-progress-tracker',
  standalone: true,
  imports: [
    MatCardModule, MatSelectModule, MatFormFieldModule, MatTableModule,
    MatButtonModule, MatIconModule, NgApexchartsModule, DatePipe,
    TopicStatusChipComponent, LoadingSkeletonComponent,
  ],
  templateUrl: './progress-tracker.component.html',
  styleUrl: './progress-tracker.component.scss',
})
export class ProgressTrackerComponent implements OnInit {
  private readonly progressApi = inject(TopicProgressApiService);
  private readonly planApi = inject(LessonPlanApiService);
  readonly dialog = inject(MatDialog);

  plans: LessonPlanSummary[] = [];
  selectedPlanId = '';
  stats: CompletionStats | null = null;
  progressRecords: TopicProgress[] = [];
  filteredRecords: TopicProgress[] = [];
  loading = false;
  loadingPlans = true;

  readonly displayedColumns = ['topic', 'chapter', 'status', 'completion', 'method', 'date'];

  chartOptions = {
    series: [0, 0, 0, 0],
    chart: { type: 'donut' as const, height: 280, toolbar: { show: false } },
    labels: ['Completed', 'In Progress', 'Pending', 'Skipped'],
    colors: ['#16a34a', '#2563eb', '#64748b', '#dc2626'],
    legend: { position: 'bottom' as const },
    plotOptions: { pie: { donut: { size: '65%' } } },
    dataLabels: { enabled: false },
    tooltip: { y: { formatter: (v: number) => `${v} topics` } },
  };

  get overallPct(): number {
    if (!this.stats) return 0;
    const total = this.stats.total_topics ?? 0;
    if (!total) return 0;
    return Math.round(((this.stats.completed_topics ?? 0) / total) * 100);
  }

  ngOnInit(): void {
    this.planApi.getPlans(0, 100).subscribe({
      next: (res) => {
        this.plans = res.data ?? [];
        this.loadingPlans = false;
        if (this.plans.length > 0) this.onPlanChange(this.plans[0].id);
      },
      error: () => { this.loadingPlans = false; },
    });
  }

  onPlanChange(planId: string): void {
    this.selectedPlanId = planId;
    this.loading = true;
    this.progressApi.getCompletionStats(planId).subscribe(res => {
      this.stats = res.data ?? null;
      this.updateChart();
    });
    this.progressApi.getFacultyProgress(planId, 0, 200).subscribe({
      next: (res) => {
        this.progressRecords = res.data ?? [];
        this.filteredRecords = [...this.progressRecords];
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }

  onStatusFilter(status: string): void {
    this.filteredRecords = status
      ? this.progressRecords.filter(r => r.status === status)
      : [...this.progressRecords];
  }

  private updateChart(): void {
    if (!this.stats) return;
    this.chartOptions = {
      ...this.chartOptions,
      series: [
        this.stats.completed_topics ?? 0,
        this.stats.in_progress_topics ?? 0,
        this.stats.pending_topics ?? 0,
        this.stats.skipped_topics ?? 0,
      ],
    };
  }
}
