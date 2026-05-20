export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  full_name: string;
  password: string;
  role: 'admin' | 'teacher';
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface DecodedToken {
  sub: string;
  email: string;
  role: string;
  type: 'access' | 'refresh';
  exp: number;
  iat: number;
}
