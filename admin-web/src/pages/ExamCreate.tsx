import { type ChangeEvent, type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import {
  AlertCircle,
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  Info,
  Loader2,
  Plus,
  Save,
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
import examCover1Url from "../assets/exam-cover-1.jpeg";
import examCover2Url from "../assets/exam-cover-2.jpeg";
import examCover3Url from "../assets/exam-cover-3.jpeg";
import examCover4Url from "../assets/exam-cover-4.jpeg";

type ExamScope = "system" | "class";
type ExamCreateTab = "basic" | "questions" | "advanced";

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
  { key: "basic", label: "Thông tin cơ bản" },
  { key: "questions", label: "Soạn câu hỏi" },
  { key: "advanced", label: "Cài đặt nâng cao" },
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

const examCoverPresets = [
  { label: "Ảnh 1", src: examCover1Url },
  { label: "Ảnh 2", src: examCover2Url },
  { label: "Ảnh 3", src: examCover3Url },
  { label: "Ảnh 4", src: examCover4Url },
];

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
  const [activeTab, setActiveTab] = useState<ExamCreateTab>("basic");
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null);

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

  const handleSubmit = async (publish: boolean) => {
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    setError(null);
    const payload: CreateAdminExamPayload = {
      title: title.trim(),
      description: description.trim() || null,
      grade: grade.trim(),
      image_url: imageUrl.trim() || null,
      scope,
      classroom_id: scope === "class" ? Number(classroomId) : null,
      duration_minutes: Number(durationMinutes),
      start_time: toIsoDateTime(startTime),
      end_time: toIsoDateTime(endTime),
      is_published: publish,
      is_active: publish,
      questions: questions.map(buildQuestionPayload),
    };

    try {
      await adminApi.createExam(payload);
      toast.success(publish ? "Đã tạo và xuất bản đề thi." : "Đã lưu nháp đề thi.");
      navigate("/exams");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tạo được đề thi.");
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
            <h1 className="text-xl font-bold text-on-surface">Tạo đề thi mới</h1>
            <p className={mutedClass}>Thiết lập thông tin, lịch làm bài và câu hỏi cho đề thi.</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => void handleSubmit(false)}
            className="flex items-center justify-center gap-2 rounded-md border border-outline-variant bg-surface-container-lowest px-4 py-2 text-sm font-semibold text-on-surface hover:bg-surface-container-low disabled:opacity-60"
          >
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Lưu nháp
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => void handleSubmit(true)}
            className="flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-on-primary shadow-sm hover:bg-primary/90 disabled:opacity-60"
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <CheckCircle2 className="h-4 w-4" />
            )}
            Xuất bản
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 flex items-start gap-2 rounded-md border border-error-container bg-error-container/60 px-4 py-3 text-sm text-on-error-container">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className={`${cardClass} mb-4 w-fit max-w-full overflow-hidden`}>
        <div className="flex min-w-0 overflow-x-auto pt-1">
          {examCreateTabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`shrink-0 border-b-2 px-5 py-2.5 text-sm font-semibold transition-colors ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-outline hover:text-on-surface"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <form
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            void handleSubmit(true);
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
                        className="h-full w-full object-cover"
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
                            className="h-full w-full object-cover"
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
            <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
              <section className={`${cardClass} overflow-hidden`}>
                <div className="flex items-center justify-between gap-3 px-4 py-4">
                  <h2 className="text-base font-semibold text-on-surface">Danh sách phần thi</h2>
                  <button
                    type="button"
                    onClick={() => toast.info("Phần thi sẽ được bổ sung khi backend hỗ trợ lưu nhiều phần.")}
                    className="rounded-md px-2 py-1 text-sm font-semibold text-primary hover:bg-primary-container"
                  >
                    Thêm mới
                  </button>
                </div>
                <div className="px-4 pb-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-on-primary"
                    >
                      Phần 1
                    </button>
                    <button
                      type="button"
                      className="flex h-9 w-9 items-center justify-center rounded-md text-primary hover:bg-primary-container"
                      aria-label="Chỉnh sửa phần thi"
                    >
                      <ClipboardList className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                <div className="border-t border-outline-variant px-4 py-4">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <h3 className="text-base font-semibold text-on-surface">Danh mục câu hỏi</h3>
                    <span className="text-sm text-outline">{questions.length} câu</span>
                  </div>
                  <div className="mb-4 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-1">
                    <button
                      type="button"
                      onClick={addQuestion}
                      className="flex items-center justify-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-on-primary hover:bg-primary/90"
                    >
                      <Plus className="h-4 w-4" />
                      Thêm câu hỏi
                    </button>
                    <button
                      type="button"
                      onClick={() => toast.info("Tính năng thêm bằng văn bản sẽ được bổ sung sau.")}
                      className="flex items-center justify-center gap-2 rounded-md border border-outline-variant bg-surface-container-lowest px-3 py-2 text-sm font-semibold text-on-surface hover:bg-surface-container-low"
                    >
                      <ClipboardList className="h-4 w-4" />
                      Thêm bằng văn bản
                    </button>
                  </div>

                  <div className="space-y-2">
                    {questions.map((question, questionIndex) => {
                      const isSelected = question.id === selectedQuestion?.id;
                      const preview = question.prompt.trim() || "Chưa nhập nội dung câu hỏi";
                      return (
                        <button
                          key={question.id}
                          type="button"
                          onClick={() => setSelectedQuestionId(question.id)}
                          className={`w-full rounded-md border px-3 py-3 text-left transition-colors ${
                            isSelected
                              ? "border-primary bg-primary-container/60"
                              : "border-outline-variant bg-surface-container-lowest hover:bg-surface-container-low"
                          }`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-sm font-semibold text-on-surface">
                                Câu {questionIndex + 1}
                              </p>
                              <p className="mt-1 line-clamp-2 text-sm text-outline">{preview}</p>
                            </div>
                            <span className="shrink-0 rounded-full bg-surface-container-high px-2 py-1 text-xs font-semibold text-outline">
                              {question.points || 0}đ
                            </span>
                          </div>
                          <p className="mt-2 text-xs font-medium text-primary">
                            {questionTypeLabels[question.question_type]}
                          </p>
                        </button>
                      );
                    })}
                  </div>
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
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
              <section className={cardClass}>
                <div className="border-b border-outline-variant px-4 py-3">
                  <h2 className="text-base font-semibold text-on-surface">Lịch và phạm vi</h2>
                </div>
                <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2">
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

                  <div className="hidden md:block" />

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
              </section>

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
          )}
      </form>
    </div>
  );
}
