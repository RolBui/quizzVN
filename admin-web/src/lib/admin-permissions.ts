import type { AuthUser } from "./api";

export type AdminPermissionKey =
  | "teachers"
  | "students"
  | "admins"
  | "classes"
  | "exams"
  | "documents";

export interface PermissionOption {
  key: AdminPermissionKey;
  label: string;
}

export const defaultAdminPermissions: AdminPermissionKey[] = [];

export const permissionOptions: PermissionOption[] = [
  { key: "teachers", label: "Giáo viên" },
  { key: "students", label: "Học sinh" },
  { key: "admins", label: "Quản trị viên" },
  { key: "classes", label: "Lớp học" },
  { key: "exams", label: "Bài thi" },
  { key: "documents", label: "Tài liệu" },
];

const allowedPermissionKeys = new Set(
  permissionOptions.map((option) => option.key),
);

export function getAdminPermissions(user: AuthUser | null | undefined) {
  if (!user) {
    return [];
  }
  if (user.role_name !== "admin") {
    return permissionOptions.map((option) => option.key);
  }
  return normalizePermissions(user.admin_permissions);
}

export function hasAdminPermission(
  user: AuthUser | null | undefined,
  permission: AdminPermissionKey,
) {
  if (!user) {
    return false;
  }
  if (user.role_name !== "admin") {
    return true;
  }
  return getAdminPermissions(user).includes(permission);
}

export function useAdminPermissions(user: AuthUser | null | undefined) {
  return getAdminPermissions(user);
}

export function normalizePermissions(value: unknown): AdminPermissionKey[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((key): key is AdminPermissionKey =>
    allowedPermissionKeys.has(key as AdminPermissionKey),
  );
}
