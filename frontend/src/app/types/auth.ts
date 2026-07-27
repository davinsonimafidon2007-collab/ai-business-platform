export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_verified: boolean;
  role: string;
  created_at: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}