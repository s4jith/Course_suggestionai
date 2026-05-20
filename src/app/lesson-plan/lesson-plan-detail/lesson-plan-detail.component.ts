import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TitleCasePipe, DecimalPipe } from '@angular/common';
import { switchMap } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { LessonPlanApiService } from '../../services/lesson-plan-api.service';
import { TopicProgressApiService } from '../../services/topic-progress-api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { LessonPlan, CompletionStats } from '../../models/lesson-plan.model';

@Component({
  selector: 'app-lesson-plan-detail',
  standalone: true,
  imports: [
    RouterLink, TitleCasePipe, DecimalPipe,
    MatCardModule, MatExpansionModule, MatButtonModule, MatIconModule,
    MatProgressBarModule, MatDividerModule, MatProgressSpinnerModule,
    PageHeaderComponent,
  ],
  templateUrl: './lesson-plan-detail.component.html',
  styleUrl: './lesson-plan-detail.component.scss',
})
export class LessonPlanDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly planApi = inject(LessonPlanApiService);
  private readonly progressApi = inject(TopicProgressApiService);

  plan: LessonPlan | null = null;
  stats: CompletionStats | null = null;
  loading = true;

  ngOnInit(): void {
    this.route.paramMap.pipe(
      switchMap(params => this.planApi.getPlan(params.get('id')!))
    ).subscribe({
      next: (res) => {
        this.loading = false;
        this.plan = res.data;
        if (res.data) {
          this.progressApi.getCompletionStats(res.data.id).subscribe(statsRes => {
            this.stats = statsRes.data;
          });
        }
      },
      error: () => { this.loading = false; },
    });
  }

  get aiRoute(): string[] {
    return ['/ai'];
  }
}
