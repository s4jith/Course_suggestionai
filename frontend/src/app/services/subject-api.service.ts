import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ApiResponse, PaginatedResponse } from '../models/api-response.model';
import { Subject, SubjectCreate } from '../models/lesson-plan.model';

@Injectable({ providedIn: 'root' })
export class SubjectApiService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/subjects`;

  getSubjects(
    skip = 0,
    limit = 20,
    search?: string,
    department?: string
  ): Observable<PaginatedResponse<Subject>> {
    let params = new HttpParams()
      .set('skip', skip)
      .set('limit', limit);
    if (search) params = params.set('search', search);
    if (department) params = params.set('department', department);
    return this.http.get<PaginatedResponse<Subject>>(this.base, { params });
  }

  getSubject(id: string): Observable<ApiResponse<Subject>> {
    return this.http.get<ApiResponse<Subject>>(`${this.base}/${id}`);
  }

  createSubject(body: SubjectCreate): Observable<ApiResponse<Subject>> {
    return this.http.post<ApiResponse<Subject>>(this.base, body);
  }

  updateSubject(id: string, body: Partial<SubjectCreate>): Observable<ApiResponse<Subject>> {
    return this.http.patch<ApiResponse<Subject>>(`${this.base}/${id}`, body);
  }

  deactivateSubject(id: string): Observable<ApiResponse<null>> {
    return this.http.delete<ApiResponse<null>>(`${this.base}/${id}`);
  }
}
