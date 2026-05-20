import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TitleCasePipe, DecimalPipe } from '@angular/common';
import { forkJoin } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog } from '@angular/material/dialog';
import { LessonPlanApiService } from '../../services/lesson-plan-api.service';
import { TopicProgressApiService } from '../../services/topic-progress-api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { TopicStatusChipComponent } from '../../shared/components/topic-status-chip/topic-status-chip.component';
import { LoadingSkeletonComponent } from '../../shared/components/loading-skeleton/loading-skeleton.component';
import { LessonPlan, CompletionStats, TopicProgress, Chapter, Topic } from '../../models/lesson-plan.model';

@Component({
  selector: 'app-lesson-plan-detail',
  standalone: true,
  imports: [
    RouterLink, TitleCasePipe, DecimalPipe,
    MatCardModule, MatExpansionModule, MatButtonModule, MatIconModule,
    MatProgressBarModule, MatDividerModule, MatProgressSpinnerModule,
    PageHeaderComponent, TopicStatusChipComponent, LoadingSkeletonComponent,
  ],
  templateUrl: './lesson-plan-detail.component.html',
  styleUrl: './lesson-plan-detail.component.scss',
})
export class LessonPlanDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly planApi = inject(LessonPlanApiService);
  private readonly progressApi = inject(TopicProgressApiService);
  private readonly dialog = inject(MatDialog);

  plan: LessonPlan | null = null;
  stats: CompletionStats | null = null;
  progressMap = new Map<string, TopicProgress>();
  loading = true;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id')!;
    forkJoin({
      plan: this.planApi.getPlan(id),
      stats: this.progressApi.getCompletionStats(id),
      progress: this.progressApi.getFacultyProgress(id, 0, 200),
    }).subscribe({
      next: ({ plan, stats, progress }) => {
        this.loading = false;
        this.plan = plan.data ?? null;
        this.stats = stats.data ?? null;
        (progress.data ?? []).forEach(p => this.progressMap.set(p.topic_id, p));
      },
      error: () => { this.loading = false; },
    });
  }

  getTopicProgress(topicId: string): TopicProgress | undefined {
    return this.progressMap.get(topicId);
  }

  async openAddChapter(): Promise<void> {
    if (!this.plan) return;
    const { ChapterFormDialogComponent } = await import('../chapter-form-dialog/chapter-form-dialog.component');
    const ref = this.dialog.open(ChapterFormDialogComponent, {
      data: { plan: this.plan },
      width: '500px',
    });
    ref.afterClosed().subscribe((updated: LessonPlan) => {
      if (updated) this.plan = updated;
    });
  }

  async openAddTopic(chapter: Chapter): Promise<void> {
    if (!this.plan) return;
    const { TopicFormDialogComponent } = await import('../topic-form-dialog/topic-form-dialog.component');
    const ref = this.dialog.open(TopicFormDialogComponent, {
      data: { plan: this.plan, chapter },
      width: '560px',
      maxHeight: '90vh',
    });
    ref.afterClosed().subscribe((updated: LessonPlan) => {
      if (updated) this.plan = updated;
    });
  }

  async openUpdateProgress(chapter: Chapter, topic: Topic): Promise<void> {
    if (!this.plan) return;
    const { TopicUpdateDialogComponent } = await import('../topic-update-dialog/topic-update-dialog.component');
    const ref = this.dialog.open(TopicUpdateDialogComponent, {
      data: {
        plan: this.plan,
        chapter,
        topic,
        existingProgress: this.progressMap.get(topic.topic_id),
      },
      width: '640px',
      maxHeight: '90vh',
    });
    ref.afterClosed().subscribe((result: TopicProgress) => {
      if (result) this.progressMap.set(result.topic_id, result);
    });
  }

  get aiRoute(): string[] { return ['/ai']; }
}
