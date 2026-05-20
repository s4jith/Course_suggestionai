import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError, BehaviorSubject, filter, take } from 'rxjs';
import { TokenService } from '../services/token.service';
import { AuthService } from '../services/auth.service';
import { NotificationService } from '../services/notification.service';
import { LoadingService } from '../services/loading.service';
import { environment } from '../../../environments/environment';
import { HttpClient } from '@angular/common/http';
import { ApiResponse } from '../../models/api-response.model';
import { AuthTokens } from '../../models/auth.model';
import { finalize } from 'rxjs';

let isRefreshing = false;
const refreshTokenSubject$ = new BehaviorSubject<string | null>(null);

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const tokenService = inject(TokenService);
  const authService = inject(AuthService);
  const notification = inject(NotificationService);
  const loading = inject(LoadingService);
  const http = inject(HttpClient);

  loading.show();

  return next(req).pipe(
    finalize(() => loading.hide()),
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 && !req.url.includes('/auth/login') && !req.url.includes('/auth/refresh')) {
        return handle401(req, next, http, tokenService, authService, notification);
      }

      if (error.status === 403) {
        notification.error('You do not have permission to perform this action.');
      } else if (error.status === 422) {
        const detail = error.error?.detail;
        if (Array.isArray(detail) && detail.length > 0) {
          notification.error(detail[0].msg ?? 'Validation error');
        } else {
          notification.error('Validation error. Please check your input.');
        }
      } else if (error.status === 500) {
        notification.error('Internal server error. Please try again later.');
      } else if (error.status === 0) {
        notification.error('Cannot connect to the server. Please check your connection.');
      } else if (error.status !== 401) {
        const msg = error.error?.message ?? error.message ?? 'An unexpected error occurred.';
        notification.error(msg);
      }

      return throwError(() => error);
    })
  );
};

function handle401(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
  http: HttpClient,
  tokenService: TokenService,
  authService: AuthService,
  notification: NotificationService
) {
  if (isRefreshing) {
    return refreshTokenSubject$.pipe(
      filter(token => token !== null),
      take(1),
      switchMap(token => next(req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })))
    );
  }

  isRefreshing = true;
  refreshTokenSubject$.next(null);

  const refreshToken = tokenService.getRefreshToken();
  if (!refreshToken) {
    isRefreshing = false;
    authService.logout();
    return throwError(() => new Error('No refresh token'));
  }

  return http.post<ApiResponse<AuthTokens>>(
    `${environment.apiUrl}/auth/refresh`,
    { refresh_token: refreshToken }
  ).pipe(
    switchMap(response => {
      isRefreshing = false;
      const tokens = response.data!;
      tokenService.setTokens(tokens.access_token, tokens.refresh_token);
      refreshTokenSubject$.next(tokens.access_token);
      return next(req.clone({ setHeaders: { Authorization: `Bearer ${tokens.access_token}` } }));
    }),
    catchError(err => {
      isRefreshing = false;
      authService.logout();
      notification.error('Session expired. Please log in again.');
      return throwError(() => err);
    })
  );
}
