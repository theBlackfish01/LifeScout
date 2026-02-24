"use client";

import { Skeleton } from "@/components/ui/skeleton";

export default function TypingIndicator() {
    return (
        <div className="flex justify-start w-full">
            <div className="bg-[#1a1f2e] border border-white/5 rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-1.5">
                <Skeleton className="h-2 w-2 rounded-full bg-purple-400 animate-bounce [animation-delay:0ms]" />
                <Skeleton className="h-2 w-2 rounded-full bg-purple-400 animate-bounce [animation-delay:150ms]" />
                <Skeleton className="h-2 w-2 rounded-full bg-purple-400 animate-bounce [animation-delay:300ms]" />
            </div>
        </div>
    );
}
