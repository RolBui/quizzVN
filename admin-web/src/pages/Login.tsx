import { FormEvent, useState } from "react";
import { AlertCircle, Eye, EyeOff, Loader2 } from "lucide-react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import loginIllustration from "../assets/auth-login-illustration.png";
import { ApiError, getGoogleLoginUrl } from "../lib/api";
import { useAuth } from "../lib/auth";

interface LocationState {
  from?: {
    pathname?: string;
  };
}

type AdminOauthNotice = {
  tone: "success" | "warning" | "error";
  message: string;
};

function getAdminOauthNotice(
  status: string | null,
  email: string | null,
): AdminOauthNotice | null {
  const emailLabel = email ? ` cho ${email}` : "";

  if (status === "verification_email_sent") {
    return {
      tone: "success",
      message: `Đã gửi email xác thực quản trị${emailLabel}. Vui lòng mở email, nhập OTP rồi chờ Administrator duyệt quyền.`,
    };
  }

  if (status === "pending_approval") {
    return {
      tone: "warning",
      message: `Yêu cầu quản trị${emailLabel} đang chờ Administrator duyệt.`,
    };
  }
  if (status === "admin_email_exists") {
    const existingEmailLabel = email ? `Email ${email}` : "Email này";
    return {
      tone: "warning",
      message: `${existingEmailLabel} đã có tài khoản quản trị. Vui lòng đăng nhập bằng email và mật khẩu đã được cấp. Nếu cần đăng ký lại, Administrator gốc phải xóa tài khoản cũ trước.`,
    };
  }

  if (status === "admin_disabled") {
    return {
      tone: "error",
      message: `Tài khoản quản trị${emailLabel} đang bị vô hiệu hóa.`,
    };
  }

  if (status === "google_state_mismatch") {
    return {
      tone: "error",
      message:
        "Phiên đăng nhập Google đã hết hạn hoặc bị lệch host. Vui lòng bấm đăng ký Google lại.",
    };
  }

  if (status === "google_user_info_not_found") {
    return {
      tone: "error",
      message: "Không lấy được thông tin Google. Vui lòng thử lại.",
    };
  }

  return null;
}

