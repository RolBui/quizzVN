export function formatNumber(value: number | null | undefined, suffix = "") {
  return `${Math.round(value ?? 0).toLocaleString("vi-VN")}${suffix}`;
}

export function formatDecimal(value: number | null | undefined, suffix = "") {
  if (value === null || value === undefined) {
    return `0${suffix}`;
  }
  return `${value.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}${suffix}`;
}

function parseDisplayDate(value: string) {
  const dateOnly = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (dateOnly) {
    const [, year, month, day] = dateOnly;
    return new Date(Number(year), Number(month) - 1, Number(day));
  }
  return new Date(value);
}

export function formatDate(value: string | null | undefined) {
  if (!value) {
    return "Chưa có";
  }
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(parseDisplayDate(value));
}

export function formatAge(value: string | null | undefined) {
  if (!value) {
    return "Chưa cập nhật";
  }

  const birthDate = parseDisplayDate(value);
  if (Number.isNaN(birthDate.getTime())) {
    return "Chưa cập nhật";
  }

  const today = new Date();
  let age = today.getFullYear() - birthDate.getFullYear();
  const hasHadBirthdayThisYear =
    today.getMonth() > birthDate.getMonth() ||
    (today.getMonth() === birthDate.getMonth() &&
      today.getDate() >= birthDate.getDate());

  if (!hasHadBirthdayThisYear) {
    age -= 1;
  }

  return age >= 0 ? `${age} tuổi` : "Chưa cập nhật";
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "Chưa có";
  }
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(value));
}

export function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) {
    return "?";
  }
  return parts.slice(0, 2).map((part) => part[0]?.toUpperCase()).join("");
}

export function accountStatusLabel(status: string) {
  if (status === "active") {
    return "Hoạt động";
  }
  if (status === "disabled") {
    return "Vô hiệu hóa";
  }
  return status || "Không rõ";
}

export function scopeLabel(scope: string) {
  return scope === "class" ? "Trong lớp" : "Hệ thống";
}
