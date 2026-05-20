import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatCardModule } from '@angular/material/card';
import { LessonPlanApiService } from '../../services/lesson-plan-api.service';
import { SubjectApiService } from '../../services/subject-api.service';
import { NotificationService } from '../../core/services/notification.service';
import { Subject } from '../../models/lesson-plan.model';
import { LESSON_PLAN_STATUSES, getAcademicYearOptions } from '../lesson-plan.constants';

@Component({
  selector: 'app-lesson-plan-form',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule, MatInputModule, MatSelectModule,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatCardModule,
  ],
  templateUrl: './lesson-plan-form.component.html',
  styleUrl: './lesson-plan-form.component.scss',
})
export class LessonPlanFormComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly planApi = inject(LessonPlanApiService);
  private readonly subjectApi = inject(SubjectApiService);
  private readonly notification = inject(NotificationService);
  private readonly router = inject(Router);

  readonly academicYears = getAcademicYearOptions();
  readonly planStatuses = LESSON_PLAN_STATUSES.slice(0, 2); // only draft / active
  readonly semesters = [1, 2, 3, 4, 5, 6, 7, 8];

  subjects: Subject[] = [];
  loadingSubjects = true;
  submitting = false;

  form = this.fb.group({
    subject_id:    ['', Validators.required],
    academic_year: [this.academicYears[1], Validators.required],
    semester:      [null as number | null, [Validators.required, Validators.min(1), Validators.max(8)]],
    title:         ['', [Validators.required, Validators.minLength(5)]],
    description:   [''],
    status:        ['draft', Validators.required],
  });

  ngOnInit(): void {
    this.subjectApi.getSubjects(0, 100).subscribe({
      next: (res) => {
        this.subjects = res.data ?? [];
        this.loadingSubjects = false;
      },
      error: () => { this.loadingSubjects = false; },
    });
  }

  onSubjectChange(subjectId: string): void {
    const subject = this.subjects.find(s => s.id === subjectId);
    if (subject && !this.form.get('semester')?.value) {
      this.form.get('semester')?.setValue(subject.semester);
    }
  }

  onSubmit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.submitting = true;
    const raw = this.form.getRawValue();
    this.planApi.createPlan({
      subject_id:    raw.subject_id!,
      academic_year: raw.academic_year!,
      semester:      raw.semester!,
      title:         raw.title!,
      description:   raw.description || undefined,
    }).subscribe({
      next: (res) => {
        this.submitting = false;
        if (res.success && res.data) {
          this.notification.success('Lesson plan created!');
          this.router.navigate(['/lesson-plans', res.data.id]);
        }
      },
      error: () => { this.submitting = false; },
    });
  }

  goBack(): void {
    this.router.navigate(['/lesson-plans']);
  }
}
