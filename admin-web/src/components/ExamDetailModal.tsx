import { useEffect, useState } from "react";
import {
  CheckCircle2,
  Clock,
  FileText,
  GraduationCap,
  HelpCircle,
  ImageIcon,
  ListChecks,
  Trophy,
  X,
} from "lucide-react";
import { adminApi } from "../lib/api";
import { cn } from "../lib/utils";
import { formatDateTime, formatDecimal } from "../lib/format";

interface ExamDetailModalProps {
  exam: any | null;
  open: boolean;
  onClose: () => void;
}

const getQuestionTypeLabel = (type: string) => {
  switch (type) {
    case "single_choice":
      return "Một đáp án";
    case "multiple_choice":
      return "Nhiều đáp án";
    case "true_false":
      return "Đúng / sai";
    case "fill_in_blank":
      return "Điền vào chỗ trống";
    case "short_answer":
      return "Trả lời ngắn";
    case "text":
    case "essay":
      return "Tự luận";
    default:
      return type;
  }
};

export function ExamDetailModal({ exam, open, onClose }: ExamDetailModalProps) {
  const [detail, setDetail] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && exam?.id) {
      setIsLoading(true);
      setError(null);
      adminApi
        .getExamDetail(exam.id)
        .then((res) => {
          setDetail(res);
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : "Không thể tải chi tiết đề thi.");
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      setDetail(null);
    }
  }, [open, exam]);

  if (!open || !exam) return null;

  const resolvedExam = detail || exam;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/55 backdrop-blur-xs">
      <div className="relative w-full max-w-4xl bg-surface-container-lowest border border-outline-variant rounded-xl shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-outline-variant flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-on-surface">Chi tiết đề thi</h2>
            <p className="text-xs text-outline">
              Xem đầy đủ nội dung câu hỏi, đáp án và trạng thái đề thi.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-surface-container-low text-outline hover:text-on-surface transition-colors"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 [scrollbar-width:thin]">
          {isLoading && !detail ? (
            <div className="py-20 text-center text-sm text-outline flex items-center justify-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent" />
              <span>Đang tải thông tin đề thi...</span>
            </div>
          ) : error ? (
            <div className="p-4 rounded-lg bg-error-container/40 border border-error-container text-center text-sm text-on-error-container">
              {error}
            </div>
          ) : (
            <>
              {/* Exam Info Card */}
              <section className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-low shadow-sm">
                <div className="relative p-6 bg-linear-to-br from-primary/10 via-secondary/5 to-tertiary/10 text-on-surface space-y-4">
                  <div className="flex flex-wrap gap-2">
                    <span className="inline-flex items-center rounded-full bg-surface-container-highest px-2.5 py-0.5 text-xs font-bold text-on-surface border border-outline-variant">
                      {resolvedExam.is_published ? "Đã xuất bản" : "Bản nháp"}
                    </span>
                    <span
                      className={cn(
                        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold border",
                        resolvedExam.is_active
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : "bg-rose-50 text-rose-700 border-rose-200"
                      )}
                    >
                      {resolvedExam.is_active ? "Hoạt động" : "Tạm dừng"}
                    </span>
                  </div>

                  <div className="space-y-1.5">
                    <h3 className="text-2xl font-bold">{resolvedExam.title}</h3>
                    <p className="text-sm text-outline">
                      {resolvedExam.description || "Đề thi chưa có mô tả."}
                    </p>
                  </div>
                </div>
              </section>

              {/* Metrics Grid */}
              <section className="grid gap-4 grid-cols-2 md:grid-cols-4">
                <div className="rounded-xl border border-outline-variant bg-surface-container-low p-4">
                  <div className="flex items-center gap-1.5 text-xs text-outline">
                    <Clock className="size-3.5" />
                    <span>Thời lượng</span>
                  </div>
                  <p className="mt-1 text-base font-semibold text-on-surface">
                    {resolvedExam.duration_minutes} phút
                  </p>
                </div>
                <div className="rounded-xl border border-outline-variant bg-surface-container-low p-4">
                  <div className="flex items-center gap-1.5 text-xs text-outline">
                    <Trophy className="size-3.5" />
                    <span>Tổng điểm</span>
                  </div>
                  <p className="mt-1 text-base font-semibold text-on-surface">
                    {resolvedExam.total_points || 10} điểm
                  </p>
                </div>
                <div className="rounded-xl border border-outline-variant bg-surface-container-low p-4">
                  <div className="flex items-center gap-1.5 text-xs text-outline">
                    <ListChecks className="size-3.5" />
                    <span>Số câu hỏi</span>
                  </div>
                  <p className="mt-1 text-base font-semibold text-on-surface">
                    {resolvedExam.question_count || 0} câu
                  </p>
                </div>
                <div className="rounded-xl border border-outline-variant bg-surface-container-low p-4">
                  <div className="flex items-center gap-1.5 text-xs text-outline">
                    <CheckCircle2 className="size-3.5" />
                    <span>Lượt làm</span>
                  </div>
                  <p className="mt-1 text-base font-semibold text-on-surface">
                    {resolvedExam.attempt_count || 0} lượt
                  </p>
                </div>
              </section>

              {/* Additional Metadata Info */}
              <section className="grid gap-4 rounded-xl border border-outline-variant bg-surface-container-low p-5 md:grid-cols-3">
                <div>
                  <span className="text-xs text-outline">Lớp học</span>
                  <p className="mt-0.5 text-sm font-semibold text-on-surface">
                    {resolvedExam.classroom_name || "Chưa gắn lớp học"}
                  </p>
                </div>
                <div>
                  <span className="text-xs text-outline">Ngày tạo</span>
                  <p className="mt-0.5 text-sm font-semibold text-on-surface">
                    {formatDateTime(resolvedExam.created_at)}
                  </p>
                </div>
                <div>
                  <span className="text-xs text-outline">Phân loại nguồn</span>
                  <p className="mt-0.5 text-sm font-semibold text-on-surface">
                    {resolvedExam.source === "system" ? "Hệ thống" : "Giáo viên"}
                  </p>
                </div>
              </section>

              {/* Questions List */}
              <section className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-primary/10 p-3 text-primary">
                    <HelpCircle className="size-5" />
                  </div>
                  <div>
                    <h4 className="text-base font-bold text-on-surface">
                      Danh sách câu hỏi
                    </h4>
                    <p className="text-xs text-outline">
                      Các đáp án đúng được làm nổi bật để kiểm tra nhanh.
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  {resolvedExam.questions && resolvedExam.questions.length > 0 ? (
                    resolvedExam.questions
                      .slice()
                      .sort((a: any, b: any) => a.order_index - b.order_index)
                      .map((question: any, idx: number) => (
                        <div
                          key={question.id || idx}
                          className="rounded-xl border border-outline-variant bg-surface-container-low p-5 space-y-4"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="inline-flex items-center rounded bg-surface-container-highest px-2 py-0.5 text-xs font-bold text-on-surface border border-outline-variant">
                                Câu {idx + 1}
                              </span>
                              <span className="inline-flex items-center rounded bg-surface-container-highest px-2 py-0.5 text-xs font-semibold text-outline border border-outline-variant">
                                {getQuestionTypeLabel(question.question_type)}
                              </span>
                            </div>
                            <span className="text-xs font-bold text-primary">
                              {question.points} điểm
                            </span>
                          </div>

                          <p className="text-sm font-semibold text-on-surface whitespace-pre-wrap">
                            {question.prompt}
                          </p>

                          {question.image_url && (
                            <div className="overflow-hidden rounded-lg border border-outline-variant max-w-md bg-surface">
                              <img
                                src={question.image_url}
                                alt={`Hình ảnh minh họa câu ${idx + 1}`}
                                className="max-h-60 object-contain w-full"
                              />
                            </div>
                          )}

                          {question.question_type === "fill_in_blank" || question.question_type === "short_answer" ? (
                            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                              <div className="flex items-center gap-2 text-xs font-bold text-emerald-800">
                                <FileText className="size-4" />
                                <span>Đáp án chấp nhận:</span>
                              </div>
                              <div className="mt-2 flex flex-wrap gap-2">
                                {question.accepted_answers && question.accepted_answers.length > 0 ? (
                                  question.accepted_answers.map((answer: string) => (
                                    <span
                                      key={answer}
                                      className="inline-flex items-center rounded bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 border border-emerald-200"
                                    >
                                      {answer}
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-xs text-emerald-700 italic">
                                    Chưa có đáp án nào.
                                  </span>
                                )}
                              </div>
                            </div>
                          ) : question.question_type === "true_false" ? (
                            <div className="grid gap-2.5 sm:grid-cols-2">
                              {[
                                { label: "Đúng", value: "true" },
                                { label: "Sai", value: "false" }
                              ].map((opt) => {
                                const isCorrect = question.accepted_answers?.[0] === opt.value;
                                return (
                                  <div
                                    key={opt.value}
                                    className={cn(
                                      "rounded-lg border px-4 py-3 flex items-center gap-3 text-xs transition-colors",
                                      isCorrect
                                        ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                                        : "border-outline-variant bg-surface text-on-surface-variant"
                                    )}
                                  >
                                    <div
                                      className={cn(
                                        "flex size-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-bold",
                                        isCorrect
                                          ? "border-emerald-500 bg-emerald-500 text-white"
                                          : "border-outline-variant bg-surface-container text-outline"
                                      )}
                                    >
                                      {isCorrect ? "✓" : ""}
                                    </div>
                                    <p className={isCorrect ? "font-bold" : ""}>
                                      {opt.label}
                                    </p>
                                  </div>
                                );
                              })}
                            </div>
                          ) : (
                            <div className="grid gap-2.5 sm:grid-cols-2">
                              {question.options &&
                                question.options.map((option: any, oIdx: number) => (
                                  <div
                                    key={option.id || oIdx}
                                    className={cn(
                                      "rounded-lg border px-4 py-3 flex items-start gap-3 text-xs transition-colors",
                                      option.is_correct
                                        ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                                        : "border-outline-variant bg-surface text-on-surface-variant"
                                    )}
                                  >
                                    <div
                                      className={cn(
                                        "flex size-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-bold",
                                        option.is_correct
                                          ? "border-emerald-500 bg-emerald-500 text-white"
                                          : "border-outline-variant bg-surface-container text-outline"
                                      )}
                                    >
                                      {option.option_key || String.fromCharCode(65 + oIdx)}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                      <p className={option.is_correct ? "font-bold text-emerald-900" : ""}>
                                        {option.option_text}
                                      </p>
                                      {option.image_url && (
                                        <img
                                          src={option.image_url}
                                          alt={`Ảnh đáp án ${option.option_key}`}
                                          className="mt-2 max-h-32 rounded object-cover"
                                        />
                                      )}
                                    </div>
                                    {option.is_correct && (
                                      <span className="inline-flex items-center rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-800 border border-emerald-200 ml-auto whitespace-nowrap">
                                        Đáp án đúng
                                      </span>
                                    )}
                                  </div>
                                ))}
                            </div>
                          )}
                        </div>
                      ))
                  ) : (
                    <div className="p-6 border border-outline-variant rounded-xl text-center text-sm text-outline bg-surface-container-low">
                      Đề thi này chưa có câu hỏi nào.
                    </div>
                  )}
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
