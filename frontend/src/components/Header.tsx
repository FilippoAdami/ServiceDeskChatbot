import React from "react";
import { Headset } from "lucide-react";
import { ViewSwitch, type ActiveView } from "./ViewSwitch";
import { ConnectionBadge } from "./ConnectionBadge";
import type { UseHealthResult } from "../hooks/useHealth";

interface HeaderProps {
  activeView: ActiveView;
  onViewChange: (view: ActiveView) => void;
  healthState: UseHealthResult;
}

export const Header: React.FC<HeaderProps> = ({
  activeView,
  onViewChange,
  healthState,
}) => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-card/50 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6 sm:py-4">
        {/* Brand / Title */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <Headset className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-foreground sm:text-xl">
                Service Desk AI
              </h1>
              <span className="rounded-md bg-secondary px-2 py-0.5 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Prototipo Locale
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Supporto IT Interno • 500 Dipendenti
            </p>
          </div>
        </div>

        {/* View switcher and status */}
        <div className="flex flex-wrap items-center gap-3 sm:gap-4">
          <ConnectionBadge healthState={healthState} />
          <ViewSwitch activeView={activeView} onViewChange={onViewChange} />
        </div>
      </div>
    </header>
  );
};
