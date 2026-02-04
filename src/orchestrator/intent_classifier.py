
INTENT_PATTERNS = {
    "requirements_gathering": {
        "keywords": ["need", "want", "goal", "problem", "user story"],
        "phase_compatibility": ["initialization", "discovery"],
        "triggers": ["clarify", "what if", "constraints"]
    },
    "architecture_design": {
        "keywords": ["architecture", "tech stack", "database", "API"],
        "phase_compatibility": ["requirements_complete"],
        "triggers": ["diagram", "structure", "how does"]
    },
    "mockup_creation": {
        "keywords": ["UI", "screen", "flow", "wireframe", "design"],
        "phase_compatibility": ["requirements_complete"],
        "triggers": ["looks like", "user journey"]
    },
    "execution_planning": {
        "keywords": ["roadmap", "timeline", "milestone", "sprint"],
        "phase_compatibility": ["architecture_complete"],
        "triggers": ["how long", "when", "priority"]
    },
    "export": {
        "keywords": ["export", "download", "document", "PDF"],
        "phase_compatibility": ["*"],
        "triggers": ["generate", "compile"]
    }
}