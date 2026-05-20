import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ApiResponse, PaginatedResponse } from '../models/api-response.model';
import { TopicProgress, CompletionStats, TeachingMethod, UnderstandingLevel } from '../models/lesson-plan.model';

export interface RecordProgressBody {
  lesson_plan_id: string;
  chapter_id: string;
  topic_id: string;
  subtopic_id?: string;
  subject_id: string;
  status: string;
  completion_percentage?: number;
  teaching_method?: TeachingMethod;
  actual_date?: string;
  duration_taken?: number;
  student_understanding_level?: UnderstandingLevel;
  remarks?: string;
  issues?: string;
}

@Injectable({ providedIn: 'root' })
export class TopicProgressApiService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/topic-progress`;

  recordProgress(body: RecordProgressBody): Observable<ApiResponse<TopicProgress>> {
    return this.http.post<ApiResponse<TopicProgress>>(this.base, body);
  }

  updateProgress(id: string, body: Partial<RecordProgressBody>): Observable<ApiResponse<TopicProgress>> {
    return this.http.patch<ApiResponse<TopicProgress>>(`${this.base}/${id}`, body);
  }

  getPending(lessonPlanId?: string): Observable<PaginatedResponse<TopicProgress>> {
    let params = new HttpParams();
    if (lessonPlanId) params = params.set('lesson_plan_id', lessonPlanId);
    return this.http.get<PaginatedResponse<TopicProgress>>(`${this.base}/pending`, { params });
  }

  getCompletionStats(lessonPlanId: string): Observable<ApiResponse<CompletionStats>> {
    return this.http.get<ApiResponse<CompletionStats>>(
      `${this.base}/stats/${lessonPlanId}`
    );
  }

  getFacultyProgress(
    lessonPlanId: string,
    skip = 0,
    limit = 50
  ): Observable<PaginatedResponse<TopicProgress>> {
    const params = new HttpParams()
      .set('lesson_plan_id', lessonPlanId)
      .set('skip', skip)
      .set('limit', limit);
    return this.http.get<PaginatedResponse<TopicProgress>>(this.base, { params });
  }
}
