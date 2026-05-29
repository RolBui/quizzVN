import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  chatApi,
  type ChatConversation,
  type ChatMessage,
} from "./api";
import { useAuth } from "./auth";

interface ChatNotificationsContextValue {
  notificationConversations: ChatConversation[];
  notificationCount: number;
  totalUnread: number;
  clearNotificationBadge: () => void;
  refreshNotifications: () => Promise<void>;
  markConversationRead: (conversationId: number) => void;
  setActiveConversationId: (conversationId: number | null) => void;
}

const ChatNotificationsContext =
  createContext<ChatNotificationsContextValue | null>(null);

function updateConversationForMessage(
  conversation: ChatConversation,
  message: ChatMessage,
  currentUserId: number,
  activeConversationId: number | null,
) {
  const isActiveConversation = conversation.id === activeConversationId;
  const isOwnMessage = message.sender_id === currentUserId;
  const alreadyApplied = conversation.last_message?.id === message.id;
  return {
    ...conversation,
    last_message: {
      ...message,
      is_own: isOwnMessage,
    },
    unread_count: alreadyApplied
      ? conversation.unread_count
      : isOwnMessage || isActiveConversation
        ? 0
        : conversation.unread_count + 1,
    updated_at: message.created_at,
  };
}

export function ChatNotificationsProvider({
  children,
}: {
  children: ReactNode;
}) {
  const { user } = useAuth();
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [incomingMessageIds, setIncomingMessageIds] = useState<Set<number>>(
    () => new Set(),
  );
  const socketRef = useRef<WebSocket | null>(null);
  const activeConversationIdRef = useRef<number | null>(null);

  const refreshNotifications = useCallback(async () => {
    if (!user) {
      setConversations([]);
      setIncomingMessageIds(new Set());
      return;
    }
    const response = await chatApi.listConversations();
    setConversations(response.items);
  }, [user]);

  const clearNotificationBadge = useCallback(() => {
    setIncomingMessageIds(new Set());
  }, []);

  const markConversationRead = useCallback((conversationId: number) => {
    activeConversationIdRef.current = conversationId;
    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === conversationId
          ? { ...conversation, unread_count: 0 }
          : conversation,
      ),
    );
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(
        JSON.stringify({ type: "mark_read", conversation_id: conversationId }),
      );
    }
  }, []);

  const setActiveConversationId = useCallback((conversationId: number | null) => {
    activeConversationIdRef.current = conversationId;
    if (conversationId !== null) {
      markConversationRead(conversationId);
    }
  }, [markConversationRead]);

  useEffect(() => {
    void refreshNotifications();
  }, [refreshNotifications]);

  useEffect(() => {
    if (!user) {
      return undefined;
    }

    const handleFocus = () => {
      void refreshNotifications();
    };
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        void refreshNotifications();
      }
    };

    window.addEventListener("focus", handleFocus);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      window.removeEventListener("focus", handleFocus);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [refreshNotifications, user]);

  useEffect(() => {
    if (!user) {
      return undefined;
    }

    let socket: WebSocket | null = null;
    let connectTimeout: number | null = null;
    let reconnectTimeout: number | null = null;
    let reconnectAttempt = 0;
    let isDisposed = false;

    const scheduleReconnect = () => {
      if (isDisposed) {
        return;
      }
      if (reconnectTimeout !== null) {
        window.clearTimeout(reconnectTimeout);
      }
      const delay = Math.min(1000 * 2 ** reconnectAttempt, 5000);
      reconnectAttempt += 1;
      reconnectTimeout = window.setTimeout(connect, delay);
    };

    const connect = () => {
      if (isDisposed) {
        return;
      }
      socket = new WebSocket(chatApi.websocketUrl());
      socketRef.current = socket;

      socket.onopen = () => {
        if (!socket || socketRef.current !== socket) {
          return;
        }
        reconnectAttempt = 0;
        void refreshNotifications();
      };

      socket.onclose = () => {
        if (!socket || socketRef.current !== socket) {
          return;
        }
        socketRef.current = null;
        scheduleReconnect();
      };

      socket.onerror = () => {
        if (!socket || socketRef.current !== socket) {
          return;
        }
        socket.close();
      };

      socket.onmessage = (event) => {
        if (!socket || socketRef.current !== socket) {
          return;
        }
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "message_deleted") {
            window.dispatchEvent(
              new CustomEvent("chat:message_deleted", {
                detail: {
                  conversation_id: payload.conversation_id,
                  message_id: payload.message_id,
                },
              }),
            );
            setIncomingMessageIds((current) => {
              if (!current.has(payload.message_id)) {
                return current;
              }
              const next = new Set(current);
              next.delete(payload.message_id);
              return next;
            });
            void refreshNotifications();
            return;
          }
          if (payload.type !== "message_created") {
            return;
          }

          const incoming = payload.message as ChatMessage;
          window.dispatchEvent(
            new CustomEvent("chat:message_created", { detail: incoming }),
          );

          if (incoming.sender_id !== user.id) {
            setIncomingMessageIds((current) => {
              if (current.has(incoming.id)) {
                return current;
              }
              const next = new Set(current);
              next.add(incoming.id);
              return next;
            });
          }

          const isActiveConversation =
            incoming.conversation_id === activeConversationIdRef.current;

          setConversations((current) => {
            let didUpdate = false;
            const next = current.map((conversation) => {
              if (conversation.id !== incoming.conversation_id) {
                return conversation;
              }
              didUpdate = true;
              return updateConversationForMessage(
                conversation,
                incoming,
                user.id,
                activeConversationIdRef.current,
              );
            });

            if (!didUpdate) {
              void refreshNotifications();
              return current;
            }

            return next.sort(
              (first, second) =>
                new Date(second.updated_at).getTime() -
                new Date(first.updated_at).getTime(),
            );
          });

          if (
            isActiveConversation &&
            incoming.sender_id !== user.id
          ) {
            socket.send(
              JSON.stringify({
                type: "mark_read",
                conversation_id: incoming.conversation_id,
              }),
            );
          }
        } catch {
          // Keep notifications quiet; the Chat page still owns visible errors.
        }
      };
    };

    connectTimeout = window.setTimeout(connect, 0);

    return () => {
      isDisposed = true;
      if (connectTimeout !== null) {
        window.clearTimeout(connectTimeout);
      }
      if (reconnectTimeout !== null) {
        window.clearTimeout(reconnectTimeout);
      }
      if (socket) {
        socket.close();
      }
      if (socket && socketRef.current === socket) {
        socketRef.current = null;
      }
    };
  }, [refreshNotifications, user]);

  const totalUnread = useMemo(
    () =>
      conversations.reduce(
        (total, conversation) => total + conversation.unread_count,
        0,
      ),
    [conversations],
  );
  const notificationCount = Math.max(totalUnread, incomingMessageIds.size);
  const notificationConversations = useMemo(
    () =>
      conversations
        .filter((conversation) => conversation.unread_count > 0)
        .slice(0, 5),
    [conversations],
  );

  const value = useMemo(
    () => ({
      notificationConversations,
      notificationCount,
      totalUnread,
      clearNotificationBadge,
      refreshNotifications,
      markConversationRead,
      setActiveConversationId,
    }),
    [
      notificationConversations,
      notificationCount,
      totalUnread,
      incomingMessageIds,
      clearNotificationBadge,
      refreshNotifications,
      markConversationRead,
      setActiveConversationId,
    ],
  );

  return (
    <ChatNotificationsContext.Provider value={value}>
      {children}
    </ChatNotificationsContext.Provider>
  );
}

export function useChatNotifications() {
  const context = useContext(ChatNotificationsContext);
  if (!context) {
    throw new Error(
      "useChatNotifications must be used inside ChatNotificationsProvider",
    );
  }
  return context;
}
