import ReactMarkdown from "react-markdown";
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
    ? "text-emerald-600 dark:text-emerald-300"
    : "text-gray-600 dark:text-gray-400";

  return (
    <div className="font-mono text-[13px] mb-5 group hover:bg-gray-50 dark:hover:bg-[#0d0d0d] px-2 py-2 -mx-2 transition-colors rounded">
      <div className="flex items-center gap-2 mb-1.5">
        <span className={`font-bold uppercase tracking-widest text-[11px] ${nameColor}`}>
          {isUser ? "You" : (message.agentName ?? "Orchestrator")}
        </span>
        <span className="text-[10px] text-gray-300 dark:text-gray-600">{message.timestamp}</span>
      </div>

      {isUser ? (
        <div className={`text-[13px] leading-[1.55] whitespace-pre-wrap pl-1 ${bodyColor}`}>
          {message.content}
        </div>
      ) : (
        <div className={`pl-1 ${bodyColor} markdown-body`}>
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="text-[13px] leading-[1.55] mb-2 last:mb-0">{children}</p>,
              strong: ({ children }) => <strong className="font-bold text-black dark:text-white">{children}</strong>,
              em: ({ children }) => <em className="italic">{children}</em>,
              ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
              li: ({ children }) => <li className="text-[13px] leading-[1.55]">{children}</li>,
              code: ({ children }) => <code className="bg-gray-100 dark:bg-[#1a1a1a] text-black dark:text-white px-1 py-0.5 text-[11px] rounded">{children}</code>,
              pre: ({ children }) => <pre className="bg-gray-100 dark:bg-[#1a1a1a] p-3 mb-2 overflow-x-auto text-[11px] rounded">{children}</pre>,
              h1: ({ children }) => <h1 className="font-bold text-[15px] text-black dark:text-white mb-1">{children}</h1>,
              h2: ({ children }) => <h2 className="font-bold text-[14px] text-black dark:text-white mb-1">{children}</h2>,
              h3: ({ children }) => <h3 className="font-bold text-[13px] text-black dark:text-white mb-1">{children}</h3>,
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}
