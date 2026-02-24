"use client";

import type { ChatMessage } from "@/types";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import { motion } from "framer-motion";

interface MessageBubbleProps {
    message: ChatMessage;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
    const isUser = message.role === "user";
    const isSystem = message.role === "system";

    return (
        <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}
        >
            <div
                className={cn(
                    "max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
                    isUser
                        ? "bg-blue-600 text-white rounded-br-md"
                        : isSystem
                            ? "bg-yellow-500/10 text-yellow-300 border border-yellow-500/20 rounded-bl-md"
                            : "bg-[#1a1f2e] text-gray-200 border border-white/5 rounded-bl-md"
                )}
            >
                {!isUser && message.agentName && (
                    <p className="text-[10px] text-purple-400 font-medium mb-1 uppercase tracking-wider">
                        {message.agentName}
                    </p>
                )}
                {isUser ? (
                    <p>{message.content}</p>
                ) : (
                    <div className="prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-li:my-0">
                        <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                )}
            </div>
        </motion.div>
    );
}
