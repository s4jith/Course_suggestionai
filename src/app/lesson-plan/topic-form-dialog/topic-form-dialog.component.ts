import { Component, inject } from '@angular/core';
import { FormBuilder, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { LessonPlanApiService } from '../../services/lesson-plan-api.service';
import { NotificationService } from '../../core/services/notification.service';
import { Chapter, LessonPlan, Topic } from '../../models/lesson-plan.model';

export interface TopicFormDialogData {
  plan: LessonPlan;
  chapter: Chapter;
}

@Component({
  selector: 'app-topic-form-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatDialogModule, MatFormFieldModule, MatInputModule,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule,
  ],
  templateUrl: './topic-form-dialog.component.html',
  styles: [`.dialog-form { display:flex; flex-direction:column; gap:4px; min-width:480px; } .full-width { width:100%; } .form-row { display:flex; gap:12px; } .flex-1 { flex:1; } .subtopic-row { display:flex; align-items:center; gap:8px; }`]
})
export class TopicFormDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly planApi = inject(LessonPlanApiService);
  private readonly notification = inject(NotificationService);
  readonly dialogRef = inject(MatDialogRef<TopicFormDialogComponent>);
  readonly data = inject<TopicFormDialogData>(MAT_DIALOG_DATA);

  loading = false;

  form = this.fb.group({
    title:        ['', [Validators.required, Validators.minLength(3)]],
    description:  [''],
    planned_hours: [1, [Validators.required, Validators.min(0.5)]],
    planned_date:  ['' as string],
    subtopics:    this.fb.array([] as ReturnType<typeof this.createSubtopicGroup>[]),
  });

  get subtopics() { return this.form.get('subtopics') as FormArray; }

  createSubtopicGroup() {
    return this.fb.group({ title: ['', Validators.required] });
  }

  addSubtopic() { this.subtopics.push(this.createSubtopicGroup()); }
  removeSubtopic(i: number) { this.subtopics.removeAt(i); }

  onSubmit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.loading = true;
    const raw = this.form.getRawValue();
    const nextOrder = (this.data.chapter.topics?.length ?? 0) + 1;
    const subtopics = (raw.subtopics as { title: string }[]).map((s, idx) => ({
      title: s.title,
      order: idx + 1,
    }));
    this.planApi.addTopic(this.data.plan.id, this.data.chapter.chapter_id, {
      title: raw.title!,
      description: raw.description || undefined,
      planned_hours: raw.planned_hours!,
      planned_date: raw.planned_date || undefined,
      order: nextOrder,
      subtopics: subtopics as never,
    } as Partial<Topic>).subscribe({
      next: (res) => {
        this.loading = false;
        if (res.success && res.data) {
          this.notification.success('Topic added');
          this.dialogRef.close(res.data);
        }
      },
      error: () => { this.loading = false; },
    });
  }
}
