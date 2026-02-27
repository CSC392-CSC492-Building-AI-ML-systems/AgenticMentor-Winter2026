import { Message } from "@/lib/types"; 

export default function ConsoleMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";

  const getColor = (color?: string) => {
    switch (color) {
      case "purple": return "text-purple-600 dark:text-purple-400";
      case "blue": return "text-blue-600 dark:text-blue-400";
      case "red": return "text-red-600 dark:text-red-400";
      case "orange": return "text-orange-600 dark:text-orange-400";
      case "green": return "text-green-600 dark:text-green-400";
      default: return "text-black dark:text-white";
    }
  };

  return (
    <div className="font-mono text-xs sm:text-sm mb-3 flex flex-col sm:flex-row sm:gap-4 leading-relaxed tracking-wide group hover:bg-gray-100 dark:hover:bg-[#111] p-1 -mx-1 transition-colors">
      <div className="flex-shrink-0 flex gap-3 whitespace-nowrap opacity-80 group-hover:opacity-100 transition-opacity">
        <span className="text-gray-400 dark:text-gray-500">[{message.timestamp}]</span>
        {isUser ? (
          <span className="text-black dark:text-white font-bold w-24 text-right">OPERATOR &gt;</span>
        ) : (
          <span className={`${getColor(message.avatarColor)} font-bold w-24 text-right uppercase`}>
            {message.agentName?.split(" ")[0]} &gt;
          </span>
        )}
      </div>
      <div className={`flex-1 ${isUser ? "text-gray-700 dark:text-gray-300" : "text-black dark:text-white font-bold"}`}>
        <div className="whitespace-pre-wrap">{message.content}</div>
      </div>
    </div>
  );
}