import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Header } from "./components/Header";
import { EmployeeView } from "./components/EmployeeView";
import { TechnicianView } from "./components/TechnicianView";
import { DebugView } from "./components/DebugView";
import { useHealth } from "./hooks/useHealth";
import type { ActiveView } from "./components/ViewSwitch";

export const App: React.FC = () => {
  const [activeView, setActiveView] = useState<ActiveView>("employee");
  const healthState = useHealth();

  return (
    <div className="relative flex h-screen flex-col overflow-hidden bg-[#0b101b] text-foreground">
      {/* Ambient luminous glow & texture background for translucent glass effects */}
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-40 -left-40 h-[28rem] w-[28rem] rounded-full bg-blue-600/15 blur-[100px]" />
        <div className="absolute top-1/3 -right-40 h-[32rem] w-[32rem] rounded-full bg-cyan-500/12 blur-[120px]" />
        <div className="absolute -bottom-40 left-1/3 h-[28rem] w-[28rem] rounded-full bg-indigo-600/15 blur-[110px]" />
        <div className="absolute inset-0 bg-[radial-gradient(rgba(255,255,255,0.06)_1px,transparent_1px)] [background-size:24px_24px] opacity-40" />
      </div>

      <div className="shrink-0">
        <Header
          activeView={activeView}
          onViewChange={setActiveView}
          healthState={healthState}
        />
      </div>

      <main className="mx-auto w-full max-w-7xl flex-1 min-h-0 px-3 py-3 sm:px-6 sm:py-4 flex flex-col overflow-hidden">
        <AnimatePresence mode="wait">
          {activeView === "employee" ? (
            <motion.div
              key="employee"
              className="h-full min-h-0 flex flex-col"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              <EmployeeView />
            </motion.div>
          ) : activeView === "technician" ? (
            <motion.div
              key="technician"
              className="h-full min-h-0 flex flex-col"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              <TechnicianView />
            </motion.div>
          ) : (
            <motion.div
              key="debug"
              className="h-full min-h-0 flex flex-col overflow-y-auto pr-1"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              <DebugView />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="shrink-0 border-t border-white/10 bg-card/60 backdrop-blur-md py-2.5 text-xs text-muted-foreground z-10">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-1.5 px-4 sm:flex-row sm:px-6">
          <span>
            Service Desk AI Assistant • Architettura Locale (React + FastAPI + SQLite)
          </span>
          <div className="flex items-center gap-3">
            <span>Milestone G04: Agente Gemini & RAG Operativo</span>
            <span>•</span>
            <span>
              UTC{" "}
              {healthState.data?.timestamp
                ? new Date(healthState.data.timestamp).toLocaleTimeString()
                : "--:--:--"}
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
