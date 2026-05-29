import { useEffect, useMemo, useState } from "react";
import { AlertCircle, FileText, Hash, MoreVertical, Search, Users } from "lucide-react";
import { adminApi, type AdminClass, type AdminClassOverview } from "../lib/api";
import { formatDate, initials } from "../lib/format";

const fallbackOverview: AdminClassOverview = {
  metrics: [],
  items: [],
};

function TeacherAvatar({ classroom }: { classroom: AdminClass }) {
  if (classroom.teacher_avatar_url) {
    return <img src={classroom.teacher_avatar_url} alt={classroom.teacher_name || "Giáo viên"} className="w-10 h-10 rounded-full object-cover" />;
  }
  return (
    <div className="w-10 h-10 rounded-full bg-surface-container flex items-center justify-center text-outline font-semibold text-sm">
      {classroom.teacher_name ? initials(classroom.teacher_name) : "GV"}
    </div>
  );
}

export function Classes() {
  const [overview, setOverview] = useState<AdminClassOverview>(fallbackOverview);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    adminApi
      .getClassesOverview()
      .then((response) => {
        if (isMounted) {
          setOverview(response);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Không thể tải danh sách lớp học.");
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const filteredClasses = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return overview.items.filter((classroom) => {
      return (
        !normalizedQuery ||
        classroom.name.toLowerCase().includes(normalizedQuery) ||
        classroom.join_code.toLowerCase().includes(normalizedQuery) ||
        (classroom.teacher_name || "").toLowerCase().includes(normalizedQuery)
      );
    });
  }, [overview.items, query]);

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-xl md:text-xl font-bold text-on-surface">Quản lý Lớp học</h1>
        </div>
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tìm lớp, mã lớp hoặc giáo viên..."
            className="w-full bg-surface-container-lowest border border-surface-variant rounded-lg pl-9 pr-3 py-2 text-sm text-on-surface focus:ring-1 focus:ring-primary outline-none placeholder:text-outline"
          />
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-[#F59E0B]/40 bg-[#F59E0B]/10 px-4 py-3 text-sm text-on-surface flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-[#F59E0B]" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {overview.metrics.map((metric) => (
          <div key={metric.key} className="bg-surface-container-lowest rounded-xl p-5 border border-surface-variant shadow-(--shadow-level-1)">
            <p className="text-sm text-outline">{metric.label}</p>
            <p className="text-2xl font-bold text-on-surface mt-2">{metric.value.toLocaleString("vi-VN")}{metric.suffix}</p>
            <p className="text-xs text-outline mt-1">{metric.subtext}</p>
          </div>
        ))}
      </div>

      <div className="border-b border-surface-variant flex gap-6 mt-2">
        <button className="pb-3 text-sm font-semibold text-primary border-b-2 border-primary">Tất cả Lớp học</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-2">
        {filteredClasses.map((classroom) => (
          <div key={classroom.id} className="bg-surface-container-lowest rounded-xl shadow-(--shadow-level-1) border border-surface-variant overflow-hidden flex flex-col">
            <div className="h-24 bg-surface-container-low relative flex items-center justify-between px-5">
              <div>
                <p className="text-[10px] uppercase tracking-widest text-outline font-bold">Mã lớp</p>
                <p className="text-2xl font-bold text-primary">{classroom.join_code}</p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                <Hash className="w-6 h-6" />
              </div>
            </div>

            <div className="p-5 flex flex-col flex-1">
              <div className="flex justify-between items-start mb-2">
                <p className="text-[10px] font-bold text-primary uppercase tracking-widest">{formatDate(classroom.created_at)}</p>
                <MoreVertical className="w-4 h-4 text-outline cursor-pointer" />
              </div>
              <h3 className="text-lg font-bold text-on-surface leading-tight mb-2">{classroom.name}</h3>
              <p className="text-sm text-outline line-clamp-2 min-h-10">{classroom.description || "Chưa có mô tả lớp học."}</p>

              <div className="flex items-center gap-3 my-5">
                <TeacherAvatar classroom={classroom} />
                <div>
                  <p className="text-sm font-semibold text-on-surface">{classroom.teacher_name || "Chưa gán giáo viên"}</p>
                  <p className="text-xs text-outline">Giáo viên phụ trách</p>
                </div>
              </div>

              <div className="mt-auto grid grid-cols-3 pt-4 border-t border-surface-variant gap-4">
                <div>
                  <p className="text-xs font-semibold text-outline flex items-center gap-1.5 mb-1"><Users className="w-3.5 h-3.5" /> Học sinh</p>
                  <p className="text-xl font-bold text-on-surface leading-none">{classroom.student_count}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-outline flex items-center gap-1.5 mb-1"><FileText className="w-3.5 h-3.5" /> Bài thi</p>
                  <p className="text-xl font-bold text-on-surface leading-none">{classroom.exam_count}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-outline flex items-center gap-1.5 mb-1"><FileText className="w-3.5 h-3.5" /> Tài liệu</p>
                  <p className="text-xl font-bold text-on-surface leading-none">{classroom.document_count}</p>
                </div>
              </div>
            </div>
          </div>
        ))}

        {!isLoading && filteredClasses.length === 0 && (
          <div className="md:col-span-2 lg:col-span-3 bg-surface-container-lowest rounded-xl border border-surface-variant p-10 text-center text-sm text-outline">
            Chưa có lớp học phù hợp.
          </div>
        )}
        {isLoading && (
          <div className="md:col-span-2 lg:col-span-3 bg-surface-container-lowest rounded-xl border border-surface-variant p-10 text-center text-sm text-outline">
            Đang tải dữ liệu lớp học...
          </div>
        )}
      </div>
    </div>
  );
}
