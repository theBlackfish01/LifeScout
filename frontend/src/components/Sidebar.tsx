"use client";

import { useAppStore } from "@/store/useAppStore";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { AgentType } from "@/types";

const agents: { id: AgentType; label: string; icon: string; description: string }[] = [
    { id: "career", label: "Career", icon: "🎯", description: "Jobs, resume, interviews" },
    { id: "life", label: "Life", icon: "🌱", description: "Goals, habits, health" },
    { id: "learning", label: "Learning", icon: "📚", description: "Courses, study plans" },
    { id: "settings", label: "Settings", icon: "⚙️", description: "Profile management" },
];

export default function Sidebar() {
    const { activeAgent, setActiveAgent, tasks } = useAppStore();

    const getTaskCount = (agent: AgentType) =>
        tasks.filter((t) => t.agent_group === agent && (t.status === "running" || t.status === "pending")).length;

    return (
        <aside className="hidden md:flex flex-col w-64 border-r border-white/10 bg-[#0d1117] p-4 gap-2">
            {/* Logo */}
            <div className="flex items-center gap-2 px-2 mb-4">
                <span className="text-2xl">🔭</span>
                <h1 className="text-lg font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                    LifeScout
                </h1>
            </div>

            <Separator className="bg-white/10 mb-2" />

            {/* Agent Buttons */}
            <nav className="flex flex-col gap-1">
                {agents.map((agent) => {
                    const count = getTaskCount(agent.id);
                    return (
                        <Button
                            key={agent.id}
                            variant={activeAgent === agent.id ? "secondary" : "ghost"}
                            className={cn(
                                "justify-start gap-3 h-12 px-3 transition-all duration-200",
                                activeAgent === agent.id
                                    ? "bg-blue-500/15 text-blue-400 border border-blue-500/30"
                                    : "text-gray-400 hover:text-white hover:bg-white/5"
                            )}
                            onClick={() => setActiveAgent(agent.id)}
                        >
                            <span className="text-lg">{agent.icon}</span>
                            <div className="flex flex-col items-start">
                                <span className="text-sm font-medium">{agent.label}</span>
                                <span className="text-[10px] text-gray-500">{agent.description}</span>
                            </div>
                            {count > 0 && (
                                <Badge variant="secondary" className="ml-auto bg-purple-500/20 text-purple-400 text-[10px] px-1.5">
                                    {count}
                                </Badge>
                            )}
                        </Button>
                    );
                })}
            </nav>

            <div className="mt-auto">
                <Separator className="bg-white/10 mb-3" />
                <p className="text-[10px] text-gray-600 text-center">LifeScout AI v1.0</p>
            </div>
        </aside>
    );
}
