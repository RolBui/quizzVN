import { FormEvent, useEffect, useState } from "react";
import { AlertCircle, Calendar, Image as ImageIcon, Link, LayoutTemplate, UploadCloud, Users } from "lucide-react";
import { adminApi, type AdminAppearanceOverview, type AdminBanner } from "../lib/api";
import { formatDate } from "../lib/format";

const fallbackOverview: AdminAppearanceOverview = {
  metrics: [],
  banners: [],
};

const today = new Date().toISOString().slice(0, 10);

function audienceLabel(audience: string) {
  if (audience === "teachers") {
    return "Tất cả giáo viên";
  }
  if (audience === "students") {
    return "Tất cả học sinh";
  }
  return "Tất cả người dùng";
}

function bannerStatus(banner: AdminBanner) {
  if (banner.status === "active") {
    return { label: "Đang hoạt động", className: "text-green-700 bg-green-100" };
  }
  if (banner.status === "scheduled") {
    return { label: "Đã lên lịch", className: "text-primary bg-primary/10" };
  }
  if (banner.status === "expired") {
    return { label: "Hết hạn", className: "text-outline bg-surface-variant" };
  }
  return { label: "Vô hiệu hóa", className: "text-[#EF4444] bg-[#EF4444]/10" };
}

function toApiDate(value: string, endOfDay = false) {
  return `${value}T${endOfDay ? "23:59:59" : "00:00:00"}+07:00`;
}

