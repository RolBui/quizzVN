const configuredApiBaseUrl = (
  import.meta.env.VITE_API_BASE_URL as string | undefined
)
  ?.trim()
  .replace(/\/$/, "");
const API_BASE_URL = configuredApiBaseUrl || "http://localhost:8000";

function apiWebSocketUrl(path: string) {
  const url = new URL(`${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export interface AuthUser {
  id: number;
  role_id: number | null;
  role_name: string | null;
  full_name: string;
  username: string;
  email: string;
  phone: string | null;
  avatar_url: string | null;
  auth_type: string;
  email_verified: boolean;
  status: string;
  is_first_login: boolean;
  max_exam_create: number;
  max_document_create: number;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
  needs_onboarding: boolean;
}

export type AdminAccountRole = "administrator" | "admin";
export type AdminAccountStatus = "active" | "disabled";

export interface AdminAccount {
  id: number;
  full_name: string;
  username: string;
  email: string;
  role_name: AdminAccountRole;
  status: string;
  is_online: boolean;
  email_verified: boolean;
  auth_type: string;
  avatar_url: string | null;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminAccountListResponse {
  items: AdminAccount[];
}

export interface AdminAccountResponse {
  message: string;
  admin: AdminAccount;
}

export interface AuthSession {
  id: number;
  login_method: string;
  ip_address: string | null;
  user_agent: string | null;
  is_revoked: boolean;
  expires_at: string;
  refresh_expires_at: string | null;
  created_at: string;
  last_used_at: string | null;
}

export interface AuthSessionResponse {
  message: string;
  user: AuthUser;
  session: AuthSession;
}

export interface MeResponse {
  user: AuthUser;
  session: AuthSession;
}

export interface CrmMetric {
  key: string;
  label: string;
  value: number;
  suffix: string;
  trend: string;
  is_up: boolean;
  subtext: string;
  sparkline?: number[];
}

export interface CrmTrafficPoint {
  name: string;
  current: number;
  last: number;
}

export interface CrmScoreBucket {
  name: string;
  users: number;
}

export interface CrmRecentResult {
  attempt_id: number;
  code: string;
  student_name: string;
  exam_title: string;
  submitted_at: string;
  score_label: string;
  score_percent: number;
  status: string;
}

export interface CrmOverview {
  metrics: CrmMetric[];
  traffic: CrmTrafficPoint[];
  score_distribution: CrmScoreBucket[];
  recent_results: CrmRecentResult[];
  last_updated_at: string;
}

export type CrmPeriod = "7d" | "30d" | "year";

export type AnalyticsPeriod = "7d" | "30d" | "year";

export interface AnalyticsMetric {
  key: string;
  label: string;
  value: number;
  suffix: string;
  trend: string;
  is_up: boolean;
  subtext: string;
}

export interface AnalyticsTrafficPoint {
  name: string;
  current: number;
  last: number;
}

export interface AnalyticsBreakdownItem {
  name: string;
  value: number;
}

export interface AnalyticsPopularPage {
  path: string;
  title: string | null;
  views: number;
  unique_visitors: number;
}

export interface AnalyticsRealtimePage {
  path: string;
  title: string | null;
  active_users: number;
}

export interface AnalyticsRealtime {
  active_users: number;
  active_sessions: number;
  active_pages: AnalyticsRealtimePage[];
  active_window_seconds: number;
  last_updated_at: string;
}

export interface AnalyticsOverview {
  metrics: AnalyticsMetric[];
  traffic: AnalyticsTrafficPoint[];
  devices: AnalyticsBreakdownItem[];
  sources: AnalyticsBreakdownItem[];
  popular_pages: AnalyticsPopularPage[];
  realtime: AnalyticsRealtime;
  last_updated_at: string;
}

export interface AdminMetric {
  key: string;
  label: string;
  value: number;
  suffix: string;
  trend: string;
  is_up: boolean;
  subtext: string;
  sparkline?: number[];
}

export interface AdminTeacher {
  id: number;
  code: string;
  full_name: string;
  username: string;
  email: string;
  phone: string | null;
  avatar_url: string | null;
  status: string;
  is_online: boolean;
  school_name: string | null;
  date_of_birth: string | null;
  gender: string | null;
  class_count: number;
  exam_count: number;
  document_count: number;
  last_login_at: string | null;
  created_at: string;
}

export interface AdminTeacherOverview {
  metrics: AdminMetric[];
  items: AdminTeacher[];
}

export interface AdminStudent {
  id: number;
  code: string;
  full_name: string;
  username: string;
  email: string;
  phone: string | null;
  avatar_url: string | null;
  status: string;
  is_online: boolean;
  school_name: string | null;
  date_of_birth: string | null;
  gender: string | null;
  class_count: number;
  attempt_count: number;
  average_score: number | null;
  last_login_at: string | null;
  created_at: string;
}

export interface AdminStudentOverview {
  metrics: AdminMetric[];
  items: AdminStudent[];
}

export interface AdminClass {
  id: number;
  name: string;
  description: string | null;
  join_code: string;
  teacher_id: number | null;
  teacher_name: string | null;
  teacher_avatar_url: string | null;
  student_count: number;
  exam_count: number;
  document_count: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AdminClassOverview {
  metrics: AdminMetric[];
  items: AdminClass[];
}

export interface AdminExam {
  id: number;
  title: string;
  description: string | null;
  scope: string;
  classroom_id: number | null;
  classroom_name: string | null;
  teacher_id: number | null;
  teacher_name: string | null;
  duration_minutes: number;
  total_points: number;
  question_count: number;
  attempt_count: number;
  average_score: number | null;
  is_published: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminExamOverview {
  metrics: AdminMetric[];
  items: AdminExam[];
}

export interface AdminDocument {
  id: number;
  title: string;
  summary: string | null;
  content_preview: string;
  file_url: string | null;
  file_name: string | null;
  file_content_type: string | null;
  file_size_bytes: number | null;
  scope: string;
  classroom_id: number | null;
  classroom_name: string | null;
  teacher_id: number | null;
  teacher_name: string | null;
  is_published: boolean;
  content_length: number;
  created_at: string;
  updated_at: string;
}

export interface AdminDocumentOverview {
  metrics: AdminMetric[];
  items: AdminDocument[];
}

export interface AdminTeacherClassDetail {
  id: number;
  name: string;
  description: string | null;
  join_code: string;
  student_count: number;
  exam_count: number;
  document_count: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AdminStudentClassDetail {
  id: number;
  name: string;
  description: string | null;
  join_code: string;
  teacher_id: number | null;
  teacher_name: string | null;
  student_count: number;
  exam_count: number;
  document_count: number;
  joined_at: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AdminStudentAttempt {
  id: number;
  exam_id: number;
  exam_title: string;
  classroom_id: number | null;
  classroom_name: string | null;
  score: number | null;
  total_points: number;
  score_percent: number | null;
  status: string;
  started_at: string;
  submitted_at: string | null;
  created_at: string;
}

export interface AdminTeacherDetail {
  teacher: AdminTeacher;
  metrics: AdminMetric[];
  classes: AdminTeacherClassDetail[];
  exams: AdminExam[];
  documents: AdminDocument[];
}

export interface AdminStudentDetail {
  student: AdminStudent;
  metrics: AdminMetric[];
  classes: AdminStudentClassDetail[];
  attempts: AdminStudentAttempt[];
  exams: AdminExam[];
  documents: AdminDocument[];
}

export interface AdminUserProfileUpdatePayload {
  full_name?: string;
  email?: string;
  phone?: string | null;
  avatar_url?: string | null;
  date_of_birth?: string | null;
  gender?: string | null;
  school_name?: string | null;
  status?: AdminAccountStatus;
}

export interface ChatUser {
  id: number;
  full_name: string;
  email: string;
  avatar_url: string | null;
  role_name: string | null;
  school_name: string | null;
  is_online: boolean;
}

export interface ChatMessage {
  id: number;
  conversation_id: number;
  sender_id: number;
  sender_name: string;
  sender_avatar_url: string | null;
  body: string;
  attachment_url: string | null;
  attachment_filename: string | null;
  attachment_content_type: string | null;
  attachment_size_bytes: number | null;
  created_at: string;
  is_own: boolean;
}

export interface ChatConversation {
  id: number;
  title: string | null;
  is_group: boolean;
  participants: ChatUser[];
  last_message: ChatMessage | null;
  unread_count: number;
  updated_at: string;
}

export interface ChatContactListResponse {
  items: ChatUser[];
}

export interface ChatConversationListResponse {
  items: ChatConversation[];
}

export interface ChatConversationResponse {
  conversation: ChatConversation;
}

export interface ChatMessageListResponse {
  items: ChatMessage[];
}

export interface ChatMessageResponse {
  message: ChatMessage;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    ...options,
    headers: {
      Accept: "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        message = body.detail;
      }
    } catch {
      // Keep the generic message when the API does not return JSON.
    }
    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<T>;
}

async function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(path);
}

async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiRequest<T>(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function apiPostForm<T>(path: string, body: FormData): Promise<T> {
  return apiRequest<T>(path, {
    method: "POST",
    body,
  });
}

async function apiDelete<T>(path: string): Promise<T> {
  return apiRequest<T>(path, {
    method: "DELETE",
  });
}

export const authApi = {
  login: (email: string, password: string) =>
    apiPost<AuthSessionResponse>("/auth/login", { email, password }),
  me: () => apiGet<MeResponse>("/auth/me"),
  logout: () => apiPost<{ message: string }>("/auth/logout"),
};

export const adminApi = {
  getCrmOverview: (period: CrmPeriod = "7d") =>
    apiGet<CrmOverview>(`/admin/crm/overview?period=${period}`),
  getAnalyticsTraffic: (period: AnalyticsPeriod = "7d") =>
    apiGet<AnalyticsOverview>(`/admin/analytics/traffic?period=${period}`),
  getAnalyticsRealtime: () =>
    apiGet<AnalyticsRealtime>("/admin/analytics/realtime"),
  getTeachersOverview: () => apiGet<AdminTeacherOverview>("/admin/teachers"),
  getTeacherDetail: (teacherId: number) =>
    apiGet<AdminTeacherDetail>(`/admin/teachers/${teacherId}`),
  updateTeacherProfile: (
    teacherId: number,
    payload: AdminUserProfileUpdatePayload,
  ) =>
    apiRequest<AdminTeacherDetail>(`/admin/teachers/${teacherId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }),
  resetTeacherPassword: (teacherId: number, password: string) =>
    apiPost<{ message: string }>(`/admin/teachers/${teacherId}/reset-password`, {
      password,
    }),
  deleteTeacher: (teacherId: number) =>
    apiDelete<{ message: string }>(`/admin/teachers/${teacherId}`),
  getStudentsOverview: () => apiGet<AdminStudentOverview>("/admin/students"),
  getStudentDetail: (studentId: number) =>
    apiGet<AdminStudentDetail>(`/admin/students/${studentId}`),
  updateStudentProfile: (
    studentId: number,
    payload: AdminUserProfileUpdatePayload,
  ) =>
    apiRequest<AdminStudentDetail>(`/admin/students/${studentId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }),
  resetStudentPassword: (studentId: number, password: string) =>
    apiPost<{ message: string }>(`/admin/students/${studentId}/reset-password`, {
      password,
    }),
  deleteStudent: (studentId: number) =>
    apiDelete<{ message: string }>(`/admin/students/${studentId}`),
  getClassesOverview: () => apiGet<AdminClassOverview>("/admin/classes"),
  getExamsOverview: () => apiGet<AdminExamOverview>("/admin/exams"),
  deleteExam: (examId: number) =>
    apiDelete<{ message: string }>(`/admin/exams/${examId}`),
  getDocumentsOverview: () => apiGet<AdminDocumentOverview>("/admin/documents"),
  listAccounts: () => apiGet<AdminAccountListResponse>("/admin/users"),
  createAccount: (payload: {
    full_name: string;
    email: string;
    password: string;
  }) => apiPost<AdminAccountResponse>("/admin/users", payload),
  deleteAccount: (userId: number) =>
    apiRequest<{ message: string }>(`/admin/users/${userId}`, {
      method: "DELETE",
    }),
};

export const chatApi = {
  listContacts: (query = "") =>
    apiGet<ChatContactListResponse>(
      `/chat/contacts${query ? `?query=${encodeURIComponent(query)}` : ""}`,
    ),
  listConversations: () => apiGet<ChatConversationListResponse>("/chat/conversations"),
  createConversation: (participantId: number) =>
    apiPost<ChatConversationResponse>("/chat/conversations", {
      participant_id: participantId,
    }),
  deleteConversation: (conversationId: number) =>
    apiDelete<{ message: string }>(`/chat/conversations/${conversationId}`),
  deleteMessage: (messageId: number) =>
    apiDelete<{ message: string }>(`/chat/messages/${messageId}`),
  listMessages: (conversationId: number) =>
    apiGet<ChatMessageListResponse>(`/chat/conversations/${conversationId}/messages`),
  sendMessage: (conversationId: number, body: string) =>
    apiPost<ChatMessageResponse>(`/chat/conversations/${conversationId}/messages`, {
      body,
    }),
  sendAttachment: (conversationId: number, file: File, body = "") => {
    const formData = new FormData();
    formData.append("file", file);
    if (body.trim()) {
      formData.append("body", body.trim());
    }
    return apiPostForm<ChatMessageResponse>(
      `/chat/conversations/${conversationId}/attachments`,
      formData,
    );
  },
  shareMessage: (messageId: number, participantId: number, body = "") =>
    apiPost<ChatMessageResponse>(`/chat/messages/${messageId}/share`, {
      participant_id: participantId,
      body,
    }),
  websocketUrl: () => apiWebSocketUrl("/chat/ws"),
};
