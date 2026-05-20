import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { LessonPlanApiService } from '../../services/lesson-plan-api.service';
import { NotificationService } from '../../core/services/notification.service';
import { Chapter, LessonPlan } from '../../models/lesson-plan.model';

export interface ChapterFormDialogData {
  plan: LessonPlan;
}

@Component({
  selector: 'app-chapter-form-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatDialogModule, MatFormFieldModule, MatInputModule,
    MatButtonModule, MatProgressSpinnerModule,
  ],
  template: `
    <h2 mat-dialog-title>Add Chapter</h2>
    <mat-dialog-content>
      <form [formGroup]="form" novalidate class="dialog-form">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Chapter Title</mat-label>
          <input matInput formControlName="title" placeholder="e.g. Introduction to Arrays" />
          @if (form.get('title')?.invalid && form.get('title')?.touched) {
            <mat-error>Title is required</mat-error>
          }
        </mat-form-field>
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Description (Optional)</mat-label>
          <textarea matInput formControlName="description" rows="3"></textarea>
        </mat-form-field>
      </form>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Cancel</button>
      <button mat-flat-button color="primary" (click)="onSubmit()" [disabled]="loading">
        @if (loading) { <mat-spinner diameter="18" style="display:inline-block;margin-right:6px" /> }
        Add Chapter
      </button>
    </mat-dialog-actions>
  `,
  styles: [`.dialog-form { display:flex; flex-direction:column; gap:4px; min-width:420px; } .full-width { width:100%; }`]
})
export class ChapterFormDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly planApi = inject(LessonPlanApiService);
  private readonly notification = inject(NotificationService);
  readonly dialogRef = inject(MatDialogRef<ChapterFormDialogComponent>);
  readonly data = inject<ChapterFormDialogData>(MAT_DIALOG_DATA);

  loading = false;
  form = this.fb.group({
    title: ['', [Validators.required, Validators.minLength(3)]],
    description: [''],
  });

  onSubmit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.loading = true;
    const nextOrder = (this.data.plan.chapters?.length ?? 0) + 1;
    const { title, description } = this.form.getRawValue() as { title: string; description: string };
    this.planApi.addChapter(this.data.plan.id, {
      title,
      description: description || undefined,
      order: nextOrder,
      topics: [],
    } as Partial<Chapter>).subscribe({
      next: (res) => {
        this.loading = false;
        if (res.success && res.data) {
          this.notification.success('Chapter added');
          this.dialogRef.close(res.data);
        }
      },
      error: () => { this.loading = false; },
    });
  }
}