export function Appearance() {
  const [overview, setOverview] = useState<AdminAppearanceOverview>(fallbackOverview);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [form, setForm] = useState({
    title: "",
    image_url: "",
    link_url: "",
    audience: "all" as "all" | "teachers" | "students",
    start_at: today,
    end_at: today,
  });

  const loadAppearance = () => {
    setIsLoading(true);
    setError(null);
    adminApi
      .getAppearanceOverview()
      .then((response) => setOverview(response))
      .catch((err) => setError(err instanceof Error ? err.message : "Không thể tải dữ liệu giao diện."))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadAppearance();
  }, []);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await adminApi.createBanner({
        title: form.title,
        image_url: form.image_url || null,
        link_url: form.link_url || null,
        audience: form.audience,
        start_at: toApiDate(form.start_at),
        end_at: toApiDate(form.end_at, true),
        is_active: true,
      });
      setSuccess("Đã lưu banner vào DB.");
      setForm({
        title: "",
        image_url: "",
        link_url: "",
        audience: "all",
        start_at: today,
        end_at: today,
      });
      loadAppearance();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể tạo banner.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-xl md:text-xl font-bold text-on-surface">Tùy chỉnh Giao diện</h1>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-[#F59E0B]/40 bg-[#F59E0B]/10 px-4 py-3 text-sm text-on-surface flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-[#F59E0B]" />
          {error}
        </div>
      )}
      {success && (
        <div className="rounded-lg border border-[#10B981]/40 bg-[#10B981]/10 px-4 py-3 text-sm text-[#047857]">
          {success}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {overview.metrics.map((metric) => (
          <div key={metric.key} className="bg-surface-container-lowest rounded-xl p-5 border border-surface-variant shadow-(--shadow-level-1)">
            <p className="text-sm text-outline">{metric.label}</p>
            <p className="text-2xl font-bold text-on-surface mt-2">{metric.value.toLocaleString("vi-VN")}</p>
            <p className="text-xs text-outline mt-1">{metric.subtext}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <form onSubmit={handleSubmit} className="bg-surface-container-lowest rounded-xl p-6 shadow-(--shadow-level-1) border border-surface-variant flex flex-col">
          <h2 className="text-lg font-bold text-on-surface flex items-center gap-2 mb-6">
            <ImageIcon className="w-5 h-5 text-[#4C5B9E]" /> Tạo Banner mới
          </h2>

          <div className="space-y-5">
            <div>
              <label className="block text-[11px] font-bold text-outline uppercase tracking-wider mb-2">Tiêu đề Banner</label>
              <input
                value={form.title}
                onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                required
                className="w-full px-4 py-2 bg-surface-container-low border border-outline-variant rounded-md text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-[#4C5B9E] outline-none"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold text-outline uppercase tracking-wider mb-2">URL hình ảnh</label>
              <div className="relative">
                <UploadCloud className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  value={form.image_url}
                  onChange={(event) => setForm((current) => ({ ...current, image_url: event.target.value }))}
                  type="url"
                  placeholder="https://..."
                  className="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-md text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-[#4C5B9E] outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-outline uppercase tracking-wider mb-2">URL liên kết đích</label>
              <div className="relative">
                <Link className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  value={form.link_url}
                  onChange={(event) => setForm((current) => ({ ...current, link_url: event.target.value }))}
                  type="url"
                  placeholder="https://..."
                  className="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-md text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-[#4C5B9E] outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-bold text-outline uppercase tracking-wider mb-2">Ngày bắt đầu</label>
                <div className="relative">
                  <Calendar className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    value={form.start_at}
                    onChange={(event) => setForm((current) => ({ ...current, start_at: event.target.value }))}
                    type="date"
                    required
                    className="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-md text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-[#4C5B9E] outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-outline uppercase tracking-wider mb-2">Ngày kết thúc</label>
                <div className="relative">
                  <Calendar className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    value={form.end_at}
                    onChange={(event) => setForm((current) => ({ ...current, end_at: event.target.value }))}
                    type="date"
                    required
                    className="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-md text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-[#4C5B9E] outline-none"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-outline uppercase tracking-wider mb-2">Đối tượng mục tiêu</label>
              <div className="relative">
                <Users className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
                <select
                  value={form.audience}
                  onChange={(event) => setForm((current) => ({ ...current, audience: event.target.value as "all" | "teachers" | "students" }))}
                  className="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-md text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-[#4C5B9E] outline-none appearance-none"
                >
                  <option value="all">Tất cả người dùng</option>
                  <option value="students">Tất cả học sinh</option>
                  <option value="teachers">Tất cả giáo viên</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSaving}
              className="px-4 py-2 bg-[#4C5B9E] text-white rounded-lg text-sm font-medium hover:bg-[#4C5B9E]/90 transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-70"
            >
              <UploadCloud className="w-4 h-4" /> {isSaving ? "Đang lưu..." : "Xuất bản Banner mới"}
            </button>
          </div>
        </form>

        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-(--shadow-level-1) border border-surface-variant flex flex-col">
          <div className="flex justify-between items-center mb-6 pb-2 border-b border-surface-variant">
            <h2 className="text-lg font-bold text-on-surface flex items-center gap-2">
              <LayoutTemplate className="w-5 h-5 text-[#4C5B9E]" />
              Banner trong DB
            </h2>
          </div>

          <div className="space-y-4">
            {overview.banners.map((banner) => {
              const status = bannerStatus(banner);
              return (
                <div key={banner.id} className="flex flex-col sm:flex-row gap-4 p-4 border border-surface-variant rounded-xl shadow-sm hover:bg-surface-container-low/50 transition-colors">
                  <div className="relative w-full sm:w-48 h-28 shrink-0 rounded-lg overflow-hidden bg-surface-container">
                    {banner.image_url ? (
                      <img src={banner.image_url} alt={banner.title} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-outline">
                        <ImageIcon className="w-8 h-8" />
                      </div>
                    )}
                    <div className="absolute top-2 right-2">
                      <span className={`text-[9px] uppercase font-bold tracking-widest px-2 py-0.5 rounded-sm ${status.className}`}>
                        {status.label}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col justify-center gap-1.5">
                    <h3 className="font-bold text-on-surface leading-tight text-sm">{banner.title}</h3>
                    <p className="text-sm text-outline flex items-center gap-2">
                      <Users className="w-4 h-4" /> {audienceLabel(banner.audience)}
                    </p>
                    <p className="text-sm text-outline flex items-center gap-2">
                      <Calendar className="w-4 h-4" /> {formatDate(banner.start_at)} - {formatDate(banner.end_at)}
                    </p>
                    {banner.link_url && <p className="text-xs text-primary truncate max-w-70">{banner.link_url}</p>}
                  </div>
                </div>
              );
            })}
            {!isLoading && overview.banners.length === 0 && (
              <div className="rounded-xl border border-dashed border-surface-variant p-10 text-center text-sm text-outline">
                Chưa có banner nào trong DB.
              </div>
            )}
            {isLoading && (
              <div className="rounded-xl border border-dashed border-surface-variant p-10 text-center text-sm text-outline">
                Đang tải banner...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
