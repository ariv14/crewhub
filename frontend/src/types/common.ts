// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
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
