"use client";

import { useEffect } from "react";
import { useAppStore } from "@/store/useAppStore";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface DashboardDrawerProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

const statusColor: Record<string, string> = {
    running: "bg-green-500/20 text-green-400",
    pending: "bg-yellow-500/20 text-yellow-400",
    completed: "bg-blue-500/20 text-blue-400",
    failed: "bg-red-500/20 text-red-400",
    cancelled: "bg-gray-500/20 text-gray-400",
};

export default function DashboardDrawer({ open, onOpenChange }: DashboardDrawerProps) {
    const { tasks, fetchTasks, artifacts, fetchArtifacts } = useAppStore();

    useEffect(() => {
        if (open) {
            fetchTasks();
            fetchArtifacts();
        }
    }, [open, fetchTasks, fetchArtifacts]);

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent className="w-[400px] sm:w-[450px] bg-[#0d1117] border-white/10 text-white">
                <SheetHeader>
                    <SheetTitle className="text-white">📊 Dashboard</SheetTitle>
                </SheetHeader>

                <Tabs defaultValue="tasks" className="mt-4">
                    <TabsList className="bg-[#1a1f2e] border border-white/10 w-full">
                        <TabsTrigger value="tasks" className="flex-1 data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
                            Tasks
                        </TabsTrigger>
                        <TabsTrigger value="artifacts" className="flex-1 data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-400">
                            Artifacts
                        </TabsTrigger>
                    </TabsList>

                    {/* Tasks Tab */}
                    <TabsContent value="tasks">
                        <ScrollArea className="h-[calc(100vh-200px)]">
                            <div className="flex flex-col gap-2 pr-2">
                                {tasks.length === 0 ? (
                                    <p className="text-sm text-gray-500 text-center py-8">No tasks yet.</p>
                                ) : (
                                    tasks.map((task) => (
                                        <Card key={task.id} className="bg-[#1a1f2e] border-white/5">
                                            <CardHeader className="py-3 px-4">
                                                <div className="flex items-center justify-between">
                                                    <CardTitle className="text-sm text-white">{task.title}</CardTitle>
                                                    <Badge className={statusColor[task.status] || "bg-gray-500/20 text-gray-400"}>
                                                        {task.status}
                                                    </Badge>
                                                </div>
                                            </CardHeader>
                                            <CardContent className="px-4 pb-3 pt-0">
                                                <p className="text-[11px] text-gray-500">
                                                    {task.agent_group} / {task.sub_agent}
                                                </p>
                                            </CardContent>
                                        </Card>
                                    ))
                                )}
                            </div>
                        </ScrollArea>
                    </TabsContent>

                    {/* Artifacts Tab */}
                    <TabsContent value="artifacts">
                        <ScrollArea className="h-[calc(100vh-200px)]">
                            <div className="flex flex-col gap-2 pr-2">
                                {artifacts.length === 0 ? (
                                    <p className="text-sm text-gray-500 text-center py-8">No artifacts generated yet.</p>
                                ) : (
                                    artifacts.map((artifact) => (
                                        <Card key={artifact.id} className="bg-[#1a1f2e] border-white/5">
                                            <CardHeader className="py-3 px-4">
                                                <CardTitle className="text-sm text-white">{artifact.title || artifact.filename}</CardTitle>
                                            </CardHeader>
                                            <CardContent className="px-4 pb-3 pt-0 flex items-center justify-between">
                                                <p className="text-[11px] text-gray-500">{artifact.agent_group}</p>
                                                <a
                                                    href={`${API_BASE}/api/artifacts/files/${artifact.agent_group}/${artifact.filename}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-[11px] text-blue-400 hover:underline"
                                                >
                                                    Download ↓
                                                </a>
                                            </CardContent>
                                        </Card>
                                    ))
                                )}
                            </div>
                        </ScrollArea>
                    </TabsContent>
                </Tabs>
            </SheetContent>
        </Sheet>
    );
}
