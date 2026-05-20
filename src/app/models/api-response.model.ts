/** Standard API envelope returned by the FastAPI backend. */
export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T | null;
}

export interface ApiError {
  success: false;
  error_code: string;
  message: string;
  detail: unknown;
}

export interface PaginatedResponse<T> {
  success: boolean;
  message: string;
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
