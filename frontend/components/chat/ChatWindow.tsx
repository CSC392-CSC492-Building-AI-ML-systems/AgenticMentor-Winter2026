"use client";
import { useState, useRef, useEffect } from "react";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import { Loader2 } from "lucide-react";
import { Message } from "@/lib/types"; // Make sure this path is correct

export default function ChatWindow() {
  // Initialize with your mock data or an empty array
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "agent",
      agentName: "Architect",
      timestamp: "10:23 AM",
      avatarColor: "purple",
      content: "Hello! I'm ready to help you plan your project. What are we building today?"
    }
  ]); 
  
  const [isAgentTyping, setIsAgentTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom whenever messages change
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isAgentTyping]);

  const handleSendMessage = (text: string) => {
    // 1. Create the User Message object
    const userMsg: Message = {
      id: Date.now().toString(), // Temporary ID
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    // 2. Add it to the chat list
    setMessages((prev) => [...prev, userMsg]);

    // 3. Simulate the AI responding
    setIsAgentTyping(true);
    
    // Simulate a 1.5 second delay for the "Backend" response
    setTimeout(() => {
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        agentName: "Requirements Agent",
        avatarColor: "purple",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        content: `I've noted that: "${text}". Let me process that and update the project requirements.`
      };
      
      setMessages((prev) => [...prev, aiMsg]);
      setIsAgentTyping(false);
    }, 1500);
  };

  return (
    <div className="flex-1 flex flex-col relative bg-white h-full overflow-hidden">
      <div className="flex-1 overflow-y-auto p-8 pb-40">
        <div className="max-w-3xl mx-auto">
          
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {/* Typing Indicator */}
          {isAgentTyping && (
            <div className="flex gap-4 mb-8">
              <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white">
                <Loader2 size={14} className="animate-spin" />
              </div>
              <div className="bg-gray-50 px-4 py-2 rounded-2xl rounded-tl-sm text-gray-400 text-sm border border-gray-100">
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