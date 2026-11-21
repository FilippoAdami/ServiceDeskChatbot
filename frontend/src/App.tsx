import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Header } from "./components/Header";
import { EmployeePlaceholder } from "./components/EmployeePlaceholder";
import { TechnicianPlaceholder } from "./components/TechnicianPlaceholder";
import { useHealth } from "./hooks/useHealth";
import type { ActiveView } from "./components/ViewSwitch";

export const App: React.FC = () => {
  const [activeView, setActiveView] = useState<ActiveView>("employee");
  const healthState = useHealth();

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <Header
        activeView={activeView}
        onViewChange={setActiveView}
        healthState={healthState}
      />

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 sm:py-8">
        <AnimatePresence mode="wait">
          {activeView === "employee" ? (
            <motion.div
              key="employee"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              <EmployeePlaceholder />
            </motion.div>
          ) : (
            <motion.div
              key="technician"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              <TechnicianPlaceholder />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="border-t border-border/60 bg-card/40 py-4 text-xs text-muted-foreground">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 sm:flex-row sm:px-6">
          <span>
            Service Desk AI Assistant • Architettura Locale (React + FastAPI + SQLite)
          </span>
          <div className="flex items-center gap-3">
            <span>Milestone G01: Fondazioni Eseguibili</span>
            <span>•</span>
            <span>UTC {healthState.data?.timestamp ? new Date(healthState.data.timestamp).toLocaleTimeString() : "--:--:--"}</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
