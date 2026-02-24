"use client";

import { useAppStore } from "@/store/useAppStore";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";

const agentLabels: Record<string, string> = {
    career: "🎯 Career Agent",
    life: "🌱 Life Agent",
    learning: "📚 Learning Agent",
    settings: "⚙️ Settings",
};

interface HeaderProps {
    onToggleDashboard: () => void;
}

export default function Header({ onToggleDashboard }: HeaderProps) {
    const { activeAgent, userProfile } = useAppStore();

    const initials = userProfile?.demographics?.occupation
        ? userProfile.demographics.occupation.slice(0, 2).toUpperCase()
        : "LS";

    return (
        <header className="flex items-center justify-between h-14 px-6 border-b border-white/10 bg-[#0d1117]/80 backdrop-blur-sm">
            <div className="flex items-center gap-3">
                <h2 className="text-base font-semibold text-white">
                    {agentLabels[activeAgent] || "LifeScouter"}
                </h2>
            </div>

            <div className="flex items-center gap-3">
                <Button
                    variant="ghost"
                    size="sm"
                    className="text-gray-400 hover:text-white text-xs"
                    onClick={onToggleDashboard}
                >
                    📊 Dashboard
                </Button>

                <Avatar className="h-8 w-8 border border-white/20">
                    <AvatarFallback className="bg-gradient-to-br from-blue-500 to-purple-600 text-white text-xs font-bold">
                        {initials}
                    </AvatarFallback>
                </Avatar>
            </div>
        </header>
    );
}
