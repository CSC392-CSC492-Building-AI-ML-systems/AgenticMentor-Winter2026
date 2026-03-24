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
  mockups: StitchMockup[];
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

function getScreenSpec(mockup: StitchMockup): StitchScreenSpec {
  return mockup.wireframe_spec ?? {};
}

function getScreenLabel(mockup: StitchMockup, index: number): string {
  const spec = getScreenSpec(mockup);
  return spec.screen_name || mockup.screen_name || spec.screen_id || mockup.screen_id || `Screen ${index + 1}`;
}

function summarizeScreen(mockup: StitchMockup, index: number): string {
  const spec = getScreenSpec(mockup);
  const screenName = getScreenLabel(mockup, index);
  const screenId = spec.screen_id || mockup.screen_id || `screen-${index + 1}`;
  const template = spec.template || "custom";
  const components = Array.isArray(spec.components) ? spec.components : [];
  const componentSummary = components.length > 0
    ? components.map((component, componentIndex) => `  ${componentIndex + 1}. ${summarizeComponent(component)}`).join("\n")
    : "  1. Preserve the current screen structure shown in the existing mockup.";
  const interactions = Array.isArray(mockup.interactions) && mockup.interactions.length > 0
    ? mockup.interactions.map((interaction) => `  - ${interaction}`).join("\n")
    : "  - Maintain the primary user actions implied by the current mockup.";
  const notes = spec.notes || mockup.user_flow || "No extra screen notes were provided.";

  return `Screen ${index + 1}: ${screenName}
- Screen id: ${screenId}
- Screen template: ${template}
- Structure:
${componentSummary}
- Key interactions:
${interactions}
- Notes:
  ${notes}`;
}

export function buildStitchPrompt({
  projectName,
  requirements,
  architecture,
  mockups,
}: BuildStitchPromptInput): string {
  const projectMockups = Array.isArray(mockups) ? mockups : [];
  const screenNames = projectMockups.length > 0
    ? projectMockups.map((mockup, index) => `- ${getScreenLabel(mockup, index)}`).join("\n")
    : "- Preserve the current product screen flow shown in the mockups.";
  const screenSummaries = projectMockups.length > 0
    ? projectMockups.map((mockup, index) => summarizeScreen(mockup, index)).join("\n\n")
    : "Screen 1: Preserve the current screen structure shown in the existing mockups.";
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
  const wireframeCodeHint = projectMockups.some((mockup) => !!mockup.wireframe_code)
    ? `\nReference hint: some of the existing mockups also have rough wireframe/code representations. Use them as structural inspiration, not as strict visual limits.`
    : "";

  return `Create an enhanced version of an existing product UI mockup set in Google Stitch.

Project: ${projectName || "Untitled Project"}
Product type: ${requirements?.project_type || "Web application"}
Target users: ${targetUsers}
${frontendStack}

Goal:
Redesign and enhance this set of related product screens while preserving each screen's original purpose, information hierarchy, and core user flow. Keep it recognizably the same product, but improve the UX and visual polish so it feels more production-ready and consistent across the whole flow.

Screens in scope:
${screenNames}

Current wireframe set:
${screenSummaries}

System-level expectation:
- Treat these screens as one coherent product flow, not isolated mockups.
- Keep navigation, hierarchy, and visual language consistent across all screens.
- Preserve the intent of each screen while improving the overall design system cohesion.

Functional context:
${functionalRequirements}

Constraints:
${constraints}

Design direction:
- Keep this as a responsive web UI.
- Improve spacing, typography hierarchy, alignment, and visual rhythm.
- Make the layout feel cleaner, more modern, and easier to scan.
- Upgrade the component styling, states, and call-to-action emphasis.
- Preserve the semantic purpose of each section and control on every screen.
- If useful, add subtle supporting UI elements that improve clarity without changing the screen's purpose.
- Maintain consistency with the existing product context and adjacent screens.
- Introduce a coherent visual system shared across the wireframe set.

Additional context:
Use the supplied wireframes as the source of truth for screen purpose and structure.${wireframeCodeHint}

What to generate:
- A refined multi-screen version of this product flow
- Better visual hierarchy and spacing across all screens
- More polished components and interactions
- A result that still maps clearly back to the original mockup set`;
}
