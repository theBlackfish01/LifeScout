"use client";

import { useState, type FormEvent } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/store/useAppStore";

interface ChatInputProps {
    agentOverride?: string;
}

export default function ChatInput({ agentOverride }: ChatInputProps) {
    const [text, setText] = useState("");
    const isProcessing = useAppStore((s) => s.isProcessing);

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        const trimmed = text.trim();
        if (!trimmed || isProcessing) return;

        // Use the override agent or the store's active agent for routing
        const store = useAppStore.getState();
        const agent = agentOverride || store.activeAgent;

        // Add user message locally
        store.addMessage({
            id: crypto.randomUUID(),
            role: "user",
            content: trimmed,
            timestamp: Date.now(),
        });

        // Send through WebSocket
        const ws = store.ws;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ message: trimmed, active_agent: agent }));
        } else {
            // Reconnect and send
            const threadId = `${agent}-session`;
            store.connectWs(threadId);
            setTimeout(() => {
                const currentWs = useAppStore.getState().ws;
                if (currentWs && currentWs.readyState === WebSocket.OPEN) {
                    currentWs.send(JSON.stringify({ message: trimmed, active_agent: agent }));
                }
            }, 500);
        }

        setText("");
    };

    return (
        <form
            onSubmit={handleSubmit}
            className="flex items-center gap-2 p-4 border-t border-white/10 bg-[#0d1117]/60 backdrop-blur-sm"
        >
            <Input
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Type a message..."
                disabled={isProcessing}
                className="flex-1 bg-[#1a1f2e] border-white/10 text-white placeholder:text-gray-500 focus-visible:ring-blue-500/50"
            />
            <Button
                type="submit"
                disabled={!text.trim() || isProcessing}
                className="bg-blue-600 hover:bg-blue-500 text-white px-5"
            >
                Send
            </Button>
        </form>
    );
}
