"use client";

import { useEffect, useState } from "react";
import { useAppStore } from "@/store/useAppStore";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import ChatWindow from "@/components/chat/ChatWindow";
import DashboardDrawer from "@/components/dashboard/DashboardDrawer";
import OnboardingModal from "@/components/onboarding/OnboardingModal";

export default function Home() {
  const { fetchProfile, onboardingComplete } = useAppStore();
  const [dashboardOpen, setDashboardOpen] = useState(false);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0a0f1a]">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className="flex flex-col flex-1 min-w-0">
        <Header onToggleDashboard={() => setDashboardOpen(true)} />
        <ChatWindow />
      </div>

      {/* Dashboard Drawer */}
      <DashboardDrawer open={dashboardOpen} onOpenChange={setDashboardOpen} />

      {/* Onboarding Gate */}
      {!onboardingComplete && <OnboardingModal />}
    </div>
  );
}
