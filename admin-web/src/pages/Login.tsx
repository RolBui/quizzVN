import { FormEvent, useState } from "react";
import { AlertCircle, Loader2, Lock, Mail } from "lucide-react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";

interface LocationState {
  from?: {
    pathname?: string;
  };
}

export function Login() {
  const { user, isCheckingSession, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LocationState | null;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (
    !isCheckingSession &&
    (user?.role_name === "administrator" || user?.role_name === "admin")
  ) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login(email, password);
      navigate(state?.from?.pathname || "/", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Email hoặc mật khẩu không đúng.");
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Không thể đăng nhập. Vui lòng thử lại.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background font-sans text-on-surface flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-105">
        <div className="mb-8 flex items-center gap-3">
          <div>
            <h1 className="text-xl font-black leading-tight">QuizzVN Admin</h1>
            <p className="text-sm text-on-surface-variant">
              Đăng nhập quản trị
            </p>
          </div>
        </div>

        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl shadow-(--shadow-level-1) p-6">
          <div className="mb-6">
            <h2 className="text-2xl font-bold tracking-tight">Đăng nhập</h2>
            <p className="text-sm text-on-surface-variant mt-1">
              Chỉ tài khoản do Administrator cấp mới vào được hệ thống.
            </p>
          </div>

          {error && (
            <div className="mb-5 flex items-start gap-3 rounded-lg border border-error-container bg-error-container/60 px-4 py-3 text-sm text-on-error-container">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <label className="block">
              <span className="text-sm font-semibold text-on-surface">
                Email
              </span>
              <div className="relative mt-2">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-outline" />
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="admin@example.com"
                  autoComplete="email"
                  required
                  className="w-full h-11 rounded-lg border border-outline-variant bg-surface-container-low pl-10 pr-3 text-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary placeholder:text-outline"
                />
              </div>
            </label>

            <label className="block">
              <span className="text-sm font-semibold text-on-surface">
                Mật khẩu
              </span>
              <div className="relative mt-2">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-outline" />
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Nhập mật khẩu"
                  autoComplete="current-password"
                  required
                  className="w-full h-11 rounded-lg border border-outline-variant bg-surface-container-low pl-10 pr-3 text-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary placeholder:text-outline"
                />
              </div>
            </label>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-11 rounded-lg bg-primary text-on-primary font-semibold text-sm flex items-center justify-center gap-2 hover:bg-primary/90 disabled:opacity-70 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              Đăng nhập
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
