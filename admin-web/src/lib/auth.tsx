import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { ApiError, authApi, type AuthUser } from "./api";

interface AuthContextValue {
  user: AuthUser | null;
  isCheckingSession: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function isAdminUser(user: AuthUser | null) {
  return (
    user?.status === "active" &&
    (user.role_name === "administrator" || user.role_name === "admin")
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  const refreshSession = useCallback(async () => {
    try {
      const response = await authApi.me();
      setUser(response.user);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setUser(null);
        return;
      }
      setUser(null);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    authApi
      .me()
      .then((response) => {
        if (isMounted) {
          setUser(response.user);
        }
      })
      .catch(() => {
        if (isMounted) {
          setUser(null);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsCheckingSession(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await authApi.login(email, password);
    if (!isAdminUser(response.user)) {
      try {
        await authApi.logout();
      } catch {
        // The backend may already have rejected or expired the session.
      }
      setUser(null);
      throw new Error("Tài khoản này chưa được Administrator cấp quyền quản trị.");
    }
    setUser(response.user);
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      isCheckingSession,
      login,
      logout,
      refreshSession,
    }),
    [user, isCheckingSession, login, logout, refreshSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}

export function RequireAdmin() {
  const { user, isCheckingSession } = useAuth();
  const location = useLocation();

  if (isCheckingSession) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center font-sans text-on-surface">
        <div className="flex items-center gap-3 text-sm text-on-surface-variant">
          <div className="h-5 w-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          Đang kiểm tra phiên đăng nhập...
        </div>
      </div>
    );
  }

  if (!isAdminUser(user)) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
