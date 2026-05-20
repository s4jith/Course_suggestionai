import { Component, inject, OnInit } from '@angular/core';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { DatePipe } from '@angular/common';
import { TopicProgressApiService } from '../../services/topic-progress-api.service';
import { LessonPlanApiService } from '../../services/lesson-plan-api.service';
import { TopicProgress, LessonPlanSummary } from '../../models/lesson-plan.model';
import { TopicStatusChipComponent } from '../../shared/components/topic-status-chip/topic-status-chip.component';
import { LoadingSkeletonComponent } from '../../shared/components/loading-skeleton/loading-skeleton.component';

@Component({
  selector: 'app-pending-topics',
  standalone: true,
  imports: [
    MatTableModule, MatButtonModule, MatIconModule, MatSelectModule,
    MatFormFieldModule, MatDialogModule, MatProgressBarModule, DatePipe,
    TopicStatusChipComponent, LoadingSkeletonComponent,
  ],
  templateUrl: './pending-topics.component.html',
  styleUrl: './pending-topics.component.scss',
})
export class PendingTopicsComponent implements OnInit {
  private readonly progressApi = inject(TopicProgressApiService);
  private readonly planApi = inject(LessonPlanApiService);
  readonly dialog = inject(MatDialog);

  topics: TopicProgress[] = [];
  filteredTopics: TopicProgress[] = [];
  plans: LessonPlanSummary[] = [];

  selectedPlanId = '';
  loading = true;

  readonly displayedColumns = ['topic', 'plan', 'chapter', 'planned_date', 'status', 'completion', 'actions'];

  ngOnInit(): void {
    this.loadData();
    this.planApi.getPlans(0, 100).subscribe(res => { this.plans = res.data ?? []; });
  }

  loadData(): void {
    this.loading = true;
    const planId = this.selectedPlanId || undefined;
    this.progressApi.getPending(planId).subscribe({
      next: (res) => {
        this.topics = res.data ?? [];
        this.filteredTopics = [...this.topics];
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }

  onPlanFilter(planId: string): void {
    this.selectedPlanId = planId;
    this.loadData();
  }

  async openUpdateDialog(topic: TopicProgress): Promise<void> {
    const { TopicUpdateDialogComponent } = await import('../topic-update-dialog/topic-update-dialog.component');
    const plan = this.plans.find(p => p.id === topic.lesson_plan_id);
    if (!plan) return;

    // Build minimal context for dialog
    const planFull = { id: plan.id, subject_id: topic.subject_id } as never;
    const chapter = { chapter_id: topic.chapter_id, title: topic.chapter_title ?? 'Chapter', topics: [] } as never;
    const topicObj = { topic_id: topic.topic_id, title: topic.topic_title ?? 'Topic' } as never;

    const ref = this.dialog.open(TopicUpdateDialogComponent, {
      data: { plan: planFull, chapter, topic: topicObj, existingProgress: topic },
      width: '640px',
      maxHeight: '90vh',
    });
    ref.afterClosed().subscribe(result => {
      if (result) this.loadData();
    });
  }

  getPlanTitle(planId: string): string {
    return this.plans.find(p => p.id === planId)?.title ?? planId.slice(0, 8) + '…';
  }
}
