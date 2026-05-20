import { Component, OnInit, inject } from '@angular/core';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { TitleCasePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { NgApexchartsModule, ApexChart, ApexNonAxisChartSeries, ApexTitleSubtitle, ApexDataLabels, ApexLegend } from 'ng-apexcharts';
import { SubjectApiService } from '../services/subject-api.service';
import { LessonPlanApiService } from '../services/lesson-plan-api.service';
import { AiApiService } from '../services/ai-api.service';
import { StatCardComponent } from '../shared/components/stat-card/stat-card.component';
import { PageHeaderComponent } from '../shared/components/page-header/page-header.component';
import { LessonPlanSummary } from '../models/lesson-plan.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    TitleCasePipe, RouterLink,
    MatCardModule, MatButtonModule, MatIconModule, MatProgressBarModule,
    NgApexchartsModule, StatCardComponent, PageHeaderComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  private readonly subjectApi = inject(SubjectApiService);
  private readonly lessonPlanApi = inject(LessonPlanApiService);
  private readonly aiApi = inject(AiApiService);

  totalSubjects = 0;
  totalPlans = 0;
  recentPlans: LessonPlanSummary[] = [];
  aiHealthy = false;

  chartOptions: {
    series: ApexNonAxisChartSeries;
    chart: ApexChart;
    labels: string[];
    dataLabels: ApexDataLabels;
    legend: ApexLegend;
    title: ApexTitleSubtitle;
  } = {
    series: [44, 30, 26],
    chart: { type: 'donut', height: 260 },
    labels: ['Completed', 'In Progress', 'Pending'],
    dataLabels: { enabled: false },
    legend: { position: 'bottom' },
    title: { text: 'Topic Completion Overview', align: 'left', style: { fontSize: '14px', fontWeight: '600' } },
  };

  ngOnInit(): void {
    forkJoin({
      subjects: this.subjectApi.getSubjects(0, 1).pipe(catchError(() => of(null))),
      plans: this.lessonPlanApi.getPlans(0, 5).pipe(catchError(() => of(null))),
      aiHealth: this.aiApi.getHealth().pipe(catchError(() => of(null))),
    }).subscribe(({ subjects, plans, aiHealth }) => {
      this.totalSubjects = subjects?.total ?? 0;
      this.totalPlans = plans?.total ?? 0;
      this.recentPlans = plans?.data ?? [];
      this.aiHealthy = aiHealth?.data?.available ?? false;
    });
  }
}
