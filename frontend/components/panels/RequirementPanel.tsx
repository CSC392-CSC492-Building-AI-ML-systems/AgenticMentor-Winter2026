"use client";
import { FileText, CheckCircle2, Circle, Users, Target, Zap, Lock, AlertTriangle, Clock, DollarSign, Layers } from "lucide-react";
import { useProjectStore } from "@/store/useProjectStore";

function SectionCard({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="border border-gray-200 dark:border-[#222] bg-white dark:bg-[#050505] transition-colors">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-gray-200 dark:border-[#222] bg-gray-50 dark:bg-[#0a0a0a]">
        <span className="text-gray-500 dark:text-gray-400">{icon}</span>
        <span className="text-[10px] font-bold uppercase tracking-widest text-black dark:text-white">{title}</span>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function ListItems({ items, accent }: { items: string[]; accent?: string }) {
  return (
    <ul className="space-y-2">
      {items.map((item, i) => (
        <li key={i} className="flex gap-3 text-[13px] font-mono leading-[1.5]">
          <span className={`font-bold shrink-0 ${accent ?? "text-gray-300 dark:text-gray-600"}`}>
            {String(i + 1).padStart(2, "0")}
          </span>
          <span className="text-gray-700 dark:text-gray-300">{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function RequirementPanel() {
  const { requirements, currentPhase, isLoading } = useProjectStore();

  const appName: string = requirements?.app_name ?? requirements?.project_type ?? "Untitled Project";
  const projectType: string = requirements?.project_type ?? "";
  const functional: string[] = requirements?.functional ?? requirements?.key_features ?? [];
  const nonFunctional: string[] = requirements?.non_functional ?? [];
  const constraints: string[] = requirements?.constraints ?? requirements?.technical_constraints ?? [];
  const userStories: any[] = requirements?.user_stories ?? [];
  const gaps: string[] = requirements?.gaps ?? [];
  const users: string[] = requirements?.target_users ?? [];
  const goals: string[] = requirements?.business_goals ?? [];
  const timeline: string = requirements?.timeline ?? "";
  const budget: string = requirements?.budget ?? "";
  const isComplete: boolean = !!requirements?.is_complete;
  const progress: number = requirements?.progress ?? 0;
  const progressPct = Math.round(progress * 100);

  const hasData = !!(requirements?.project_type || requirements?.app_name || functional.length);

  return (
    <div className="flex flex-col h-full">
      {/* Header bar */}
      <div className="h-10 border-b border-gray-300 dark:border-[#444] flex items-center justify-between px-4 bg-gray-50 dark:bg-black flex-shrink-0 transition-colors">
        <div className="flex items-center gap-2">
          <FileText size={12} className="text-black dark:text-white" />
          <span className="text-[10px] tracking-widest uppercase font-bold text-black dark:text-white">Project_Requirements</span>
        </div>
        <div className="flex items-center gap-3">
          {hasData && (
            <span className="text-[10px] font-bold font-mono text-gray-500 dark:text-gray-400">
              {progressPct}% complete
            </span>
          )}
          <span className={`text-[9px] border px-2 py-1 font-bold uppercase tracking-widest flex items-center gap-1.5 transition-colors
            ${isComplete
              ? "border-green-300 dark:border-green-800 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400"
              : hasData
              ? "border-blue-200 dark:border-blue-900/50 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400"
              : "border-gray-200 dark:border-[#333] text-gray-400"
            }`}>
            {isComplete ? <CheckCircle2 size={9} /> : <Circle size={9} />}
            {isComplete ? "Complete" : hasData ? "In Progress" : "Pending"}
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-gray-100 dark:bg-[#080808] transition-colors">
        {/* Empty states */}
        {isLoading && !hasData && (
          <div className="flex items-center justify-center h-full">
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest animate-pulse">
              -- LOADING REQUIREMENTS --
            </p>
          </div>
        )}
        {!isLoading && !hasData && (
          <div className="flex items-center justify-center h-full">
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest text-center px-8">
              -- NO REQUIREMENTS YET. USE THE CONSOLE TO START COLLECTING --
            </p>
          </div>
        )}

        {hasData && (
          <div className="p-6 space-y-5">

            {/* Project identity block */}
            <div className="border border-gray-200 dark:border-[#222] bg-white dark:bg-[#050505] p-5 transition-colors">
              <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                  <p className="text-[10px] text-gray-400 dark:text-gray-500 uppercase tracking-widest font-mono mb-1">App Name</p>
                  <h1 className="text-2xl font-bold text-black dark:text-white tracking-tight leading-tight">
                    {appName}
                  </h1>
                  {projectType && projectType !== appName && (
                    <p className="text-[11px] text-gray-500 dark:text-gray-400 font-mono mt-1 uppercase tracking-widest">{projectType}</p>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <p className="text-[10px] text-gray-400 dark:text-gray-500 uppercase tracking-widest font-mono mb-1">Phase</p>
                  <p className="text-xs font-bold text-black dark:text-white uppercase tracking-widest font-mono">{currentPhase}</p>
                </div>
              </div>

              {/* Progress bar */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-[10px] text-gray-400 dark:text-gray-500 uppercase tracking-widest font-mono">Collection Progress</span>
                  <span className="text-[10px] font-bold text-black dark:text-white font-mono">{progressPct}%</span>
                </div>
                <div className="h-1.5 bg-gray-100 dark:bg-[#1a1a1a] w-full">
                  <div
                    className={`h-full transition-all duration-500 ${isComplete ? "bg-green-500" : "bg-black dark:bg-white"}`}
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              </div>

              {/* Meta row: timeline + budget */}
              {(timeline || budget) && (
                <div className="flex gap-6 mt-4 pt-4 border-t border-gray-100 dark:border-[#1a1a1a]">
                  {timeline && (
                    <div className="flex items-center gap-2 text-xs font-mono text-gray-600 dark:text-gray-400">
                      <Clock size={11} className="text-gray-400" />
                      <span className="text-gray-400 uppercase text-[10px]">Timeline:</span>
                      <span className="font-bold text-black dark:text-white">{timeline}</span>
                    </div>
                  )}
                  {budget && (
                    <div className="flex items-center gap-2 text-xs font-mono text-gray-600 dark:text-gray-400">
                      <DollarSign size={11} className="text-gray-400" />
                      <span className="text-gray-400 uppercase text-[10px]">Budget:</span>
                      <span className="font-bold text-black dark:text-white">{budget}</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Two-column grid */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

              {/* Functional Requirements */}
              {functional.length > 0 && (
                <SectionCard icon={<Zap size={12} />} title="Functional Requirements">
                  <ListItems items={functional} accent="text-blue-400 dark:text-blue-500" />
                </SectionCard>
              )}

              {/* Non-Functional Requirements */}
              {nonFunctional.length > 0 && (
                <SectionCard icon={<Layers size={12} />} title="Non-Functional Requirements">
                  <ListItems items={nonFunctional} accent="text-purple-400 dark:text-purple-500" />
                </SectionCard>
              )}

              {/* Technical Constraints */}
              {constraints.length > 0 && (
                <SectionCard icon={<Lock size={12} />} title="Technical Constraints">
                  <ListItems items={constraints} accent="text-orange-400 dark:text-orange-500" />
                </SectionCard>
              )}

              {/* Business Goals */}
              {goals.length > 0 && (
                <SectionCard icon={<Target size={12} />} title="Business Goals">
                  <ListItems items={goals} accent="text-green-400 dark:text-green-500" />
                </SectionCard>
              )}

              {/* Target Users */}
              {users.length > 0 && (
                <SectionCard icon={<Users size={12} />} title="Target Users">
                  <div className="flex flex-wrap gap-2">
                    {users.map((u, i) => (
                      <span key={i} className="text-[11px] font-mono font-bold px-3 py-1.5 border border-gray-200 dark:border-[#333] text-black dark:text-white bg-gray-50 dark:bg-[#111] uppercase tracking-wide">
                        {u}
                      </span>
                    ))}
                  </div>
                </SectionCard>
              )}

              {/* Gaps / Unknowns */}
              {gaps.length > 0 && (
                <SectionCard icon={<AlertTriangle size={12} />} title="Open Questions & Gaps">
                  <ListItems items={gaps} accent="text-yellow-400 dark:text-yellow-500" />
                </SectionCard>
              )}
            </div>

            {/* User Stories — full width */}
            {userStories.length > 0 && (
              <SectionCard icon={<Users size={12} />} title="User Stories">
                <div className="space-y-3">
                  {userStories.map((story: any, i: number) => (
                    <div key={i} className="border border-gray-100 dark:border-[#1a1a1a] p-3 bg-gray-50 dark:bg-[#0a0a0a]">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 bg-black dark:bg-white text-white dark:text-black font-mono">
                          {story.role}
                        </span>
                      </div>
                      <p className="text-[13px] font-mono text-gray-700 dark:text-gray-300 leading-[1.5] mt-1.5">
                        I want to <span className="text-black dark:text-white font-bold">{story.goal}</span>
                        {story.reason && (
                          <span className="text-gray-500 dark:text-gray-500"> so that {story.reason}</span>
                        )}
                      </p>
                    </div>
                  ))}
                </div>
              </SectionCard>
            )}

          </div>
        )}
      </div>
    </div>
  );
}
