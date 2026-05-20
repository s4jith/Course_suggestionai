import { Injectable } from '@angular/core';
import { DecodedToken } from '../../models/auth.model';

const ACCESS_TOKEN_KEY = 'lp_access_token';
const REFRESH_TOKEN_KEY = 'lp_refresh_token';
const USER_KEY = 'lp_user';

@Injectable({ providedIn: 'root' })
export class TokenService {

  setTokens(access: string, refresh: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, access);
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  }

  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  clearTokens(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  isAuthenticated(): boolean {
    const token = this.getAccessToken();
    if (!token) return false;
    try {
      const decoded = this.decode(token);
      return decoded.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  }

  isExpired(): boolean {
    return !this.isAuthenticated();
  }

  decode(token: string): DecodedToken {
    const payload = token.split('.')[1];
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decoded) as DecodedToken;
  }

  getDecodedToken(): DecodedToken | null {
    const token = this.getAccessToken();
    if (!token) return null;
    try { return this.decode(token); } catch { return null; }
  }

  getRole(): string | null {
    return this.getDecodedToken()?.role ?? null;
  }

  isAdmin(): boolean {
    return this.getRole() === 'admin';
  }
}
