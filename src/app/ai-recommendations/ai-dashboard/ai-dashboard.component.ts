import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { TitleCasePipe, DatePipe, DecimalPipe } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTableModule } from '@angular/material/table';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { NgApexchartsModule, ApexChart, ApexAxisChartSeries, ApexXAxis, ApexDataLabels, ApexPlotOptions, ApexTitleSubtitle } from 'ng-apexcharts';
import { AiApiService } from '../../services/ai-api.service';
import { LessonPlanApiService } from '../../services/lesson-plan-api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { RiskBadgeComponent } from '../../shared/components/risk-badge/risk-badge.component';
import { AIRecommendationResponse, TimetableEntry } from '../../models/ai.model';
import { LessonPlanSummary } from '../../models/lesson-plan.model';
import { catchError, of } from 'rxjs';

@Component({
  selector: 'app-ai-dashboard',
  standalone: true,
  imports: [
    ReactiveFormsModule, TitleCasePipe, DatePipe, DecimalPipe,
    MatCardModule, MatButtonModule, MatIconModule, MatProgressBarModule,
    MatTableModule, MatSelectModule, MatTooltipModule, MatProgressSpinnerModule,
    NgApexchartsModule, PageHeaderComponent, RiskBadgeComponent,
  ],
  templateUrl: './ai-dashboard.component.html',
  styleUrl: './ai-dashboard.component.scss',
})
export class AiDashboardComponent implements OnInit {
  private readonly aiApi = inject(AiApiService);
  private readonly planApi = inject(LessonPlanApiService);

  plans: LessonPlanSummary[] = [];
  selectedPlanId = new FormControl<string>('');
  aiData: AIRecommendationResponse | null = null;
  loading = false;
  timetableCols = ['slot', 'date', 'topic_title', 'chapter_title', 'teaching_method', 'hours'];

  methodChartOptions: {
    series: ApexAxisChartSeries;
    chart: ApexChart;
    xaxis: ApexXAxis;
    dataLabels: ApexDataLabels;
    plotOptions: ApexPlotOptions;
    title: ApexTitleSubtitle;
  } = {
    series: [{ name: 'Avg Understanding', data: [] }],
    chart: { type: 'bar', height: 220 },
    xaxis: { categories: [] },
    dataLabels: { enabled: true },
    plotOptions: { bar: { horizontal: true } },
    title: { text: 'Teaching Method Effectiveness', align: 'left', style: { fontSize: '14px', fontWeight: '600' } },
  };

  ngOnInit(): void {
    this.planApi.getPlans(0, 50).pipe(catchError(() => of(null))).subscribe(res => {
      this.plans = res?.data ?? [];
      if (this.plans.length > 0) {
        this.selectedPlanId.setValue(this.plans[0].id);
        this.loadRecommendations(this.plans[0].id);
      }
    });

    this.selectedPlanId.valueChanges.subscribe(id => {
      if (id) this.loadRecommendations(id);
    });
  }

  loadRecommendations(planId: string): void {
    this.loading = true;
    this.aiData = null;
    this.aiApi.getFullRecommendations(planId, true)
      .pipe(catchError(() => of(null)))
      .subscribe(res => {
        this.loading = false;
        this.aiData = res?.data ?? null;
        if (this.aiData?.method_effectiveness?.length) {
          const methods = this.aiData.method_effectiveness;
          this.methodChartOptions = {
            ...this.methodChartOptions,
            series: [{ name: 'Avg Understanding', data: methods.map(m => +(m.avg_understanding_score).toFixed(2)) }],
            xaxis: { categories: methods.map(m => m.method.replace('_', ' ')) },
          };
        }
      });
  }

  refresh(): void {
    const id = this.selectedPlanId.value;
    if (id) this.loadRecommendations(id);
  }
}
