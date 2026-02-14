import { FileText } from "lucide-react";

export default function RequirementPanel() {
  return (
    <>
      <div className="h-10 border-b border-[#333] flex items-center justify-between px-4 bg-black">
        <div className="flex items-center gap-2 text-gray-300">
          <FileText size={12} />
          <span className="text-[10px] tracking-widest uppercase font-bold text-white">Requirement</span>
        </div>
        <span className="text-[10px] text-gray-400">PRD-04</span>
      </div>

      <div className="p-6 overflow-y-auto flex-1">
        <h1 className="text-xl font-bold text-white mb-8 tracking-tight">Authentication Flow Refresh</h1>
        
        <div className="mb-8">
          <h2 className="text-[10px] font-bold text-gray-300 tracking-widest uppercase mb-4">Overview</h2>
          <p className="text-sm text-gray-300 leading-relaxed">
            Implement a modular MFA system utilizing GitHub-style recovery codes and TOTP verification. 
            Security must be prioritized over convenience, with hardware key support for advanced users.
          </p>
        </div>

        <div>
          <h2 className="text-[10px] font-bold text-gray-300 tracking-widest uppercase mb-4">Technical Specs</h2>
          
          <div className="space-y-1">
            <div className="flex gap-4 p-3 text-sm text-gray-300">
              <span className="text-gray-400 font-mono">01</span>
              <p>Argon2id password hashing with custom salt parameters.</p>
            </div>
            
            <div className="flex gap-4 p-3 bg-[#111] border-l-2 border-white text-sm text-white font-medium">
              <span className="text-gray-400 font-mono">02</span>
              <p>WebAuthn integration for biometric passkey support.</p>
            </div>

            <div className="flex gap-4 p-3 text-sm text-gray-300">
              <span className="text-gray-400 font-mono">03</span>
              <p>Rate-limiting middleware (10 req/min) for sensitive endpoints.</p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}