import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ApiResponse } from '../models/api-response.model';
import {
  AIRecommendationResponse, RiskAssessment, NextTopicRecommendation,
  WeakAreaAlert, TimetableEntry, OllamaHealthStatus
} from '../models/ai.model';

@Injectable({ providedIn: 'root' })
export class AiApiService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/ai`;

  getHealth(): Observable<ApiResponse<OllamaHealthStatus>> {
    return this.http.get<ApiResponse<OllamaHealthStatus>>(`${this.base}/health`);
  }

  getFullRecommendations(lessonPlanId: string, useAi = true): Observable<ApiResponse<AIRecommendationResponse>> {
    return this.http.get<ApiResponse<AIRecommendationResponse>>(
      `${this.base}/recommendations/${lessonPlanId}?use_ai=${useAi}`
    );
  }

  getRiskAssessment(lessonPlanId: string): Observable<ApiResponse<RiskAssessment>> {
    return this.http.get<ApiResponse<RiskAssessment>>(
      `${this.base}/risk/${lessonPlanId}`
    );
  }

  getNextTopic(lessonPlanId: string): Observable<ApiResponse<NextTopicRecommendation>> {
    return this.http.get<ApiResponse<NextTopicRecommendation>>(
      `${this.base}/next-topic/${lessonPlanId}`
    );
  }

  getTimetable(lessonPlanId: string, weeksAhead = 4): Observable<ApiResponse<TimetableEntry[]>> {
    return this.http.get<ApiResponse<TimetableEntry[]>>(
      `${this.base}/timetable/${lessonPlanId}?weeks_ahead=${weeksAhead}`
    );
  }

  getWeakAreas(lessonPlanId: string): Observable<ApiResponse<WeakAreaAlert[]>> {
    return this.http.get<ApiResponse<WeakAreaAlert[]>>(
      `${this.base}/weak-areas/${lessonPlanId}`
    );
  }
}
