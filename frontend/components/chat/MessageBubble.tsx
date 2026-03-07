import { Bot, User } from "lucide-react";
import { Message } from "@/lib/types";
import RequirementsView from "@/components/artifacts/RequirementsView";
import MockupView from "@/components/artifacts/MockupView";

// Code block component for the JSON in screenshot 2
const CodeBlock = ({ code }: { code: string }) => (
  <div className="bg-white border border-gray-200 rounded-lg p-4 mt-2 font-mono text-xs text-green-600 overflow-x-auto shadow-sm">
    <pre>{code}</pre>
  </div>
);

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex w-full mb-8 ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`flex max-w-[80%] ${isUser ? "flex-row-reverse" : "flex-row"} gap-4`}>
        
        {/* Avatar */}
        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1
          ${isUser 
            ? "bg-emerald-100" 
            : message.avatarColor === "orange" 
              ? "bg-orange-100 text-orange-600"
              : "bg-purple-600 text-white"
          }`}
        >
          {isUser ? (
            <img src="/api/placeholder/32/32" alt="User" className="w-8 h-8 rounded-full" />
          ) : (
            <Bot size={18} />
          )}
        </div>

        {/* Content Content */}
        <div className="flex flex-col gap-1">
          {/* Agent Name */}
          {!isUser && (
            <span className="text-xs font-bold text-gray-500 ml-1">
              {message.agentName || "Agent"} <span className="text-gray-300 font-normal ml-2">{message.timestamp}</span>
            </span>
          )}

          {/* Bubble */}
          <div
            className={`px-5 py-3.5 text-sm leading-relaxed shadow-sm
              ${isUser 
                ? "bg-blue-600 text-white rounded-2xl rounded-tr-sm" // User: Blue, Sharp top-right corner
                : "bg-white border border-gray-100 text-gray-700 rounded-2xl rounded-tl-sm" // Agent: White, Sharp top-left
              }`}
          >
             {/* Text Content */}
            {message.content && <div className="whitespace-pre-wrap">{message.content}</div>}
            
            {/* Inline Artifacts */}
            {message.artifact?.type === "code" && (
                <CodeBlock code={message.artifact.content} />
            )}
          </div>

          {/* Large Artifact Cards (Rendered outside the small bubble, but inside the message block) */}
          {message.artifact?.type === "requirements" && <RequirementsView />}
          {message.artifact?.type === "figma" && <MockupView />}
          
        </div>
      </div>
    </div>
  );
}