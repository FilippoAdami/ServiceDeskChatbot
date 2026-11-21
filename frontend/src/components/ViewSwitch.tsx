import React from "react";
import { User, Wrench } from "lucide-react";
import { motion } from "framer-motion";

export type ActiveView = "employee" | "technician";

interface ViewSwitchProps {
  activeView: ActiveView;
  onViewChange: (view: ActiveView) => void;
}

export const ViewSwitch: React.FC<ViewSwitchProps> = ({ activeView, onViewChange }) => {
  return (
    <div
      role="tablist"
      aria-label="Selezione Vista Ruolo"
      className="inline-flex items-center rounded-xl border border-border bg-card/80 p-1.5 shadow-sm backdrop-blur-md"
    >
      <button
        role="tab"
        id="tab-employee"
        aria-selected={activeView === "employee"}
        aria-controls="panel-employee"
        onClick={() => onViewChange("employee")}
        className={`relative flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
          activeView === "employee"
            ? "text-primary-foreground font-semibold"
            : "text-muted-foreground hover:text-foreground"
        }`}
      >
        {activeView === "employee" && (
          <motion.div
            layoutId="active-view-indicator"
            className="absolute inset-0 rounded-lg bg-primary shadow-md"
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
          />
        )}
        <span className="relative z-10 flex items-center gap-2">
          <User className="h-4 w-4" />
          <span>Vista Dipendente</span>
        </span>
      </button>

      <button
        role="tab"
        id="tab-technician"
        aria-selected={activeView === "technician"}
        aria-controls="panel-technician"
        onClick={() => onViewChange("technician")}
        className={`relative flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
          activeView === "technician"
            ? "text-primary-foreground font-semibold"
            : "text-muted-foreground hover:text-foreground"
        }`}
      >
        {activeView === "technician" && (
          <motion.div
            layoutId="active-view-indicator"
            className="absolute inset-0 rounded-lg bg-primary shadow-md"
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
          />
        )}
        <span className="relative z-10 flex items-center gap-2">
          <Wrench className="h-4 w-4" />
          <span>Vista Tecnico</span>
        </span>
      </button>
    </div>
  );
};
