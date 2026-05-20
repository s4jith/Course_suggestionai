import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { SubjectApiService } from '../../services/subject-api.service';
import { NotificationService } from '../../core/services/notification.service';
import { Subject } from '../../models/lesson-plan.model';

@Component({
  selector: 'app-subject-form-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatDialogModule, MatFormFieldModule, MatInputModule,
    MatSelectModule, MatButtonModule, MatProgressSpinnerModule,
  ],
  templateUrl: './subject-form-dialog.component.html',
  styleUrl: './subject-form-dialog.component.scss',
})
export class SubjectFormDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly subjectApi = inject(SubjectApiService);
  private readonly notification = inject(NotificationService);
  readonly dialogRef = inject(MatDialogRef<SubjectFormDialogComponent>);

  loading = false;

  form = this.fb.group({
    name:        ['', [Validators.required, Validators.minLength(3)]],
    code:        ['', [Validators.required, Validators.minLength(2), Validators.maxLength(20)]],
    department:  ['', Validators.required],
    semester:    [null as number | null, [Validators.required, Validators.min(1), Validators.max(8)]],
    total_hours: [60, [Validators.required, Validators.min(1)]],
    description: [''],
  });

  readonly semesters = [1, 2, 3, 4, 5, 6, 7, 8];

  onSubmit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.loading = true;
    const { name, code, department, semester, total_hours, description } = this.form.getRawValue() as {
      name: string; code: string; department: string;
      semester: number; total_hours: number; description: string;
    };
    this.subjectApi.createSubject({ name, code, department, semester, total_hours, description: description || undefined }).subscribe({
      next: (res) => {
        this.loading = false;
        if (res.success && res.data) {
          this.notification.success(`Subject "${res.data.name}" created.`);
          this.dialogRef.close(res.data as Subject);
        }
      },
      error: () => { this.loading = false; },
    });
  }
}
