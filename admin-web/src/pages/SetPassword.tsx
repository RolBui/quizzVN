import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Eye,
  EyeOff,
  Loader2,
} from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "react-toastify";
import loginIllustration from "../assets/auth-login-illustration.png";
import { ApiError, authApi, type PasswordSetupTokenResponse } from "../lib/api";

function getSetupErrorMessage(error: unknown) {
  const message = error instanceof Error ? error.message : "";

  switch (message) {
    case "password_setup_token_required":
      return "Thiếu mã đặt mật khẩu. Vui lòng mở lại liên kết trong email.";
    case "password_setup_token_invalid":
      return "Liên kết đặt mật khẩu không hợp lệ.";
    case "password_setup_token_used":
      return "Liên kết này đã được sử dụng.";
    case "password_setup_token_revoked":
      return "Liên kết này đã bị vô hiệu hóa do có liên kết mới hơn.";
    case "password_setup_token_expired":
      return "Liên kết đã hết hạn. Vui lòng liên hệ Administrator để gửi lại.";
    case "admin_account_disabled":
      return "Tài khoản quản trị đang bị vô hiệu hóa.";
    case "password_setup_password_mismatch":
      return "Mật khẩu nhập lại không khớp.";
    case "password_setup_password_too_short":
      return "Mật khẩu mới phải có ít nhất 6 ký tự.";
    default:
      if (error instanceof ApiError) {
        return message || "Không thể kiểm tra liên kết đặt mật khẩu.";
      }
      return "Không thể kết nối máy chủ. Vui lòng thử lại.";
  }
}

