"use client";
import { useState, useRef, useEffect } from "react";
import MessageBubble from "@/components/chat/MessageBubble";
import ChatInput from "@/components/chat/ChatInput";
import { Loader2 } from "lucide-react";

export default function ChatWindow() {
  const [messages, setMessages] = useState<any[]>([]); 
  const [isAgentTyping, setIsAgentTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isAgentTyping]);

  // text comes from the textarea, agent comes from the selector
  const handleSendMessage = (text: string, agent: any) => {
    const userMsg = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsAgentTyping(true);

    // MOCK BACKEND CALL
    setTimeout(() => {
      const aiMsg = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        agentName: agent.name,      // Match the name
        avatarColor: agent.color,   // Match the color
        content: `As the ${agent.name}, I've processed your request regarding: "${text}".`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, aiMsg]);
      setIsAgentTyping(false);
    }, 1200);
  };

  return (
    <div className="flex-1 flex flex-col relative bg-white h-full overflow-hidden">
      <div className="flex-1 overflow-y-auto p-8 pb-40">
        <div className="max-w-3xl mx-auto">
          {messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)}
          {isAgentTyping && (
            <div className="flex gap-4 mb-8">
              <div className="w-8 h-8 rounded-full bg-gray-200 animate-pulse" />
              <div className="bg-gray-50 px-4 py-2 rounded-2xl text-gray-400 text-sm border border-gray-100">
                Agent is thinking...
              </div>
            </div>
          )}
          <div ref={scrollRef} />
        </div>
      </div>
      <ChatInput onSend={handleSendMessage} />
    </div>
  );
}