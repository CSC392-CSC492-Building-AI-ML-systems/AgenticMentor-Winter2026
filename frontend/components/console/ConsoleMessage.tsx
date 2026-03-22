import { Message } from "@/lib/types";

export default function ConsoleMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const isSystem = message.agentName === "System";

  const nameColor = isUser
    ? "text-blue-500 dark:text-blue-400"
    : isSystem
    ? "text-emerald-400 dark:text-emerald-400"
    : "text-gray-500 dark:text-gray-400";

  const bodyColor = isUser
    ? "text-gray-800 dark:text-gray-200"
    : isSystem
    ? "text-emerald-600 dark:text-emerald-300 font-mono"
    : "text-gray-600 dark:text-gray-400";

  return (
    <div className="font-mono text-[13px] mb-5 group hover:bg-gray-50 dark:hover:bg-[#0d0d0d] px-2 py-2 -mx-2 transition-colors rounded">
      {/* Name + timestamp row */}
      <div className="flex items-center gap-2 mb-1.5">
        <span className={`font-bold uppercase tracking-widest text-[11px] ${nameColor}`}>
          {isUser ? "You" : (message.agentName ?? "Orchestrator")}
        </span>
        <span className="text-[10px] text-gray-300 dark:text-gray-600">{message.timestamp}</span>
      </div>
      {/* Message body */}
      <div className={`text-[13px] leading-[1.55] whitespace-pre-wrap pl-1 ${bodyColor}`}>
        {message.content}
      </div>
    </div>
  );
}
