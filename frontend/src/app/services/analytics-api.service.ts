import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { ApiResponse } from '../models/api-response.model';
import {
  AnalyticsFilters,
  CompletionTrendResponse,
  DelayedTopicsResponse,
  FacultyAnalyticsResponse,
  HeatmapResponse,
  OverviewKPI,
  RiskScoresResponse,
  SubjectAnalyticsResponse,
  SyllabusCompletionResponse,
  TeachingMethodResponse,
  UnderstandingAnalyticsResponse,
} from '../models/analytics.model';

@Injectable({ providedIn: 'root' })
export class AnalyticsApiService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/analytics`;

  private buildParams(filters?: AnalyticsFilters, extras?: Record<string, string | number>): HttpParams {
    let params = new HttpParams();
    if (filters?.academic_year) params = params.set('academic_year', filters.academic_year);
    if (filters?.semester != null) params = params.set('semester', filters.semester);
    if (filters?.department) params = params.set('department', filters.department);
    if (filters?.teacher_id) params = params.set('teacher_id', filters.teacher_id);
    if (filters?.subject_id) params = params.set('subject_id', filters.subject_id);
    if (extras) {
      Object.entries(extras).forEach(([k, v]) => { params = params.set(k, v); });
    }
    return params;
  }

  getOverview(filters?: AnalyticsFilters): Observable<OverviewKPI> {
    return this.http
      .get<ApiResponse<OverviewKPI>>(`${this.base}/overview`, { params: this.buildParams(filters) })
      .pipe(map(r => r.data!));
  }

  getSyllabusCompletion(filters?: AnalyticsFilters): Observable<SyllabusCompletionResponse> {
    return this.http
      .get<ApiResponse<SyllabusCompletionResponse>>(`${this.base}/syllabus-completion`, { params: this.buildParams(filters) })
      .pipe(map(r => r.data!));
  }

  getFacultyAnalytics(filters?: AnalyticsFilters): Observable<FacultyAnalyticsResponse> {
    return this.http
      .get<ApiResponse<FacultyAnalyticsResponse>>(`${this.base}/faculty`, { params: this.buildParams(filters) })
      .pipe(map(r => r.data!));
  }

  getSubjectAnalytics(filters?: AnalyticsFilters): Observable<SubjectAnalyticsResponse> {
    return this.http
      .get<ApiResponse<SubjectAnalyticsResponse>>(`${this.base}/subjects`, { params: this.buildParams(filters) })
      .pipe(map(r => r.data!));
  }

  getDelayedTopics(filters?: AnalyticsFilters): Observable<DelayedTopicsResponse> {
    return this.http
      .get<ApiResponse<DelayedTopicsResponse>>(`${this.base}/delayed-topics`, { params: this.buildParams(filters) })
      .pipe(map(r => r.data!));
  }

  getRiskScores(filters?: AnalyticsFilters): Observable<RiskScoresResponse> {
    return this.http
      .get<ApiResponse<RiskScoresResponse>>(`${this.base}/risk-scores`, { params: this.buildParams(filters) })
      .pipe(map(r => r.data!));
  }

  getTeachingMethodEffectiveness(filters?: AnalyticsFilters): Observable<TeachingMethodResponse> {
    return this.http
      .get<ApiResponse<TeachingMethodResponse>>(`${this.base}/teaching-methods`, { params: this.buildParams(filters) })
      .pipe(map(r => r.data!));
  }

  getUnderstandingAnalytics(filters?: AnalyticsFilters): Observable<UnderstandingAnalyticsResponse> {
    return this.http
      .get<ApiResponse<UnderstandingAnalyticsResponse>>(`${this.base}/understanding`, { params: this.buildParams(filters) })
      .pipe(map(r => r.data!));
  }

  getCompletionTrend(days = 30, teacherId?: string): Observable<CompletionTrendResponse> {
    const extras: Record<string, string | number> = { days };
    if (teacherId) extras['teacher_id'] = teacherId;
    return this.http
      .get<ApiResponse<CompletionTrendResponse>>(`${this.base}/completion-trend`, { params: this.buildParams(undefined, extras) })
      .pipe(map(r => r.data!));
  }

  getHeatmap(days = 90, teacherId?: string): Observable<HeatmapResponse> {
    const extras: Record<string, string | number> = { days };
    if (teacherId) extras['teacher_id'] = teacherId;
    return this.http
      .get<ApiResponse<HeatmapResponse>>(`${this.base}/heatmap`, { params: this.buildParams(undefined, extras) })
      .pipe(map(r => r.data!));
  }
}