function GoogleMark() {
  return (
    <svg className="h-8 w-8" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}
export function Login() {
  const { user, isCheckingSession, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LocationState | null;
  const searchParams = new URLSearchParams(location.search);
  const adminOauthNotice = getAdminOauthNotice(
    searchParams.get("admin_oauth"),
    searchParams.get("email"),
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const isFormReady = email.trim().length > 0 && password.trim().length > 0;

  if (
    !isCheckingSession &&
    (user?.role_name === "administrator" || user?.role_name === "admin")
  ) {
    return <Navigate to="/" replace />;
  }

  const handleGoogleRegistration = () => {
    setIsGoogleLoading(true);
    window.location.href = getGoogleLoginUrl();
  };
  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login(email, password);
      toast.success("Đăng nhập thành công.", { toastId: "login-success" });
      navigate(state?.from?.pathname || "/", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Email hoặc mật khẩu không đúng.");
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Không thể đăng nhập. Vui lòng thử lại.");
      }
      const toastMessage =
        err instanceof ApiError && err.status === 401
          ? "Email hoặc mật khẩu không đúng."
          : err instanceof Error
            ? err.message
            : "Không thể đăng nhập. Vui lòng thử lại.";
      toast.error(toastMessage, { toastId: "login-error" });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-white font-sans text-on-surface lg:grid lg:grid-cols-[minmax(0,1.65fr)_minmax(520px,1fr)]">
      <section
        className="relative hidden min-h-screen overflow-hidden bg-[#edf4ff] lg:block"
        aria-hidden="true"
      >
        <img
          src={loginIllustration}
          alt=""
          className="absolute inset-0 h-full w-full object-cover object-left"
        />
      </section>

      <section className="flex min-h-screen items-center justify-center px-6 py-10 sm:px-10 lg:px-16">
        <div className="w-full max-w-[500px]">
          <div className="mb-7">
            <h1 className="text-[28px] font-semibold leading-tight text-[#222222]">
              Đăng nhập
            </h1>
            <p className="mt-2 max-w-[420px] text-sm leading-6 text-on-surface-variant">
              Đăng nhập bằng tài khoản đã được cấp, hoặc gửi yêu cầu đăng ký
              quản trị .
            </p>
          </div>

          {error && (
            <div className="mb-6 flex items-start gap-3 rounded-[8px] border border-error-container bg-error-container/60 px-4 py-3 text-sm text-on-error-container">
              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {adminOauthNotice && (
            <div
              className={[
                "mb-6 flex items-start gap-3 rounded-[8px] border px-4 py-3 text-sm leading-6",
                adminOauthNotice.tone === "success"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                  : adminOauthNotice.tone === "warning"
                    ? "border-amber-200 bg-amber-50 text-amber-800"
                    : "border-error-container bg-error-container/60 text-on-error-container",
              ].join(" ")}
            >
              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
              <span>{adminOauthNotice.message}</span>
            </div>
          )}

          <div className="mb-7 space-y-5">
            <button
              type="button"
              onClick={handleGoogleRegistration}
              disabled={isGoogleLoading}
              className="relative flex h-[56px] w-full items-center justify-center rounded-[8px] bg-[linear-gradient(90deg,#3478ff_0%,#6557f5_54%,#d63cf4_100%)] px-5 text-base font-semibold text-white shadow-[0_8px_18px_rgba(103,85,245,0.28)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_10px_22px_rgba(103,85,245,0.34)] disabled:cursor-not-allowed disabled:opacity-75 disabled:hover:translate-y-0 disabled:hover:shadow-none"
            >
              <span className="absolute left-8 flex h-8 w-8 items-center justify-center">
                {isGoogleLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <GoogleMark />
                )}
              </span>
              {isGoogleLoading
                ? "Đang chuyển hướng..."
                : "Đăng ký quản trị bằng Google"}
            </button>

            <div className="flex items-center gap-3 text-sm text-[#2e2e2e]">
              <div className="h-px flex-1 bg-[#e0e0e0]" />
              <span className="shrink-0">
                hoặc đăng nhập bằng tài khoản được cấp
              </span>
              <div className="h-px flex-1 bg-[#e0e0e0]" />
            </div>
          </div>
          <form onSubmit={handleSubmit} className="space-y-7">
            <label className="block">
              <span className="text-base font-medium text-[#4b3f5d]">
                Tài khoản đăng nhập
              </span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="Nhập tài khoản hoặc email"
                autoComplete="email"
                required
                className="mt-3 h-[52px] w-full rounded-[8px] border border-[#aeb8d4] bg-white px-4 text-base text-on-surface outline-none transition-colors placeholder:text-[#9f9f9f] hover:border-[#8795bd] focus:border-[#7788c7]"
              />
            </label>

            <label className="block">
              <span className="text-base font-medium text-[#4b3f5d]">
                Mật khẩu
              </span>
              <div className="relative mt-3">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Nhập mật khẩu của bạn"
                  autoComplete="current-password"
                  required
                  className="h-[52px] w-full rounded-[8px] border border-[#aeb8d4] bg-white px-4 pr-12 text-base text-on-surface outline-none transition-colors placeholder:text-[#9f9f9f] hover:border-[#8795bd] focus:border-[#7788c7]"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((current) => !current)}
                  aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[#c527ff] transition-colors hover:text-[#8f2fe8]"
                >
                  {showPassword ? (
                    <EyeOff className="h-6 w-6" />
                  ) : (
                    <Eye className="h-6 w-6" />
                  )}
                </button>
              </div>
            </label>

            <button
              type="submit"
              disabled={isSubmitting || !isFormReady}
              className={[
                "mt-10 flex h-[50px] w-full items-center justify-center gap-2 rounded-[6px] text-lg font-semibold text-white transition-all duration-200",
                isFormReady && !isSubmitting
                  ? "bg-[linear-gradient(90deg,#3478ff_0%,#6557f5_54%,#d63cf4_100%)] shadow-[0_8px_18px_rgba(103,85,245,0.28)] hover:-translate-y-0.5 hover:shadow-[0_10px_22px_rgba(103,85,245,0.34)]"
                  : "bg-[linear-gradient(90deg,#94b4ff_0%,#cfc0ff_52%,#efc3f6_100%)] opacity-70",
                "disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-none",
              ].join(" ")}
            >
              {isSubmitting && <Loader2 className="h-5 w-5 animate-spin" />}
              Đăng nhập
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}
