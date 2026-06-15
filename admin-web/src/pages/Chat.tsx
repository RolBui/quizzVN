import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  FileText,
  Forward,
  MoreHorizontal,
  Paperclip,
  Phone,
  Pin,
  Search,
  Send,
  Trash2,
  Video,
  X,
} from "lucide-react";
import {
  ApiError,
  chatApi,
  type ChatConversation,
  type ChatMessage,
  type ChatUser,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { useChatNotifications } from "../lib/chat-notifications";
import { initials } from "../lib/format";
import { useLocation } from "react-router-dom";

type SocketState = "connecting" | "connected" | "disconnected";
type ConversationMenuState = {
  id: number;
  top: number;
  left: number;
};
type DeletedMessageEvent = {
  conversation_id: number;
  message_id: number;
};
type ChatRouteState = {
  conversationId?: number;
} | null;
type ChatTimelineMessage = ChatMessage & {
  local_file_url?: string | null;
  upload_progress?: number;
  upload_status?: "uploading";
};

function roleLabel(roleName: string | null) {
  if (roleName === "teacher") {
    return "Giáo viên";
  }
  if (roleName === "student") {
    return "Học sinh";
  }
  if (roleName === "administrator") {
    return "Administrator";
  }
  if (roleName === "admin") {
    return "Admin";
  }
  return "Người dùng";
}

function formatTime(value: string | null | undefined) {
  if (!value) {
    return "";
  }
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatConversationTime(value: string | null | undefined) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  const today = new Date();
  const isToday = date.toDateString() === today.toDateString();
  if (isToday) {
    return formatTime(value);
  }
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
  }).format(date);
}

