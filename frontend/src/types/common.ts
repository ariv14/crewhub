export interface PaginatedResponse<T> {
  total: number;
  page?: number;
  per_page?: number;
  items?: T[];
}

export interface ApiError {
  detail: string;
  status_code?: number;
}
