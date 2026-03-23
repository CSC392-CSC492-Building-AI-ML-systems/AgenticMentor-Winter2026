"use client";

interface StitchComponent {
  type?: string;
  label?: string;
  children?: string[];
  metadata?: Record<string, unknown>;
}

interface StitchScreenSpec {
  screen_name?: string;
  screen_id?: string;
  template?: string;
  notes?: string;
  components?: StitchComponent[];
}

interface StitchMockup {
  screen_name?: string;
  screen_id?: string;
  wireframe_spec?: StitchScreenSpec;
  interactions?: string[];
  user_flow?: string;
  wireframe_code?: string;
}

interface StitchRequirements {
  project_type?: string;
  target_users?: string[];
  functional?: string[];
  constraints?: string[];
}

interface StitchArchitecture {
  tech_stack?: Record<string, string>;
}

export interface BuildStitchPromptInput {
  projectName?: string | null;
  requirements?: StitchRequirements | null;
  architecture?: StitchArchitecture | null;
  mockup: StitchMockup;
}

function summarizeComponent(component: StitchComponent): string {
  const label = component.label?.trim() || "Untitled";
  const type = component.type?.replace(/_/g, " ") || "section";
  const children = Array.isArray(component.children) && component.children.length > 0
    ? ` containing ${component.children.slice(0, 5).join(", ")}`
    : "";
  const metadata = component.metadata && Object.keys(component.metadata).length > 0
    ? ` with ${Object.entries(component.metadata)
        .map(([key, value]) => `${key.replace(/_/g, " ")}=${String(value)}`)
        .join(", ")}`
    : "";

  return `${label} (${type})${children}${metadata}`;
}

export function buildStitchPrompt({
  projectName,
  requirements,
  architecture,
  mockup,
}: BuildStitchPromptInput): string {
  const spec = mockup.wireframe_spec ?? {};
  const screenName = spec.screen_name || mockup.screen_name || mockup.screen_id || "Current Screen";
  const screenId = spec.screen_id || mockup.screen_id || "current-screen";
  const template = spec.template || "custom";
  const components = Array.isArray(spec.components) ? spec.components : [];
  const componentSummary = components.length > 0
    ? components.map((component, index) => `${index + 1}. ${summarizeComponent(component)}`).join("\n")
    : "1. Preserve the current screen structure shown in the existing mockup.";
  const interactions = Array.isArray(mockup.interactions) && mockup.interactions.length > 0
    ? mockup.interactions.map((interaction) => `- ${interaction}`).join("\n")
    : "- Maintain the primary user actions implied by the current mockup.";
  const targetUsers = requirements?.target_users?.length
    ? requirements.target_users.slice(0, 5).join(", ")
    : "General end users";
  const functionalRequirements = requirements?.functional?.length
    ? requirements.functional.slice(0, 6).map((item) => `- ${item}`).join("\n")
    : "- Preserve the current functionality and intent of this screen.";
  const constraints = requirements?.constraints?.length
    ? requirements.constraints.slice(0, 4).map((item) => `- ${item}`).join("\n")
    : "- No additional hard constraints beyond staying consistent with the current product direction.";
  const frontendStack = architecture?.tech_stack?.frontend
    ? `Frontend stack context: ${architecture.tech_stack.frontend}`
    : "Frontend stack context: not specified";
  const notes = spec.notes || mockup.user_flow || "";
  const wireframeCodeHint = mockup.wireframe_code
    ? `\nReference hint: the existing mockup also has a rough wireframe/code representation. Use it as structural inspiration, not as a strict visual limit.`
    : "";

  return `Create an enhanced version of an existing product UI mockup in Google Stitch.

Project: ${projectName || "Untitled Project"}
Product type: ${requirements?.project_type || "Web application"}
Target users: ${targetUsers}
Screen name: ${screenName}
Screen id: ${screenId}
Screen template: ${template}
${frontendStack}

Goal:
Redesign and enhance this specific screen while preserving its original purpose, information hierarchy, and core user flow. Keep it recognizably the same product, but improve the UX and visual polish so it feels more production-ready.

Current screen structure:
${componentSummary}

Key interactions to preserve:
${interactions}

Functional context:
${functionalRequirements}

Constraints:
${constraints}

Design direction:
- Keep this as a responsive web UI.
- Improve spacing, typography hierarchy, alignment, and visual rhythm.
- Make the layout feel cleaner, more modern, and easier to scan.
- Upgrade the component styling, states, and call-to-action emphasis.
- Preserve the semantic purpose of each section and control.
- If useful, add subtle supporting UI elements that improve clarity without changing the screen's purpose.
- Maintain consistency with the existing product context and adjacent screens.

Additional context:
${notes || "No extra screen notes were provided."}${wireframeCodeHint}

What to generate:
- A refined version of this screen
- Better visual hierarchy and spacing
- More polished components and interactions
- A result that still maps clearly back to the original mockup`;
}
