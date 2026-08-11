import { type ChangeEvent, type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "react-toastify";
import {
  AlertCircle,
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  Info,
  ListChecks,
  FileCheck,
  Loader2,
  Plus,
  Save,
  Sparkles,
  Trash2,
  Upload,
} from "lucide-react";
import {
  adminApi,
  type AdminClass,
  type AdminExamQuestionPayload,
  type AdminExamQuestionType,
  type CreateAdminExamPayload,
} from "../lib/api";
import { examCoverPresets } from "../lib/exam-covers";

type ExamScope = "system" | "class";
type ExamCreateTab = "basic" | "questions" | "advanced";
type ExamSubmitIntent = "save" | "publish";

type ExamSubmitPayload = {
  title: string;
  description: string | null;
  grade: string;
  image_url: string | null;
  scope: ExamScope;
  classroom_id: number | null;
  duration_minutes: number;
  start_time?: string | null;
  end_time?: string | null;
  is_published?: boolean;
  is_active?: boolean;
  questions?: AdminExamQuestionPayload[];
};

type OptionForm = {
  option_key: string;
  option_text: string;
};

type QuestionForm = {
  id: string;
  question_type: AdminExamQuestionType;
  prompt: string;
  explanation: string;
  points: string;
  options: OptionForm[];
  correctOptionIndex: number;
  trueFalseAnswer: "true" | "false";
  acceptedAnswersText: string;
};

const OPTION_KEYS = ["A", "B", "C", "D", "E", "F"];

const examCreateTabs: Array<{ key: ExamCreateTab; label: string }> = [
  { key: "basic", label: "Thông tin đề thi" },
  { key: "questions", label: "Xây dựng câu hỏi" },
  { key: "advanced", label: "Xem lại & lưu" },
];

const trueFalseOptions: Array<{ label: string; value: "true" | "false" }> = [
  { label: "Đúng", value: "true" },
  { label: "Sai", value: "false" },
];

const questionTypeLabels: Record<AdminExamQuestionType, string> = {
  single_choice: "Một đáp án",
  true_false: "Đúng / Sai",
  short_answer: "Trả lời ngắn",
  text: "Tự luận",
};

function makeQuestion(): QuestionForm {
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    question_type: "single_choice",
    prompt: "",
    explanation: "",
    points: "1",
    options: [
      { option_key: "A", option_text: "" },
      { option_key: "B", option_text: "" },
      { option_key: "C", option_text: "" },
      { option_key: "D", option_text: "" },
    ],
    correctOptionIndex: 0,
    trueFalseAnswer: "true",
    acceptedAnswersText: "",
  };
}

