"use client";

import { useAppStore } from "@/store/useAppStore";
import ChatWindow from "@/components/chat/ChatWindow";

export default function OnboardingModal() {
    const onboardingComplete = useAppStore((s) => s.onboardingComplete);

    if (onboardingComplete) return null;

    return (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center">
            <div className="w-full max-w-2xl h-[80vh] bg-[#0d1117] rounded-2xl border border-white/10 flex flex-col overflow-hidden shadow-2xl">
                {/* Header */}
                <div className="px-6 py-4 border-b border-white/10 bg-gradient-to-r from-blue-500/10 to-purple-500/10">
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                        <span>👋</span> Welcome to LifeScouter
                    </h2>
                    <p className="text-sm text-gray-400 mt-1">
                        Let&apos;s set up your profile to personalize your experience.
                    </p>
                </div>

                {/* Chat — force onboarding agent */}
                <div className="flex-1 min-h-0">
                    <ChatWindow agentOverride="onboarding" />
                </div>
            </div>
        </div>
    );
}
