import { useEffect, useState, useRef, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import {
  ArrowLeft,
  Loader2,
  Sparkles,
  CheckCircle2,
  Plus,
  Save,
  WandSparkles,
  CircleHelp,
  ChevronDown,
  History,
  RefreshCw,
  Eye,
  FolderOpen,
  ChevronLeft,
  ChevronRight,
  Coins,
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

const AI_EXAM_RECENT_DRAFTS_KEY = "admin_ai_exam_recent_drafts";
const AI_EXAM_RECENT_DRAFT_LIMIT = 20;

export interface AIExamHistoryItem {
  approvedCount: number;
  createdAt: string;
  grade?: string;
  id: number;
  qcCost?: number;
  questionCount: number;
  scope: "system" | "class";
  status: string;
  subject?: string;
  title: string;
  topic?: string;
  updatedAt: string;
}

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
  content: string;
  explanation: string;
  points: number;
  order: number;
  is_approved: boolean;
  options: string[];
  correct_answer: any;
}

// Local history helpers
function readAIExamHistoryItems(): AIExamHistoryItem[] {
  try {
    const rawValue = window.localStorage.getItem(AI_EXAM_RECENT_DRAFTS_KEY);
    const parsedValue = rawValue ? JSON.parse(rawValue) : [];
    return Array.isArray(parsedValue)
      ? parsedValue.map((item: any) => ({
          ...item,
          approvedCount: Number(item.approvedCount ?? 0),
          questionCount: Number(item.questionCount ?? 0),
          qcCost: Number(item.qcCost ?? 0),
        }))
      : [];
  } catch {
    return [];
  }
}

function writeAIExamHistoryItems(drafts: AIExamHistoryItem[]) {
  window.localStorage.setItem(
    AI_EXAM_RECENT_DRAFTS_KEY,
    JSON.stringify(drafts.slice(0, AI_EXAM_RECENT_DRAFT_LIMIT)),
  );
}

function buildAIExamHistoryItem(job: any): AIExamHistoryItem {
  const now = new Date().toISOString();
  return {
    approvedCount: job.question_drafts?.filter((draft: any) => draft.is_approved).length || 0,
    createdAt: job.created_at || now,
    grade: job.grade,
    id: job.id,
    qcCost: job.qc_charged || job.qc_reserved || 0,
    questionCount: job.question_count,
    scope: "system",
    status: job.status,
    subject: job.subject,
    title: job.title?.trim() || `${job.subject} - ${job.topic}`,
    topic: job.topic,
    updatedAt: job.updated_at || now,
  };
}

function upsertAIExamHistoryItem(job: any) {
  const draft = buildAIExamHistoryItem(job);
  const drafts = readAIExamHistoryItems().filter((item) => item.id !== job.id);
  const nextDrafts = [draft, ...drafts].slice(0, AI_EXAM_RECENT_DRAFT_LIMIT);
  writeAIExamHistoryItems(nextDrafts);
}

const AI_QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  multiple_choice: "Trắc nghiệm",
  true_false: "Đúng / sai",
  short_answer: "Trả lời ngắn",
  essay: "Tự luận",
};

function describeQuestionTypePlan(types: QuestionType[]) {
  const uniqueTypes = Array.from(new Set(types));
  if (uniqueTypes.length === 1) {
    return `Tạo đề thi ${AI_QUESTION_TYPE_LABELS[uniqueTypes[0]].toLowerCase()}`;
  }
  if (uniqueTypes.length > 1) {
    return `Tạo đề thi hỗn hợp: ${uniqueTypes.map((type) => AI_QUESTION_TYPE_LABELS[type].toLowerCase()).join(", ")}`;
  }
  return "Tạo đề thi theo cấu hình đã chọn";
}

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback;
}

function formatLocalInsufficientQCMessage(requiredQC: number, balance: number) {
  return `Bạn không đủ QC Token để tạo đề. Cần ${requiredQC.toLocaleString("vi-VN")} QC, hiện có ${balance.toLocaleString("vi-VN")} QC.`;
}

function getAIProgressStage(job: any) {
  if (!job) {
    return 0;
  }
  if (job.status === "completed") {
    return 3;
  }
  const progressCurrent = Number(job.progress_current || 0);
  const progressTotal = Number(job.progress_total || 0);
  if (progressTotal > 0 && progressCurrent >= progressTotal) {
    return 3;
  }
  if (progressCurrent > 0 || job.progress_message) {
    return 2;
  }
  if (job.status === "processing" || job.status === "pending") {
    return 1;
  }
  return 0;
}

