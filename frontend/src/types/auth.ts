export interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  is_admin?: boolean;
  created_at: string;
}

export interface UserCreate {
  email: string;
  password: string;
  name: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface UserUpdate {
  name?: string;
  email?: string;
}

export interface ApiKeyCreate {
  name: string;
}

export interface ApiKeyResponse {
  key: string;
  name: string;
  created_at: string;
}
