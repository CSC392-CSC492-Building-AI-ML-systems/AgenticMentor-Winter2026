import { FileText, CheckCircle2, Shield, Database } from "lucide-react";

export default function RequirementsView() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm mt-2 w-full max-w-2xl">
      {/* Header */}
      <div className="bg-gray-50 px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-2 text-blue-700">
          <FileText size={18} />
          <span className="font-bold text-xs tracking-wider uppercase">Requirements Artifact V1.0</span>
        </div>
        <div className="flex gap-2 text-gray-400">
          {/* Edit/Copy icons simulated */}
          <div className="w-4 h-4 bg-gray-300 rounded-sm"></div>
          <div className="w-4 h-4 bg-gray-300 rounded-sm"></div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* User Needs */}
        <div>
          <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-blue-600 rounded-full"></span> User Needs
          </h4>
          <div className="space-y-2 pl-4">
            <RequirementItem text="Merchants need a streamlined dashboard for real-time sales metrics." />
            <RequirementItem text="Customers require fast search functionality with filtering." />
          </div>
        </div>

        {/* Functional Requirements */}
        <div>
          <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-blue-600 rounded-full"></span> Functional Requirements
          </h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
              <div className="text-xs font-bold text-gray-500 uppercase mb-1">AUTH</div>
              <div className="text-sm text-gray-800">Role-based access control (RBAC)</div>
            </div>
            <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
              <div className="text-xs font-bold text-gray-500 uppercase mb-1">DATA</div>
              <div className="text-sm text-gray-800">Real-time inventory sync</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function RequirementItem({ text }: { text: string }) {
  return (
    <div className="flex items-start gap-2">
      <CheckCircle2 size={16} className="text-blue-500 mt-0.5" />
      <span className="text-sm text-gray-600">{text}</span>
    </div>
  );
}