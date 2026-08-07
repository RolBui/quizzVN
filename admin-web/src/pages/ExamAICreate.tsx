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
  WandSparkles,
  CircleHelp,
  Check,
  ChevronDown,
} from "lucide-react";
import { adminApi } from "../lib/api";

type QuestionType = "multiple_choice" | "true_false" | "short_answer" | "essay";
type Difficulty = "easy" | "medium" | "hard";

const AI_EXAM_CONTEXT_TEMPLATES = [
  "Luyện thi THPTQG 2026 - Toán - Lớp 12",
  "Phản ứng oxi hóa khử - Hóa học - Lớp 12",
  "Giải phương trình bậc 2 - Toán - THPT",
  "OOP, Design Pattern - Lập trình - Đại học",
] as const;

function parseExamContext(value: string) {
  const parts = value
    .split(/\s+-\s+/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length < 3) {
    return null;
  }

  return {
    grade: parts[parts.length - 1],
    subject: parts[parts.length - 2],
    topic: parts.slice(0, -2).join(" - "),
  };
}

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
  const [examContext, setExamContext] = useState("");
  const [questionCount, setQuestionCount] = useState(10);
  const [durationMinutes, setDurationMinutes] = useState(45);
  const [selectedTypes, setSelectedTypes] = useState<QuestionType[]>(["multiple_choice"]);
  const [questionTypeDistribution, setQuestionTypeDistribution] = useState<Record<string, number>>({
    multiple_choice: 10,
  });
  
  // Difficulty distribution
  const [difficultyDist, setDifficultyDist] = useState<Record<Difficulty, number>>({
    easy: 3,
    medium: 5,
    hard: 2,
  });

  // UI popover state
  const [showGuideHelp, setShowGuideHelp] = useState(false);
  const [showTemplatesMenu, setShowTemplatesMenu] = useState(false);

  // UI state
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentJob, setCurrentJob] = useState<any>(null);
  const [draftQuestions, setDraftQuestions] = useState<QuestionDraft[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [saveTitle, setSaveTitle] = useState("");
  const [saveDescription, setSaveDescription] = useState("");
  
  const pollIntervalRef = useRef<number | null>(null);
  const [wallet, setWallet] = useState<{ balance: number; qc_token: number } | null>(null);

  const fetchWallet = async () => {
    try {
      const data = await adminApi.getQCWallet();
      setWallet(data);
    } catch (err) {
      console.error("Failed to fetch wallet", err);
    }
  };

  useEffect(() => {
    void fetchWallet();
  }, []);

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
      const parsed = parseExamContext(examContext);
      const subject = parsed?.subject || "AI";
      const topic = parsed?.topic || "Chủ đề";
      const grade = parsed?.grade || "Hệ thống";
      setSaveTitle(`${subject} - ${topic}`);
      setSaveDescription(`Đề ${subject} cho ${grade}, chủ đề ${topic}. Tạo tự động bằng AI.`);
    }
  }, [currentJob, examContext]);

  function buildEvenQuestionTypeDistribution(
    count: number,
    types: string[],
  ): Record<string, number> {
    if (types.length === 0) {
      return {};
    }
    const countPerType = Math.floor(count / types.length);
    const distribution: Record<string, number> = {};
    types.forEach((type, idx) => {
      distribution[type] = idx === types.length - 1
        ? count - countPerType * idx
        : countPerType;
    });
    return distribution;
  }

  const toggleQuestionType = (type: QuestionType) => {
    setSelectedTypes((prev) => {
      const nextTypes = prev.includes(type)
        ? prev.filter((t) => t !== type)
        : [...prev, type];
      
      setQuestionTypeDistribution(
        buildEvenQuestionTypeDistribution(questionCount, nextTypes)
      );
      return nextTypes;
    });
  };

  const updateQuestionCount = (nextValue: number) => {
    const nextCount = Math.min(Math.max(nextValue, 1), 50);
    setQuestionCount(nextCount);

    // Build balanced difficulty distribution: 30% easy, 50% medium, remaining hard
    const easy = Math.floor(nextCount * 0.3);
    const medium = Math.floor(nextCount * 0.5);
    setDifficultyDist({
      easy,
      medium,
      hard: nextCount - easy - medium,
    });

    setQuestionTypeDistribution(
      buildEvenQuestionTypeDistribution(nextCount, selectedTypes)
    );
  };

  const updateQuestionTypeCount = (type: string, nextValue: number) => {
    const safeVal = Math.min(Math.max(nextValue, 1), 50);
    setQuestionTypeDistribution((prev) => ({
      ...prev,
      [type]: safeVal,
    }));
  };

  const updateDifficulty = (level: Difficulty, nextValue: number) => {
    const safeVal = Math.min(Math.max(nextValue, 0), 50);
    setDifficultyDist((prev) => ({
      ...prev,
      [level]: safeVal,
    }));
  };

  // Start AI Generation Job
  const handleGenerate = async () => {
    const examContextParsed = parseExamContext(examContext);
    if (!examContextParsed) {
      toast.error("Vui lòng nhập bối cảnh đề thi theo format: [Kỹ năng/Chủ đề] - [Môn học] - [Trình độ].");
      return;
    }

    if (selectedTypes.length === 0) {
      toast.error("Vui lòng chọn ít nhất một loại câu hỏi.");
      return;
    }

    const typeTotal = selectedTypes.reduce((sum, t) => sum + (questionTypeDistribution[t] || 0), 0);
    if (typeTotal !== questionCount) {
      toast.error(`Tổng số câu theo loại (${typeTotal}) phải bằng tổng số câu hỏi (${questionCount}).`);
      return;
    }

    const diffTotal = difficultyDist.easy + difficultyDist.medium + difficultyDist.hard;
    if (diffTotal !== questionCount) {
      toast.error(`Tổng phân bổ độ khó (${diffTotal}) phải bằng tổng số câu hỏi (${questionCount}).`);
      return;
    }

    setIsGenerating(true);
    setCurrentJob(null);
    setDraftQuestions([]);

    const payload = {
      topic: examContextParsed.topic,
      subject: examContextParsed.subject,
      grade: examContextParsed.grade,
      question_count: questionCount,
      duration_minutes: durationMinutes,
      question_types: selectedTypes,
      question_type_distribution: questionTypeDistribution,
      difficulty_distribution: difficultyDist,
      additional_instructions: "",
      language: "Vietnamese",
    };

    try {
      const response = await adminApi.generateAiExam(payload);
      setCurrentJob(response);
      startPolling(response.id);
    } catch (err: any) {
      const errMsg = err.response?.data?.detail?.message || err.message || "Tạo yêu cầu AI thất bại.";
      toast.error(errMsg);
      setIsGenerating(false);
      void fetchWallet();
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
          void fetchWallet();
        } else if (job.status === "failed") {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
          }
          setIsGenerating(false);
          toast.error(job.error_message || "Quá trình tạo đề bằng AI gặp lỗi.");
          void fetchWallet();
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

  const typeTotal = selectedTypes.reduce((sum, t) => sum + (questionTypeDistribution[t] || 0), 0);
  const hasBalancedQuestionTypes = typeTotal === questionCount;
  const missingQuestionTypeCount = questionCount - typeTotal;
  const difficultyTotal = difficultyDist.easy + difficultyDist.medium + difficultyDist.hard;

  return (
    <div className="min-h-full bg-background p-4 md:p-5">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
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
              Nhập bối cảnh đề thi, cấu hình số lượng câu hỏi và theo dõi kết quả AI trước khi lưu thành đề thi.
            </p>
          </div>
        </div>

        {wallet && (
          <div className="flex items-center gap-2 rounded-lg border border-outline-variant bg-surface-container-lowest px-4 py-2 text-xs font-semibold text-on-surface shadow-sm">
            <span>Ví sử dụng:</span>
            <span className="rounded bg-primary/10 px-2 py-0.5 text-primary font-bold">
              {wallet.qc_token} QC Token
            </span>
            <span className="text-outline">|</span>
            <span className="font-bold">{wallet.balance} QC</span>
          </div>
        )}
      </div>

      {draftQuestions.length === 0 && !isGenerating ? (
        <div className="grid gap-5 lg:grid-cols-2 lg:items-stretch">
          {/* Card 1: Thông tin chung */}
          <div className="flex h-full flex-col rounded-xl border border-outline-variant bg-surface-container-lowest shadow-sm">
            <div className="border-b border-outline-variant px-5 py-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-sm font-bold text-on-surface">Thông tin chung</h2>
              
              <div className="flex items-center gap-2 relative">
                {/* Guide Popover */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => {
                      setShowGuideHelp(!showGuideHelp);
                      setShowTemplatesMenu(false);
                    }}
                    className="flex items-center gap-1.5 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs font-semibold text-on-surface hover:bg-surface-container-low"
                  >
                    <CircleHelp className="w-3.5 h-3.5" />
                    Xem hướng dẫn
                  </button>
                  {showGuideHelp && (
                    <div className="absolute right-0 mt-2 w-80 bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-lg z-50 space-y-3">
                      <div>
                        <p className="text-sm font-semibold text-on-surface">Format nhập liệu</p>
                        <p className="mt-2 rounded-md bg-surface-container-low px-3 py-2 font-mono text-xs text-on-surface-variant">
                          [Kỹ năng/Chủ đề] - [Môn học] - [Trình độ]
                        </p>
                      </div>
                      <div className="space-y-1.5 text-xs leading-5 text-outline">
                        {AI_EXAM_CONTEXT_TEMPLATES.map((tpl) => (
                          <p key={tpl} className="hover:text-primary cursor-pointer" onClick={() => { setExamContext(tpl); setShowGuideHelp(false); }}>
                            {tpl}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Templates Dropdown */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => {
                      setShowTemplatesMenu(!showTemplatesMenu);
                      setShowGuideHelp(false);
                    }}
                    className="flex items-center gap-1 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs font-semibold text-on-surface hover:bg-surface-container-low"
                  >
                    Chọn template mẫu
                    <ChevronDown className="w-3.5 h-3.5" />
                  </button>
                  {showTemplatesMenu && (
                    <div className="absolute right-0 mt-2 w-80 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg z-50 py-1">
                      {AI_EXAM_CONTEXT_TEMPLATES.map((template) => (
                        <button
                          key={template}
                          type="button"
                          onClick={() => {
                            setExamContext(template);
                            setShowTemplatesMenu(false);
                          }}
                          className="w-full text-left px-4 py-2 text-xs font-semibold text-on-surface hover:bg-surface-container-low"
                        >
                          {template}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="flex flex-1 flex-col space-y-4 p-5">
              <label className="block space-y-2">
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-on-surface">
                  Bối cảnh đề thi
                </span>
                <textarea
                  value={examContext}
                  maxLength={2000}
                  onChange={(e) => setExamContext(e.target.value)}
                  placeholder="VD: Luyện thi THPTQG 2026 - Toán - Lớp 12"
                  className="w-full min-h-24 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-sm text-on-surface focus:outline-none focus:border-primary placeholder:text-outline"
                />
                <div className="flex items-center justify-between gap-3 text-xs text-outline">
                  <span>Nhập theo format: [Chủ đề] - [Môn học] - [Trình độ]</span>
                  <span>{examContext.length}/2000</span>
                </div>
              </label>

              <div className="rounded-lg border border-info-container bg-info-container/40 p-4">
                <div className="flex items-center gap-2 text-xs font-bold text-on-info-container">
                  <Sparkles className="w-4 h-4 text-primary" />
                  Tại sao cần nhập bối cảnh đề thi?
                </div>
                <ul className="mt-2 list-disc space-y-1.5 pl-5 text-[11px] leading-5 text-on-info-container">
                  <li>Xác định mục tiêu: luyện thi, kiểm tra hoặc ôn tập.</li>
                  <li>Giới hạn đúng môn học, chủ đề và trình độ.</li>
                  <li>Giúp AI phân bổ câu hỏi sát yêu cầu và dễ duyệt hơn.</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Card 2: Cấu hình tạo đề */}
          <div className="flex h-full flex-col rounded-xl border border-outline-variant bg-surface-container-lowest shadow-sm p-5 space-y-4">
            <h2 className="text-sm font-bold text-on-surface">Cấu hình tạo đề</h2>

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-2">
                <span className="text-xs font-semibold text-on-surface">Thời lượng (phút)</span>
                <input
                  type="number"
                  min={1}
                  max={300}
                  value={durationMinutes}
                  onChange={(e) => setDurationMinutes(Number(e.target.value))}
                  className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-sm text-on-surface focus:outline-none focus:border-primary"
                />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-semibold text-on-surface">Tổng số câu</span>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={questionCount}
                  onChange={(e) => updateQuestionCount(Number(e.target.value))}
                  className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-sm text-on-surface focus:outline-none focus:border-primary"
                />
              </label>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-semibold text-on-surface">
                Loại câu hỏi <span className="font-normal text-outline">(chọn một hoặc nhiều)</span>
              </p>
              <div className="grid gap-2 sm:grid-cols-2 2xl:grid-cols-4">
                {[
                  { value: "multiple_choice", label: "Trắc nghiệm" },
                  { value: "true_false", label: "Đúng / sai" },
                  { value: "short_answer", label: "Trả lời ngắn" },
                  { value: "essay", label: "Tự luận" },
                ].map((option) => {
                  const checked = selectedTypes.includes(option.value as QuestionType);
                  return (
                    <label
                      key={option.value}
                      className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs font-semibold transition-colors ${
                        checked
                          ? "border-primary/35 bg-primary/5 text-primary"
                          : "border-outline-variant bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-low"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleQuestionType(option.value as QuestionType)}
                        className="rounded border-outline-variant text-primary focus:ring-primary size-3.5"
                      />
                      {option.label}
                    </label>
                  );
                })}
              </div>
            </div>

            {selectedTypes.length > 0 && (
              <div className="space-y-2.5 rounded-lg border border-outline-variant bg-surface-container-low p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs font-semibold text-on-surface">Số câu theo loại</p>
                  <span
                    className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                      hasBalancedQuestionTypes
                        ? "bg-surface-container-lowest text-outline"
                        : "bg-amber-50 text-amber-700 border border-amber-200"
                    }`}
                  >
                    {typeTotal}/{questionCount} câu
                  </span>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-4">
                  {selectedTypes.map((type) => (
                    <label key={type} className="space-y-1.5">
                      <span className="text-[11px] font-medium text-outline capitalize">
                        {type === "multiple_choice"
                          ? "Trắc nghiệm"
                          : type === "true_false"
                          ? "Đúng / sai"
                          : type === "short_answer"
                          ? "Trả lời ngắn"
                          : "Tự luận"}
                      </span>
                      <input
                        type="number"
                        min={1}
                        max={50}
                        value={questionTypeDistribution[type] ?? 0}
                        onChange={(e) => updateQuestionTypeCount(type, Number(e.target.value))}
                        className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs text-on-surface focus:outline-none focus:border-primary"
                      />
                    </label>
                  ))}
                </div>

                {!hasBalancedQuestionTypes && (
                  <p className="text-[11px] font-medium text-amber-700">
                    {missingQuestionTypeCount > 0
                      ? `Còn thiếu ${missingQuestionTypeCount} câu. Hãy cộng vào một loại phù hợp.`
                      : `Đang dư ${Math.abs(missingQuestionTypeCount)} câu. Hãy giảm ở một loại.`}
                  </p>
                )}
              </div>
            )}

            <div className="space-y-2.5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-semibold text-on-surface">Phân bổ độ khó</p>
                <span className="rounded-full bg-surface-container-low px-2.5 py-1 text-[11px] font-semibold text-outline">
                  {difficultyTotal}/{questionCount} câu
                </span>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  { key: "easy", label: "Dễ" },
                  { key: "medium", label: "Trung bình" },
                  { key: "hard", label: "Khó" },
                ].map((opt) => (
                  <label key={opt.key} className="space-y-1.5">
                    <span className="text-[11px] font-medium text-outline">{opt.label}</span>
                    <input
                      type="number"
                      min={0}
                      max={50}
                      value={difficultyDist[opt.key as Difficulty] ?? 0}
                      onChange={(e) => updateDifficulty(opt.key as Difficulty, Number(e.target.value))}
                      className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs text-on-surface focus:outline-none focus:border-primary"
                    />
                  </label>
                ))}
              </div>
            </div>

            <button
              type="button"
              onClick={handleGenerate}
              disabled={isGenerating}
              className="mt-auto flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-[#4867F8] to-[#C62CF2] text-sm font-bold text-white shadow-sm hover:opacity-95 disabled:opacity-50"
            >
              <WandSparkles className="w-4 h-4" />
              Tạo đề bằng AI
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column: Saving status panel */}
          <div className="lg:col-span-1 space-y-5">
            {currentJob && currentJob.status === "completed" && (
              <div className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5 shadow-sm space-y-4">
                <h2 className="text-base font-bold text-on-surface flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-success" /> Lưu đề thi hệ thống
                </h2>
                <div>
                  <label className="text-sm font-semibold text-on-surface">Tiêu đề đề thi</label>
                  <input
                    type="text"
                    value={saveTitle}
                    onChange={(e) => setSaveTitle(e.target.value)}
                    className="w-full mt-1 rounded-md border border-outline-variant bg-surface-container-lowest px-3 py-2 text-sm text-on-surface focus:outline-none focus:border-primary"
                    disabled={isSaving}
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-on-surface">Mô tả</label>
                  <textarea
                    rows={3}
                    value={saveDescription}
                    onChange={(e) => setSaveDescription(e.target.value)}
                    className="w-full mt-1 rounded-md border border-outline-variant bg-surface-container-lowest px-3 py-2 text-sm text-on-surface focus:outline-none focus:border-primary"
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
                        {(q.question_type === "multiple_choice" || q.question_type === "true_false") && q.options && Array.isArray(q.options) && q.options.length > 0 && (
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                            {q.options.map((opt, optIdx) => (
                              <div key={opt.id} className="flex items-center gap-2 bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-xs text-on-surface">
                                <span className="font-bold text-primary">{opt.option_key}.</span>
                                <input
                                  type="text"
                                  value={opt.option_text}
                                  onChange={(e) => {
                                    const updatedOpts = q.options ? [...q.options] : [];
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
                            q.accepted_answers ? q.accepted_answers.join(", ") : ""
                          ) : (
                            <input
                              type="text"
                              value={q.accepted_answers ? q.accepted_answers.join(", ") : ""}
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
      )}
    </div>
  );
}
