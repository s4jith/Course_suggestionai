import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { TokenService } from './token.service';
import { User } from '../../models/user.model';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly tokenService = inject(TokenService);
  private readonly router = inject(Router);

  private readonly _currentUser$ = new BehaviorSubject<User | null>(
    this.loadUserFromStorage()
  );

  readonly currentUser$: Observable<User | null> = this._currentUser$.asObservable();

  get currentUser(): User | null {
    return this._currentUser$.value;
  }

  setUser(user: User): void {
    localStorage.setItem('lp_user', JSON.stringify(user));
    this._currentUser$.next(user);
  }

  logout(): void {
    this.tokenService.clearTokens();
    this._currentUser$.next(null);
    this.router.navigate(['/auth/login']);
  }

  isAuthenticated(): boolean {
    return this.tokenService.isAuthenticated();
  }

  isAdmin(): boolean {
    return this.tokenService.isAdmin();
  }

  private loadUserFromStorage(): User | null {
    try {
      const raw = localStorage.getItem('lp_user');
      return raw ? (JSON.parse(raw) as User) : null;
    } catch {
      return null;
    }
  }
}
