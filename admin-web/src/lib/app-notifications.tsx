import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type AppNotificationType =
  | "admin"
  | "document_import"
  | "document_export"
  | "data_export"
  | "system";

export type NotificationPreferenceKey = "messages" | AppNotificationType;

export type NotificationPreferences = Record<
  NotificationPreferenceKey,
  boolean
>;

export interface AppNotification {
  id: string;
  type: AppNotificationType;
  title: string;
  body: string;
  createdAt: string;
  read: boolean;
}

interface NewAppNotification {
  type?: AppNotificationType;
  title: string;
  body?: string;
}

interface AppNotificationsContextValue {
  notifications: AppNotification[];
  notificationPreferences: NotificationPreferences;
  unreadCount: number;
  addNotification: (notification: NewAppNotification) => void;
  markNotificationsRead: () => void;
  clearNotifications: () => void;
  replaceNotificationPreferences: (
    preferences: NotificationPreferences,
  ) => void;
  setNotificationPreference: (
    key: NotificationPreferenceKey,
    enabled: boolean,
  ) => void;
}

const STORAGE_KEY = "quizzvn-admin-notifications";
const PREFERENCES_STORAGE_KEY = "quizzvn-admin-notification-preferences";
const MAX_NOTIFICATIONS = 30;
export const defaultNotificationPreferences: NotificationPreferences = {
  messages: true,
  admin: true,
  document_import: true,
  document_export: true,
  data_export: true,
  system: true,
};

const AppNotificationsContext =
  createContext<AppNotificationsContextValue | null>(null);

function readStoredNotifications() {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(
      (item): item is AppNotification =>
        typeof item?.id === "string" &&
        typeof item?.title === "string" &&
        typeof item?.createdAt === "string",
    );
  } catch {
    return [];
  }
}

function saveNotifications(notifications: AppNotification[]) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications));
}

function readStoredPreferences() {
  if (typeof window === "undefined") {
    return defaultNotificationPreferences;
  }

  try {
    const raw = window.localStorage.getItem(PREFERENCES_STORAGE_KEY);
    if (!raw) {
      return defaultNotificationPreferences;
    }
    const parsed = JSON.parse(raw) as Partial<NotificationPreferences>;
    return {
      ...defaultNotificationPreferences,
      ...parsed,
    };
  } catch {
    return defaultNotificationPreferences;
  }
}

function savePreferences(preferences: NotificationPreferences) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(
    PREFERENCES_STORAGE_KEY,
    JSON.stringify(preferences),
  );
}

export function AppNotificationsProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [notifications, setNotifications] = useState<AppNotification[]>(
    readStoredNotifications,
  );
  const [notificationPreferences, setNotificationPreferences] =
    useState<NotificationPreferences>(readStoredPreferences);

  const addNotification = useCallback((notification: NewAppNotification) => {
    const type = notification.type ?? "system";
    if (!notificationPreferences[type]) {
      return;
    }

    const item: AppNotification = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      type,
      title: notification.title,
      body: notification.body ?? "",
      createdAt: new Date().toISOString(),
      read: false,
    };

    setNotifications((current) => {
      const next = [item, ...current].slice(0, MAX_NOTIFICATIONS);
      saveNotifications(next);
      return next;
    });
  }, [notificationPreferences]);

  const replaceNotificationPreferences = useCallback(
    (preferences: NotificationPreferences) => {
      setNotificationPreferences(preferences);
      savePreferences(preferences);
    },
    [],
  );

  const setNotificationPreference = useCallback(
    (key: NotificationPreferenceKey, enabled: boolean) => {
      setNotificationPreferences((current) => {
        const next = { ...current, [key]: enabled };
        savePreferences(next);
        return next;
      });
    },
    [],
  );

  const markNotificationsRead = useCallback(() => {
    setNotifications((current) => {
      if (current.every((item) => item.read)) {
        return current;
      }
      const next = current.map((item) => ({ ...item, read: true }));
      saveNotifications(next);
      return next;
    });
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
    saveNotifications([]);
  }, []);

  const unreadCount = useMemo(
    () =>
      notifications.filter(
        (item) => !item.read && notificationPreferences[item.type],
      ).length,
    [notifications, notificationPreferences],
  );

  const value = useMemo(
    () => ({
      notifications,
      notificationPreferences,
      unreadCount,
      addNotification,
      markNotificationsRead,
      clearNotifications,
      replaceNotificationPreferences,
      setNotificationPreference,
    }),
    [
      notifications,
      notificationPreferences,
      unreadCount,
      addNotification,
      markNotificationsRead,
      clearNotifications,
      replaceNotificationPreferences,
      setNotificationPreference,
    ],
  );

  return (
    <AppNotificationsContext.Provider value={value}>
      {children}
    </AppNotificationsContext.Provider>
  );
}

export function useAppNotifications() {
  const context = useContext(AppNotificationsContext);
  if (!context) {
    throw new Error(
      "useAppNotifications must be used inside AppNotificationsProvider",
    );
  }
  return context;
}
