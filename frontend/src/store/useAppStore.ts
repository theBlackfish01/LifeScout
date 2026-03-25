import { create } from "zustand";
import type { AgentType, ChatMessage, UserProfile, Task, Artifact, Notification } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// Pending messages queued while WebSocket is connecting
type PendingMessage = { message: string; active_agent: AgentType };

interface AppState {
    // --- Agent Routing ---
    activeAgent: AgentType;
    setActiveAgent: (agent: AgentType) => void;

    // --- User Profile ---
    userProfile: UserProfile | null;
    onboardingComplete: boolean;
    fetchProfile: () => Promise<void>;

    // --- Chat ---
    messages: ChatMessage[];
    addMessage: (msg: ChatMessage) => void;
    clearMessages: () => void;
    isProcessing: boolean;
    setProcessing: (v: boolean) => void;

    // --- Background Tasks ---
    tasks: Task[];
    fetchTasks: () => Promise<void>;

    // --- Artifacts ---
    artifacts: Artifact[];
    fetchArtifacts: () => Promise<void>;

    // --- WebSocket ---
    ws: WebSocket | null;
    threadId: string;
    pendingQueue: PendingMessage[];
    connectWs: (threadId: string) => void;
    disconnectWs: () => void;
    sendMessage: (text: string) => void;

    // --- Notifications ---
    notifications: Notification[];
    unreadCount: number;
    fetchNotifications: () => Promise<void>;
    markNotificationRead: (id: string) => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
    // --- Agent Routing ---
    activeAgent: "career",
    setActiveAgent: (agent) => {
        const current = get().activeAgent;
        if (current === agent) return; // Prevent no-op updates
        const ws = get().ws;
        if (ws) ws.close();
        set({ activeAgent: agent, messages: [], ws: null });
    },

    // --- User Profile ---
    userProfile: null,
    onboardingComplete: false,
    fetchProfile: async () => {
        try {
            const res = await fetch(`${API_BASE}/api/profile`);
            if (res.ok) {
                const profile: UserProfile = await res.json();
                set({ userProfile: profile, onboardingComplete: profile.onboarding_complete });
            }
        } catch (err) {
            console.error("Failed to fetch profile:", err);
        }
    },

    // --- Chat ---
    messages: [],
    addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
    clearMessages: () => set({ messages: [] }),
    isProcessing: false,
    setProcessing: (v) => set({ isProcessing: v }),

    // --- Background Tasks ---
    tasks: [],
    fetchTasks: async () => {
        try {
            const res = await fetch(`${API_BASE}/api/tasks`);
            if (res.ok) {
                const tasks: Task[] = await res.json();
                set({ tasks });
            }
        } catch (err) {
            console.error("Failed to fetch tasks:", err);
        }
    },

    // --- Artifacts ---
    artifacts: [],
    fetchArtifacts: async () => {
        try {
            const res = await fetch(`${API_BASE}/api/artifacts`);
            if (res.ok) {
                const artifacts: Artifact[] = await res.json();
                set({ artifacts });
            }
        } catch (err) {
            console.error("Failed to fetch artifacts:", err);
        }
    },

    // --- WebSocket ---
    ws: null,
    threadId: "default-thread",
    pendingQueue: [],
    connectWs: (threadId) => {
        const existing = get().ws;
        // Guard: skip if already connected to this exact thread
        if (existing && existing.readyState === WebSocket.OPEN && get().threadId === threadId) {
            return;
        }
        // Close any stale connection first
        if (existing) {
            existing.close();
        }

        // Update threadId immediately to prevent re-entry
        set({ threadId, ws: null });

        const wsUrl = API_BASE.replace(/^http/, "ws");
        const socket = new WebSocket(`${wsUrl}/api/chat/${threadId}`);

        socket.onopen = () => {
            console.log("[WS] Connected to", threadId);
            set({ ws: socket });

            // Flush any messages that were queued while connecting
            const queue = get().pendingQueue;
            if (queue.length > 0) {
                for (const pending of queue) {
                    socket.send(JSON.stringify(pending));
                }
                set({ pendingQueue: [] });
            }
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === "ai_message") {
                    const msg: ChatMessage = {
                        id: crypto.randomUUID(),
                        role: "ai",
                        content: data.content,
                        agentName: data.agent_name,
                        timestamp: Date.now(),
                    };
                    get().addMessage(msg);
                } else if (data.type === "status" && data.content === "processing") {
                    set({ isProcessing: true });
                } else if (data.type === "done") {
                    set({ isProcessing: false });
                } else if (data.type === "error") {
                    const msg: ChatMessage = {
                        id: crypto.randomUUID(),
                        role: "system",
                        content: `⚠️ ${data.content}`,
                        timestamp: Date.now(),
                    };
                    get().addMessage(msg);
                    set({ isProcessing: false });
                }
            } catch {
                console.error("[WS] Failed to parse message");
            }
        };

        socket.onclose = () => {
            console.log("[WS] Disconnected from", threadId);
            // Only clear ws if this socket is still the current one
            if (get().ws === socket) {
                set({ ws: null });
            }
        };
    },

    disconnectWs: () => {
        const ws = get().ws;
        if (ws) {
            ws.close();
            set({ ws: null, pendingQueue: [] });
        }
    },

    sendMessage: (text) => {
        const { ws, activeAgent, threadId, connectWs } = get();

        // Add user message to local state immediately
        const userMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: "user",
            content: text,
            timestamp: Date.now(),
        };
        get().addMessage(userMsg);

        const payload: PendingMessage = { message: text, active_agent: activeAgent };

        // Send immediately if connected, otherwise queue and connect
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(payload));
        } else {
            set((s) => ({ pendingQueue: [...s.pendingQueue, payload] }));
            connectWs(threadId);
        }
    },

    // --- Notifications ---
    notifications: [],
    unreadCount: 0,
    fetchNotifications: async () => {
        try {
            const res = await fetch(`${API_BASE}/api/notifications`);
            if (res.ok) {
                const notifications: Notification[] = await res.json();
                const unreadCount = notifications.filter((n) => !n.read).length;
                set({ notifications, unreadCount });
            }
        } catch (err) {
            console.error("Failed to fetch notifications:", err);
        }
    },
    markNotificationRead: async (id) => {
        try {
            await fetch(`${API_BASE}/api/notifications/${id}/read`, { method: "PUT" });
            get().fetchNotifications();
        } catch (err) {
            console.error("Failed to mark notification read:", err);
        }
    },
}));
