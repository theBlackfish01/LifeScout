"use client";

import { useEffect, useRef } from "react";
import { useAppStore } from "@/store/useAppStore";
import { ScrollArea } from "@/components/ui/scroll-area";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";
import ChatInput from "./ChatInput";

interface ChatWindowProps {
    agentOverride?: string;
}

export default function ChatWindow({ agentOverride }: ChatWindowProps) {
    const messages = useAppStore((s) => s.messages);
    const isProcessing = useAppStore((s) => s.isProcessing);
    const activeAgent = useAppStore((s) => s.activeAgent);
    const bottomRef = useRef<HTMLDivElement>(null);
    const connectedRef = useRef<string | null>(null);

    const effectiveAgent = agentOverride || activeAgent;

    // Connect WebSocket when agent changes — use a ref to prevent re-entry
    useEffect(() => {
        const wsThreadId = `${effectiveAgent}-session`;
        if (connectedRef.current === wsThreadId) return;
        connectedRef.current = wsThreadId;
        useAppStore.getState().connectWs(wsThreadId);
    }, [effectiveAgent]);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isProcessing]);

    return (
        <div className="flex flex-col flex-1 min-h-0">
            <ScrollArea className="flex-1 p-6">
                <div className="flex flex-col gap-4 max-w-3xl mx-auto">
                    {messages.length === 0 && (
                        <div className="flex flex-col items-center justify-center h-[50vh] text-center gap-3">
                            <span className="text-5xl">🔭</span>
                            <h3 className="text-lg font-semibold text-white">Ready to assist</h3>
                            <p className="text-sm text-gray-500 max-w-sm">
                                Send a message to begin working with your {effectiveAgent} agent.
                            </p>
                        </div>
                    )}

                    {messages.map((msg) => (
                        <MessageBubble key={msg.id} message={msg} />
                    ))}

                    {isProcessing && <TypingIndicator />}

                    <div ref={bottomRef} />
                </div>
            </ScrollArea>

            <ChatInput agentOverride={agentOverride} />
        </div>
    );
}
