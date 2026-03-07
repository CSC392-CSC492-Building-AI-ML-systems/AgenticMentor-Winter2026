export type Role = "user" | "agent" | "system";

export interface ArtifactData {
  title: string;
  type: "requirements" | "figma" | "code";
  version?: string;
  content?: any;
}

export interface Message {
  id: string;
  role: Role;
  agentName?: string;
  avatarColor?: string; // "purple", "orange", "blue"
  content?: string;
  artifact?: ArtifactData;
  timestamp?: string;
}