function AIExamGenerationProgress({
  currentJob,
  durationMinutes,
  questionCount,
  selectedTypes,
}: {
  currentJob: any;
  durationMinutes: number;
  questionCount: number;
  selectedTypes: QuestionType[];
}) {
  const activeStage = getAIProgressStage(currentJob);
  const progressCurrent = Number(currentJob?.progress_current || 0);
  const progressTotal = Number(currentJob?.progress_total || 0);
  const questionProgressRatio = progressTotal > 0 ? Math.min(progressCurrent / progressTotal, 1) : 0;
  const progressPercent = Math.min(
    activeStage === 3 ? 100 : 94,
    Math.round(((activeStage + (activeStage === 2 ? questionProgressRatio : 0.35)) / 4) * 100),
  );
  const generatedLabel = describeQuestionTypePlan(selectedTypes);
  const steps = [
    {
      title: "Phân tích yêu cầu",
      description: "Đọc bối cảnh, môn học, lớp, chủ đề và độ khó.",
      icon: CircleHelp,
    },
    {
      title: "Tạo cấu trúc đề thi",
      description: `Chia bố cục ${questionCount} câu trong ${durationMinutes} phút.`,
      icon: Sparkles,
    },
    {
      title: generatedLabel,
      description: currentJob?.progress_message || "Soạn nội dung câu hỏi, đáp án và giải thích.",
      icon: WandSparkles,
    },
    {
      title: "Hoàn thành",
      description: "Mở bản nháp để duyệt câu hỏi trước khi lưu vào hệ thống.",
      icon: CheckCircle2,
    },
  ];
  const currentStep = steps[activeStage] ?? steps[0];

  return (
    <section className="rounded-xl border border-outline-variant bg-surface-container-lowest shadow-sm overflow-hidden">
      <div className="border-b border-outline-variant bg-surface px-5 py-4 sm:px-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase text-primary">Tiến trình AI</p>
            <h2 className="mt-1 text-lg font-bold text-on-surface">{currentStep.title}</h2>
            <p className="mt-1 text-sm text-outline">{currentStep.description}</p>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1.5 text-xs font-bold text-primary">
            <Loader2 className="size-4 animate-spin" />
            Đang xử lý
          </div>
        </div>
      </div>

      <div className="p-5 sm:p-6">
        <div className="mb-6 h-2 overflow-hidden rounded-full bg-surface-variant">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#4F62F2] to-[#7C3AED] transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        <div className="grid gap-3 md:grid-cols-4">
          {steps.map((step, index) => {
            const Icon = step.icon;
            const completed = index < activeStage;
            const active = index === activeStage;
            return (
              <div
                key={step.title}
                className={`rounded-lg border p-4 transition-colors ${
                  completed
                    ? "border-success/30 bg-success/5"
                    : active
                      ? "border-primary/40 bg-primary/5"
                      : "border-outline-variant bg-surface-container-low"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`flex size-8 items-center justify-center rounded-full ${
                      completed
                        ? "bg-success text-white"
                        : active
                          ? "bg-primary text-white"
                          : "bg-surface-variant text-outline"
                    }`}
                  >
                    {completed ? <CheckCircle2 className="size-4" /> : <Icon className="size-4" />}
                  </span>
                  <span className={`text-xs font-bold ${active || completed ? "text-on-surface" : "text-outline"}`}>
                    Bước {index + 1}
                  </span>
                </div>
                <h3 className="mt-3 text-sm font-bold text-on-surface">{step.title}</h3>
                <p className="mt-1 min-h-10 text-xs leading-5 text-outline">{step.description}</p>
                <div className="mt-3 text-[11px] font-bold uppercase">
                  {completed && <span className="text-success">Hoàn thành</span>}
                  {active && <span className="text-primary">Đang thực hiện</span>}
                  {!completed && !active && <span className="text-outline">Chờ xử lý</span>}
                </div>
              </div>
            );
          })}
        </div>

        {progressTotal > 0 && (
          <div className="mt-5 rounded-lg border border-outline-variant bg-surface-container-low px-4 py-3 text-sm text-on-surface">
            Đã tạo {progressCurrent}/{progressTotal} câu hỏi
          </div>
        )}
      </div>
    </section>
  );
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
  const [recentDrafts, setRecentDrafts] = useState<AIExamHistoryItem[]>([]);
  
  // Generate More state
  const [generateMoreCount, setGenerateMoreCount] = useState(5);
  const [generateMoreInstructions, setGenerateMoreInstructions] = useState("");
  const [generateMoreQuestionTypes, setGenerateMoreQuestionTypes] = useState<QuestionType[]>(["multiple_choice"]);
  const [generateMoreTypeDistribution, setGenerateMoreTypeDistribution] = useState<Record<string, number>>({
    multiple_choice: 5,
  });

  const pollIntervalRef = useRef<number | null>(null);
  const [wallet, setWallet] = useState<{ balance: number; qc_per_question: number } | null>(null);
  const [estimatedCost, setEstimatedCost] = useState<number>(0);
  const [isLoadingCost, setIsLoadingCost] = useState(false);
  const [estimatedMoreCost, setEstimatedMoreCost] = useState<number>(0);
  const [isLoadingMoreCost, setIsLoadingMoreCost] = useState(false);

  const fetchWallet = async () => {
    try {
      const data = await adminApi.getQCWallet();
      setWallet(data);
    } catch (err) {
      console.error("Failed to fetch wallet", err);
    }
  };

  const syncHistory = () => {
    setRecentDrafts(readAIExamHistoryItems());
  };

  useEffect(() => {
    void fetchWallet();
    syncHistory();
  }, []);

  // Poll cost estimate when questionCount changes
  useEffect(() => {
    let active = true;
    if (draftQuestions.length === 0 && !isGenerating && questionCount > 0) {
      setIsLoadingCost(true);
      adminApi.estimateAiQCCost({ question_count: questionCount, operation: "initial" })
        .then((res) => {
          if (active) {
            setEstimatedCost(res.qc_cost);
          }
        })
        .catch((err) => {
          console.error("Cost estimation error", err);
          if (active) {
            setEstimatedCost(questionCount * (wallet?.qc_per_question ?? 1));
          }
        })
        .finally(() => {
          if (active) {
            setIsLoadingCost(false);
          }
        });
    }
    return () => {
      active = false;
    };
  }, [questionCount, wallet, draftQuestions.length, isGenerating]);

  // Poll more cost estimate when generateMoreCount changes
  useEffect(() => {
    let active = true;
    if (currentJob && currentJob.status === "completed" && generateMoreCount > 0) {
      setIsLoadingMoreCost(true);
      adminApi.estimateAiQCCost({ question_count: generateMoreCount, operation: "generate_more" })
        .then((res) => {
          if (active) {
            setEstimatedMoreCost(res.qc_cost);
          }
        })
        .catch((err) => {
          console.error("Cost estimation error", err);
          if (active) {
            setEstimatedMoreCost(generateMoreCount * (wallet?.qc_per_question ?? 1));
          }
        })
        .finally(() => {
          if (active) {
            setIsLoadingMoreCost(false);
          }
        });
    }
    return () => {
      active = false;
    };
  }, [generateMoreCount, wallet, currentJob]);

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

    if (isLoadingCost) {
      toast.info("Đang tính chi phí QC, vui lòng chờ vài giây.");
      return;
    }

    if (wallet && estimatedCost > wallet.balance) {
      toast.error(formatLocalInsufficientQCMessage(estimatedCost, wallet.balance));
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
      upsertAIExamHistoryItem(response);
      syncHistory();
      startPolling(response.id);
    } catch (err: any) {
      toast.error(getErrorMessage(err, "Tạo yêu cầu AI thất bại."));
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
        upsertAIExamHistoryItem(job);
        syncHistory();

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
    }, 2500);
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
      if (currentJob) {
        const nextJob = { ...currentJob, question_drafts: updated };
        upsertAIExamHistoryItem(nextJob);
        syncHistory();
      }
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
      if (currentJob) {
        const nextJob = { ...currentJob, question_drafts: updated };
        upsertAIExamHistoryItem(nextJob);
        syncHistory();
      }
    } catch (err: any) {
      toast.error("Không lưu được chỉnh sửa câu hỏi.");
    }
  };

  // Generate More questions
  const handleGenerateMore = async () => {
    if (!currentJob) return;

    const distTotal = generateMoreQuestionTypes.reduce((sum, t) => sum + (generateMoreTypeDistribution[t] || 0), 0);
    if (distTotal !== generateMoreCount) {
      toast.error(`Tổng số câu tạo thêm theo loại (${distTotal}) phải bằng số câu cần thêm (${generateMoreCount}).`);
      return;
    }

    if (isLoadingMoreCost) {
      toast.info("Đang tính chi phí QC, vui lòng chờ vài giây.");
      return;
    }

    if (wallet && estimatedMoreCost > wallet.balance) {
      toast.error(formatLocalInsufficientQCMessage(estimatedMoreCost, wallet.balance));
      return;
    }

    setIsGenerating(true);

    try {
      const payload = {
        count: generateMoreCount,
        additional_instructions: generateMoreInstructions,
        question_types: generateMoreQuestionTypes,
        question_type_distribution: generateMoreTypeDistribution,
      };
      const response = await adminApi.generateMoreAiQuestions(currentJob.id, payload);
      setCurrentJob(response);
      upsertAIExamHistoryItem(response);
      syncHistory();
      startPolling(response.id);
      setGenerateMoreInstructions("");
    } catch (err: any) {
      toast.error(getErrorMessage(err, "Tạo thêm câu hỏi thất bại."));
      setIsGenerating(false);
    }
  };

  // Open past task from history table
  const openAIExamDraft = async (jobId: number) => {
    setIsGenerating(true);
    setCurrentJob(null);
    setDraftQuestions([]);
    try {
      const job = await adminApi.getAiExamJob(jobId);
      setCurrentJob(job);
      if (job.status === "completed") {
        setDraftQuestions(job.question_drafts || []);
        setIsGenerating(false);
      } else {
        startPolling(job.id);
      }
    } catch (err: any) {
      toast.error("Không thể mở lại tác vụ AI này.");
      setIsGenerating(false);
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

  const currentCost = currentJob
    ? (currentJob.qc_charged || currentJob.qc_reserved || 0)
    : estimatedCost;
  const hasInsufficientInitialQC = Boolean(wallet && !isLoadingCost && estimatedCost > wallet.balance);
  const hasInsufficientMoreQC = Boolean(wallet && !isLoadingMoreCost && estimatedMoreCost > wallet.balance);

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
          <div className="flex items-center gap-1.5 rounded-full border border-outline-variant bg-surface-container-lowest px-4 py-1.5 text-xs text-on-surface shadow-sm">
            <span>Ví sử dụng:</span>
            <span className="font-bold text-primary">
              {wallet.balance.toLocaleString("vi-VN")} QC Token
            </span>
            <span className="h-4 w-px bg-outline-variant" />
            <span className="font-bold text-on-surface">
              {isLoadingCost ? "..." : `${currentCost.toLocaleString("vi-VN")} QC`}
            </span>
          </div>
        )}
      </div>

      {draftQuestions.length === 0 && !isGenerating ? (
        <div className="space-y-6">
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

                <div className="rounded-lg border border-outline-variant bg-surface-container-low p-4 text-primary">
                  <div className="flex items-center gap-2 text-xs font-bold text-on-surface">
                    <Sparkles className="w-4 h-4 text-primary" />
                    Tại sao cần nhập bối cảnh đề thi?
                  </div>
                  <ul className="mt-2 list-disc space-y-1.5 pl-5 text-[11px] leading-5 text-outline">
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
                          : "border border-amber-500/30 bg-amber-500/10 text-amber-500"
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
                    <p className="text-[11px] font-medium text-amber-500">
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
              <div className="mt-auto space-y-2">
                <button
                  type="button"
                  onClick={handleGenerate}
                  disabled={isGenerating || isLoadingCost}
                  className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-[#4F62F2] to-[#7C3AED] text-sm font-bold text-white shadow-sm hover:opacity-95 disabled:opacity-50"
                >
                  <WandSparkles className="w-4 h-4" />
                  {hasInsufficientInitialQC ? "Không đủ QC Token" : isLoadingCost ? "Đang tính QC..." : "Tạo đề bằng AI"}
                </button>
                {wallet && hasInsufficientInitialQC && (
                  <p className="rounded-lg border border-error/20 bg-error/5 px-3 py-2 text-xs font-semibold text-error">
                    {formatLocalInsufficientQCMessage(estimatedCost, wallet.balance)}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* AI History Table */}
          <AIJobHistoryTable
            items={recentDrafts}
            onOpen={openAIExamDraft}
            onRefresh={syncHistory}
          />
        </div>
      ) : (
        <div className={isGenerating ? "space-y-5" : "grid grid-cols-1 lg:grid-cols-3 gap-6"}>
          {/* Left column: Saving status panel & Generate More */}
          <div className={isGenerating ? "hidden" : "lg:col-span-1 space-y-5"}>
            {currentJob && currentJob.status === "completed" && (
              <>
                {/* Result summary card */}
                <div className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5 shadow-sm space-y-4">
                  <h2 className="text-base font-bold text-on-surface">Kết quả AI</h2>
                  <p className="text-xs text-outline">Theo dõi trạng thái tạo đề và duyệt câu hỏi nháp trước khi lưu.</p>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-outline-variant bg-surface p-3 text-center">
                      <p className="text-[10px] uppercase font-bold text-outline">Câu hỏi</p>
                      <p className="mt-1 text-lg font-bold text-on-surface">
                        {draftQuestions.length}/{currentJob.question_count}
                      </p>
                    </div>
                    <div className="rounded-xl border border-outline-variant bg-surface p-3 text-center">
                      <p className="text-[10px] uppercase font-bold text-outline">Đã duyệt</p>
                      <p className="mt-1 text-lg font-bold text-success">
                        {draftQuestions.filter((q) => q.is_approved).length}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Generate More section */}
                {wallet && (
                  <div className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5 shadow-sm space-y-4">
                    <div className="flex flex-col gap-1.5 pb-3 border-b border-outline-variant/60">
                      <div className="flex items-center justify-between text-xs text-on-surface">
                        <div className="flex items-center gap-1.5 font-bold">
                          <Coins className="size-4 text-primary" />
                          {isLoadingMoreCost ? "Đang tính..." : `${estimatedMoreCost} QC`}
                        </div>
                        <span className="font-semibold text-primary">
                          Số dư {wallet.balance.toLocaleString("vi-VN")} QC
                        </span>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <label className="block space-y-1">
                        <span className="text-xs font-semibold text-on-surface">Số câu thêm</span>
                        <input
                          type="number"
                          min={1}
                          max={50}
                          value={generateMoreCount}
                          onChange={(e) => {
                            const val = Number(e.target.value);
                            setGenerateMoreCount(val);
                            setGenerateMoreTypeDistribution(
                              buildEvenQuestionTypeDistribution(val, generateMoreQuestionTypes)
                            );
                          }}
                          className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs text-on-surface focus:outline-none focus:border-primary"
                        />
                      </label>

                      <label className="block space-y-1">
                        <span className="text-xs font-semibold text-on-surface">Hướng dẫn thêm</span>
                        <textarea
                          value={generateMoreInstructions}
                          onChange={(e) => setGenerateMoreInstructions(e.target.value)}
                          placeholder="Ví dụ: thêm câu vận dụng cao, tránh trùng câu đã có"
                          rows={2}
                          className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs text-on-surface focus:outline-none focus:border-primary placeholder:text-outline animate-none"
                        />
                      </label>

                      {/* Question Type selector for Generate More */}
                      <div className="space-y-2 pt-2 border-t border-outline-variant/30">
                        <p className="text-xs font-bold text-on-surface">Loại câu tạo thêm</p>
                        <div className="grid grid-cols-2 gap-1.5">
                          {[
                            { value: "multiple_choice", label: "Trắc nghiệm" },
                            { value: "true_false", label: "Đúng / sai" },
                            { value: "short_answer", label: "Trả lời ngắn" },
                            { value: "essay", label: "Tự luận" },
                          ].map((option) => {
                            const checked = generateMoreQuestionTypes.includes(option.value as QuestionType);
                            return (
                              <label
                                key={option.value}
                                className={`flex cursor-pointer items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] font-semibold transition-colors ${
                                  checked
                                    ? "border-primary bg-primary/5 text-primary"
                                    : "border-outline-variant bg-surface-container-lowest text-on-surface-variant"
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() => {
                                    const nextTypes = checked
                                      ? generateMoreQuestionTypes.filter((t) => t !== option.value)
                                      : [...generateMoreQuestionTypes, option.value as QuestionType];
                                    setGenerateMoreQuestionTypes(nextTypes);
                                    setGenerateMoreTypeDistribution(
                                      buildEvenQuestionTypeDistribution(generateMoreCount, nextTypes)
                                    );
                                  }}
                                  className="rounded text-primary focus:ring-primary size-3"
                                />
                                {option.label}
                              </label>
                            );
                          })}
                        </div>

                        {generateMoreQuestionTypes.length > 0 && (
                          <div className="grid grid-cols-2 gap-2 mt-2 bg-surface p-2.5 rounded-lg border border-outline-variant">
                            {generateMoreQuestionTypes.map((type) => (
                              <label key={type} className="space-y-1">
                                <span className="text-[10px] uppercase font-bold text-outline capitalize">
                                  {type === "multiple_choice"
                                    ? "Trắc nghiệm"
                                    : type === "true_false"
                                    ? "Đúng / sai"
                                    : type === "short_answer"
                                    ? "Trả lời"
                                    : "Tự luận"}
                                </span>
                                <input
                                  type="number"
                                  min={1}
                                  value={generateMoreTypeDistribution[type] ?? 0}
                                  onChange={(e) => {
                                    const val = Number(e.target.value);
                                    setGenerateMoreTypeDistribution((prev) => ({
                                      ...prev,
                                      [type]: val,
                                    }));
                                  }}
                                  className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-2.5 py-1 text-xs focus:outline-none focus:border-primary"
                                />
                              </label>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="space-y-2">
                        <button
                          type="button"
                          disabled={isGenerating || isLoadingMoreCost || generateMoreQuestionTypes.length === 0}
                          onClick={handleGenerateMore}
                          className="w-full flex items-center justify-center gap-1.5 rounded-lg border border-primary text-primary py-2 text-xs font-bold hover:bg-primary/5 transition-colors disabled:opacity-50"
                        >
                          <Plus className="size-3.5" />
                          {hasInsufficientMoreQC ? "Không đủ QC Token" : isLoadingMoreCost ? "Đang tính QC..." : "Tạo thêm"}
                        </button>
                        {wallet && hasInsufficientMoreQC && (
                          <p className="rounded-lg border border-error/20 bg-error/5 px-3 py-2 text-[11px] font-semibold text-error">
                            {formatLocalInsufficientQCMessage(estimatedMoreCost, wallet.balance)}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Save exam card */}
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
              </>
            )}
          </div>

          {/* Right column: Generated Question list/status */}
          <div className={isGenerating ? "space-y-5" : "lg:col-span-2 space-y-5"}>
            {isGenerating && (
              <AIExamGenerationProgress
                currentJob={currentJob}
                durationMinutes={durationMinutes}
                questionCount={questionCount}
                selectedTypes={selectedTypes}
              />
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
                            {q.question_type === "multiple_choice"
                              ? "Trắc nghiệm"
                              : q.question_type === "true_false"
                              ? "Đúng / Sai"
                              : q.question_type === "short_answer"
                              ? "Trả lời ngắn"
                              : "Tự luận"}
                          </span>
                        </div>

                        <textarea
                          value={q.content}
                          onChange={(e) => handleEditQuestion(idx, { content: e.target.value })}
                          className="w-full bg-transparent border-none text-sm font-semibold text-on-surface resize-y focus:outline-none focus:ring-1 focus:ring-primary rounded p-1"
                          rows={2}
                        />

                        {/* Display options for multiple choice */}
                        {q.question_type === "multiple_choice" && q.options && Array.isArray(q.options) && q.options.length > 0 && (
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                            {q.options.map((opt, optIdx) => {
                              const prefix = String.fromCharCode(65 + optIdx);
                              return (
                                <div key={optIdx} className="flex items-center gap-2 bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-xs text-on-surface">
                                  <span className="font-bold text-primary">{prefix}.</span>
                                  <input
                                    type="text"
                                    value={opt}
                                    onChange={(e) => {
                                      const updatedOpts = [...q.options];
                                      updatedOpts[optIdx] = e.target.value;
                                      handleEditQuestion(idx, { options: updatedOpts });
                                    }}
                                    className="bg-transparent border-none outline-none flex-1 text-xs text-on-surface"
                                  />
                                </div>
                              );
                            })}
                          </div>
                        )}

                        {/* Correct Answers & Explanations */}
                        <div className="flex flex-col gap-2 mt-3 pt-2 border-t border-outline-variant/30">
                          <label className="flex flex-col gap-1">
                            <span className="text-xs font-bold text-success">Đáp án đúng</span>
                            {q.question_type === "multiple_choice" ? (
                              <select
                                value={q.correct_answer || ""}
                                onChange={(e) => handleEditQuestion(idx, { correct_answer: e.target.value })}
                                className="max-w-xs rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs font-semibold text-on-surface focus:outline-none focus:border-primary"
                              >
                                <option value="">-- Chọn đáp án đúng --</option>
                                {q.options?.map((opt, optIdx) => {
                                  const prefix = String.fromCharCode(65 + optIdx);
                                  return (
                                    <option key={optIdx} value={opt}>
                                      {prefix}. {opt}
                                    </option>
                                  );
                                })}
                              </select>
                            ) : q.question_type === "true_false" ? (
                              <select
                                value={q.correct_answer === true || q.correct_answer === "true" ? "true" : "false"}
                                onChange={(e) => handleEditQuestion(idx, { correct_answer: e.target.value === "true" })}
                                className="max-w-xs rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs font-semibold text-on-surface focus:outline-none focus:border-primary"
                              >
                                <option value="true">Đúng</option>
                                <option value="false">Sai</option>
                              </select>
                            ) : q.question_type === "short_answer" ? (
                              <input
                                type="text"
                                value={Array.isArray(q.correct_answer) ? q.correct_answer.join(", ") : String(q.correct_answer || "")}
                                onChange={(e) =>
                                  handleEditQuestion(idx, {
                                    correct_answer: e.target.value.split(",").map((s) => s.trim()),
                                  })
                                }
                                className="max-w-md rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs font-semibold text-on-surface focus:outline-none focus:border-primary"
                                placeholder="Nhập các đáp án chấp nhận, cách nhau bằng dấu phẩy"
                              />
                            ) : (
                              <textarea
                                value={String(q.correct_answer || "")}
                                onChange={(e) => handleEditQuestion(idx, { correct_answer: e.target.value })}
                                className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs font-semibold text-on-surface focus:outline-none focus:border-primary"
                                rows={2}
                                placeholder="Nhập hướng dẫn chấm hoặc đáp án tự luận tham khảo"
                              />
                            )}
                          </label>
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

// Subcomponent: AI History Table
function getStatusLabel(status: string): string {
  switch (status) {
    case "completed":
      return "Hoàn tất";
    case "failed":
      return "Có lỗi";
    case "pending":
    case "processing":
      return "Đang xử lý";
    default:
      return status;
  }
}

function isJobFailed(status: string): boolean {
  return status === "failed";
}

function isJobRunning(status: string): boolean {
  return status === "pending" || status === "processing";
}

const HIST_PAGE_SIZE = 5;
const ALL_CATEGORIES = "__all_categories__";
const ALL_STATUSES = "__all_statuses__";

interface AIJobHistoryTableProps {
  items: AIExamHistoryItem[];
  onOpen: (jobId: number) => void;
  onRefresh: () => void;
}

function AIJobHistoryTable({ items, onOpen, onRefresh }: AIJobHistoryTableProps) {
  const [category, setCategory] = useState(ALL_CATEGORIES);
  const [status, setStatus] = useState(ALL_STATUSES);
  const [page, setPage] = useState(1);

  const categories = useMemo(() => {
    const list = items.map((item) => {
      const subject = item.subject?.trim() || "Chưa xác định";
      const grade = item.grade?.trim();
      return grade ? `${subject} - ${grade}` : subject;
    });
    return Array.from(new Set(list)).sort();
  }, [items]);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      const subject = item.subject?.trim() || "Chưa xác định";
      const grade = item.grade?.trim();
      const itemCat = grade ? `${subject} - ${grade}` : subject;

      if (category !== ALL_CATEGORIES && itemCat !== category) {
        return false;
      }

      let statGroup = "completed";
      if (isJobFailed(item.status)) statGroup = "failed";
      else if (isJobRunning(item.status)) statGroup = "running";

      if (status !== ALL_STATUSES && statGroup !== status) {
        return false;
      }

      return true;
    });
  }, [category, items, status]);

  const totalPages = Math.max(1, Math.ceil(filteredItems.length / HIST_PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageItems = filteredItems.slice(
    (safePage - 1) * HIST_PAGE_SIZE,
    safePage * HIST_PAGE_SIZE,
  );

  const formatDateTime = (value: string) => {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return "Vừa tạo";
    return new Intl.DateTimeFormat("vi-VN", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(parsed);
  };

  const getInputLabel = (item: AIExamHistoryItem) => {
    const parts = [item.topic, item.subject, item.grade].map((v) => v?.trim()).filter(Boolean);
    return parts.length > 0 ? parts.join(" - ") : item.title;
  };

  return (
    <section className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest shadow-sm mt-6">
      <div className="flex flex-col gap-3 border-b border-outline-variant px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <History className="size-4 text-primary" />
          <div>
            <h2 className="text-sm font-bold text-on-surface">Lịch sử tác vụ AI</h2>
            <p className="mt-0.5 text-[11px] text-outline">
              Theo dõi các lần tạo đề, trạng thái xử lý và mở lại nội dung nháp.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onRefresh}
          className="flex items-center gap-1 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs font-semibold text-on-surface hover:bg-surface-container-low"
        >
          <RefreshCw className="size-3.5" />
          Làm mới
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-outline-variant px-4 py-3">
        <select
          value={category}
          onChange={(e) => { setCategory(e.target.value); setPage(1); }}
          className="h-9 min-w-44 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 text-xs text-on-surface outline-none focus:border-primary"
        >
          <option value={ALL_CATEGORIES}>Tất cả phân loại</option>
          {categories.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>

        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className="h-9 min-w-40 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 text-xs text-on-surface outline-none focus:border-primary"
        >
          <option value={ALL_STATUSES}>Tất cả trạng thái</option>
          <option value="completed">Hoàn tất</option>
          <option value="running">Đang xử lý</option>
          <option value="failed">Có lỗi</option>
        </select>

        <span className="ml-auto text-xs font-semibold text-primary">
          {filteredItems.length} tác vụ
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[800px] border-collapse text-left text-xs">
          <thead className="bg-surface-container-low text-on-surface-variant">
            <tr>
              <th className="px-4 py-3 font-semibold">ID</th>
              <th className="px-4 py-3 font-semibold">Thời gian</th>
              <th className="px-4 py-3 font-semibold">Phân loại</th>
              <th className="px-4 py-3 font-semibold">Dữ liệu đầu vào</th>
              <th className="px-4 py-3 text-center font-semibold">EduToken</th>
              <th className="px-4 py-3 text-center font-semibold">Trạng thái</th>
              <th className="px-4 py-3 text-right font-semibold">Hành động</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-outline-variant/40">
            {pageItems.length > 0 ? (
              pageItems.map((item) => {
                const failed = isJobFailed(item.status);
                const running = isJobRunning(item.status);
                const subject = item.subject?.trim() || "Chưa xác định";
                const grade = item.grade?.trim();
                const itemCat = grade ? `${subject} - ${grade}` : subject;

                return (
                  <tr key={item.id} className="transition-colors hover:bg-surface-container-low/20">
                    <td className="whitespace-nowrap px-4 py-3 font-medium text-on-surface">
                      EA-{String(item.id).padStart(6, "0")}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-outline">
                      {formatDateTime(item.updatedAt || item.createdAt)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-on-surface">
                      {itemCat}
                    </td>
                    <td className="max-w-[360px] px-4 py-3">
                      <p className="truncate font-medium text-on-surface">{getInputLabel(item)}</p>
                      <p className="mt-1 text-[11px] text-outline">
                        {item.approvedCount}/{item.questionCount} câu đã duyệt
                      </p>
                    </td>
                    <td className="px-4 py-3 text-center font-medium text-on-surface">
                      {item.qcCost ?? 0}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                        failed ? "border border-error/30 bg-error/10 text-error" : running ? "border border-amber-500/30 bg-amber-500/10 text-amber-500" : "border border-success/30 bg-success/10 text-success"
                      }`}>
                        {getStatusLabel(item.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => onOpen(item.id)}
                          className="flex items-center gap-1 rounded border border-outline-variant bg-surface px-2 py-1 text-[11px] font-semibold text-on-surface hover:bg-surface-container-low"
                        >
                          <Eye className="size-3" />
                          Xem
                        </button>
                        <button
                          type="button"
                          onClick={() => onOpen(item.id)}
                          className="flex items-center gap-1 rounded border border-outline-variant bg-surface px-2 py-1 text-[11px] font-semibold text-on-surface hover:bg-surface-container-low"
                        >
                          <FolderOpen className="size-3" />
                          Mở lại
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-sm text-outline">
                  Chưa có tác vụ AI phù hợp với bộ lọc.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 border-t border-outline-variant px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-outline">
          Hiển thị {pageItems.length} / {filteredItems.length} tác vụ
        </p>

        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={safePage <= 1}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            className="flex size-7 items-center justify-center rounded border border-outline-variant hover:bg-surface-container-low disabled:opacity-50"
          >
            <ChevronLeft className="size-4" />
          </button>

          <span className="flex size-7 items-center justify-center rounded bg-primary text-xs font-bold text-white">
            {safePage}
          </span>

          <button
            type="button"
            disabled={safePage >= totalPages}
            onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
            className="flex size-7 items-center justify-center rounded border border-outline-variant hover:bg-surface-container-low disabled:opacity-50"
          >
            <ChevronRight className="size-4" />
          </button>
        </div>
      </div>
    </section>
  );
}
