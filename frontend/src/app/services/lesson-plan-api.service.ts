import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ApiResponse, PaginatedResponse } from '../models/api-response.model';
import {
  LessonPlan, LessonPlanSummary, LessonPlanCreate,
  Chapter, Topic, Subtopic
} from '../models/lesson-plan.model';

@Injectable({ providedIn: 'root' })
export class LessonPlanApiService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/lesson-plans`;

  getPlans(
    skip = 0,
    limit = 20,
    teacherId?: string,
    subjectId?: string,
    status?: string
  ): Observable<PaginatedResponse<LessonPlanSummary>> {
    let params = new HttpParams().set('skip', skip).set('limit', limit);
    if (teacherId) params = params.set('teacher_id', teacherId);
    if (subjectId) params = params.set('subject_id', subjectId);
    if (status) params = params.set('status', status);
    return this.http.get<PaginatedResponse<LessonPlanSummary>>(this.base, { params });
  }

  getPlan(id: string): Observable<ApiResponse<LessonPlan>> {
    return this.http.get<ApiResponse<LessonPlan>>(`${this.base}/${id}`);
  }

  createPlan(body: LessonPlanCreate): Observable<ApiResponse<LessonPlan>> {
    return this.http.post<ApiResponse<LessonPlan>>(this.base, body);
  }

  updatePlan(id: string, body: Partial<LessonPlanCreate>): Observable<ApiResponse<LessonPlan>> {
    return this.http.patch<ApiResponse<LessonPlan>>(`${this.base}/${id}`, body);
  }

  deletePlan(id: string): Observable<ApiResponse<null>> {
    return this.http.delete<ApiResponse<null>>(`${this.base}/${id}`);
  }

  addChapter(planId: string, body: Partial<Chapter>): Observable<ApiResponse<LessonPlan>> {
    return this.http.post<ApiResponse<LessonPlan>>(`${this.base}/${planId}/chapters`, body);
  }

  updateChapter(planId: string, chapterId: string, body: Partial<Chapter>): Observable<ApiResponse<LessonPlan>> {
    return this.http.patch<ApiResponse<LessonPlan>>(`${this.base}/${planId}/chapters/${chapterId}`, body);
  }

  addTopic(planId: string, chapterId: string, body: Partial<Topic>): Observable<ApiResponse<LessonPlan>> {
    return this.http.post<ApiResponse<LessonPlan>>(`${this.base}/${planId}/chapters/${chapterId}/topics`, body);
  }

  addSubtopic(planId: string, chapterId: string, topicId: string, body: Partial<Subtopic>): Observable<ApiResponse<LessonPlan>> {
    return this.http.post<ApiResponse<LessonPlan>>(
      `${this.base}/${planId}/chapters/${chapterId}/topics/${topicId}/subtopics`,
      body
    );
  }
}
