import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { TitleCasePipe } from '@angular/common';
import { debounceTime, distinctUntilChanged, switchMap, startWith, of, catchError } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { LessonPlanApiService } from '../../services/lesson-plan-api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { LessonPlanSummary, LessonPlanStatus } from '../../models/lesson-plan.model';

@Component({
  selector: 'app-lesson-plan-list',
  standalone: true,
  imports: [
    RouterLink, ReactiveFormsModule, TitleCasePipe,
    MatCardModule, MatButtonModule, MatIconModule,
    MatFormFieldModule, MatInputModule, MatSelectModule,
    MatPaginatorModule, MatProgressSpinnerModule,
    PageHeaderComponent,
  ],
  templateUrl: './lesson-plan-list.component.html',
  styleUrl: './lesson-plan-list.component.scss',
})
export class LessonPlanListComponent implements OnInit {
  private readonly planApi = inject(LessonPlanApiService);

  plans: LessonPlanSummary[] = [];
  total = 0;
  pageSize = 12;
  pageIndex = 0;
  loading = false;

  statusFilter = new FormControl<LessonPlanStatus | ''>('');

  ngOnInit(): void {
    this.statusFilter.valueChanges.pipe(
      startWith(''),
      debounceTime(200),
      distinctUntilChanged(),
      switchMap(status => {
        this.loading = true;
        this.pageIndex = 0;
        return this.planApi.getPlans(0, this.pageSize, undefined, undefined, status || undefined)
          .pipe(catchError(() => of(null)));
      })
    ).subscribe(res => {
      this.loading = false;
      this.plans = res?.data ?? [];
      this.total = res?.total ?? 0;
    });
  }

  onPage(e: PageEvent): void {
    this.pageIndex = e.pageIndex;
    this.pageSize = e.pageSize;
    const skip = this.pageIndex * this.pageSize;
    this.loading = true;
    this.planApi.getPlans(skip, this.pageSize, undefined, undefined, this.statusFilter.value || undefined)
      .pipe(catchError(() => of(null)))
      .subscribe(res => {
        this.loading = false;
        this.plans = res?.data ?? [];
        this.total = res?.total ?? 0;
      });
  }

  statusColor(status: LessonPlanStatus): string {
    const map: Record<LessonPlanStatus, string> = {
      active: 'status-active',
      draft: 'status-draft',
      completed: 'status-completed',
      archived: 'status-archived',
    };
    return map[status] ?? '';
  }
}
