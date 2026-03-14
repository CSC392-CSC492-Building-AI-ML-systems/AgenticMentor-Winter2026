"use client";
import { FileText, CheckCircle2 } from "lucide-react";
import { useProjectStore } from "@/store/useProjectStore";

export default function RequirementPanel() {
  const { requirements, currentPhase, isLoading } = useProjectStore();

  const features: string[] = requirements?.key_features ?? requirements?.functional ?? [];
  const constraints: string[] = requirements?.technical_constraints ?? requirements?.constraints ?? [];
  const goals: string[] = requirements?.business_goals ?? [];
  const users: string[] = requirements?.target_users ?? [];
  const isComplete: boolean = !!requirements?.is_complete;
  const progress: number = requirements?.progress ?? 0;
  const hasData = !!(requirements?.project_type || features.length || constraints.length);

  return (
    <>
      <div className="h-10 border-b border-gray-300 dark:border-[#444] flex items-center justify-between px-4 bg-gray-50 dark:bg-black flex-shrink-0 transition-colors">
        <div className="flex items-center gap-2 text-black dark:text-white">
          <FileText size={12} />
          <span className="text-[10px] tracking-widest uppercase font-bold">Project_Requirements</span>
        </div>
        <div className="flex gap-2 items-center">
          {hasData && (
            <span className="text-[9px] font-bold uppercase tracking-widest text-gray-500">
              {Math.round(progress * 100)}%
            </span>
          )}
          <span className={`text-[9px] border px-2 py-1 font-bold uppercase tracking-widest flex items-center gap-1
            ${isComplete
              ? "border-green-200 dark:border-green-900/50 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400"
              : "border-blue-200 dark:border-blue-900/50 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400"
            }`}>
            Status: {isComplete ? "Complete" : hasData ? "In Progress" : "Pending"}
          </span>
        </div>
      </div>

      <div className="p-6 overflow-y-auto flex-1 bg-white dark:bg-black transition-colors">
        {isLoading && !hasData && (
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest animate-pulse">
            -- LOADING REQUIREMENTS --
          </p>
        )}

        {!isLoading && !hasData && (
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">
            -- NO REQUIREMENTS YET. USE THE CONSOLE TO CHAT WITH THE REQUIREMENTS COLLECTOR AGENT --
          </p>
        )}

        {hasData && (
          <div className="space-y-6">
            <div className="mb-6 pb-4 border-b border-gray-200 dark:border-[#333]">
              <h1 className="text-lg font-bold text-black dark:text-white mb-1 tracking-tight uppercase">
                {requirements?.project_type ?? "Project Requirements"}
              </h1>
              <p className="text-xs text-gray-500 font-mono">&gt; Phase: {currentPhase}</p>
            </div>

            {features.length > 0 && (
              <div className="border border-gray-200 dark:border-[#333] bg-gray-50 dark:bg-[#050505] p-4 transition-colors">
                <h3 className="text-xs font-bold text-black dark:text-white uppercase tracking-widest mb-3 border-b border-gray-200 dark:border-[#333] pb-2 flex items-center gap-2">
                  <CheckCircle2 size={14} className="text-green-600 dark:text-green-500" />
                  Core Features
                </h3>
                <ul className="space-y-2 font-mono text-sm text-gray-700 dark:text-gray-300">
                  {features.map((f, i) => (
                    <li key={i} className="flex gap-3">
                      <span className="text-gray-400 dark:text-gray-600">{String(i + 1).padStart(2, "0")}</span>
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {constraints.length > 0 && (
              <div className="border border-gray-200 dark:border-[#333] bg-gray-50 dark:bg-[#050505] p-4 transition-colors">
                <h3 className="text-xs font-bold text-black dark:text-white uppercase tracking-widest mb-3 border-b border-gray-200 dark:border-[#333] pb-2">
                  Technical Constraints
                </h3>
                <ul className="space-y-2 font-mono text-sm text-gray-700 dark:text-gray-300">
                  {constraints.map((c, i) => (
                    <li key={i} className="flex gap-3">
                      <span className="text-gray-400 dark:text-gray-600">{String(i + 1).padStart(2, "0")}</span>
                      {c}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {(users.length > 0 || goals.length > 0) && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {users.length > 0 && (
                  <div className="border border-gray-200 dark:border-[#333] bg-gray-50 dark:bg-[#050505] p-4 transition-colors">
                    <h3 className="text-xs font-bold text-black dark:text-white uppercase tracking-widest mb-2">Target Users</h3>
                    <ul className="space-y-1 text-sm font-mono text-gray-700 dark:text-gray-300">
                      {users.map((u, i) => <li key={i}>&gt; {u}</li>)}
                    </ul>
                  </div>
                )}
                {goals.length > 0 && (
                  <div className="border border-gray-200 dark:border-[#333] bg-gray-50 dark:bg-[#050505] p-4 transition-colors">
                    <h3 className="text-xs font-bold text-black dark:text-white uppercase tracking-widest mb-2">Business Goals</h3>
                    <ul className="space-y-1 text-sm font-mono text-gray-700 dark:text-gray-300">
                      {goals.map((g, i) => <li key={i}>&gt; {g}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {(requirements?.timeline || requirements?.budget) && (
              <div className="flex gap-6 text-xs font-mono text-gray-500">
                {requirements.timeline && <span>Timeline: {requirements.timeline}</span>}
                {requirements.budget && <span>Budget: {requirements.budget}</span>}
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}