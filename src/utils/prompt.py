from typing import Dict, Any

# System prompt for the Requirements Collector Agent
SYSTEM_PROMPT = """You are an expert Requirements Collector Agent helping users define their software project requirements.

Your goal is to gather comprehensive project requirements through a natural, conversational interview process.

## Core Principles:
1. **Ask ONE question at a time** - Never overwhelm the user with multiple questions
2. **Be adaptive** - Follow up based on their specific answers
3. **Be thorough but efficient** - Cover all important areas without being repetitive
4. **Update incrementally** - Build on existing information, don't start over
5. **Stay focused** - Each question should have a clear purpose

## Information to Gather:
- **Project Type**: What kind of system/application (web app, mobile, API, etc.)
- **Target Users**: Who will use this? What are their needs?
- **Key Features**: What must the system do? Core functionality?
- **Technical Constraints**: Technology preferences, existing systems, platforms
- **Business Goals**: Why build this? Success metrics? Timeline?
- **Budget & Resources**: Any limitations to be aware of?

## Question Strategy:
1. Start broad (project type, purpose)
2. Drill into specifics based on their answers
3. Ask clarifying questions when answers are vague
4. Confirm understanding before moving to next area
5. Recognize when you have enough information

## Conversation Style:
- Professional but friendly
- Clear and concise
- Show you're listening by referencing previous answers
- Use examples to help users articulate needs
- Don't make assumptions - ask when unclear

## When Requirements are Complete:
When you have sufficient information across all key areas (project type, users, features, constraints, goals), 
confirm with the user that you've captured everything and mark requirements as complete.
"""

# Instructions for analyzing conversation and determining next question
ANALYSIS_PROMPT = """Based on the conversation history and current requirements state, analyze what information is still needed.

Current Requirements State:
{requirements_json}

Conversation History:
{conversation_history}

Your tasks:
1. Identify what information is MISSING or INCOMPLETE
2. Determine the MOST IMPORTANT next question to ask
3. Make the question specific and actionable
4. Ensure the question builds on what you already know

Return your analysis as JSON with this structure:
{{
    "missing_info": ["list of what's still needed"],
    "next_area": "the area to focus on next",
    "next_question": "the specific question to ask",
    "reasoning": "why this question is the most important next step"
}}
"""

# Instructions for updating requirements state
UPDATE_PROMPT = """Extract relevant information from the user's latest response and update the requirements state.

Current Requirements:
{requirements_json}

User's Response:
{user_message}

Your tasks:
1. Extract any NEW information from the user's response
2. MERGE it with existing requirements (don't overwrite unless correcting)
3. Update progress based on completeness
4. Identify any decisions or assumptions made

Return the UPDATED requirements state as JSON, preserving all existing information and adding new details.

IMPORTANT: Only update fields that have new information. Keep existing values intact.
"""

# Instructions for determining if requirements are complete
COMPLETION_CHECK_PROMPT = """Evaluate if the requirements are sufficiently complete to move forward.

Current Requirements:
{requirements_json}

Assess completeness across these dimensions:
- Project Type: Do we know what kind of system this is?
- Target Users: Do we understand who will use it?
- Key Features: Do we have at least 3-5 core features defined?
- Technical Constraints: Do we know technical preferences/limitations?
- Business Goals: Do we understand the "why" and timeline?

Return JSON:
{{
    "is_complete": true/false,
    "completeness_score": 0.0-1.0,
    "missing_critical_info": ["list items if incomplete"],
    "recommendation": "continue asking questions" or "confirm and finalize"
}}
"""

# Example questions by area for adaptive follow-ups
EXAMPLE_QUESTIONS = {
    "project_type": [
        "What type of application or system are you looking to build?",
        "Is this a web application, mobile app, API, or something else?",
        "What platform will this run on?"
    ],
    "target_users": [
        "Who are the primary users of this system?",
        "What problems are your users trying to solve?",
        "How many users do you expect to have?"
    ],
    "key_features": [
        "What are the core features this system must have?",
        "Can you walk me through a typical user journey?",
        "What's the most important thing users should be able to do?"
    ],
    "technical_constraints": [
        "Are there any specific technologies you want to use or avoid?",
        "Do you need to integrate with any existing systems?",
        "Are there any performance or security requirements?"
    ],
    "business_goals": [
        "What's the main goal you're trying to achieve with this project?",
        "When do you need this launched?",
        "How will you measure success?"
    ],
    "budget": [
        "Do you have a budget range in mind?",
        "Are there any resource constraints I should know about?"
    ]
}


def get_adaptive_question_prompt(requirements: Dict[str, Any], last_answer: str) -> str:
    """Generate a prompt for an adaptive follow-up question based on context."""
    return f"""The user just said: "{last_answer}"

Current requirements state:
{requirements}

Generate a thoughtful follow-up question that:
1. Directly relates to what they just told you
2. Digs deeper into specifics
3. Helps clarify any vague points
4. Moves the requirements gathering forward

Keep it conversational and focused on ONE thing."""


def format_conversation_history(messages: list) -> str:
    """Format conversation history for prompts."""
    formatted = []
    for msg in messages[-10:]:  # Last 10 messages for context
        role = msg.get("role", "user")
        content = msg.get("content", "")
        formatted.append(f"{role.upper()}: {content}")
    return "\n".join(formatted)