function formatFileSize(value: number | null | undefined) {
  if (!value) {
    return "";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function isImageAttachment(message: ChatMessage) {
  return Boolean(message.attachment_content_type?.startsWith("image/"));
}

function isUploadingMessage(message: ChatTimelineMessage) {
  return message.upload_status === "uploading";
}

function fileExtensionLabel(filename: string | null, contentType: string | null) {
  if (contentType === "application/pdf") {
    return "PDF";
  }
  const extension = filename?.split(".").pop()?.trim().toUpperCase();
  return extension ? extension.slice(0, 4) : "FILE";
}

function isSameLocalDay(first: Date, second: Date) {
  return first.toDateString() === second.toDateString();
}

function formatTimelineLabel(value: string) {
  const date = new Date(value);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);

  let dayLabel = new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
  if (isSameLocalDay(date, today)) {
    dayLabel = "Hôm nay";
  } else if (isSameLocalDay(date, yesterday)) {
    dayLabel = "Hôm qua";
  }

  return `${formatTime(value)} ${dayLabel}`;
}

function shouldShowTimelineLabel(
  message: ChatMessage,
  previousMessage: ChatMessage | undefined,
) {
  if (!previousMessage) {
    return true;
  }
  const currentDate = new Date(message.created_at);
  const previousDate = new Date(previousMessage.created_at);
  if (!isSameLocalDay(currentDate, previousDate)) {
    return true;
  }
  return currentDate.getTime() - previousDate.getTime() >= 30 * 60 * 1000;
}

function Avatar({ user, size = "md" }: { user: ChatUser; size?: "sm" | "md" | "lg" }) {
  const sizeClass = size === "lg" ? "w-24 h-24 text-2xl" : size === "sm" ? "w-9 h-9 text-xs" : "w-12 h-12 text-sm";
  if (user.avatar_url) {
    return (
      <img
        src={user.avatar_url}
        alt={user.full_name}
        className={`${sizeClass} rounded-full object-cover border border-outline-variant/30`}
      />
    );
  }
  return (
    <div className={`${sizeClass} rounded-full bg-primary-fixed-dim text-on-primary-fixed flex items-center justify-center font-bold border border-outline-variant/30`}>
      {initials(user.full_name)}
    </div>
  );
}

function conversationName(conversation: ChatConversation, currentUserId: number | undefined) {
  if (conversation.title) {
    return conversation.title;
  }
  const peer = conversation.participants.find((participant) => participant.id !== currentUserId);
  return peer?.full_name || "Cuộc trò chuyện";
}

function conversationPreview(conversation: ChatConversation) {
  if (!conversation.last_message) {
    return "Bắt đầu cuộc trò chuyện";
  }
  if (conversation.last_message.attachment_url) {
    return conversation.last_message.attachment_filename || conversation.last_message.body || "Tệp đính kèm";
  }
  return conversation.last_message.body;
}

function conversationPeer(conversation: ChatConversation | null, currentUserId: number | undefined) {
  if (!conversation) {
    return null;
  }
  return conversation.participants.find((participant) => participant.id !== currentUserId) || conversation.participants[0] || null;
}

export function Chat() {
  const { user } = useAuth();
  const location = useLocation();
  const requestedConversationId =
    (location.state as ChatRouteState)?.conversationId ?? null;
  const {
    markConversationRead,
    refreshNotifications,
    setActiveConversationId,
  } = useChatNotifications();
  const [query, setQuery] = useState("");
  const [isConversationListCollapsed, setIsConversationListCollapsed] = useState(false);
  const [isMobileConversationOpen, setIsMobileConversationOpen] = useState(
    Boolean(requestedConversationId),
  );
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [contacts, setContacts] = useState<ChatUser[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatTimelineMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isUploadingAttachment, setIsUploadingAttachment] = useState(false);
  const [socketState, setSocketState] = useState<SocketState>("disconnected");
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [openConversationMenu, setOpenConversationMenu] = useState<ConversationMenuState | null>(null);
  const [deletingConversationId, setDeletingConversationId] = useState<number | null>(null);
  const [activeMessageActionId, setActiveMessageActionId] = useState<number | null>(null);
  const [deletingMessageId, setDeletingMessageId] = useState<number | null>(null);
  const [sharingMessage, setSharingMessage] = useState<ChatTimelineMessage | null>(null);
  const [isSharingMessage, setIsSharingMessage] = useState(false);
  const [hiddenConversationIds, setHiddenConversationIds] = useState<Set<number>>(new Set());
  const [hiddenContactIds, setHiddenContactIds] = useState<Set<number>>(new Set());
  const [pinnedConversationIds, setPinnedConversationIds] = useState<Set<number>>(new Set());
  const [onlineUserIds, setOnlineUserIds] = useState<Set<number>>(new Set());
  const socketRef = useRef<WebSocket | null>(null);
  const selectedConversationRef = useRef<number | null>(null);
  const conversationIdsRef = useRef<Set<number>>(new Set());
  const hiddenConversationIdsRef = useRef<Set<number>>(new Set());
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const actionHoldTimerRef = useRef<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const pinnedStorageKey = user?.id ? `quizzvn:chat:pinned:${user.id}` : null;
  const hiddenContactsStorageKey = user?.id ? `quizzvn:chat:hidden-contacts:${user.id}` : null;

  useEffect(() => {
    function handleClickOutside() {
      setOpenConversationMenu(null);
      setActiveMessageActionId(null);
    }
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, []);

  useEffect(() => {
    const mobileMedia = window.matchMedia("(max-width: 767px)");
    const resetCollapsedListOnMobile = () => {
      if (mobileMedia.matches) {
        setIsConversationListCollapsed(false);
      }
    };

    resetCollapsedListOnMobile();
    mobileMedia.addEventListener("change", resetCollapsedListOnMobile);
    return () =>
      mobileMedia.removeEventListener("change", resetCollapsedListOnMobile);
  }, []);

  useEffect(() => {
    return () => {
      if (actionHoldTimerRef.current !== null) {
        window.clearTimeout(actionHoldTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!pinnedStorageKey) {
      setPinnedConversationIds(new Set());
      return;
    }

    try {
      const rawValue = window.localStorage.getItem(pinnedStorageKey);
      const parsedValue = rawValue ? JSON.parse(rawValue) : [];
      const ids = Array.isArray(parsedValue)
        ? parsedValue.filter((id): id is number => typeof id === "number")
        : [];
      setPinnedConversationIds(new Set(ids));
    } catch {
      setPinnedConversationIds(new Set());
    }
  }, [pinnedStorageKey]);

  useEffect(() => {
    if (!hiddenContactsStorageKey) {
      setHiddenContactIds(new Set());
      return;
    }

    try {
      const rawValue = window.localStorage.getItem(hiddenContactsStorageKey);
      const parsedValue = rawValue ? JSON.parse(rawValue) : [];
      const ids = Array.isArray(parsedValue)
        ? parsedValue.filter((id): id is number => typeof id === "number")
        : [];
      setHiddenContactIds(new Set(ids));
    } catch {
      setHiddenContactIds(new Set());
    }
  }, [hiddenContactsStorageKey]);

  useEffect(() => {
    selectedConversationRef.current = selectedConversationId;
  }, [selectedConversationId]);

  useEffect(() => {
    if (requestedConversationId) {
      setIsMobileConversationOpen(true);
    }
  }, [requestedConversationId]);

  useEffect(() => {
    hiddenConversationIdsRef.current = hiddenConversationIds;
  }, [hiddenConversationIds]);

  useEffect(() => {
    conversationIdsRef.current = new Set(
      conversations.map((conversation) => conversation.id),
    );
  }, [conversations]);

  useEffect(() => {
    return () => setActiveConversationId(null);
  }, [setActiveConversationId]);

  useEffect(() => {
    setActiveConversationId(selectedConversationId);
    if (selectedConversationId) {
      setConversations((current) =>
        current.map((conversation) =>
          conversation.id === selectedConversationId
            ? { ...conversation, unread_count: 0 }
            : conversation,
        ),
      );
    }
  }, [selectedConversationId, setActiveConversationId]);

  const refreshConversations = useCallback(async () => {
    const response = await chatApi.listConversations();
    const visibleItems = response.items.filter(
      (conversation) => !hiddenConversationIdsRef.current.has(conversation.id),
    );
    setConversations(visibleItems);
    if (!selectedConversationRef.current && visibleItems.length) {
      const requestedConversation = visibleItems.find(
        (conversation) => conversation.id === requestedConversationId,
      );
      setSelectedConversationId(requestedConversation?.id ?? visibleItems[0].id);
    }
  }, [requestedConversationId]);

  const refreshContacts = useCallback(async (search = "") => {
    const response = await chatApi.listContacts(search);
    setContacts(response.items);
  }, []);

  const syncSelectedConversation = useCallback(async () => {
    const conversationId = selectedConversationRef.current;
    if (!conversationId || !user) {
      return;
    }

    const [messageResponse, conversationResponse] = await Promise.all([
      chatApi.listMessages(conversationId),
      chatApi.listConversations(),
    ]);
    setMessages(
      messageResponse.items.map((message) => ({
        ...message,
        is_own: message.sender_id === user.id,
      })),
    );
    setConversations(
      conversationResponse.items.filter(
        (conversation) => !hiddenConversationIdsRef.current.has(conversation.id),
      ),
    );
    markConversationRead(conversationId);
  }, [markConversationRead, user]);

  const handleMessageCreated = useCallback(
    (incoming: ChatMessage) => {
      if (!user) {
        return;
      }

      const normalizedMessage = {
        ...incoming,
        is_own: incoming.sender_id === user.id,
      };
      if (selectedConversationRef.current === incoming.conversation_id) {
        setMessages((current) => {
          if (current.some((message) => message.id === incoming.id)) {
            return current;
          }
          const pendingIndex = current.findIndex(
            (message) =>
              message.upload_status === "uploading" &&
              message.conversation_id === incoming.conversation_id &&
              message.attachment_filename === incoming.attachment_filename &&
              message.attachment_size_bytes === incoming.attachment_size_bytes,
          );
          if (pendingIndex >= 0) {
            const next = [...current];
            next[pendingIndex] = normalizedMessage;
            return next;
          }
          return [...current, normalizedMessage];
        });
        if (incoming.sender_id !== user.id) {
          markConversationRead(incoming.conversation_id);
        }
      }
      const shouldRefreshConversations = !conversationIdsRef.current.has(
        incoming.conversation_id,
      );
      setConversations((current) => {
        const next = current.map((conversation) => {
          if (conversation.id !== incoming.conversation_id) {
            return conversation;
          }
          const isSelected =
            selectedConversationRef.current === incoming.conversation_id;
          const isOwnMessage = incoming.sender_id === user.id;
          const alreadyApplied = conversation.last_message?.id === incoming.id;
          const unreadCount = alreadyApplied
            ? conversation.unread_count
            : isSelected || isOwnMessage
              ? 0
              : conversation.unread_count + 1;
          return {
            ...conversation,
            last_message: normalizedMessage,
            unread_count: unreadCount,
            updated_at: incoming.created_at,
          };
        });

        if (shouldRefreshConversations) {
          return current;
        }

        return next.sort(
          (first, second) =>
            new Date(second.updated_at).getTime() -
            new Date(first.updated_at).getTime(),
        );
      });
      if (shouldRefreshConversations) {
        void refreshConversations();
      }
    },
    [markConversationRead, refreshConversations, user],
  );

  const handleMessageDeleted = useCallback(
    (conversationId: number, messageId: number) => {
      if (selectedConversationRef.current === conversationId) {
        setMessages((current) =>
          current.filter((message) => message.id !== messageId),
        );
      }
      setActiveMessageActionId((current) =>
        current === messageId ? null : current,
      );
      setSharingMessage((current) =>
        current?.id === messageId ? null : current,
      );
      void refreshConversations();
      void refreshNotifications();
    },
    [refreshConversations, refreshNotifications],
  );

  useEffect(() => {
    let isMounted = true;
    Promise.all([chatApi.listConversations(), chatApi.listContacts()])
      .then(([conversationResponse, contactResponse]) => {
        if (!isMounted) {
          return;
        }
        const visibleItems = conversationResponse.items.filter(
          (conversation) => !hiddenConversationIdsRef.current.has(conversation.id),
        );
        setConversations(visibleItems);
        setContacts(contactResponse.items);
        if (visibleItems.length) {
          const requestedConversation = visibleItems.find(
            (conversation) => conversation.id === requestedConversationId,
          );
          setSelectedConversationId(requestedConversation?.id ?? visibleItems[0].id);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Không thể tải tin nhắn.");
        }
      });
    return () => {
      isMounted = false;
    };
  }, [requestedConversationId]);

  useEffect(() => {
    const handleGlobalMessageCreated = (event: Event) => {
      const incoming = (event as CustomEvent<ChatMessage>).detail;
      if (incoming) {
        handleMessageCreated(incoming);
      }
    };
    const handleGlobalMessageDeleted = (event: Event) => {
      const detail = (event as CustomEvent<DeletedMessageEvent>).detail;
      if (detail) {
        handleMessageDeleted(detail.conversation_id, detail.message_id);
      }
    };

    window.addEventListener("chat:message_created", handleGlobalMessageCreated);
    window.addEventListener("chat:message_deleted", handleGlobalMessageDeleted);
    return () => {
      window.removeEventListener(
        "chat:message_created",
        handleGlobalMessageCreated,
      );
      window.removeEventListener(
        "chat:message_deleted",
        handleGlobalMessageDeleted,
      );
    };
  }, [handleMessageCreated, handleMessageDeleted]);

  useEffect(() => {
    if (!user) {
      return undefined;
    }

    setSocketState("connecting");
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
      setSocketState("connecting");
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
        setSocketState("connected");
        setError(null);
        reconnectAttempt = 0;
        void refreshConversations();
        void syncSelectedConversation();
      };
      socket.onclose = (event) => {
        if (!socket || socketRef.current !== socket) {
          return;
        }
        setSocketState("disconnected");
        socketRef.current = null;
        if (event.code === 1008) {
          console.warn("Chat realtime authentication was rejected.");
          return;
        }
        scheduleReconnect();
      };
      socket.onerror = () => {
        if (!socket || socketRef.current !== socket) {
          return;
        }
        setSocketState("disconnected");
        socket.close();
      };
      socket.onmessage = (event) => {
        if (!socket || socketRef.current !== socket) {
          return;
        }
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "presence_snapshot") {
            setOnlineUserIds(new Set(payload.user_ids || []));
            return;
          }
          if (payload.type === "presence_changed") {
            setOnlineUserIds((current) => {
              const next = new Set(current);
              if (payload.is_online) {
                next.add(payload.user_id);
              } else {
                next.delete(payload.user_id);
              }
              return next;
            });
            return;
          }
          if (payload.type === "message_created") {
            handleMessageCreated(payload.message as ChatMessage);
            return;
          }
          if (payload.type === "message_deleted") {
            handleMessageDeleted(payload.conversation_id, payload.message_id);
            return;
          }
          if (payload.type === "error") {
            setError(payload.detail || "Socket chat bị lỗi.");
          }
        } catch {
          setError("Không đọc được dữ liệu realtime.");
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
  }, [
    handleMessageCreated,
    handleMessageDeleted,
    refreshConversations,
    syncSelectedConversation,
    user,
  ]);

  useEffect(() => {
    if (!selectedConversationId || !user) {
      setMessages([]);
      return;
    }

    let isMounted = true;
    setIsLoadingMessages(true);
    chatApi
      .listMessages(selectedConversationId)
      .then((response) => {
        if (isMounted) {
          setMessages(
            response.items.map((message) => ({
              ...message,
              is_own: message.sender_id === user.id,
            })),
          );
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Không thể tải lịch sử tin nhắn.");
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoadingMessages(false);
        }
      });

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({ type: "mark_read", conversation_id: selectedConversationId }),
      );
    }
    markConversationRead(selectedConversationId);
    void refreshConversations();

    return () => {
      isMounted = false;
    };
  }, [markConversationRead, refreshConversations, selectedConversationId, user]);

  useEffect(() => {
    if (!user) {
      return undefined;
    }

    const syncChatState = () => {
      void refreshConversations();
      void refreshNotifications();
      void syncSelectedConversation();
    };
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        syncChatState();
      }
    };

    window.addEventListener("focus", syncChatState);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.removeEventListener("focus", syncChatState);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [refreshConversations, refreshNotifications, syncSelectedConversation, user]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, selectedConversationId]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void refreshContacts(query);
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [query, refreshContacts]);

  const selectedConversation = useMemo(
    () =>
      conversations.find((conversation) => conversation.id === selectedConversationId) ||
      null,
    [conversations, selectedConversationId],
  );
  const selectedPeer = conversationPeer(selectedConversation, user?.id);
  const timelineMessages = useMemo(
    () =>
      messages.map((message, index) => ({
        message,
        showTimeline: shouldShowTimelineLabel(message, messages[index - 1]),
      })),
    [messages],
  );
  const sharedFiles = useMemo(
    () => messages.filter((message) => Boolean(message.attachment_url)).slice().reverse(),
    [messages],
  );

  const visibleConversations = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const filteredConversations = normalizedQuery
      ? conversations.filter((conversation) => {
      const name = conversationName(conversation, user?.id).toLowerCase();
      const lastMessage = conversation.last_message?.body.toLowerCase() || "";
      return name.includes(normalizedQuery) || lastMessage.includes(normalizedQuery);
        })
      : conversations;

    return [...filteredConversations].sort((first, second) => {
      const firstPinned = pinnedConversationIds.has(first.id);
      const secondPinned = pinnedConversationIds.has(second.id);
      if (firstPinned !== secondPinned) {
        return firstPinned ? -1 : 1;
      }
      return (
        new Date(second.updated_at).getTime() -
        new Date(first.updated_at).getTime()
      );
    });
  }, [conversations, pinnedConversationIds, query, user?.id]);

  const visibleContacts = useMemo(() => {
    const existingPeerIds = new Set(
      conversations
        .map((conversation) => conversationPeer(conversation, user?.id)?.id)
        .filter((id): id is number => typeof id === "number"),
    );
    return contacts.filter(
      (contact) =>
        !existingPeerIds.has(contact.id) && !hiddenContactIds.has(contact.id),
    );
  }, [contacts, conversations, hiddenContactIds, user?.id]);
  const shareTargets = useMemo(() => {
    const targetMap = new Map<number, ChatUser>();
    visibleConversations.forEach((conversation) => {
      if (conversation.id === selectedConversationId) {
        return;
      }
      const peer = conversationPeer(conversation, user?.id);
      if (peer && peer.id !== user?.id) {
        targetMap.set(peer.id, peer);
      }
    });
    return Array.from(targetMap.values());
  }, [selectedConversationId, user?.id, visibleConversations]);
  const shouldShowContacts = query.trim().length > 0 || visibleConversations.length === 0;

  function savePinnedConversationIds(nextIds: Set<number>) {
    if (!pinnedStorageKey) {
      return;
    }
    window.localStorage.setItem(
      pinnedStorageKey,
      JSON.stringify(Array.from(nextIds)),
    );
  }

  function saveHiddenContactIds(nextIds: Set<number>) {
    if (!hiddenContactsStorageKey) {
      return;
    }
    window.localStorage.setItem(
      hiddenContactsStorageKey,
      JSON.stringify(Array.from(nextIds)),
    );
  }

  function togglePinConversation(conversationId: number) {
    setPinnedConversationIds((current) => {
      const next = new Set(current);
      if (next.has(conversationId)) {
        next.delete(conversationId);
      } else {
        next.add(conversationId);
      }
      savePinnedConversationIds(next);
      return next;
    });
    setOpenConversationMenu(null);
  }

  async function startConversation(contact: ChatUser) {
    try {
      setError(null);
      const response = await chatApi.createConversation(contact.id);
      setHiddenContactIds((current) => {
        if (!current.has(contact.id)) {
          return current;
        }
        const next = new Set(current);
        next.delete(contact.id);
        saveHiddenContactIds(next);
        return next;
      });
      setHiddenConversationIds((current) => {
        if (!current.has(response.conversation.id)) {
          return current;
        }
        const next = new Set(current);
        next.delete(response.conversation.id);
        hiddenConversationIdsRef.current = next;
        return next;
      });
      setConversations((current) => {
        const withoutDuplicate = current.filter(
          (conversation) => conversation.id !== response.conversation.id,
        );
        return [response.conversation, ...withoutDuplicate];
      });
      setSelectedConversationId(response.conversation.id);
      setIsMobileConversationOpen(true);
      void refreshNotifications();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể tạo cuộc trò chuyện.");
    }
  }

  async function sendMessage(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedConversationId) {
      return;
    }
    const body = draft.trim();
    if (!body) {
      return;
    }

    setDraft("");
    setError(null);
    try {
      const response = await chatApi.sendMessage(selectedConversationId, body);
      const message = {
        ...response.message,
        is_own: response.message.sender_id === user?.id,
      };
      setMessages((current) => {
        if (current.some((item) => item.id === message.id)) {
          return current;
        }
        return [...current, message];
      });
      await refreshConversations();
      await refreshNotifications();
    } catch (err) {
      setDraft(body);
      setError(err instanceof Error ? err.message : "Không thể gửi tin nhắn.");
    }
  }

  async function sendAttachment(file: File) {
    if (!selectedConversationId || isUploadingAttachment) {
      return;
    }

    const caption = draft.trim();
    const localMessageId = -Date.now();
    const localFileUrl = file.type.startsWith("image/")
      ? window.URL.createObjectURL(file)
      : null;
    const pendingMessage: ChatTimelineMessage = {
      id: localMessageId,
      conversation_id: selectedConversationId,
      sender_id: user?.id ?? 0,
      sender_name: user?.full_name || "Bạn",
      sender_avatar_url: user?.avatar_url || null,
      body: caption || file.name,
      attachment_url: null,
      attachment_filename: file.name,
      attachment_content_type: file.type || "application/octet-stream",
      attachment_size_bytes: file.size,
      created_at: new Date().toISOString(),
      is_own: true,
      local_file_url: localFileUrl,
      upload_progress: 12,
      upload_status: "uploading",
    };
    setDraft("");
    setError(null);
    setIsUploadingAttachment(true);
    setMessages((current) => [...current, pendingMessage]);
    let progressTimer: number | null = window.setInterval(() => {
      setMessages((current) =>
        current.map((message) =>
          message.id === localMessageId
            ? {
                ...message,
                upload_progress: Math.min(
                  (message.upload_progress || 12) + 8,
                  92,
                ),
              }
            : message,
        ),
      );
    }, 260);
    try {
      const response = await chatApi.sendAttachment(selectedConversationId, file, caption);
      const message = {
        ...response.message,
        is_own: response.message.sender_id === user?.id,
      };
      setMessages((current) => {
        const withoutPending = current.filter((item) => item.id !== localMessageId);
        if (withoutPending.some((item) => item.id === message.id)) {
          return withoutPending;
        }
        return [...withoutPending, message];
      });
      await refreshConversations();
      await refreshNotifications();
    } catch (err) {
      setDraft(caption);
      setMessages((current) => current.filter((message) => message.id !== localMessageId));
      setError(err instanceof Error ? err.message : "Không thể gửi tệp.");
    } finally {
      if (progressTimer !== null) {
        window.clearInterval(progressTimer);
        progressTimer = null;
      }
      if (localFileUrl) {
        window.URL.revokeObjectURL(localFileUrl);
      }
      setIsUploadingAttachment(false);
    }
  }

  function handleAttachmentChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) {
      void sendAttachment(file);
    }
  }

  function beginMessageHold(messageId: number) {
    if (actionHoldTimerRef.current !== null) {
      window.clearTimeout(actionHoldTimerRef.current);
    }
    actionHoldTimerRef.current = window.setTimeout(() => {
      setActiveMessageActionId(messageId);
    }, 420);
  }

  function cancelMessageHold() {
    if (actionHoldTimerRef.current !== null) {
      window.clearTimeout(actionHoldTimerRef.current);
      actionHoldTimerRef.current = null;
    }
  }

  function canDeleteMessage(message: ChatMessage) {
    return (
      message.is_own ||
      user?.role_name === "admin" ||
      user?.role_name === "administrator"
    );
  }

  function openShareDialog(message: ChatMessage) {
    setSharingMessage(message);
    setActiveMessageActionId(null);
  }

  async function shareAttachmentMessage(target: ChatUser) {
    if (!sharingMessage || isSharingMessage) {
      return;
    }

    setIsSharingMessage(true);
    setError(null);
    try {
      const response = await chatApi.shareMessage(sharingMessage.id, target.id);
      const sharedMessage = {
        ...response.message,
        is_own: response.message.sender_id === user?.id,
      };
      setSharingMessage(null);
      setHiddenConversationIds((current) => {
        if (!current.has(response.message.conversation_id)) {
          return current;
        }
        const next = new Set(current);
        next.delete(response.message.conversation_id);
        hiddenConversationIdsRef.current = next;
        return next;
      });
      setHiddenContactIds((current) => {
        if (!current.has(target.id)) {
          return current;
        }
        const next = new Set(current);
        next.delete(target.id);
        saveHiddenContactIds(next);
        return next;
      });
      setSelectedConversationId(response.message.conversation_id);
      setMessages((current) => {
        if (selectedConversationRef.current !== response.message.conversation_id) {
          return current;
        }
        if (current.some((message) => message.id === sharedMessage.id)) {
          return current;
        }
        return [...current, sharedMessage];
      });
      await refreshConversations();
      await refreshNotifications();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể chia sẻ tệp.");
    } finally {
      setIsSharingMessage(false);
    }
  }

  async function deleteMessage(message: ChatMessage) {
    if (deletingMessageId) {
      return;
    }

    const previousMessages = messages;
    setDeletingMessageId(message.id);
    setActiveMessageActionId(null);
    setError(null);
    setMessages((current) => current.filter((item) => item.id !== message.id));
    try {
      await chatApi.deleteMessage(message.id);
      await refreshConversations();
      await refreshNotifications();
    } catch (err) {
      setMessages(previousMessages);
      setError(err instanceof Error ? err.message : "Không thể thu hồi tin nhắn.");
    } finally {
      setDeletingMessageId(null);
    }
  }

  async function deleteConversation(conversationId: number) {
    if (deletingConversationId) {
      return;
    }

    const nextConversation =
      visibleConversations.find((conversation) => conversation.id !== conversationId) ||
      null;
    const deletedConversation =
      visibleConversations.find((conversation) => conversation.id === conversationId) ||
      conversations.find((conversation) => conversation.id === conversationId) ||
      null;
    const deletedPeerId = conversationPeer(deletedConversation, user?.id)?.id;
    const applyDeletedConversation = () => {
      setHiddenConversationIds((current) => {
        if (current.has(conversationId)) {
          return current;
        }
        const next = new Set(current);
        next.add(conversationId);
        hiddenConversationIdsRef.current = next;
        return next;
      });
      if (deletedPeerId) {
        setHiddenContactIds((current) => {
          if (current.has(deletedPeerId)) {
            return current;
          }
          const next = new Set(current);
          next.add(deletedPeerId);
          saveHiddenContactIds(next);
          return next;
        });
      }
      setConversations((current) =>
        current.filter((conversation) => conversation.id !== conversationId),
      );
      setPinnedConversationIds((current) => {
        const next = new Set(current);
        next.delete(conversationId);
        savePinnedConversationIds(next);
        return next;
      });
      if (selectedConversationId === conversationId) {
        setSelectedConversationId(nextConversation?.id ?? null);
        if (!nextConversation) {
          setMessages([]);
        }
      }
    };
    const restoreDeletedConversation = () => {
      setHiddenConversationIds((current) => {
        if (!current.has(conversationId)) {
          return current;
        }
        const next = new Set(current);
        next.delete(conversationId);
        hiddenConversationIdsRef.current = next;
        return next;
      });
      if (deletedPeerId) {
        setHiddenContactIds((current) => {
          if (!current.has(deletedPeerId)) {
            return current;
          }
          const next = new Set(current);
          next.delete(deletedPeerId);
          saveHiddenContactIds(next);
          return next;
        });
      }
    };

    setDeletingConversationId(conversationId);
    setOpenConversationMenu(null);
    setError(null);
    applyDeletedConversation();
    try {
      await chatApi.deleteConversation(conversationId);
      await refreshConversations();
      await refreshContacts(query);
      await refreshNotifications();
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        await refreshContacts(query);
        await refreshNotifications();
        return;
      }
      restoreDeletedConversation();
      await refreshConversations();
      setError(err instanceof Error ? err.message : "Không thể xóa hội thoại.");
    } finally {
      setDeletingConversationId(null);
    }
  }

  const activePeerOnline = Boolean(
    selectedPeer && (onlineUserIds.has(selectedPeer.id) || selectedPeer.is_online),
  );

  function toggleConversationList() {
    setOpenConversationMenu(null);
    setIsConversationListCollapsed((current) => !current);
  }

  function openConversation(conversationId: number) {
    setSelectedConversationId(conversationId);
    setIsMobileConversationOpen(true);
  }

  return (
    <div className="flex h-[calc(100dvh-3.5rem)] bg-surface md:h-[calc(100dvh-4rem)]">
      <div
        className={`border-r border-surface-variant flex-col bg-surface-container-lowest shrink-0 overflow-hidden transition-[width] duration-200 ${
          isMobileConversationOpen ? "hidden md:flex" : "flex"
        } w-full ${
          isConversationListCollapsed ? "md:w-14" : "md:w-80"
        }`}
      >
        <div
          className={`border-b border-surface-variant flex flex-col shrink-0 ${
            isConversationListCollapsed
              ? "h-16 p-2 gap-0 justify-center"
              : "p-4 gap-4"
          }`}
        >
          <div
            className={`flex items-center ${
              isConversationListCollapsed ? "justify-center" : "justify-between"
            }`}
          >
            <div className={isConversationListCollapsed ? "hidden" : ""}>
              <h2 className="text-xl font-bold text-on-surface">Tin nhắn</h2>
            </div>
            <button
              type="button"
              onClick={toggleConversationList}
              className={`hidden text-primary hover:bg-primary/10 rounded-lg transition-colors md:flex items-center justify-center ${
                isConversationListCollapsed ? "h-10 w-10" : "p-1.5"
              }`}
              aria-label={
                isConversationListCollapsed
                  ? "Mở danh sách tin nhắn"
                  : "Thu gọn danh sách tin nhắn"
              }
              title={
                isConversationListCollapsed
                  ? "Mở danh sách tin nhắn"
                  : "Thu gọn danh sách tin nhắn"
              }
            >
              {isConversationListCollapsed ? (
                <ChevronRight className="w-5 h-5" />
              ) : (
                <ChevronLeft className="w-5 h-5" />
              )}
            </button>
          </div>
          <div className={isConversationListCollapsed ? "hidden" : "relative"}>
            <Search className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Tìm kiếm cuộc trò chuyện..."
              className="w-full pl-9 pr-4 py-2 bg-surface-container-low rounded-lg text-sm text-on-surface focus:ring-1 focus:ring-primary outline-none"
            />
          </div>
        </div>

        <div
          className="flex-1 overflow-x-hidden overflow-y-auto"
          onScroll={() => setOpenConversationMenu(null)}
        >
          {visibleConversations.map((conversation) => {
            const peer = conversationPeer(conversation, user?.id);
            const isSelected = selectedConversationId === conversation.id;
            const isPinned = pinnedConversationIds.has(conversation.id);
            const isOnline = Boolean(peer && (onlineUserIds.has(peer.id) || peer.is_online));

            if (isConversationListCollapsed) {
              return (
                <button
                  key={conversation.id}
                  type="button"
                  onClick={() => openConversation(conversation.id)}
                  className={`relative flex h-14 w-full items-center justify-center border-l-2 transition-colors ${
                    isSelected
                      ? "border-primary bg-primary/10"
                      : "border-transparent hover:bg-surface-container-low"
                  }`}
                  aria-label={conversationName(conversation, user?.id)}
                  title={conversationName(conversation, user?.id)}
                >
                  <div className="relative shrink-0">
                    {peer ? (
                      <Avatar user={peer} size="sm" />
                    ) : (
                      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary-container text-xs font-bold text-on-secondary-container">
                        ?
                      </div>
                    )}
                    {isOnline && (
                      <div className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border-2 border-surface-container-lowest bg-emerald-500" />
                    )}
                  </div>
                  {conversation.unread_count > 0 && (
                    <span className="absolute right-0.5 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[9px] font-bold leading-none text-on-primary">
                      {conversation.unread_count > 99
                        ? "99+"
                        : conversation.unread_count}
                    </span>
                  )}
                </button>
              );
            }

            return (
              <div
                key={conversation.id}
                onClick={() => openConversation(conversation.id)}
                className={`group w-full flex gap-3 p-4 text-left cursor-pointer relative border-l-4 transition-colors ${
                  isSelected
                    ? "border-primary bg-primary/5"
                    : isPinned
                      ? "border-transparent bg-surface-container-low/70 hover:bg-surface-container-low"
                    : "border-transparent hover:bg-surface-container-low"
                }`}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    openConversation(conversation.id);
                  }
                }}
              >
                <div className="relative shrink-0">
                  {peer ? (
                    <Avatar user={peer} />
                  ) : (
                    <div className="w-12 h-12 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-bold">
                      ?
                    </div>
                  )}
                  {isOnline && (
                    <div className="absolute bottom-0 right-0 w-3 h-3 bg-emerald-500 border-2 border-surface-container-lowest rounded-full" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-baseline mb-1">
                    <p className="font-semibold text-on-surface truncate">
                      {conversationName(conversation, user?.id)}
                    </p>
                    <div className="relative shrink-0 ml-2">
                      <p
                        className={`text-xs text-outline transition-opacity ${
                          openConversationMenu?.id === conversation.id
                            ? "opacity-0"
                            : "group-hover:opacity-0"
                        }`}
                      >
                        {formatConversationTime(conversation.last_message?.created_at || conversation.updated_at)}
                      </p>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          const rect = event.currentTarget.getBoundingClientRect();
                          setOpenConversationMenu((current) =>
                            current?.id === conversation.id
                              ? null
                              : {
                                  id: conversation.id,
                                  top: Math.max(
                                    8,
                                    Math.min(rect.top, window.innerHeight - 168),
                                  ),
                                  left: Math.max(
                                    8,
                                    Math.min(rect.right + 10, window.innerWidth - 304),
                                  ),
                                },
                          );
                        }}
                        className={`absolute -top-2 right-0 h-7 w-7 rounded-lg flex items-center justify-center text-outline hover:bg-surface-container-high hover:text-on-surface transition-all ${
                          openConversationMenu?.id === conversation.id
                            ? "opacity-100"
                            : "opacity-0 group-hover:opacity-100"
                        }`}
                        aria-label="Mở tùy chọn hội thoại"
                      >
                        <MoreHorizontal className="w-4 h-4" />
                      </button>
                      {isPinned && (
                        <Pin
                          className={`absolute right-1 top-7 h-3.5 w-3.5 rotate-45 fill-current text-outline transition-opacity ${
                            openConversationMenu?.id === conversation.id
                              ? "opacity-100"
                              : "opacity-80 group-hover:opacity-100"
                          }`}
                          aria-hidden="true"
                        />
                      )}
                    </div>
                  </div>
                  <p className={`text-sm truncate ${conversation.unread_count ? "text-on-surface font-medium" : "text-outline"}`}>
                    {conversationPreview(conversation)}
                  </p>
                </div>
                {conversation.unread_count > 0 && (
                  <div className="w-5 h-5 rounded-full bg-primary text-on-primary flex items-center justify-center text-[10px] font-bold mt-6">
                    {conversation.unread_count}
                  </div>
                )}
              </div>
            );
          })}

          {shouldShowContacts && (
            <>
              <div
                className={
                  isConversationListCollapsed
                    ? "hidden"
                    : "px-4 pt-4 pb-2 text-xs font-bold text-outline uppercase tracking-wider"
                }
              >
                Liên hệ
              </div>
              {visibleContacts.map((contact) => {
                const isOnline = onlineUserIds.has(contact.id) || contact.is_online;

                if (isConversationListCollapsed) {
                  return (
                    <button
                      key={contact.id}
                      type="button"
                      onClick={() => void startConversation(contact)}
                      className="flex h-14 w-full items-center justify-center border-l-2 border-transparent transition-colors hover:bg-surface-container-low"
                      aria-label={contact.full_name}
                      title={contact.full_name}
                    >
                      <div className="relative shrink-0">
                        <Avatar user={contact} size="sm" />
                        {isOnline && (
                          <div className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border-2 border-surface-container-lowest bg-emerald-500" />
                        )}
                      </div>
                    </button>
                  );
                }

                return (
                  <button
                    key={contact.id}
                    type="button"
                    onClick={() => void startConversation(contact)}
                    className="w-full flex gap-3 p-4 text-left hover:bg-surface-container-low transition-colors border-l-4 border-transparent"
                  >
                    <div className="relative shrink-0">
                      <Avatar user={contact} />
                      {isOnline && (
                        <div className="absolute bottom-0 right-0 w-3 h-3 bg-emerald-500 border-2 border-surface-container-lowest rounded-full" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-on-surface truncate">{contact.full_name}</p>
                      <p className="text-sm text-outline truncate">{roleLabel(contact.role_name)}</p>
                    </div>
                  </button>
                );
              })}
            </>
          )}

          {!visibleConversations.length && (!shouldShowContacts || !visibleContacts.length) && (
            <div
              className={
                isConversationListCollapsed
                  ? "hidden"
                  : "p-6 text-sm text-outline text-center"
              }
            >
              Không tìm thấy người dùng phù hợp.
            </div>
          )}
        </div>
      </div>

      <div
        className={`flex-1 flex-col bg-surface-container-lowest/50 min-w-0 ${
          isMobileConversationOpen ? "flex" : "hidden md:flex"
        }`}
      >
        <div className="h-16 px-3 sm:px-6 border-b border-surface-variant flex justify-between items-center bg-surface-container-lowest shrink-0">
          {selectedPeer ? (
            <div className="flex items-center gap-3 min-w-0">
              <button
                type="button"
                onClick={() => {
                  setIsProfileOpen(false);
                  setIsMobileConversationOpen(false);
                }}
                className="md:hidden h-9 w-9 shrink-0 rounded-lg text-outline hover:bg-surface-container-low hover:text-on-surface flex items-center justify-center"
                aria-label="Quay lại danh sách tin nhắn"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <div className="md:hidden">
                <Avatar user={selectedPeer} size="sm" />
              </div>
              <div className="min-w-0">
                <h3 className="font-bold text-on-surface truncate">{selectedPeer.full_name}</h3>
                <p className={`text-xs font-medium ${activePeerOnline ? "text-emerald-600" : "text-outline"}`}>
                  {activePeerOnline ? "Trực tuyến" : "Ngoại tuyến"}
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 min-w-0">
              <button
                type="button"
                onClick={() => setIsMobileConversationOpen(false)}
                className="md:hidden h-9 w-9 shrink-0 rounded-lg text-outline hover:bg-surface-container-low hover:text-on-surface flex items-center justify-center"
                aria-label="Quay lại danh sách tin nhắn"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <div className="min-w-0">
                <h3 className="font-bold text-on-surface truncate">Chọn cuộc trò chuyện</h3>
                <p className="text-xs text-outline truncate">Chọn liên hệ bên trái để bắt đầu.</p>
              </div>
            </div>
          )}
          <div className="flex items-center gap-3 sm:gap-4">
            <button className="hidden sm:block text-outline hover:text-on-surface disabled:opacity-40" disabled={!selectedPeer}>
              <Phone className="w-5 h-5" />
            </button>
            <button className="hidden sm:block text-outline hover:text-on-surface disabled:opacity-40" disabled={!selectedPeer}>
              <Video className="w-5 h-5" />
            </button>
            <button
              type="button"
              onClick={() => setIsProfileOpen((current) => !current)}
              className={`p-1 rounded-lg transition-colors disabled:opacity-40 ${
                isProfileOpen
                  ? "text-primary bg-primary/10"
                  : "text-outline hover:text-on-surface hover:bg-surface-variant/50"
              }`}
              disabled={!selectedPeer}
              aria-label={isProfileOpen ? "Đóng hồ sơ" : "Mở hồ sơ"}
              title={isProfileOpen ? "Đóng hồ sơ" : "Mở hồ sơ"}
            >
              <MoreHorizontal className="w-5 h-5" />
            </button>
          </div>
        </div>

        {error && (
          <div className="mx-6 mt-4 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-on-surface flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-500" />
            {error}
          </div>
        )}

          <div className="flex-1 overflow-y-auto p-3 sm:p-4 flex flex-col gap-4">
          {selectedConversation && (
            <div className="text-center font-medium text-xs text-outline tracking-wider">
              {messages.length ? "Lịch sử trò chuyện" : "Chưa có tin nhắn"}
            </div>
          )}

          {isLoadingMessages && (
            <div className="text-center text-sm text-outline">Đang tải tin nhắn...</div>
          )}

          {!selectedConversation && (
            <div className="h-full flex items-center justify-center text-sm text-outline">
              Chọn một liên hệ để nhắn tin realtime.
            </div>
          )}

          {timelineMessages.map(({ message, showTimeline }) => (
            <div
              key={message.id}
              className="contents"
            >
              {showTimeline && (
                <div className="flex justify-center my-2">
                  <span className="rounded-full bg-outline/40 px-4 py-1 text-xs font-semibold text-white shadow-sm">
                    {formatTimelineLabel(message.created_at)}
                  </span>
                </div>
              )}
              <div
                className={`group flex flex-col gap-1 ${message.is_own ? "items-end" : "items-start"}`}
                onClick={(event) => event.stopPropagation()}
                onContextMenu={(event) => {
                  if (isUploadingMessage(message)) {
                    return;
                  }
                  event.preventDefault();
                  setActiveMessageActionId(message.id);
                }}
                onPointerDown={(event) => {
                  if (event.pointerType !== "mouse" && !isUploadingMessage(message)) {
                    beginMessageHold(message.id);
                  }
                }}
                onPointerUp={cancelMessageHold}
                onPointerCancel={cancelMessageHold}
                onPointerLeave={cancelMessageHold}
              >
                <div
                  className={`flex items-end gap-2 max-w-[92%] sm:max-w-[84%] ${message.is_own ? "flex-row-reverse" : "flex-row"}`}
                >
                  <div
                    className={`min-w-0 ${
                      isUploadingMessage(message)
                        ? "px-5 py-3 rounded-2xl shadow-sm border border-blue-100 bg-blue-50 text-on-surface rounded-tr-sm"
                        : message.attachment_url
                        ? "p-0 bg-transparent text-on-surface shadow-none"
                        : message.is_own
                        ? "px-5 py-3 rounded-2xl shadow-sm bg-primary text-on-primary rounded-tr-sm"
                        : "px-5 py-3 rounded-2xl shadow-sm bg-surface-container-low text-on-surface rounded-tl-sm"
                    }`}
                  >
                    {isUploadingMessage(message) ? (
                      <div className="flex min-w-0 w-[min(16rem,calc(100vw-5rem))] max-w-md flex-col gap-3 sm:min-w-64 sm:w-auto">
                        {message.local_file_url && isImageAttachment(message) ? (
                          <div className="overflow-hidden rounded-xl border border-blue-100 bg-white">
                            <img
                              src={message.local_file_url}
                              alt={message.attachment_filename || message.body}
                              className="max-h-72 w-full object-contain"
                            />
                          </div>
                        ) : (
                          <div className="flex items-center gap-3">
                            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg bg-red-500 text-xs font-bold text-white">
                              {fileExtensionLabel(
                                message.attachment_filename,
                                message.attachment_content_type,
                              )}
                            </div>
                            <span className="min-w-0">
                              <span className="block truncate text-sm font-semibold">
                                {message.attachment_filename || message.body}
                              </span>
                              <span className="block text-xs text-outline">
                                {formatFileSize(message.attachment_size_bytes)}
                              </span>
                            </span>
                          </div>
                        )}
                        <div className="h-2 overflow-hidden rounded-full bg-slate-300">
                          <div
                            className="h-full rounded-full bg-primary transition-[width] duration-200"
                            style={{ width: `${message.upload_progress || 12}%` }}
                          />
                        </div>
                        <div className="flex justify-end">
                          <span className="rounded-full bg-outline/70 px-2.5 py-1 text-xs font-semibold text-white">
                            Đang gửi
                          </span>
                        </div>
                      </div>
                    ) : message.attachment_url ? (
                      <div className="flex min-w-0 w-[min(14rem,calc(100vw-5rem))] flex-col gap-2 sm:min-w-56 sm:w-auto">
                        {isImageAttachment(message) ? (
                          <a
                            href={message.attachment_url}
                            target="_blank"
                            rel="noreferrer"
                            className={`block overflow-hidden rounded-xl ${
                              message.is_own
                                ? "bg-transparent"
                                : "border border-outline-variant bg-black/5"
                            }`}
                          >
                            <img
                              src={message.attachment_url}
                              alt={message.attachment_filename || message.body}
                              className="max-h-80 max-w-full object-contain"
                            />
                          </a>
                        ) : (
                          <a
                            href={message.attachment_url}
                            target="_blank"
                            rel="noreferrer"
                            className={`flex items-center gap-3 rounded-xl border px-3 py-2 transition-colors ${
                              message.is_own
                                ? "border-primary bg-primary text-on-primary shadow-sm hover:bg-primary/90"
                                : "border-outline-variant bg-surface-container-lowest hover:bg-surface-container-low"
                            }`}
                          >
                            <FileText className="h-5 w-5 shrink-0" />
                            <span className="min-w-0">
                              <span className="block truncate text-sm font-semibold">
                                {message.attachment_filename || message.body}
                              </span>
                              <span className={`block text-xs ${message.is_own ? "text-white/75" : "text-outline"}`}>
                                {formatFileSize(message.attachment_size_bytes)}
                              </span>
                            </span>
                          </a>
                        )}
                        {message.body && message.body !== message.attachment_filename && (
                          <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                            {message.body}
                          </p>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                        {message.body}
                      </p>
                    )}
                  </div>
                  {!isUploadingMessage(message) && (
                    <div
                      className={`flex items-center gap-1 rounded-full border border-surface-variant bg-surface-container-lowest p-1 shadow-lg transition-all ${
                        activeMessageActionId === message.id
                          ? "opacity-100 translate-y-0 pointer-events-auto"
                          : "opacity-0 translate-y-1 pointer-events-none group-hover:opacity-100 group-hover:translate-y-0 group-hover:pointer-events-auto group-focus-within:opacity-100 group-focus-within:translate-y-0 group-focus-within:pointer-events-auto"
                      }`}
                    >
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          openShareDialog(message);
                        }}
                        className="h-8 w-8 rounded-full text-outline hover:bg-primary/10 hover:text-primary flex items-center justify-center transition-colors"
                        aria-label="Chuyển tiếp"
                        title="Chuyển tiếp"
                      >
                        <Forward className="h-4 w-4" />
                      </button>
                      {canDeleteMessage(message) && (
                        <button
                          type="button"
                          disabled={deletingMessageId === message.id}
                          onClick={(event) => {
                            event.stopPropagation();
                            void deleteMessage(message);
                          }}
                          className="h-8 w-8 rounded-full text-outline hover:bg-error-container hover:text-on-error-container flex items-center justify-center transition-colors disabled:opacity-50"
                          aria-label="Thu hồi tin nhắn"
                          title="Thu hồi tin nhắn"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  )}
                </div>
                <p className="text-xs text-outline">
                  {formatTime(message.created_at)}
                </p>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <form
          onSubmit={(event) => void sendMessage(event)}
          className="p-2.5 sm:p-4 bg-surface-container-lowest border-t border-surface-variant shrink-0"
        >
          <div className="flex items-center gap-2">
            <div className="flex-1 min-w-0 bg-surface-container-low rounded-xl border border-outline-variant flex items-center pl-3 sm:pl-4 pr-2 py-2">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={!selectedConversation || isUploadingAttachment}
                className="text-outline hover:text-on-surface mr-3 disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Gửi tệp"
                title="Gửi tệp"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip"
                className="hidden"
                onChange={handleAttachmentChange}
              />
              <input
                type="text"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                disabled={!selectedConversation}
                placeholder={selectedConversation ? "Nhập tin nhắn..." : "Chọn cuộc trò chuyện trước"}
                className="flex-1 min-w-0 bg-transparent text-sm text-on-surface outline-none disabled:cursor-not-allowed"
              />
            </div>
            <button
              type="submit"
              disabled={!selectedConversation || !draft.trim()}
              className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-primary text-on-primary flex items-center justify-center hover:bg-primary/90 transition-colors shrink-0 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-5 h-5 ml-1" />
            </button>
          </div>
        </form>
      </div>

      {openConversationMenu && (
        <div
          onClick={(event) => event.stopPropagation()}
          className="fixed z-[80] w-56 rounded-xl border border-surface-variant bg-surface-container-lowest p-2 shadow-[0_18px_42px_rgba(15,23,42,0.22)]"
          style={{
            top: openConversationMenu.top,
            left: openConversationMenu.left,
          }}
        >
          <button
            type="button"
            onClick={() => togglePinConversation(openConversationMenu.id)}
            className="w-full rounded-lg px-3 py-3 text-left text-sm font-medium text-on-surface hover:bg-surface-container-low"
          >
            {pinnedConversationIds.has(openConversationMenu.id)
              ? "Bỏ ghim hội thoại"
              : "Ghim hội thoại"}
          </button>
          <button
            type="button"
            disabled={deletingConversationId === openConversationMenu.id}
            onClick={() => void deleteConversation(openConversationMenu.id)}
            className="mt-1 w-full rounded-lg px-3 py-3 text-left text-sm font-medium text-error hover:bg-error-container hover:text-on-error-container disabled:opacity-60"
          >
            {deletingConversationId === openConversationMenu.id
              ? "Đang xóa..."
              : "Xóa hội thoại"}
          </button>
        </div>
      )}

      {sharingMessage && (
        <div
          className="fixed inset-0 z-[90] bg-black/35 flex items-center justify-center p-4"
          onClick={() => {
            if (!isSharingMessage) {
              setSharingMessage(null);
            }
          }}
        >
          <div
            className="w-full max-w-md rounded-xl border border-surface-variant bg-surface-container-lowest shadow-[0_24px_60px_rgba(15,23,42,0.28)]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-surface-variant px-5 py-4">
              <div className="min-w-0">
                <h3 className="font-semibold text-on-surface">Chuyển tiếp tin nhắn</h3>
                <p className="truncate text-sm text-outline">
                  {sharingMessage.attachment_filename || sharingMessage.body}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSharingMessage(null)}
                disabled={isSharingMessage}
                className="h-9 w-9 rounded-full text-outline hover:bg-surface-container-low hover:text-on-surface flex items-center justify-center disabled:opacity-50"
                aria-label="Đóng"
                title="Đóng"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[50vh] overflow-y-auto py-2">
              {shareTargets.length ? (
                shareTargets.map((target) => (
                  <button
                    key={target.id}
                    type="button"
                    onClick={() => void shareAttachmentMessage(target)}
                    disabled={isSharingMessage}
                    className="w-full flex items-center gap-3 px-5 py-3 text-left hover:bg-surface-container-low disabled:opacity-60"
                  >
                    <Avatar user={target} size="sm" />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-semibold text-on-surface">
                        {target.full_name}
                      </span>
                      <span className="block truncate text-xs text-outline">
                        {roleLabel(target.role_name)}
                      </span>
                    </span>
                    <Forward className="ml-auto h-4 w-4 text-outline" />
                  </button>
                ))
              ) : (
                <div className="px-5 py-8 text-center text-sm text-outline">
                  Chưa có hội thoại nào trong danh sách để chuyển tiếp.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {isProfileOpen && (
      <div className="fixed inset-0 z-[70] flex flex-col bg-surface-container-lowest lg:static lg:z-auto lg:w-72 lg:shrink-0 lg:border-l lg:border-surface-variant">
        {selectedPeer ? (
          <>
            <div className="relative p-8 flex flex-col items-center border-b border-surface-variant">
              <button
                type="button"
                onClick={() => setIsProfileOpen(false)}
                className="absolute right-3 top-3 h-9 w-9 rounded-lg text-outline hover:bg-surface-container-low hover:text-on-surface flex items-center justify-center lg:hidden"
                aria-label="Đóng hồ sơ"
              >
                <X className="h-5 w-5" />
              </button>
              <Avatar user={selectedPeer} size="lg" />
              <h3 className="font-bold text-lg text-on-surface text-center mt-4">
                {selectedPeer.full_name}
              </h3>
              <p className="text-sm text-outline mt-1 text-center">
                {roleLabel(selectedPeer.role_name)}
                {selectedPeer.school_name ? ` • ${selectedPeer.school_name}` : ""}
              </p>
              <button className="w-full mt-6 py-2 border border-primary text-primary rounded-lg text-sm font-semibold hover:bg-primary/5 transition-colors">
                Hồ sơ
              </button>
            </div>

            <div className="p-5 flex-1 overflow-y-auto">
              <h4 className="text-xs font-bold text-outline uppercase tracking-wider mb-4">
                Tệp & phương tiện đã chia sẻ
              </h4>
              {sharedFiles.length ? (
                <div className="flex flex-col gap-3">
                  {sharedFiles.map((message) => (
                    <a
                      key={message.id}
                      href={message.attachment_url || "#"}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-3 rounded-xl border border-surface-variant p-3 text-sm hover:bg-surface-container-low"
                    >
                      {isImageAttachment(message) ? (
                        <img
                          src={message.attachment_url || ""}
                          alt={message.attachment_filename || message.body}
                          className="h-10 w-10 rounded-lg object-cover"
                        />
                      ) : (
                        <div className="h-10 w-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                          <FileText className="h-5 w-5" />
                        </div>
                      )}
                      <span className="min-w-0">
                        <span className="block truncate font-semibold text-on-surface">
                          {message.attachment_filename || message.body}
                        </span>
                        <span className="block text-xs text-outline">
                          {formatFileSize(message.attachment_size_bytes)}
                        </span>
                      </span>
                    </a>
                  ))}
                </div>
              ) : (
                <div className="p-4 border border-dashed border-outline-variant rounded-xl text-sm text-outline text-center">
                  Chưa có tệp được chia sẻ.
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="p-8 text-center text-sm text-outline">
            Thông tin liên hệ sẽ hiển thị ở đây.
          </div>
        )}
      </div>
      )}
    </div>
  );
}