function mapQuestionDetailToForm(q: any): QuestionForm {
  let correctOptionIndex = 0;
  if (q.question_type === "single_choice" && q.options) {
    const idx = q.options.findIndex((opt: any) => opt.is_correct);
    if (idx >= 0) {
      correctOptionIndex = idx;
    }
  }

  const trueFalseAnswer = (q.accepted_answers?.[0] === "false" ? "false" : "true") as "true" | "false";
  const acceptedAnswersText = q.accepted_answers ? q.accepted_answers.join("\n") : "";

  return {
    id: q.id ? String(q.id) : `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    question_type: q.question_type,
    prompt: q.prompt || "",
    explanation: q.explanation || "",
    points: String(q.points || 1),
    options: q.options ? q.options.map((opt: any) => ({
      option_key: opt.option_key || "",
      option_text: opt.option_text || "",
    })) : [
      { option_key: "A", option_text: "" },
      { option_key: "B", option_text: "" },
      { option_key: "C", option_text: "" },
      { option_key: "D", option_text: "" },
    ],
    correctOptionIndex,
    trueFalseAnswer,
    acceptedAnswersText,
  };
}

function toIsoDateTime(value: string) {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toISOString();
}

function splitAcceptedAnswers(value: string) {
  return value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildQuestionPayload(question: QuestionForm, index: number): AdminExamQuestionPayload {
  const base = {
    question_type: question.question_type,
    prompt: question.prompt.trim(),
    explanation: question.explanation.trim(),
    order_index: index + 1,
    points: Number(question.points) || 1,
  };

  if (question.question_type === "single_choice") {
    return {
      ...base,
      options: question.options.map((option, optionIndex) => ({
        option_key: option.option_key || OPTION_KEYS[optionIndex] || String(optionIndex + 1),
        option_text: option.option_text.trim(),
        image_url: null,
        is_correct: optionIndex === question.correctOptionIndex,
      })),
      accepted_answers: [],
    };
  }

  if (question.question_type === "true_false") {
    return {
      ...base,
      options: [],
      accepted_answers: [question.trueFalseAnswer],
    };
  }

  return {
    ...base,
    options: [],
    accepted_answers: splitAcceptedAnswers(question.acceptedAnswersText),
  };
}

function getQuestionSignature(questions: QuestionForm[]) {
  return JSON.stringify(questions.map(buildQuestionPayload));
}

function normalizeSubmitError(error: unknown) {
  const message = error instanceof Error ? error.message : "Thao tác thất bại.";
  if (message.includes("Cannot replace questions after students have started attempts")) {
    return "Đề này đã có học sinh bắt đầu làm bài nên không thể thay đổi danh sách câu hỏi. Bạn vẫn có thể cập nhật thông tin, lịch làm bài, ảnh và trạng thái xuất bản nếu không sửa câu hỏi.";
  }
  return message;
}

function validateQuestionForm(question: QuestionForm, index: number) {
  const label = `Câu ${index + 1}`;
  if (!question.prompt.trim()) {
    return `${label}: vui lòng nhập nội dung câu hỏi.`;
  }
  if (!question.points || Number(question.points) <= 0) {
    return `${label}: điểm câu hỏi phải lớn hơn 0.`;
  }
  if (question.question_type === "single_choice") {
    const filledOptions = question.options.filter((option) => option.option_text.trim());
    if (filledOptions.length < 2) {
      return `${label}: câu một đáp án cần ít nhất 2 đáp án.`;
    }
    if (!question.options[question.correctOptionIndex]?.option_text.trim()) {
      return `${label}: đáp án đúng không được để trống.`;
    }
  }
  if (
    (question.question_type === "short_answer" || question.question_type === "text") &&
    splitAcceptedAnswers(question.acceptedAnswersText).length < 1
  ) {
    return `${label}: vui lòng nhập ít nhất một đáp án chấp nhận.`;
  }
  return null;
}

export function ExamCreate() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEditMode = Boolean(id);

  const [mode, setMode] = useState<"select" | "manual">("select");
  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const [classes, setClasses] = useState<AdminClass[]>([]);
  const [isLoadingClasses, setIsLoadingClasses] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [grade, setGrade] = useState("");
  const [description, setDescription] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [scope, setScope] = useState<ExamScope>("system");
  const [classroomId, setClassroomId] = useState("");
  const [durationMinutes, setDurationMinutes] = useState("30");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [questions, setQuestions] = useState<QuestionForm[]>(() => [makeQuestion()]);
  const [originalQuestionSignature, setOriginalQuestionSignature] = useState<string | null>(null);
  const [hasStartedAttempts, setHasStartedAttempts] = useState(false);
  const [isPublished, setIsPublished] = useState(false);
  const [activeTab, setActiveTab] = useState<ExamCreateTab>("basic");
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null);

  useEffect(() => {
    if (isEditMode && id) {
      setMode("manual");
      adminApi
        .getExamDetail(Number(id))
        .then((exam) => {
          setTitle(exam.title || "");
          setGrade(exam.grade || "");
          setDescription(exam.description || "");
          setImageUrl(exam.image_url || "");
          setScope(exam.scope || "system");
          setClassroomId(exam.classroom_id ? String(exam.classroom_id) : "");
          setDurationMinutes(String(exam.duration_minutes || "30"));
          setStartTime(exam.start_time ? exam.start_time.substring(0, 16) : "");
          setEndTime(exam.end_time ? exam.end_time.substring(0, 16) : "");
          setHasStartedAttempts((exam.attempt_count || 0) > 0);
          setIsPublished(Boolean(exam.is_published && exam.is_active));
          
          if (exam.questions && exam.questions.length > 0) {
            const mapped = exam.questions.map(mapQuestionDetailToForm);
            setQuestions(mapped);
            setOriginalQuestionSignature(getQuestionSignature(mapped));
            setSelectedQuestionId(mapped[0].id);
          }
        })
        .catch((err) => {
          toast.error("Không thể tải chi tiết đề thi cần chỉnh sửa.");
          console.error(err);
        });
    }
  }, [isEditMode, id]);

  useEffect(() => {
    let mounted = true;
    setIsLoadingClasses(true);
    adminApi
      .getClassesOverview()
      .then((response) => {
        if (mounted) {
          setClasses(response.items);
        }
      })
      .catch(() => {
        if (mounted) {
          setClasses([]);
        }
      })
      .finally(() => {
        if (mounted) {
          setIsLoadingClasses(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    setSelectedQuestionId((currentId) => {
      if (currentId && questions.some((question) => question.id === currentId)) {
        return currentId;
      }
      return questions[0]?.id ?? null;
    });
  }, [questions]);

  const totalPoints = useMemo(
    () =>
      questions.reduce((sum, question) => {
        const value = Number(question.points);
        return sum + (Number.isFinite(value) && value > 0 ? value : 0);
      }, 0),
    [questions],
  );

  const selectedQuestionIndex = selectedQuestionId
    ? questions.findIndex((question) => question.id === selectedQuestionId)
    : -1;
  const selectedQuestion =
    selectedQuestionIndex >= 0 ? questions[selectedQuestionIndex] : questions[0] ?? null;

  const addQuestion = () => {
    const question = makeQuestion();
    setQuestions((items) => [...items, question]);
    setSelectedQuestionId(question.id);
  };

  const removeQuestion = (questionId: string) => {
    if (questions.length <= 1) {
      return;
    }
    const removedIndex = questions.findIndex((question) => question.id === questionId);
    const nextQuestions = questions.filter((question) => question.id !== questionId);
    setQuestions(nextQuestions);
    if (selectedQuestionId === questionId) {
      setSelectedQuestionId(
        nextQuestions[Math.min(Math.max(removedIndex, 0), nextQuestions.length - 1)]?.id ??
          null,
      );
    }
  };

  const saveSelectedQuestion = () => {
    if (!selectedQuestion) {
      return;
    }
    const validationError = validateQuestionForm(selectedQuestion, selectedQuestionIndex);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    toast.success(`Đã lưu câu ${selectedQuestionIndex + 1}.`);
  };

  const updateQuestion = (questionId: string, patch: Partial<QuestionForm>) => {
    setQuestions((items) =>
      items.map((item) => (item.id === questionId ? { ...item, ...patch } : item)),
    );
  };

  const updateOption = (
    questionId: string,
    optionIndex: number,
    patch: Partial<OptionForm>,
  ) => {
    setQuestions((items) =>
      items.map((question) => {
        if (question.id !== questionId) {
          return question;
        }
        const nextOptions = question.options.map((option, index) =>
          index === optionIndex ? { ...option, ...patch } : option,
        );
        return { ...question, options: nextOptions };
      }),
    );
  };

  const addOption = (questionId: string) => {
    setQuestions((items) =>
      items.map((question) => {
        if (question.id !== questionId || question.options.length >= OPTION_KEYS.length) {
          return question;
        }
        return {
          ...question,
          options: [
            ...question.options,
            {
              option_key: OPTION_KEYS[question.options.length],
              option_text: "",
            },
          ],
        };
      }),
    );
  };

  const removeOption = (questionId: string, optionIndex: number) => {
    setQuestions((items) =>
      items.map((question) => {
        if (question.id !== questionId || question.options.length <= 2) {
          return question;
        }
        const nextOptions = question.options.filter((_, index) => index !== optionIndex);
        return {
          ...question,
          options: nextOptions.map((option, index) => ({
            ...option,
            option_key: OPTION_KEYS[index],
          })),
          correctOptionIndex:
            question.correctOptionIndex >= nextOptions.length
              ? Math.max(0, nextOptions.length - 1)
              : question.correctOptionIndex,
        };
      }),
    );
  };

  const validateForm = () => {
    if (!title.trim()) {
      return "Vui lòng nhập tên đề thi.";
    }
    if (!grade.trim()) {
      return "Vui lòng nhập trình độ đề thi.";
    }
    if (scope === "class" && !classroomId) {
      return "Vui lòng chọn lớp học cho đề thi trong lớp.";
    }
    if (!durationMinutes || Number(durationMinutes) < 1) {
      return "Thời lượng làm bài phải lớn hơn 0 phút.";
    }
    if (startTime && endTime && new Date(startTime) >= new Date(endTime)) {
      return "Thời gian bắt đầu phải nhỏ hơn thời gian kết thúc.";
    }
    if (questions.length < 1) {
      return "Vui lòng thêm ít nhất một câu hỏi.";
    }

    for (const [index, question] of questions.entries()) {
      const questionError = validateQuestionForm(question, index);
      if (questionError) {
        return questionError;
      }
    }

    return null;
  };

  const handleSubmit = async (intent: ExamSubmitIntent) => {
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    setError(null);

    const questionPayloads = questions.map(buildQuestionPayload);
    const questionsChanged = !isEditMode || getQuestionSignature(questions) !== originalQuestionSignature;
    if (isEditMode && hasStartedAttempts && questionsChanged) {
      setIsSubmitting(false);
      setError(
        "Đề này đã có học sinh bắt đầu làm bài nên không thể thay đổi danh sách câu hỏi. Hãy hoàn tác thay đổi ở phần câu hỏi hoặc tạo đề mới nếu cần đổi nội dung câu hỏi.",
      );
      return;
    }

    const payload: ExamSubmitPayload = {
      title: title.trim(),
      description: description.trim() || null,
      grade: grade.trim(),
      image_url: imageUrl.trim() || null,
      scope,
      classroom_id: scope === "class" ? Number(classroomId) : null,
      duration_minutes: Number(durationMinutes),
    };
    const normalizedStartTime = toIsoDateTime(startTime);
    const normalizedEndTime = toIsoDateTime(endTime);
    if (isEditMode) {
      payload.start_time = normalizedStartTime;
      payload.end_time = normalizedEndTime;
    } else {
      if (normalizedStartTime) {
        payload.start_time = normalizedStartTime;
      }
      if (normalizedEndTime) {
        payload.end_time = normalizedEndTime;
      }
    }

    try {
      if (isEditMode && id) {
        if (questionsChanged) {
          payload.questions = questionPayloads;
        }
        if (intent === "publish") {
          payload.is_published = true;
          payload.is_active = true;
        }
        await adminApi.updateExam(Number(id), payload);
        toast.success(intent === "publish" ? "Đã lưu thay đổi và xuất bản đề thi." : "Đã cập nhật đề thi.");
      } else {
        payload.is_published = intent === "publish";
        payload.is_active = intent === "publish";
        payload.questions = questionPayloads;
        await adminApi.createExam(payload as CreateAdminExamPayload);
        toast.success(intent === "publish" ? "Đã tạo và xuất bản đề thi." : "Đã lưu nháp đề thi.");
      }
      navigate("/exams");
    } catch (err) {
      setError(normalizeSubmitError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleImageUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }

    setIsUploadingImage(true);
    setError(null);
    try {
      const response = await adminApi.uploadExamImage(file);
      setImageUrl(response.image.url);
      toast.success("Đã tải ảnh đề thi lên.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được ảnh đề thi.");
    } finally {
      setIsUploadingImage(false);
    }
  };

  const inputClass =
    "w-full rounded-md border border-outline-variant bg-surface-container-lowest px-3 py-2.5 text-sm text-on-surface outline-none transition-colors placeholder:text-outline focus:border-primary";
  const selectClass = `${inputClass} appearance-none pr-9`;
  const cardClass =
    "rounded-md border border-outline-variant bg-surface-container-lowest shadow-(--shadow-level-1)";
  const labelClass = "text-sm font-semibold text-on-surface";
  const mutedClass = "text-sm text-outline";
  const normalizedImageUrl = imageUrl.trim();

  if (mode === "select") {
    const creationMethods = [
      {
        title: "Tạo đề AI",
        description: "Tạo đề tự động bằng AI, chọn loại câu hỏi và rà soát từng câu trước khi lưu.",
        action: () => navigate("/exams/ai"),
        imageSrc: "/image/text2.png",
        hoverClassName: "hover:from-[#FF5277] hover:to-[#FF855A]",
      },
      {
        title: "Soạn thảo văn bản",
        description: "Nhập trực tiếp câu hỏi và đáp án dạng văn bản theo cú pháp để hệ thống tự động trích xuất và xem trước.",
        action: () => navigate("/exams/text"),
        imageSrc: "/image/text1.png",
        hoverClassName: "hover:from-[#4F62F2] hover:to-[#7C3AED]",
      },
      {
        title: "Trình soạn thảo thủ công",
        description: "Tạo đề từ đầu và tự nhập thông tin, câu hỏi, đáp án theo từng bước.",
        action: () => setMode("manual"),
        imageSrc: "/image/text3.png",
        hoverClassName: "hover:from-[#06B6D4] hover:to-[#4F62F2]",
      },
    ] as const;

    return (
      <div className="min-h-full bg-background p-4 md:p-5 space-y-4">
        <div>
          <h1 className="text-lg font-bold text-on-surface">Lựa chọn phương thức tạo đề thi phù hợp</h1>
          <p className="mt-1 text-xs text-outline">
            Mỗi phương thức đều lưu về cùng hệ thống quản lý đề thi của hệ thống.
          </p>
        </div>

        <section className="rounded-[10px] border border-outline-variant bg-surface-container-low p-4">
          <div className="grid gap-4 md:grid-cols-3">
            {creationMethods.map((method) => (
              <div
                key={method.title}
                onClick={method.action}
                className={`group relative flex min-h-[230px] flex-col items-center justify-between overflow-hidden rounded-[10px] bg-surface-container-lowest p-5 text-center shadow-sm cursor-pointer transition-all duration-300 hover:-translate-y-0.5 hover:bg-gradient-to-r ${method.hoverClassName} hover:shadow-md`}
              >
                <div>
                  <h2 className="text-sm font-bold text-on-surface transition-colors group-hover:text-white">{method.title}</h2>
                  <p className="mx-auto mt-2 max-w-[280px] text-xs leading-5 text-outline transition-colors group-hover:text-white/90">{method.description}</p>
                </div>

                <div className="mt-5 flex h-[84px] w-[140px] items-center justify-center">
                  <img
                    src={method.imageSrc}
                    alt=""
                    className="h-[84px] w-[140px] object-contain"
                  />
                </div>

                <span className="mt-4 text-xs font-bold text-primary transition-colors group-hover:text-white">Chọn phương thức</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-background p-4 md:p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate("/exams")}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-outline-variant bg-surface-container-lowest text-on-surface shadow-sm hover:bg-surface-container-low"
            aria-label="Quay lại danh sách bài thi"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-on-surface">
              {isEditMode ? "Cập nhật đề thi" : "Tạo đề thi mới"}
            </h1>
            <p className={mutedClass}>Thiết lập thông tin, lịch làm bài và câu hỏi cho đề thi.</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => void handleSubmit("save")}
            className="flex items-center justify-center gap-2 rounded-md border border-outline-variant bg-surface-container-lowest px-4 py-2 text-sm font-semibold text-on-surface hover:bg-surface-container-low disabled:opacity-60"
          >
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {isEditMode ? "Cập nhật" : "Lưu nháp"}
          </button>
          {isEditMode && isPublished ? (
            <div
              className="flex items-center justify-center gap-2 rounded-md border border-success/30 bg-success/10 px-4 py-2 text-sm font-semibold text-success"
              title="Đề này đang được xuất bản. Bấm Cập nhật sẽ lưu thay đổi và vẫn giữ trạng thái xuất bản."
            >
              <CheckCircle2 className="h-4 w-4" />
              Đã xuất bản
            </div>
          ) : (
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => void handleSubmit("publish")}
              className="flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-on-primary shadow-sm hover:bg-primary/90 disabled:opacity-60"
              title={isEditMode ? "Lưu thay đổi hiện tại và cho phép học sinh nhìn thấy đề." : "Tạo đề và cho phép học sinh nhìn thấy đề."}
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              Xuất bản
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 flex items-start gap-2 rounded-md border border-error-container bg-error-container/60 px-4 py-3 text-sm text-on-error-container">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <section className="overflow-hidden rounded-[10px] border border-outline-variant bg-surface-container-lowest p-2.5 shadow-sm mb-4">
        <div className="grid gap-2.5 md:grid-cols-3">
          {examCreateTabs.map((tab, index) => {
            const currentStepIndex = examCreateTabs.findIndex((t) => t.key === activeTab);
            const isCompleted = index < currentStepIndex;
            const isCurrent = index === currentStepIndex;

            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`rounded-[6px] border px-4 py-3 text-left transition-all flex items-center gap-3 cursor-pointer ${
                  isCurrent
                    ? "border-primary bg-primary/5 text-primary shadow-sm"
                    : isCompleted
                      ? "border-outline-variant bg-surface text-on-surface hover:border-outline"
                      : "border-outline-variant bg-surface-container-lowest text-outline hover:border-outline-variant"
                }`}
              >
                <div
                  className={`flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                    isCurrent
                      ? "bg-primary text-white"
                      : isCompleted
                        ? "bg-success text-white"
                        : "bg-surface-variant text-outline"
                  }`}
                >
                  {isCompleted ? "✓" : index + 1}
                </div>

                <span className="text-xs font-bold truncate">
                  {tab.label}
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <form
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            void handleSubmit("save");
          }}
          className="flex flex-col gap-4"
        >
          {activeTab === "basic" && (
            <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[326px_minmax(0,1fr)_minmax(360px,0.9fr)]">
              <section className={cardClass}>
                <div className="border-b border-outline-variant px-4 py-3">
                  <h2 className="text-base font-semibold text-on-surface">Ảnh đề thi</h2>
                </div>
                <div className="space-y-3 p-4">
                  <input
                    ref={imageInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/gif"
                    onChange={(event) => void handleImageUpload(event)}
                    className="hidden"
                  />
                  <button
                    type="button"
                    onClick={() => imageInputRef.current?.click()}
                    disabled={isUploadingImage}
                    className="flex h-40 w-full items-center justify-center overflow-hidden rounded-md border border-dashed border-outline-variant bg-surface-container-low text-on-surface transition-colors hover:border-primary hover:bg-surface-container disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    {normalizedImageUrl ? (
                      <img
                        src={normalizedImageUrl}
                        alt="Ảnh đề thi"
                        className="h-full w-full object-contain p-1"
                      />
                    ) : (
                      <div className="flex flex-col items-center gap-2 text-on-surface">
                        {isUploadingImage ? (
                          <Loader2 className="h-10 w-10 animate-spin" />
                        ) : (
                          <Upload className="h-10 w-10" />
                        )}
                        <span className="text-sm font-medium">
                          {isUploadingImage ? "Đang tải..." : "Tải lên"}
                        </span>
                      </div>
                    )}
                  </button>
                  <p className="text-sm text-outline">Tải ảnh lên hoặc chọn ảnh đề thi</p>
                  <p className="text-sm font-semibold text-on-surface">Chọn ảnh đại diện</p>
                  <div className="grid grid-cols-4 gap-2">
                    {examCoverPresets.map((preset) => {
                      const isSelected = normalizedImageUrl === preset.src;
                      return (
                        <button
                          key={preset.src}
                          type="button"
                          onClick={() => setImageUrl(preset.src)}
                          className={`h-14 overflow-hidden rounded-md border bg-surface-container-low transition-colors ${
                            isSelected
                              ? "border-primary ring-2 ring-primary/25"
                              : "border-outline-variant hover:border-primary"
                          }`}
                          aria-label={preset.label}
                        >
                          <img
                            src={preset.src}
                            alt={preset.label}
                            className="h-full w-full object-contain p-1"
                          />
                        </button>
                      );
                    })}
                  </div>
                </div>
              </section>

              <section className={cardClass}>
                <div className="border-b border-outline-variant px-4 py-3">
                  <h2 className="text-base font-semibold text-on-surface">Thông tin cơ bản</h2>
                </div>
                <div className="space-y-4 p-4">
                  <label className="flex flex-col gap-1.5">
                    <span className={labelClass}>
                      Tên đề thi <span className="text-error">*</span>
                    </span>
                    <input
                      value={title}
                      onChange={(event) => setTitle(event.target.value)}
                      placeholder="Nhập tên đề thi"
                      className={inputClass}
                    />
                  </label>

                  <label className="flex flex-col gap-1.5">
                    <span className={labelClass}>
                      Trình độ <span className="text-error">*</span>
                    </span>
                    <input
                      value={grade}
                      onChange={(event) => setGrade(event.target.value)}
                      placeholder="Ví dụ: Lớp 12"
                      className={inputClass}
                    />
                  </label>

                  <label className="flex flex-col gap-1.5">
                    <span className={labelClass}>Mô tả</span>
                    <textarea
                      value={description}
                      onChange={(event) => setDescription(event.target.value)}
                      placeholder="Mô tả ngắn về đề thi"
                      rows={5}
                      className={`${inputClass} min-h-[150px] resize-none`}
                    />
                  </label>
                </div>
              </section>

              <section className={cardClass}>
                <div className="border-b border-outline-variant px-4 py-3">
                  <h2 className="text-base font-semibold text-on-surface">Cấu hình đề thi</h2>
                </div>
                <div className="space-y-4 p-4">
                  <div className="flex items-center gap-2 rounded-md bg-primary px-3 py-3 text-sm font-semibold text-on-primary">
                    <Info className="h-4 w-4 shrink-0" />
                    Lịch làm bài và phạm vi hiển thị
                  </div>

                  <label className="flex flex-col gap-1.5">
                    <span className={labelClass}>
                      Phạm vi <span className="text-error">*</span>
                    </span>
                    <div className="relative">
                      <select
                        value={scope}
                        onChange={(event) => setScope(event.target.value as ExamScope)}
                        className={selectClass}
                      >
                        <option value="system">Hệ thống</option>
                        <option value="class">Trong lớp</option>
                      </select>
                      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-outline" />
                    </div>
                  </label>

                  <label className="flex flex-col gap-1.5">
                    <span className={labelClass}>Lớp học</span>
                    <div className="relative">
                      <select
                        value={classroomId}
                        onChange={(event) => setClassroomId(event.target.value)}
                        disabled={scope === "system" || isLoadingClasses}
                        className={`${selectClass} disabled:cursor-not-allowed disabled:opacity-60`}
                      >
                        <option value="">
                          {isLoadingClasses ? "Đang tải lớp học..." : "Chọn lớp học"}
                        </option>
                        {classes.map((classroom) => (
                          <option key={classroom.id} value={classroom.id}>
                            {classroom.name}
                          </option>
                        ))}
                      </select>
                      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-outline" />
                    </div>
                    <span className="text-xs text-outline">
                      {scope === "system"
                        ? "Phạm vi Hệ thống không gắn với lớp cụ thể, nên không cần chọn lớp."
                        : "Chọn lớp để đề chỉ hiển thị cho học viên trong lớp đó."}
                    </span>
                  </label>

                  <label className="flex flex-col gap-1.5">
                    <span className={labelClass}>Thời lượng làm bài</span>
                    <input
                      type="number"
                      min={1}
                      value={durationMinutes}
                      onChange={(event) => setDurationMinutes(event.target.value)}
                      className={inputClass}
                    />
                  </label>

                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
                    <label className="flex flex-col gap-1.5">
                      <span className={labelClass}>Bắt đầu</span>
                      <input
                        type="datetime-local"
                        value={startTime}
                        onChange={(event) => setStartTime(event.target.value)}
                        className={inputClass}
                      />
                    </label>
                    <label className="flex flex-col gap-1.5">
                      <span className={labelClass}>Kết thúc</span>
                      <input
                        type="datetime-local"
                        value={endTime}
                        onChange={(event) => setEndTime(event.target.value)}
                        className={inputClass}
                      />
                    </label>
                  </div>

                </div>
              </section>
            </div>
          )}

          {activeTab === "questions" && (
            <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
              <section className={`${cardClass} p-4 space-y-4`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-on-surface">
                    Danh sách câu hỏi
                  </span>
                  <span className="text-xs font-semibold text-outline">
                    {questions.length} câu
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={addQuestion}
                    className="flex items-center gap-1 rounded-[6px] bg-primary px-3 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-primary/90 cursor-pointer"
                  >
                    <Plus className="size-3.5" />
                    <span>Thêm câu hỏi</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => toast.info("Tính năng thêm bằng văn bản sẽ được bổ sung sau.")}
                    className="flex cursor-pointer items-center gap-1 rounded-[6px] border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs font-bold text-on-surface hover:bg-surface-container-low"
                  >
                    <ClipboardList className="size-3.5" />
                    <span>Thêm bằng văn bản</span>
                  </button>
                </div>

                <div className="flex max-h-[calc(100vh-18rem)] flex-wrap gap-1.5 overflow-y-auto pt-1 pr-1">
                  {questions.length === 0 ? (
                    <div className="my-4 w-full text-center text-xs font-medium text-outline">
                      Không tìm thấy câu hỏi nào!
                    </div>
                  ) : (
                    questions.map((question, index) => {
                      const isSelected = question.id === selectedQuestion?.id;

                      return (
                        <button
                          key={question.id}
                          type="button"
                          onClick={() => setSelectedQuestionId(question.id)}
                          className={`flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-[4px] text-xs font-bold transition-all ${
                            isSelected
                              ? "bg-primary text-white shadow-sm"
                              : "border border-outline-variant bg-surface-container-lowest text-on-surface hover:bg-surface-container-low"
                          }`}
                        >
                          {index + 1}
                        </button>
                      );
                    })
                  )}
                </div>
              </section>

              <section className={`${cardClass} overflow-hidden`}>
                {selectedQuestion ? (
                  <>
                    <div className="flex flex-col gap-2 border-b border-outline-variant px-4 py-4 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <h2 className="text-lg font-semibold text-on-surface">
                          {selectedQuestion.prompt.trim() ? "Chỉnh sửa câu hỏi" : "Thêm câu hỏi mới"}
                        </h2>
                        <p className={mutedClass}>
                          Câu {selectedQuestionIndex + 1} trong Phần 1
                        </p>
                      </div>
                      <button
                        type="button"
                        disabled={questions.length === 1}
                        onClick={() => removeQuestion(selectedQuestion.id)}
                        className="flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-semibold text-error hover:bg-error-container disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <Trash2 className="h-4 w-4" />
                        Xóa câu hỏi
                      </button>
                    </div>

                    <div className="space-y-5 p-4">
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-[minmax(0,360px)_140px]">
                        <label className="flex flex-col gap-1.5">
                          <span className={labelClass}>Loại câu hỏi</span>
                          <div className="relative">
                            <select
                              value={selectedQuestion.question_type}
                              onChange={(event) =>
                                updateQuestion(selectedQuestion.id, {
                                  question_type: event.target.value as AdminExamQuestionType,
                                })
                              }
                              className={selectClass}
                            >
                              <option value="single_choice">Một đáp án</option>
                              <option value="true_false">Đúng / Sai</option>
                              <option value="short_answer">Trả lời ngắn</option>
                            </select>
                            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-outline" />
                          </div>
                        </label>

                        <label className="flex flex-col gap-1.5">
                          <span className={labelClass}>Điểm</span>
                          <input
                            type="number"
                            min={0.25}
                            step={0.25}
                            value={selectedQuestion.points}
                            onChange={(event) =>
                              updateQuestion(selectedQuestion.id, { points: event.target.value })
                            }
                            className={inputClass}
                          />
                        </label>
                      </div>

                      <div>
                        <h3 className="mb-3 text-base font-semibold text-on-surface">Soạn câu hỏi</h3>
                        <label className="flex flex-col gap-1.5">
                          <span className={labelClass}>
                            Nội dung câu hỏi <span className="text-error">*</span>
                          </span>
                          <textarea
                            value={selectedQuestion.prompt}
                            onChange={(event) =>
                              updateQuestion(selectedQuestion.id, { prompt: event.target.value })
                            }
                            rows={7}
                            placeholder="Nhập nội dung câu hỏi"
                            className={`${inputClass} min-h-[168px] resize-y`}
                          />
                        </label>
                      </div>

                      <div>
                        <div className="mb-3 flex items-center justify-between gap-3">
                          <h3 className="text-base font-semibold text-on-surface">Câu trả lời</h3>
                          {selectedQuestion.question_type === "single_choice" && (
                            <button
                              type="button"
                              disabled={selectedQuestion.options.length >= OPTION_KEYS.length}
                              onClick={() => addOption(selectedQuestion.id)}
                              className="flex items-center justify-center gap-2 rounded-md border border-outline-variant px-3 py-2 text-sm font-semibold text-on-surface hover:bg-surface-container-low disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              <Plus className="h-4 w-4" />
                              Thêm đáp án
                            </button>
                          )}
                        </div>

                        {selectedQuestion.question_type === "single_choice" && (
                          <div className="space-y-3">
                            {selectedQuestion.options.map((option, optionIndex) => (
                              <div
                                key={`${selectedQuestion.id}-${option.option_key}`}
                                className="rounded-md border border-outline-variant bg-surface-container-lowest p-3"
                              >
                                <div className="mb-2 flex items-center justify-between gap-3">
                                  <label className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-on-surface">
                                    <input
                                      type="radio"
                                      name={`correct-${selectedQuestion.id}`}
                                      checked={selectedQuestion.correctOptionIndex === optionIndex}
                                      onChange={() =>
                                        updateQuestion(selectedQuestion.id, {
                                          correctOptionIndex: optionIndex,
                                        })
                                      }
                                      className="h-4 w-4 accent-primary"
                                    />
                                    Đáp án {optionIndex + 1}
                                  </label>
                                  <button
                                    type="button"
                                    disabled={selectedQuestion.options.length <= 2}
                                    onClick={() => removeOption(selectedQuestion.id, optionIndex)}
                                    className="flex items-center gap-1 rounded-md px-2 py-1 text-sm font-semibold text-error hover:bg-error-container disabled:cursor-not-allowed disabled:opacity-40"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                    Xóa đáp án
                                  </button>
                                </div>
                                <input
                                  value={option.option_text}
                                  onChange={(event) =>
                                    updateOption(selectedQuestion.id, optionIndex, {
                                      option_text: event.target.value,
                                    })
                                  }
                                  placeholder={`Nhập đáp án ${option.option_key}`}
                                  className={inputClass}
                                />
                              </div>
                            ))}
                          </div>
                        )}

                        {selectedQuestion.question_type === "true_false" && (
                          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                            {trueFalseOptions.map((answer) => (
                              <label
                                key={answer.value}
                                className="flex cursor-pointer items-center gap-2 rounded-md border border-outline-variant px-3 py-3 text-sm font-semibold text-on-surface"
                              >
                                <input
                                  type="radio"
                                  name={`tf-${selectedQuestion.id}`}
                                  checked={selectedQuestion.trueFalseAnswer === answer.value}
                                  onChange={() =>
                                    updateQuestion(selectedQuestion.id, {
                                      trueFalseAnswer: answer.value,
                                    })
                                  }
                                  className="h-4 w-4 accent-primary"
                                />
                                {answer.label}
                              </label>
                            ))}
                          </div>
                        )}

                        {selectedQuestion.question_type === "short_answer" && (
                          <label className="flex flex-col gap-1.5">
                            <span className={labelClass}>Đáp án chấp nhận</span>
                            <textarea
                              value={selectedQuestion.acceptedAnswersText}
                              onChange={(event) =>
                                updateQuestion(selectedQuestion.id, {
                                  acceptedAnswersText: event.target.value,
                                })
                              }
                              rows={4}
                              placeholder="Mỗi dòng là một đáp án đúng"
                              className={`${inputClass} resize-y`}
                            />
                          </label>
                        )}
                      </div>

                      <label className="flex flex-col gap-1.5">
                        <span className={labelClass}>Giải thích</span>
                        <textarea
                          value={selectedQuestion.explanation}
                          onChange={(event) =>
                            updateQuestion(selectedQuestion.id, {
                              explanation: event.target.value,
                            })
                          }
                          rows={3}
                          placeholder="Giải thích sau khi làm bài"
                          className={`${inputClass} resize-y`}
                        />
                      </label>
                    </div>

                    <div className="flex justify-end border-t border-outline-variant px-4 py-3">
                      <button
                        type="button"
                        onClick={saveSelectedQuestion}
                        className="flex items-center justify-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-on-primary hover:bg-primary/90"
                      >
                        <Save className="h-4 w-4" />
                        Lưu câu hỏi
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="p-8 text-center text-sm text-outline">
                    Không tìm thấy câu hỏi nào.
                  </div>
                )}
              </section>
            </div>
          )}

          {activeTab === "advanced" && (
            <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-12">
              <div className="lg:col-span-8">
                <div className="rounded-[10px] border border-outline-variant bg-surface-container-lowest shadow-sm">
                  <div className="flex items-center gap-3 border-b border-outline-variant p-4">
                    <div className="flex size-9 shrink-0 items-center justify-center rounded-[8px] bg-primary/10 text-primary">
                      <ListChecks className="size-4" />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-on-surface">
                        Xem lại danh sách câu hỏi
                      </p>
                      <p className="text-xs text-outline">
                        Kiểm tra nhanh nội dung và đáp án trước khi lưu đề thi.
                      </p>
                    </div>
                  </div>

                  <div className="space-y-4 p-4 divide-y divide-outline-variant/40">
                    {questions.length === 0 ? (
                      <div className="py-16 text-center text-xs font-medium text-outline">
                        Chưa có câu hỏi nào trong đề thi.
                      </div>
                    ) : (
                      questions.map((question, questionIndex) => {
                        const isChoice = question.question_type === "single_choice";
                        const isTrueFalse = question.question_type === "true_false";
                        const isShortAnswer = question.question_type === "short_answer";

                        return (
                          <div
                            key={question.id}
                            className="space-y-3 rounded-[8px] border border-outline-variant bg-surface p-4 first:mt-0 mt-4"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex min-w-0 flex-wrap items-center gap-2">
                                <span className="inline-flex items-center rounded-[4px] bg-primary/10 px-2.5 py-0.5 text-[11px] font-bold text-primary">
                                  Câu {questionIndex + 1}
                                </span>
                                <span className="inline-flex items-center rounded-[4px] border border-outline-variant bg-surface-container-low px-2.5 py-0.5 text-[11px] font-medium text-outline">
                                  {questionTypeLabels[question.question_type]}
                                </span>
                              </div>
                              <div className="inline-flex shrink-0 items-center gap-1.5 rounded-[6px] border border-outline-variant bg-surface-container-low px-2.5 py-1 text-xs font-semibold text-on-surface">
                                <FileCheck className="size-3.5 text-primary" />
                                {question.points} điểm
                              </div>
                            </div>

                            <p className="text-sm font-semibold text-on-surface whitespace-pre-wrap">
                              {question.prompt || "Chưa nhập nội dung câu hỏi"}
                            </p>

                            {isChoice && (
                              <div className="space-y-1.5">
                                <p className="text-[11px] font-bold uppercase tracking-wide text-outline">
                                  Đáp án
                                </p>
                                <div className="grid gap-1.5 sm:grid-cols-2">
                                  {question.options.map((option, optionIndex) => {
                                    const isCorrect = question.correctOptionIndex === optionIndex;
                                    return (
                                      <div
                                        key={option.option_key}
                                        className={`flex items-start gap-2 rounded-[6px] border px-3 py-2 text-xs ${
                                          isCorrect
                                            ? "border-success/30 bg-success/10 text-success"
                                            : "border-outline-variant bg-surface-container-lowest text-on-surface-variant"
                                        }`}
                                      >
                                        <span className="shrink-0 font-bold">
                                          {option.option_key || String.fromCharCode(65 + optionIndex)}
                                        </span>
                                        <p className={isCorrect ? "font-semibold" : ""}>
                                          {option.option_text || "Chưa nhập nội dung đáp án"}
                                        </p>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}

                            {isTrueFalse && (
                              <div className="space-y-1.5">
                                <p className="text-[11px] font-bold uppercase tracking-wide text-outline">
                                  Đáp án
                                </p>
                                <div className="grid gap-1.5 sm:grid-cols-2">
                                  {[
                                    { label: "Đúng", value: "true" },
                                    { label: "Sai", value: "false" }
                                  ].map((opt) => {
                                    const isCorrect = question.trueFalseAnswer === opt.value;
                                    return (
                                      <div
                                        key={opt.value}
                                        className={`flex items-start gap-2 rounded-[6px] border px-3 py-2 text-xs ${
                                          isCorrect
                                            ? "border-success/30 bg-success/10 text-success"
                                            : "border-outline-variant bg-surface-container-lowest text-on-surface-variant"
                                        }`}
                                      >
                                        <p className={isCorrect ? "font-semibold" : ""}>
                                          {opt.label}
                                        </p>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}

                            {isShortAnswer && (
                              <div className="space-y-1.5">
                                <p className="text-[11px] font-bold uppercase tracking-wide text-outline">
                                  Đáp án chấp nhận
                                </p>
                                <div className="flex flex-wrap gap-1.5">
                                  {splitAcceptedAnswers(question.acceptedAnswersText).map((ans, aIdx) => (
                                    <span
                                      key={aIdx}
                                      className="inline-flex items-center rounded border border-success/30 bg-success/10 px-2 py-0.5 text-xs font-semibold text-success"
                                    >
                                      {ans}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>

              <div className="lg:col-span-4">
                <aside className={`${cardClass} h-fit p-4`}>
                  <div className="flex items-center gap-2">
                    <CalendarClock className="h-4 w-4 text-primary" />
                    <h2 className="text-base font-semibold text-on-surface">Tóm tắt</h2>
                  </div>
                  <div className="mt-4 space-y-3 text-sm">
                    <div className="flex justify-between gap-4">
                      <span className="text-outline">Phạm vi</span>
                      <span className="font-semibold text-on-surface">
                        {scope === "system" ? "Hệ thống" : "Trong lớp"}
                      </span>
                    </div>
                    {scope === "class" && (
                      <div className="flex justify-between gap-4">
                        <span className="text-outline">Lớp học</span>
                        <span className="font-semibold text-on-surface">
                          {classes.find((c) => String(c.id) === classroomId)?.name || "Chưa chọn"}
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between gap-4">
                      <span className="text-outline">Câu hỏi</span>
                      <span className="font-semibold text-on-surface">{questions.length}</span>
                    </div>
                    <div className="flex justify-between gap-4">
                      <span className="text-outline">Tổng điểm</span>
                      <span className="font-semibold text-on-surface">{totalPoints}</span>
                    </div>
                    <div className="flex justify-between gap-4">
                      <span className="text-outline">Thời lượng</span>
                      <span className="font-semibold text-on-surface">
                        {durationMinutes || 0} phút
                      </span>
                    </div>
                  </div>
                </aside>
              </div>
            </div>
          )}
      </form>
    </div>
  );
}
