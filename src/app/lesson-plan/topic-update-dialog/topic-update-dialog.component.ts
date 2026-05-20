import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSliderModule } from '@angular/material/slider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { TopicProgressApiService } from '../../services/topic-progress-api.service';
import { NotificationService } from '../../core/services/notification.service';
import {
  Chapter, LessonPlan, Topic, TopicProgress, TopicStatus, TeachingMethod
} from '../../models/lesson-plan.model';
import { TEACHING_METHODS, TOPIC_STATUSES, UNDERSTANDING_LEVELS } from '../lesson-plan.constants';
import { TopicStatusChipComponent } from '../../shared/components/topic-status-chip/topic-status-chip.component';

export interface TopicUpdateDialogData {
  plan: LessonPlan;
  chapter: Chapter;
  topic: Topic;
  existingProgress?: TopicProgress;
}

@Component({
  selector: 'app-topic-update-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatDialogModule, MatFormFieldModule, MatInputModule, MatSelectModule,
    MatButtonModule, MatIconModule, MatSliderModule, MatProgressSpinnerModule,
    MatDividerModule, TopicStatusChipComponent,
  ],
  templateUrl: './topic-update-dialog.component.html',
  styleUrl: './topic-update-dialog.component.scss',
})
export class TopicUpdateDialogComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly progressApi = inject(TopicProgressApiService);
  private readonly notification = inject(NotificationService);
  readonly dialogRef = inject(MatDialogRef<TopicUpdateDialogComponent>);
  readonly data = inject<TopicUpdateDialogData>(MAT_DIALOG_DATA);

  readonly teachingMethods = TEACHING_METHODS;
  readonly topicStatuses = TOPIC_STATUSES;
  readonly understandingLevels = UNDERSTANDING_LEVELS;

  loading = false;
  isUpdate = false;

  form = this.fb.group({
    status:                     ['in_progress' as TopicStatus, Validators.required],
    completion_percentage:      [0, [Validators.required, Validators.min(0), Validators.max(100)]],
    teaching_method:            ['' as TeachingMethod | ''],
    actual_date:                [''],
    duration_taken:             [null as number | null, [Validators.min(0.25)]],
    student_understanding_level:[''],
    remarks:                    [''],
    issues:                     [''],
  });

  get currentPct(): number { return this.form.get('completion_percentage')?.value ?? 0; }
  get currentStatus(): TopicStatus { return (this.form.get('status')?.value as TopicStatus) ?? 'pending'; }

  ngOnInit(): void {
    const ep = this.data.existingProgress;
    if (ep) {
      this.isUpdate = true;
      this.form.patchValue({
        status:                      ep.status,
        completion_percentage:       ep.completion_percentage,
        teaching_method:             ep.teaching_method ?? '',
        actual_date:                 ep.actual_date ? ep.actual_date.split('T')[0] : '',
        duration_taken:              ep.duration_taken,
        student_understanding_level: ep.student_understanding_level ?? '',
        remarks:                     ep.remarks ?? '',
        issues:                      ep.issues ?? '',
      });
    }

    // Auto-set status based on completion %
    this.form.get('completion_percentage')?.valueChanges.subscribe(pct => {
      if (pct === 100 && this.form.get('status')?.value === 'in_progress') {
        this.form.get('status')?.setValue('completed', { emitEvent: false });
      } else if ((pct ?? 0) > 0 && this.form.get('status')?.value === 'pending') {
        this.form.get('status')?.setValue('in_progress', { emitEvent: false });
      }
    });
  }

  onSubmit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.loading = true;
    const raw = this.form.getRawValue();
    const body = {
      lesson_plan_id:              this.data.plan.id,
      chapter_id:                  this.data.chapter.chapter_id,
      topic_id:                    this.data.topic.topic_id,
      subject_id:                  this.data.plan.subject_id,
      status:                      raw.status as TopicStatus,
      completion_percentage:       raw.completion_percentage ?? 0,
      teaching_method:             (raw.teaching_method || undefined) as TeachingMethod | undefined,
      actual_date:                 raw.actual_date || undefined,
      duration_taken:              raw.duration_taken ?? undefined,
      student_understanding_level: (raw.student_understanding_level || undefined) as never,
      remarks:                     raw.remarks || undefined,
      issues:                      raw.issues || undefined,
    };

    const call$ = this.isUpdate
      ? this.progressApi.updateProgress(this.data.existingProgress!.id, body)
      : this.progressApi.recordProgress(body);

    call$.subscribe({
      next: (res) => {
        this.loading = false;
        if (res.success && res.data) {
          this.notification.success(this.isUpdate ? 'Progress updated' : 'Progress recorded');
          this.dialogRef.close(res.data as TopicProgress);
        }
      },
      error: () => { this.loading = false; },
    });
  }
}
