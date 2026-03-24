"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { fetchWithAuth } from "@/lib/api";
import { useAuthStore } from "@/store/useAuthStore";
import { useProjectStore } from "@/store/useProjectStore";
import { useLlmUiStore } from "@/store/useLlmUiStore";

interface Props {
  open: boolean;
  onClose: () => void;
}

/** Must stay in sync with backend `_MIN_APP_DEFAULT_MODELS` / allowed_default_models floor. */
const MIN_DEFAULT_MODELS = ["gemini-2.5-flash", "gemini-3-flash-preview"];
const CUSTOM_MODEL_FALLBACK = [
  "gemini-2.5-flash",
  "gemini-3-flash-preview",
  "gemini-2.0-flash",
  "gemini-2.5-pro",
  "gemini-2-flash-exp",
  "gemini-2.0-flash-lite",
  "gemini-2.5-flash-lite",
  "gemini-3.1-pro-preview",
  "gemini-3.1-flash-lite-preview",
];

interface LlmSettingsPayload {
  mode: "default" | "custom";
  model: string | null;
  has_custom_key: boolean;
  verified: boolean;
  verified_at: string | null;
  allowed_default_models: string[];
  supported_custom_models: string[];
}

export default function LlmSettingsModal({ open, onClose }: Props) {
  const { idToken } = useAuthStore();
  const { projectId } = useProjectStore();
  const bumpLlmRuntimeRefresh = useLlmUiStore((s) => s.bumpLlmRuntimeRefresh);
  const setLlmRuntimePayload = useLlmUiStore((s) => s.setLlmRuntimePayload);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const [mode, setMode] = useState<"default" | "custom">("default");
  const [model, setModel] = useState("gemini-2.5-flash");
  const [customKey, setCustomKey] = useState("");
  const [hasStoredKey, setHasStoredKey] = useState(false);
  const [verified, setVerified] = useState(false);
  const [defaultModels, setDefaultModels] = useState<string[]>(MIN_DEFAULT_MODELS);
  const [customModels, setCustomModels] = useState<string[]>(CUSTOM_MODEL_FALLBACK);

  useEffect(() => {
    if (!open || !idToken || !projectId) return;
    setLoading(true);
    setMessage(null);
    fetchWithAuth(`/projects/${projectId}/llm-settings`, { token: idToken })
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
        const payload = data as LlmSettingsPayload;
        setMode(payload.mode);
        setModel(payload.model || "gemini-2.5-flash");
        setHasStoredKey(payload.has_custom_key);
        setVerified(payload.verified);
        const apiDefaults = payload.allowed_default_models ?? [];
        setDefaultModels([...new Set([...MIN_DEFAULT_MODELS, ...apiDefaults])]);
        const apiCustom = payload.supported_custom_models ?? [];
        setCustomModels(apiCustom.length ? [...new Set([...CUSTOM_MODEL_FALLBACK, ...apiCustom])] : CUSTOM_MODEL_FALLBACK);
      })
      .catch((err) => setMessage(`Failed to load settings: ${err.message}`))
      .finally(() => setLoading(false));
  }, [open, idToken, projectId]);

  const activeModelOptions = mode === "custom" ? customModels : defaultModels;

  // Keep selected model inside the allowed list for the current mode.
  useEffect(() => {
    if (loading) return;
    const list = mode === "custom" ? customModels : defaultModels;
    if (!list.length) return;
    setModel((current) => (list.includes(current) ? current : list[0]));
  }, [mode, loading, customModels, defaultModels]);

  const saveSettings = async () => {
    if (!idToken || !projectId) return;
    setSaving(true);
    setMessage(null);
    try {
      // Always send explicit strings — JSON.stringify omits keys whose value is undefined,
      // which used to make the API default mode to "default" and wipe the custom key.
      const resolvedMode: "default" | "custom" = mode === "custom" ? "custom" : "default";
      const body: Record<string, unknown> = {
        mode: resolvedMode,
        model: model || "gemini-2.5-flash",
      };
      if (resolvedMode === "custom" && customKey.trim()) body.custom_api_key = customKey.trim();
      const res = await fetchWithAuth(`/projects/${projectId}/llm-settings`, {
        method: "POST",
        token: idToken,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
      setHasStoredKey(Boolean(data?.has_custom_key));
      setVerified(Boolean(data?.verified));
      setMessage("Settings saved.");
      bumpLlmRuntimeRefresh();
    } catch (err: any) {
      setMessage(`Save failed: ${err.message ?? "Unknown error"}`);
    } finally {
      setSaving(false);
    }
  };

  const verifyCustom = async () => {
    if (!idToken || !projectId) return;
    if (!model.trim()) {
      setMessage("Select a model first.");
      return;
    }
    const keyToVerify = customKey.trim();
    if (!keyToVerify) {
      setMessage("Enter a custom API key to verify.");
      return;
    }
    setVerifying(true);
    setMessage(null);
    try {
      const res = await fetchWithAuth(`/projects/${projectId}/llm-settings/verify`, {
        method: "POST",
        token: idToken,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ custom_api_key: keyToVerify, model }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
      setVerified(Boolean(data?.valid));
      if (data?.valid) {
        setHasStoredKey(true);
        setCustomKey("");
        if (data?.runtime && typeof data.runtime === "object") {
          setLlmRuntimePayload(data.runtime);
        }
        bumpLlmRuntimeRefresh();
      }
      setMessage(data?.message || (data?.valid ? "Verified." : "Verification failed."));
    } catch (err: any) {
      setVerified(false);
      setMessage(`Verification failed: ${err.message ?? "Unknown error"}`);
    } finally {
      setVerifying(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-100 bg-black/40 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl border border-gray-300 dark:border-[#444] bg-white dark:bg-black">
        <div className="h-11 border-b border-gray-300 dark:border-[#444] flex items-center justify-between px-4">
          <div className="text-[10px] font-bold tracking-widest uppercase text-black dark:text-white">LLM_Settings</div>
          <button onClick={onClose} className="text-gray-500 hover:text-black dark:hover:text-white">
            <X size={14} />
          </button>
        </div>

        <div className="p-4 space-y-4 text-xs">
          {loading ? (
            <div className="text-gray-500">Loading settings...</div>
          ) : (
            <>
              <div className="space-y-2">
                <div className="text-[10px] font-bold tracking-widest uppercase text-black dark:text-white">Mode</div>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2">
                    <input type="radio" checked={mode === "default"} onChange={() => setMode("default")} />
                    Use App Default
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="radio" checked={mode === "custom"} onChange={() => setMode("custom")} />
                    Use My Key
                  </label>
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-[10px] font-bold tracking-widest uppercase text-black dark:text-white">Model</div>
                <select
                  value={activeModelOptions.includes(model) ? model : activeModelOptions[0] ?? ""}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full border border-gray-300 dark:border-[#555] bg-white dark:bg-black px-3 py-2 text-sm text-black dark:text-white cursor-pointer"
                >
                  {activeModelOptions.map((m) => (
                    <option key={m} value={m} className="bg-white text-black dark:bg-[#111] dark:text-white">
                      {m}
                    </option>
                  ))}
                </select>
                <div className="text-[10px] text-gray-500">
                  {mode === "custom"
                    ? "Choose a model for your API key (verify after changing)."
                    : "Allowed models for the app default key."}
                </div>
              </div>

              {mode === "custom" && (
                <div className="space-y-2">
                  <div className="text-[10px] font-bold tracking-widest uppercase text-black dark:text-white">Custom API Key</div>
                  <input
                    type="password"
                    value={customKey}
                    onChange={(e) => setCustomKey(e.target.value)}
                    placeholder={hasStoredKey ? "Stored key exists. Paste new key to replace." : "Paste your Google AI Studio key"}
                    className="w-full border border-gray-300 dark:border-[#555] bg-white dark:bg-black px-3 py-2 text-sm"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={verifyCustom}
                      disabled={verifying}
                      className="border border-gray-300 dark:border-[#555] px-3 py-2 text-[10px] font-bold uppercase tracking-widest"
                    >
                      {verifying ? "Verifying..." : "Verify_Key"}
                    </button>
                    <span className={`text-[10px] font-bold uppercase tracking-widest ${verified ? "text-green-600 dark:text-green-400" : "text-gray-500"}`}>
                      {verified ? "Verified" : hasStoredKey ? "Stored (not verified this session)" : "Not verified"}
                    </span>
                  </div>
                </div>
              )}

              <div className="border border-gray-200 dark:border-[#333] p-3 text-[11px] text-gray-600 dark:text-gray-300 leading-relaxed">
                Get API key from{" "}
                <a
                  href="https://aistudio.google.com/apikey"
                  target="_blank"
                  rel="noreferrer"
                  className="underline text-black dark:text-white"
                >
                  Google AI Studio
                </a>
                . Custom keys are kept only in server memory (not the project database). They are cleared on
                logout and expire after idle TTL; an API restart also drops them—verify again if needed.
              </div>

              {message && <div className="text-[11px] text-gray-700 dark:text-gray-200">{message}</div>}
            </>
          )}
        </div>

        <div className="h-12 border-t border-gray-300 dark:border-[#444] px-4 flex items-center justify-end gap-2">
          <button onClick={onClose} className="border border-gray-300 dark:border-[#555] px-3 py-2 text-[10px] font-bold uppercase tracking-widest">
            Close
          </button>
          <button
            onClick={saveSettings}
            disabled={saving || loading}
            className="bg-black dark:bg-white text-white dark:text-black px-3 py-2 text-[10px] font-bold uppercase tracking-widest"
          >
            {saving ? "Saving..." : "Save_Settings"}
          </button>
        </div>
      </div>
    </div>
  );
}