function formatExpiry(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toLocaleString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function SetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token")?.trim() ?? "";
  const [account, setAccount] = useState<PasswordSetupTokenResponse | null>(
    null,
  );
  const [isChecking, setIsChecking] = useState(true);
  const [checkError, setCheckError] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function checkToken() {
      setIsChecking(true);
      setCheckError(null);
      try {
        if (!token) {
          throw new ApiError(400, "password_setup_token_required");
        }
        const response = await authApi.getAdminPasswordSetupToken(token);
        if (isMounted) {
          setAccount(response);
        }
      } catch (error) {
        if (isMounted) {
          setCheckError(getSetupErrorMessage(error));
        }
      } finally {
        if (isMounted) {
          setIsChecking(false);
        }
      }
    }

    checkToken();

    return () => {
      isMounted = false;
    };
  }, [token]);

  const expiryLabel = useMemo(
    () => (account ? formatExpiry(account.expires_at) : null),
    [account],
  );
  const isPasswordReady =
    newPassword.length >= 6 && confirmPassword.length >= 6;
  const passwordsMatch =
    newPassword.length > 0 &&
    confirmPassword.length > 0 &&
    newPassword === confirmPassword;
  const canSubmit =
    Boolean(account) &&
    !isComplete &&
    isPasswordReady &&
    passwordsMatch &&
    !isSubmitting;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!account) {
      return;
    }
    if (newPassword.length < 6) {
      toast.error("Mật khẩu mới phải có ít nhất 6 ký tự.");
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error("Mật khẩu nhập lại không khớp.");
      return;
    }

    setIsSubmitting(true);
    try {
      await authApi.completeAdminPasswordSetup({
        token,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setIsComplete(true);
      toast.success("Đặt mật khẩu thành công.");
    } catch (error) {
      toast.error(getSetupErrorMessage(error));
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
              Tạo mật khẩu
            </h1>
            <p className="mt-2 max-w-[430px] text-sm leading-6 text-on-surface-variant">
              Đặt mật khẩu quản trị để đăng nhập QuizzVN bằng tài khoản email.
            </p>
          </div>

          {isChecking && (
            <div className="flex items-center gap-3 rounded-[8px] border border-[#dbe4ff] bg-[#f3f6ff] px-4 py-3 text-sm text-[#314273]">
              <Loader2 className="h-5 w-5 animate-spin" />
              Đang kiểm tra liên kết...
            </div>
          )}

          {!isChecking && checkError && (
            <div className="rounded-[8px] border border-error-container bg-error-container/60 px-4 py-4 text-sm leading-6 text-on-error-container">
              <div className="flex items-start gap-3">
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
                <span>{checkError}</span>
              </div>
              <Link
                to="/login"
                className="mt-4 inline-flex h-10 items-center justify-center rounded-[6px] border border-[#cbd5e1] px-4 text-sm font-semibold text-[#334155] transition-colors hover:bg-[#f8fafc]"
              >
                Quay lại đăng nhập
              </Link>
            </div>
          )}

          {!isChecking && account && isComplete && (
            <div className="rounded-[8px] border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm leading-6 text-emerald-800">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
                <span>
                  Mật khẩu quản trị đã được tạo thành công. Bạn có thể đăng
                  nhập bằng email {account.email}.
                </span>
              </div>
              <Link
                to="/login"
                className="mt-4 inline-flex h-10 items-center justify-center rounded-[6px] bg-[linear-gradient(90deg,#3478ff_0%,#6557f5_54%,#d63cf4_100%)] px-4 text-sm font-semibold text-white shadow-[0_8px_18px_rgba(103,85,245,0.28)]"
              >
                Đến trang đăng nhập
              </Link>
            </div>
          )}

          {!isChecking && account && !isComplete && (
            <form onSubmit={handleSubmit} className="space-y-7">
              <div className="rounded-[8px] border border-[#dbe4ff] bg-[#f8faff] px-4 py-4">
                <p className="text-sm font-semibold text-[#4b3f5d]">
                  Tài khoản quản trị
                </p>
                <p className="mt-1 text-lg font-bold text-[#111827]">
                  {account.full_name || account.email}
                </p>
                <p className="mt-1 text-sm text-on-surface-variant">
                  {account.email}
                </p>
                {expiryLabel && (
                  <p className="mt-3 text-xs font-medium text-[#9a3412]">
                    Liên kết có hiệu lực đến {expiryLabel}.
                  </p>
                )}
              </div>

              <label className="block">
                <span className="text-base font-medium text-[#4b3f5d]">
                  Mật khẩu mới
                </span>
                <div className="relative mt-3">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    placeholder="Tối thiểu 6 ký tự"
                    autoComplete="new-password"
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

              <label className="block">
                <span className="text-base font-medium text-[#4b3f5d]">
                  Nhập lại mật khẩu mới
                </span>
                <div className="relative mt-3">
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="Nhập lại mật khẩu mới"
                    autoComplete="new-password"
                    required
                    className="h-[52px] w-full rounded-[8px] border border-[#aeb8d4] bg-white px-4 pr-12 text-base text-on-surface outline-none transition-colors placeholder:text-[#9f9f9f] hover:border-[#8795bd] focus:border-[#7788c7]"
                  />
                  <button
                    type="button"
                    onClick={() =>
                      setShowConfirmPassword((current) => !current)
                    }
                    aria-label={
                      showConfirmPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"
                    }
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-[#c527ff] transition-colors hover:text-[#8f2fe8]"
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="h-6 w-6" />
                    ) : (
                      <Eye className="h-6 w-6" />
                    )}
                  </button>
                </div>
                {confirmPassword.length > 0 && !passwordsMatch && (
                  <span className="mt-2 block text-sm text-error">
                    Mật khẩu nhập lại không khớp.
                  </span>
                )}
              </label>

              <button
                type="submit"
                disabled={!canSubmit}
                className={[
                  "mt-10 flex h-[50px] w-full items-center justify-center gap-2 rounded-[6px] text-lg font-semibold text-white transition-all duration-200",
                  canSubmit
                    ? "bg-[linear-gradient(90deg,#3478ff_0%,#6557f5_54%,#d63cf4_100%)] shadow-[0_8px_18px_rgba(103,85,245,0.28)] hover:-translate-y-0.5 hover:shadow-[0_10px_22px_rgba(103,85,245,0.34)]"
                    : "bg-[linear-gradient(90deg,#94b4ff_0%,#cfc0ff_52%,#efc3f6_100%)] opacity-70",
                  "disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-none",
                ].join(" ")}
              >
                {isSubmitting && <Loader2 className="h-5 w-5 animate-spin" />}
                {isSubmitting ? "Đang lưu..." : "Tạo mật khẩu"}
              </button>
            </form>
          )}
        </div>
      </section>
    </main>
  );
}
