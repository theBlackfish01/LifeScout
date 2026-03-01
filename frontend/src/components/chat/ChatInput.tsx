"use client";

import { useState, type FormEvent } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/store/useAppStore";
import { Paperclip, Loader2 } from "lucide-react";

interface ChatInputProps {
    agentOverride?: string;
}

export default function ChatInput({ agentOverride }: ChatInputProps) {
    const [text, setText] = useState("");
    const [isUploading, setIsUploading] = useState(false);
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

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("http://localhost:8000/api/upload/resume", {
                method: "POST",
                body: formData,
            });
            const data = await res.json();

            if (res.ok) {
                 const store = useAppStore.getState();
                 store.addMessage({
                    id: crypto.randomUUID(),
                    role: "system",
                    content: `[SYSTEM] Successfully uploaded resume: ${data.filename}. The career agent can now access this via the parsing tool.`,
                    timestamp: Date.now(),
                 });
            } else {
                 console.error("Upload failed:", data.detail); alert("Upload failed: " + data.detail);
            }
        } catch (err) {
            console.error(err);
            alert("Upload error.");
        } finally {
            setIsUploading(false);
            e.target.value = ""; // reset input
        }
    };

    return (
        <form
            onSubmit={handleSubmit}
            className="flex items-center gap-2 p-4 border-t border-white/10 bg-[#0d1117]/60 backdrop-blur-sm"
        >
            <div className="relative">
                <input
                    type="file"
                    id="resume-upload"
                    accept=".pdf,.doc,.docx"
                    className="hidden"
                    onChange={handleFileUpload}
                    disabled={isUploading || isProcessing}
                />
                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="text-gray-400 hover:text-white"
                    asChild
                >
                    <label htmlFor="resume-upload" className="cursor-pointer">
                        {isUploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Paperclip className="h-5 w-5" />}
                    </label>
                </Button>
            </div>
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
