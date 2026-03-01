"use client";

import { useAppStore } from "@/store/useAppStore";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Bell, Check, ExternalLink } from "lucide-react";
import { useState, useEffect } from "react";
import type { AgentType } from "@/types";

const agents: { id: AgentType; label: string; icon: string; description: string }[] = [
    { id: "career", label: "Career", icon: "🎯", description: "Jobs, resume, interviews" },
    { id: "life", label: "Life", icon: "🌱", description: "Goals, habits, health" },
    { id: "learning", label: "Learning", icon: "📚", description: "Courses, study plans" },
    { id: "settings", label: "Settings", icon: "⚙️", description: "Profile management" },
];

export default function Sidebar() {
    const { activeAgent, setActiveAgent, tasks, notifications, unreadCount, fetchNotifications, markNotificationRead } = useAppStore();
    const [showNotifications, setShowNotifications] = useState(false);

    useEffect(() => {
        fetchNotifications();
        const interval = setInterval(fetchNotifications, 30000);
        return () => clearInterval(interval);
    }, [fetchNotifications]);

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

            <div className="mt-auto flex flex-col gap-2">
                <div className="relative">
                    <Button
                        variant="ghost"
                        className="w-full justify-start gap-3 h-10 px-3 text-gray-400 hover:text-white hover:bg-white/5"
                        onClick={() => setShowNotifications(!showNotifications)}
                    >
                        <Bell className="h-4 w-4" />
                        <span className="text-sm font-medium">Notifications</span>
                        {unreadCount > 0 && (
                            <Badge variant="destructive" className="ml-auto text-[10px] px-1.5 h-4">
                                {unreadCount}
                            </Badge>
                        )}
                    </Button>

                    {showNotifications && (
                        <div className="absolute bottom-12 left-0 w-80 max-h-[400px] overflow-y-auto bg-[#1a1f2e] border border-white/10 rounded-lg shadow-xl z-50 p-2 flex flex-col gap-2">
                            <div className="flex items-center justify-between px-2 pb-2 border-b border-white/10">
                                <span className="font-semibold text-sm">Recent Activity</span>
                                <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => setShowNotifications(false)}>Close</Button>
                            </div>
                            {notifications.length === 0 ? (
                                <div className="text-center text-gray-500 text-xs py-4">No notifications</div>
                            ) : (
                                notifications.map(n => (
                                    <div key={n.id} className={cn("p-3 rounded-md border text-sm flex flex-col gap-1 transition-colors", n.read ? "border-transparent bg-white/5 opacity-70" : "border-blue-500/30 bg-blue-500/10")}>
                                        <div className="flex items-start justify-between gap-2">
                                            <span className="font-medium text-white">{n.title}</span>
                                            {!n.read && (
                                                <Button variant="ghost" size="icon" className="h-5 w-5 hover:bg-transparent hover:text-white" onClick={(e) => { e.stopPropagation(); markNotificationRead(n.id); }} title="Mark as read">
                                                    <Check className="h-3 w-3 text-blue-400" />
                                                </Button>
                                            )}
                                        </div>
                                        <p className="text-xs text-gray-300 line-clamp-2">{n.message}</p>
                                        <div className="flex items-center justify-between mt-1">
                                            <span className="text-[10px] text-gray-500">{new Date(n.timestamp * 1000).toLocaleTimeString()}</span>
                                            {n.link && (
                                                <a href={n.link} target="_blank" rel="noreferrer" className="text-xs text-blue-400 flex items-center gap-1 hover:underline">
                                                    View <ExternalLink className="h-3 w-3" />
                                                </a>
                                            )}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>

                <Separator className="bg-white/10" />
                <p className="text-[10px] text-gray-600 text-center pb-1">LifeScout AI v1.0</p>
            </div>
        </aside>
    );
}
