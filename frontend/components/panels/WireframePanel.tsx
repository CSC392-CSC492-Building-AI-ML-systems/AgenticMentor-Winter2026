"use client";
import { useEffect, useRef, useState } from "react";
import { Copy, ExternalLink, LayoutTemplate, Sparkles, X } from "lucide-react";
import { useProjectStore } from "@/store/useProjectStore";
import WireframeRenderer from "./WireframeRenderer";
import { buildStitchPrompt } from "@/lib/stitchPrompt";

const STITCH_URL = "https://stitch.withgoogle.com/";

export default function WireframePanel() {
  const { mockups, isLoading, projectName, requirements, architecture } = useProjectStore();
  const [selected, setSelected] = useState(0);
  const [showStitchModal, setShowStitchModal] = useState(false);
  const [copied, setCopied] = useState(false);
  const promptRef = useRef<HTMLTextAreaElement>(null);

  const hasData = mockups.length > 0;
  const current = mockups[selected];

  // Parse wireframe_spec from the mockup entry
  const getSpec = (mockup: any) => {
    if (mockup?.wireframe_spec && typeof mockup.wireframe_spec === "object") {
      return mockup.wireframe_spec;
    }
    return null;
  };

  const spec = current ? getSpec(current) : null;
  const stitchPrompt = current
    ? buildStitchPrompt({
        projectName,
        requirements,
        architecture,
        mockup: current,
      })
    : "";

  useEffect(() => {
    if (selected >= mockups.length && mockups.length > 0) {
      setSelected(0);
    }
  }, [mockups.length, selected]);

  useEffect(() => {
    if (!showStitchModal) return;

    const originalOverflow = document.body.style.overflow;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setShowStitchModal(false);
      }
    };

    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKeyDown);

    const focusTimer = window.setTimeout(() => promptRef.current?.focus(), 50);

    return () => {
      document.body.style.overflow = originalOverflow;
      document.removeEventListener("keydown", onKeyDown);
      window.clearTimeout(focusTimer);
    };
  }, [showStitchModal]);

  const handleCopyPrompt = async () => {
    if (!stitchPrompt) return;

    await navigator.clipboard.writeText(stitchPrompt);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  const openStitch = () => {
    window.open(STITCH_URL, "_blank", "noopener,noreferrer");
  };

  const stitchTrigger = hasData && current && (
    <button
      onClick={() => setShowStitchModal(true)}
      className="inline-flex items-center gap-2 border border-gray-300 dark:border-[#555] bg-white dark:bg-[#111] px-3 py-2 text-[10px] font-bold uppercase tracking-widest text-black dark:text-white hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors"
    >
      <img
        src="/stitch_logo.webp"
        alt="Google Stitch"
        className="h-4 w-4 object-contain"
      />
      Open_In_Stitch
    </button>
  );

  return (
    <>
      <div className="h-10 border-b border-gray-300 dark:border-[#444] flex items-center justify-between px-4 bg-gray-50 dark:bg-black flex-shrink-0 transition-colors">
        <div className="flex items-center gap-2 text-black dark:text-white">
          <LayoutTemplate size={12} />
          <span className="text-[10px] tracking-widest uppercase font-bold">UI_Mockups</span>
        </div>
        {hasData && (
          <div className="flex items-center gap-2">
            <span className="text-[9px] border border-gray-300 dark:border-[#555] bg-white dark:bg-[#111] px-2 py-1 text-gray-600 dark:text-gray-300 font-bold uppercase tracking-widest transition-colors">
              {mockups.length} Screen{mockups.length !== 1 ? "s" : ""}
            </span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-hidden flex bg-white dark:bg-black transition-colors">
        {/* Sidebar: screen list */}
        {hasData && mockups.length > 1 && (
          <div className="w-48 border-r border-gray-200 dark:border-[#333] overflow-y-auto flex-shrink-0">
            {mockups.map((m: any, i: number) => (
              <button
                key={i}
                onClick={() => setSelected(i)}
                className={`w-full text-left px-3 py-3 text-[10px] font-bold uppercase tracking-widest border-b border-gray-100 dark:border-[#222] transition-colors
                  ${selected === i
                    ? "bg-black dark:bg-white text-white dark:text-black"
                    : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-[#111]"
                  }`}
              >
                {m.screen_name ?? m.screen_id ?? `Screen ${i + 1}`}
              </button>
            ))}
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-6 flex items-start justify-center">
          {isLoading && !hasData && (
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest animate-pulse">
              -- LOADING MOCKUPS --
            </p>
          )}

          {!isLoading && !hasData && (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest text-center">
                -- NO MOCKUPS YET. RUN THE MOCKUP AGENT FROM THE CONSOLE --
              </p>
            </div>
          )}

          {hasData && current && spec && (
            <div className="w-full" style={{ maxWidth: "min(100%, calc(100vh * 8/9))" }}>
              <div className="mb-3 flex justify-end">
                {stitchTrigger}
              </div>
              <div style={{ aspectRatio: "6/9", width: "100%", overflow: "hidden" }}>
                <WireframeRenderer screen={spec} />
              </div>
            </div>
          )}

          {hasData && current && !spec && (
            <div className="space-y-3">
              <div className="flex justify-end">
                {stitchTrigger}
              </div>
              <h2 className="text-sm font-bold text-black dark:text-white uppercase tracking-widest">
                {current.screen_name ?? current.screen_id ?? `Screen ${selected + 1}`}
              </h2>
              {current.wireframe_code && (
                <pre className="text-[9px] font-mono text-gray-600 dark:text-gray-400 whitespace-pre-wrap overflow-auto border border-dashed border-gray-200 dark:border-[#333] p-3">
                  {typeof current.wireframe_code === "string"
                    ? current.wireframe_code
                    : JSON.stringify(current.wireframe_code, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>

      {showStitchModal && current && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setShowStitchModal(false)}
        >
          <div
            className="w-full max-w-5xl max-h-[85vh] overflow-hidden border border-gray-300 dark:border-[#444] bg-white dark:bg-black shadow-2xl flex flex-col"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-gray-300 dark:border-[#444] px-5 py-4 bg-gray-50 dark:bg-[#050505]">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center border border-gray-300 dark:border-[#444] bg-white dark:bg-[#111]">
                  <Sparkles size={16} />
                </div>
                <div>
                  <div className="text-xs font-bold uppercase tracking-widest text-black dark:text-white">
                    Stitch_Handoff
                  </div>
                  <div className="text-[10px] uppercase tracking-widest text-gray-500 dark:text-gray-400">
                    {current.screen_name ?? current.screen_id ?? `Screen ${selected + 1}`}
                  </div>
                </div>
              </div>
              <button
                onClick={() => setShowStitchModal(false)}
                className="text-gray-400 hover:text-black dark:hover:text-white transition-colors"
                aria-label="Close Stitch prompt modal"
              >
                <X size={16} />
              </button>
            </div>

            <div className="grid flex-1 overflow-hidden md:grid-cols-[minmax(0,1fr)_280px]">
              <div className="flex min-h-0 flex-col border-b border-gray-300 dark:border-[#444] md:border-b-0 md:border-r">
                <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 dark:border-[#222]">
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-widest text-black dark:text-white">
                      Mockup_Payload
                    </div>
                    <div className="text-[10px] uppercase tracking-widest text-gray-500 dark:text-gray-400 mt-1">
                      Copy this prompt into Google Stitch to enhance the current mockup.
                    </div>
                  </div>
                  <button
                    onClick={handleCopyPrompt}
                    className="inline-flex items-center gap-2 border border-gray-300 dark:border-[#555] px-3 py-2 text-[10px] font-bold uppercase tracking-widest text-gray-700 dark:text-gray-200 hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors"
                  >
                    <Copy size={12} />
                    {copied ? "Copied" : "Copy_Prompt"}
                  </button>
                </div>

                <div className="flex-1 min-h-0 p-5 bg-white dark:bg-black">
                  <textarea
                    ref={promptRef}
                    readOnly
                    value={stitchPrompt}
                    className="h-full min-h-[320px] w-full resize-none border border-gray-300 dark:border-[#444] bg-gray-50 dark:bg-[#050505] p-4 text-xs leading-relaxed text-black dark:text-white focus:outline-none font-mono"
                    aria-label="Prompt payload for Google Stitch"
                  />
                </div>
              </div>

              <div className="flex flex-col justify-between gap-6 p-5 bg-gray-50 dark:bg-[#050505]">
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <img
                      src="/stitch_logo.webp"
                      alt="Google Stitch logo"
                      className="h-10 w-10 rounded border border-gray-200 dark:border-[#222] bg-white object-contain p-1"
                    />
                    <div>
                      <div className="text-xs font-bold uppercase tracking-widest text-black dark:text-white">
                        Google_Stitch
                      </div>
                      <div className="text-[10px] uppercase tracking-widest text-gray-500 dark:text-gray-400 mt-1">
                        Open Stitch in a new tab, then paste the payload and iterate with AI.
                      </div>
                    </div>
                  </div>

                  <div className="border border-gray-200 dark:border-[#222] bg-white dark:bg-[#0b0b0b] p-4 text-[10px] uppercase tracking-widest text-gray-600 dark:text-gray-300 leading-5">
                    The generated payload preserves the current screen purpose, component layout, and interactions while asking Stitch to improve visual polish, hierarchy, spacing, and UX clarity.
                  </div>
                </div>

                <button
                  onClick={openStitch}
                  className="inline-flex w-full items-center justify-center gap-3 bg-black dark:bg-white px-4 py-3 text-[10px] font-bold uppercase tracking-widest text-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors"
                >
                  <img
                    src="/stitch_logo.webp"
                    alt=""
                    className="h-5 w-5 object-contain"
                    aria-hidden="true"
                  />
                  Open_Google_Stitch
                  <ExternalLink size={12} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {hasData && (
        <div className="h-6 border-t border-gray-200 dark:border-[#333] flex items-center px-4 bg-gray-50 dark:bg-[#050505] flex-shrink-0">
          <span className="text-[9px] text-gray-500 font-mono tracking-widest uppercase">
            Generated_By: Mockup_Rendering_Agent
          </span>
        </div>
      )}
    </>
  );
}
