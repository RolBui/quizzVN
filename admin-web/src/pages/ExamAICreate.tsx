import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import {
  ArrowLeft,
  Loader2,
  Sparkles,
  CheckCircle2,
  Trash2,
  Plus,
  Save,
  AlertCircle,
  HelpCircle,
} from "lucide-react";
import { adminApi } from "../lib/api";

type QuestionType = "multiple_choice" | "true_false" | "short_answer" | "essay";
type Difficulty = "easy" | "medium" | "hard";

interface QuestionDraft {
  id: number;
  question_type: QuestionType;
  prompt: string;
  explanation: string;
  points: number;
  order: number;
  is_approved: boolean;
  options: Array<{
    id: number;
    option_key: string;
    option_text: string;
  }>;
  accepted_answers: string[];
}

export function ExamAICreate() {
  const navigate = useNavigate();
  const [topic, setTopic] = useState("");
  const [subject, setSubject] = useState("Toán");
  const [grade, setGrade] = useState("Lớp 12");
  const [questionCount, setQuestionCount] = useState(10);
  const [durationMinutes, setDurationMinutes] = useState(45);
  const [selectedTypes, setSelectedTypes] = useState<QuestionType[]>(["multiple_choice"]);
  
  // Difficulty distribution
  const [difficultyDist, setDifficultyDist] = useState<Record<Difficulty, number>>({
    easy: 3,
    medium: 5,
    hard: 2,
  });

  // UI state
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentJob, setCurrentJob] = useState<any>(null);
  const [draftQuestions, setDraftQuestions] = useState<QuestionDraft[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [saveTitle, setSaveTitle] = useState("");
  const [saveDescription, setSaveDescription] = useState("");
  
  const pollIntervalRef = useRef<number | null>(null);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Update save title when job completes
  useEffect(() => {
    if (currentJob && currentJob.status === "completed" && !saveTitle) {
      setSaveTitle(`${subject} - ${topic || "Chủ đề AI"}`);
      setSaveDescription(`Đề ${subject} cho ${grade}, chủ đề ${topic}. Tạo tự động bằng AI.`);
    }
  }, [currentJob, subject, topic, grade]);

  const handleDifficultyChange = (level: Difficulty, val: number) => {
    const nextVal = Math.max(0, val);
    setDifficultyDist((prev) => ({
      ...prev,
      [level]: nextVal,
    }));
  };

  const toggleQuestionType = (type: QuestionType) => {
    setSelectedTypes((prev) => {
      if (prev.includes(type)) {
        if (prev.length === 1) return prev; // Keep at least one
        return prev.filter((t) => t !== type);
      }
      return [...prev, type];
    });
  };

  // Start AI Generation Job
  const handleGenerate = async () => {
    if (!topic.trim()) {
      toast.error("Vui lòng nhập chủ đề thi.");
      return;
    }

    const typeDistribution: Record<string, number> = {};
    const countPerType = Math.floor(questionCount / selectedTypes.length);
    selectedTypes.forEach((type, idx) => {
      typeDistribution[type] = idx === selectedTypes.length - 1
        ? questionCount - countPerType * idx
        : countPerType;
    });

    const diffTotal = difficultyDist.easy + difficultyDist.medium + difficultyDist.hard;
    if (diffTotal !== questionCount) {
      toast.error(`Tổng tỷ lệ độ khó (${diffTotal}) phải bằng tổng số câu hỏi (${questionCount}).`);
      return;
    }

    setIsGenerating(true);
    setCurrentJob(null);
    setDraftQuestions([]);

    const payload = {
      topic: topic.trim(),
      subject: subject,
      grade: grade,
      question_count: questionCount,
      duration_minutes: durationMinutes,
      question_types: selectedTypes,
      question_type_distribution: typeDistribution,
      difficulty_distribution: difficultyDist,
      additional_instructions: "",
      language: "Vietnamese",
    };

    try {
      const response = await adminApi.generateAiExam(payload);
      setCurrentJob(response);
      startPolling(response.id);
    } catch (err: any) {
      toast.error(err.message || "Tạo yêu cầu AI thất bại.");
      setIsGenerating(false);
    }
  };

  // Poll Job Status
  const startPolling = (jobId: number) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    pollIntervalRef.current = window.setInterval(async () => {
      try {
        const job = await adminApi.getAiExamJob(jobId);
        setCurrentJob(job);

        if (job.status === "completed") {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
          }
          setIsGenerating(false);
          setDraftQuestions(job.question_drafts || []);
          toast.success("Đã tạo đề thi AI thành công!");
        } else if (job.status === "failed") {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
          }
          setIsGenerating(false);
          toast.error(job.error_message || "Quá trình tạo đề bằng AI gặp lỗi.");
        }
      } catch (err: any) {
        console.error("Polling error", err);
      }
    }, 2000);
  };

  // Toggle approve status of a draft question
  const handleToggleApprove = async (index: number) => {
    const target = draftQuestions[index];
    const nextApproved = !target.is_approved;

    // Optimistically update
    const updated = [...draftQuestions];
    updated[index] = { ...target, is_approved: nextApproved };
    setDraftQuestions(updated);

    try {
      await adminApi.updateQuestionDraft(target.id, { is_approved: nextApproved });
    } catch (err: any) {
      toast.error("Không cập nhật được trạng thái câu hỏi.");
      // Rollback
      const rolledBack = [...draftQuestions];
      rolledBack[index] = target;
      setDraftQuestions(rolledBack);
    }
  };

  // Edit prompt or values of a draft question
  const handleEditQuestion = async (index: number, patch: Partial<QuestionDraft>) => {
    const target = draftQuestions[index];
    const updated = [...draftQuestions];
    updated[index] = { ...target, ...patch } as QuestionDraft;
    setDraftQuestions(updated);

    try {
      await adminApi.updateQuestionDraft(target.id, patch);
    } catch (err: any) {
      toast.error("Không lưu được chỉnh sửa câu hỏi.");
    }
  };

  // Save AI Exam to System Quizzes
  const handleSaveToSystem = async () => {
    if (!saveTitle.trim()) {
      toast.error("Vui lòng nhập tiêu đề bài thi.");
      return;
    }

    const approvedCount = draftQuestions.filter((q) => q.is_approved).length;
    if (approvedCount === 0) {
      toast.error("Vui lòng duyệt ít nhất một câu hỏi trước khi lưu.");
      return;
    }

    setIsSaving(true);
    try {
      await adminApi.saveAiExamToQuiz(currentJob.id, {
        title: saveTitle.trim(),
        description: saveDescription.trim(),
        scope: "system",
        duration_minutes: durationMinutes,
        is_published: true,
        is_active: true,
      });
      toast.success("Đã tạo đề thi hệ thống thành công!");
      navigate("/exams");
    } catch (err: any) {
      toast.error(err.message || "Không lưu được đề thi vào hệ thống.");
    } finally {
      setIsSaving(false);
    }
  };

  const inputClass =
    "w-full rounded-md border border-outline-variant bg-surface-container-lowest px-3 py-2 text-sm text-on-surface outline-none transition-colors placeholder:text-outline focus:border-primary";
  const labelClass = "text-sm font-semibold text-on-surface";

  return (
    <div className="min-h-full bg-background p-4 md:p-5">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/exams")}
            className="rounded-full p-2 text-on-surface-variant hover:bg-surface-variant transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-on-surface">Tạo đề thi bằng AI</h1>
            <p className="text-sm text-outline">
              Nhập chủ đề và AI sẽ tự động soạn câu hỏi cho đề thi hệ thống
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: AI Generator settings */}
        <div className="lg:col-span-1 space-y-5">
          <div className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5 shadow-sm">
            <h2 className="text-base font-bold text-on-surface mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" /> Cấu hình AI
            </h2>

            <div className="space-y-4">
              <div>
                <label className={labelClass}>Chủ đề thi *</label>
                <input
                  type="text"
                  placeholder="Ví dụ: Đạo hàm lớp 12, Lịch sử nhà Trần..."
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className={`${inputClass} mt-1`}
                  disabled={isGenerating}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>Môn học</label>
                  <select
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className={`${inputClass} mt-1`}
                    disabled={isGenerating}
                  >
                    <option value="Toán">Toán</option>
                    <option value="Vật lý">Vật lý</option>
                    <option value="Hóa học">Hóa học</option>
                    <option value="Sinh học">Sinh học</option>
                    <option value="Lịch sử">Lịch sử</option>
                    <option value="Địa lý">Địa lý</option>
                    <option value="Tiếng Anh">Tiếng Anh</option>
                    <option value="Khác">Khác</option>
                  </select>
                </div>

                <div>
                  <label className={labelClass}>Khối lớp</label>
                  <select
                    value={grade}
                    onChange={(e) => setGrade(e.target.value)}
                    className={`${inputClass} mt-1`}
                    disabled={isGenerating}
                  >
                    <option value="Lớp 10">Lớp 10</option>
                    <option value="Lớp 11">Lớp 11</option>
                    <option value="Lớp 12">Lớp 12</option>
                    <option value="Đại học">Đại học</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>Số lượng câu hỏi</label>
                  <input
                    type="number"
                    min={5}
                    max={50}
                    value={questionCount}
                    onChange={(e) => setQuestionCount(Number(e.target.value))}
                    className={`${inputClass} mt-1`}
                    disabled={isGenerating}
                  />
                </div>

                <div>
                  <label className={labelClass}>Thời gian (phút)</label>
                  <input
                    type="number"
                    min={5}
                    max={180}
                    value={durationMinutes}
                    onChange={(e) => setDurationMinutes(Number(e.target.value))}
                    className={`${inputClass} mt-1`}
                    disabled={isGenerating}
                  />
                </div>
              </div>

              <div>
                <label className={labelClass}>Loại câu hỏi</label>
                <div className="mt-2 grid grid-cols-2 gap-2">
                  {[
                    { key: "multiple_choice", label: "Trắc nghiệm" },
                    { key: "true_false", label: "Đúng / Sai" },
                    { key: "short_answer", label: "Trả lời ngắn" },
                    { key: "essay", label: "Tự luận" },
                  ].map((t) => (
                    <label
                      key={t.key}
                      className="flex items-center gap-2 text-sm text-on-surface cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedTypes.includes(t.key as QuestionType)}
                        onChange={() => toggleQuestionType(t.key as QuestionType)}
                        className="rounded border-outline-variant text-primary focus:ring-primary"
                        disabled={isGenerating}
                      />
                      {t.label}
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className={labelClass}>Tỷ lệ độ khó (Tổng: {questionCount} câu)</label>
                <div className="mt-2 grid grid-cols-3 gap-2">
                  <div>
                    <span className="text-xs text-outline">Dễ</span>
                    <input
                      type="number"
                      value={difficultyDist.easy}
                      onChange={(e) => handleDifficultyChange("easy", Number(e.target.value))}
                      className={inputClass}
                      disabled={isGenerating}
                    />
                  </div>
                  <div>
                    <span className="text-xs text-outline">Vừa</span>
                    <input
                      type="number"
                      value={difficultyDist.medium}
                      onChange={(e) => handleDifficultyChange("medium", Number(e.target.value))}
                      className={inputClass}
                      disabled={isGenerating}
                    />
                  </div>
                  <div>
                    <span className="text-xs text-outline">Khó</span>
                    <input
                      type="number"
                      value={difficultyDist.hard}
                      onChange={(e) => handleDifficultyChange("hard", Number(e.target.value))}
                      className={inputClass}
                      disabled={isGenerating}
                    />
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={handleGenerate}
                disabled={isGenerating}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary py-2.5 text-sm font-semibold text-on-primary hover:bg-primary/95 transition-colors disabled:opacity-50 mt-4"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Đang tạo đề...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    Bắt đầu tạo bằng AI
                  </>
                )}
              </button>
            </div>
          </div>

          {currentJob && currentJob.status === "completed" && (
            <div className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5 shadow-sm space-y-4">
              <h2 className="text-base font-bold text-on-surface flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-success" /> Lưu đề thi hệ thống
              </h2>
              <div>
                <label className={labelClass}>Tiêu đề đề thi</label>
                <input
                  type="text"
                  value={saveTitle}
                  onChange={(e) => setSaveTitle(e.target.value)}
                  className={`${inputClass} mt-1`}
                  disabled={isSaving}
                />
              </div>
              <div>
                <label className={labelClass}>Mô tả</label>
                <textarea
                  rows={3}
                  value={saveDescription}
                  onChange={(e) => setSaveDescription(e.target.value)}
                  className={`${inputClass} mt-1`}
                  disabled={isSaving}
                />
              </div>

              <button
                type="button"
                onClick={handleSaveToSystem}
                disabled={isSaving}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-success py-2.5 text-sm font-semibold text-white hover:bg-success/95 transition-colors disabled:opacity-50"
              >
                {isSaving ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Save className="w-5 h-5" />
                )}
                Lưu vào hệ thống
              </button>
            </div>
          )}
        </div>

        {/* Right column: Generated Question list/status */}
        <div className="lg:col-span-2 space-y-5">
          {isGenerating && (
            <div className="rounded-xl border border-outline-variant bg-surface-container-lowest p-10 shadow-sm flex flex-col items-center justify-center text-center">
              <Loader2 className="w-10 h-10 text-primary animate-spin mb-4" />
              <h3 className="text-lg font-bold text-on-surface">AI đang thực hiện soạn thảo đề thi</h3>
              <p className="text-sm text-outline mt-1 max-w-md">
                {currentJob?.progress_message || "Đang phân tích chủ đề và phân bố các câu hỏi tương ứng..."}
              </p>
              {currentJob && currentJob.progress_total > 0 && (
                <div className="w-full max-w-xs bg-surface-variant rounded-full h-2.5 mt-4">
                  <div
                    className="bg-primary h-2.5 rounded-full transition-all duration-300"
                    style={{
                      width: `${(currentJob.progress_current / currentJob.progress_total) * 100}%`,
                    }}
                  />
                  <span className="text-xs text-outline mt-2 block">
                    Đã hoàn thành {currentJob.progress_current}/{currentJob.progress_total} câu hỏi
                  </span>
                </div>
              )}
            </div>
          )}

          {!isGenerating && draftQuestions.length === 0 && (
            <div className="rounded-xl border border-outline-variant bg-surface-container-lowest p-10 shadow-sm flex flex-col items-center justify-center text-center text-outline">
              <HelpCircle className="w-12 h-12 mb-3 text-outline" />
              <p className="text-base font-semibold">Chưa có câu hỏi được tạo</p>
              <p className="text-sm">Hãy điền chủ đề và nhấn nút Tạo đề bằng AI ở cột bên trái.</p>
            </div>
          )}

          {!isGenerating && draftQuestions.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between px-1">
                <h3 className="text-base font-bold text-on-surface">
                  Danh sách câu hỏi đề xuất ({draftQuestions.filter((q) => q.is_approved).length}/{draftQuestions.length} đã duyệt)
                </h3>
              </div>

              {draftQuestions.map((q, idx) => (
                <div
                  key={q.id}
                  className={`rounded-xl border p-5 shadow-sm transition-colors ${
                    q.is_approved
                      ? "border-success/30 bg-success/5"
                      : "border-outline-variant bg-surface-container-lowest"
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 space-y-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-primary bg-primary/10 px-2 py-0.5 rounded">
                          Câu {idx + 1}
                        </span>
                        <span className="text-xs font-medium text-outline bg-surface-variant px-2 py-0.5 rounded uppercase">
                          {q.question_type}
                        </span>
                      </div>

                      <textarea
                        value={q.prompt}
                        onChange={(e) => handleEditQuestion(idx, { prompt: e.target.value })}
                        className="w-full bg-transparent border-none text-sm font-semibold text-on-surface resize-y focus:outline-none focus:ring-1 focus:ring-primary rounded p-1"
                        rows={2}
                      />

                      {/* Display options for multiple choice or true/false */}
                      {(q.question_type === "multiple_choice" || q.question_type === "true_false") && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                          {q.options.map((opt, optIdx) => (
                            <div key={opt.id} className="flex items-center gap-2 bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-xs text-on-surface">
                              <span className="font-bold text-primary">{opt.option_key}.</span>
                              <input
                                type="text"
                                value={opt.option_text}
                                onChange={(e) => {
                                  const updatedOpts = [...q.options];
                                  updatedOpts[optIdx] = { ...opt, option_text: e.target.value };
                                  handleEditQuestion(idx, { options: updatedOpts });
                                }}
                                className="bg-transparent border-none outline-none flex-1 text-xs"
                              />
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Correct Answers */}
                      <div className="text-xs text-outline mt-2">
                        <span className="font-bold text-success">Đáp án đúng: </span>
                        {q.question_type === "multiple_choice" ? (
                          q.accepted_answers.join(", ")
                        ) : (
                          <input
                            type="text"
                            value={q.accepted_answers.join(", ")}
                            onChange={(e) =>
                              handleEditQuestion(idx, {
                                accepted_answers: e.target.value.split(",").map((s) => s.trim()),
                              })
                            }
                            className="bg-transparent border border-outline-variant rounded px-2 py-1 focus:outline-none focus:border-primary text-xs"
                          />
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-2">
                      <button
                        onClick={() => handleToggleApprove(idx)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-colors ${
                          q.is_approved
                            ? "bg-success text-white hover:bg-success/90"
                            : "bg-surface-variant text-outline hover:bg-outline-variant/30"
                        }`}
                      >
                        {q.is_approved ? "Đã duyệt" : "Duyệt câu"}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
