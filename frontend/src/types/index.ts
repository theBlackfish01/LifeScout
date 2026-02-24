/**
 * Shared TypeScript interfaces for the LifeScouter frontend.
 */

export interface ChatMessage {
    id: string;
    role: "user" | "ai" | "system";
    content: string;
    agentName?: string;
    timestamp: number;
}

export interface UserDemographics {
    age?: number;
    occupation?: string;
    location?: string;
}

export interface UserGoals {
    career?: string[];
    life?: string[];
    learning?: string[];
}

export interface UserConstraints {
    budget?: string;
    time_per_week?: string;
    geographic?: string;
}

export interface UserPreferences {
    working_style?: string;
    communication?: string;
}

export interface UserProfile {
    demographics?: UserDemographics;
    current_situation?: string;
    goals?: UserGoals;
    constraints?: UserConstraints;
    preferences?: UserPreferences;
    onboarding_complete: boolean;
}

export interface TaskPlan {
    steps: string[];
    estimated_time?: string;
}

export interface TaskResult {
    artifact_ids: string[];
    summary: string;
}

export interface Task {
    id: string;
    trigger: "user_initiated" | "scheduled";
    agent_group: "career" | "life" | "learning";
    sub_agent: string;
    title: string;
    plan: TaskPlan;
    status: "pending" | "running" | "completed" | "failed" | "cancelled";
    thread_id: string;
    created_at: string;
    completed_at?: string;
    result: TaskResult;
}

export interface Artifact {
    id: string;
    agent_group: string;
    filename: string;
    title: string;
    format: string;
    created_at: string;
}

export type AgentType = "career" | "life" | "learning" | "settings";
