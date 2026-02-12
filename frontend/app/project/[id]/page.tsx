import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
import ChatWindow from "@/components/chat/ChatWindow";

export default function ProjectPage() {
  return (
    <div className="flex h-screen overflow-hidden bg-white">
      {/* Fixed Sidebar */}
      <div className="flex-shrink-0">
        <Sidebar />
      </div>

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 min-w-0">
        <Topbar />
        
        {/* Chat Area */}
        <div className="flex-1 flex overflow-hidden">
            <ChatWindow />
            
            {/* Optional Right Panel - Hidden for now to match Screenshot 1's focused view, 
                but structure is here if you want to expand later */}
            {/* <div className="hidden lg:block w-[400px] border-l border-gray-200 p-4">
               Artifact Viewer Area 
            </div> */}
        </div>
      </div>
    </div>
  );
}