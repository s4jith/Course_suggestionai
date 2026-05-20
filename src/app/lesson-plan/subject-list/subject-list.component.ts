import { Component, OnInit, inject } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged, switchMap, startWith, of, catchError } from 'rxjs';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCardModule } from '@angular/material/card';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AsyncPipe } from '@angular/common';
import { SubjectApiService } from '../../services/subject-api.service';
import { NotificationService } from '../../core/services/notification.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { Subject } from '../../models/lesson-plan.model';

@Component({
  selector: 'app-subject-list',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatTableModule, MatPaginatorModule, MatButtonModule, MatIconModule,
    MatFormFieldModule, MatInputModule, MatCardModule,
    MatDialogModule, MatProgressSpinnerModule,
    PageHeaderComponent,
  ],
  templateUrl: './subject-list.component.html',
  styleUrl: './subject-list.component.scss',
})
export class SubjectListComponent implements OnInit {
  private readonly subjectApi = inject(SubjectApiService);
  private readonly notification = inject(NotificationService);
  private readonly dialog = inject(MatDialog);

  displayedColumns = ['code', 'name', 'department', 'semester', 'total_hours', 'actions'];
  subjects: Subject[] = [];
  total = 0;
  pageSize = 10;
  pageIndex = 0;
  loading = false;

  searchCtrl = new FormControl('');

  ngOnInit(): void {
    this.searchCtrl.valueChanges.pipe(
      startWith(''),
      debounceTime(300),
      distinctUntilChanged(),
      switchMap(search => {
        this.loading = true;
        this.pageIndex = 0;
        return this.subjectApi.getSubjects(0, this.pageSize, search ?? undefined).pipe(
          catchError(() => of(null))
        );
      })
    ).subscribe(res => {
      this.loading = false;
      this.subjects = res?.data ?? [];
      this.total = res?.total ?? 0;
    });
  }

  onPage(e: PageEvent): void {
    this.pageIndex = e.pageIndex;
    this.pageSize = e.pageSize;
    const skip = this.pageIndex * this.pageSize;
    this.loading = true;
    this.subjectApi.getSubjects(skip, this.pageSize, this.searchCtrl.value ?? undefined)
      .pipe(catchError(() => of(null)))
      .subscribe(res => {
        this.loading = false;
        this.subjects = res?.data ?? [];
        this.total = res?.total ?? 0;
      });
  }

  async openCreateSubject(): Promise<void> {
    const { SubjectFormDialogComponent } = await import('../subject-form-dialog/subject-form-dialog.component');
    const ref = this.dialog.open(SubjectFormDialogComponent, { width: '560px' });
    ref.afterClosed().subscribe((result: Subject) => {
      if (result) this.subjects = [result, ...this.subjects];
    });
  }

  deactivate(id: string): void {
    if (!confirm('Deactivate this subject?')) return;
    this.subjectApi.deactivateSubject(id).subscribe({
      next: () => {
        this.notification.success('Subject deactivated');
        this.subjects = this.subjects.filter(s => s.id !== id);
      },
    });
  }
}
