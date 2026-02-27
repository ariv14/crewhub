import { api } from "../api-client";
import type {
  User,
  Token,
  UserCreate,
  UserUpdate,
  ApiKeyCreate,
  ApiKeyResponse,
} from "@/types/auth";

export async function getMe(): Promise<User> {
  return api.get("/auth/me");
}

export async function loginLocal(
  email: string,
  password: string
): Promise<Token> {
  return api.post("/auth/login", { email, password, name: "" });
}

export async function registerLocal(data: UserCreate): Promise<User> {
  return api.post("/auth/register", data);
}

export async function firebaseAuth(idToken: string): Promise<User> {
  return api.post("/auth/firebase", { id_token: idToken });
}

export async function updateMe(data: UserUpdate): Promise<User> {
  return api.put("/auth/me", data);
}

export async function createApiKey(data: ApiKeyCreate): Promise<ApiKeyResponse> {
  return api.post("/auth/api-keys", data);
}
