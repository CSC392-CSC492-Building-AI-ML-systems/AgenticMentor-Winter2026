from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import operator

from src.core.config import settings
from src.core.prompt import (
    SYSTEM_PROMPT,
    ANALYSIS_PROMPT,
    UPDATE_PROMPT,
    COMPLETION_CHECK_PROMPT,
    format_conversation_history
)
from src.models.schemas import RequirementsState, ChatMessage, MessageRole


class AgentState(TypedDict):
    """State for the requirements collection agent.
    
    Each AgentState node belongs to a graph that follows a series of prompts
    """
    # Conversation messages
    messages: Annotated[Sequence[BaseMessage], operator.add]
    
    # Use our requirements state defined in the schema
    requirements: RequirementsState
    
    # Decisions made during conversation
    decisions: list[str]
    
    # Assumptions identified
    assumptions: list[str]
    
    # The next question to ask the user
    next_question: str


class RequirementsAgent:
    """Requirements Collector Agent using LangGraph.
    
    This is a conversational agent that asks questions in an interview style to
    build up a structured finished requirements state
        
    Graph Flow:
    1. analyze -> Understand conversation context
    2. update_requirements -> Extract and merge new information
    3. check_completion -> Evaluate if we have enough information
    4. generate_question -> Asks a new question depending on completion state
    
    """
    
    def __init__(self):
        """Initialize the agent with LLM and compile the graph."""
        print("Initializing Requirements Agent...")
        
        self.llm = ChatGoogleGenerativeAI(
            model=settings.model_name,
            temperature=settings.model_temperature,
            max_tokens=settings.model_max_tokens,
            google_api_key=settings.gemini_api_key,
        )
        
        self.graph = self._build_graph()
        print("Agent ready...")

    def _build_graph(self) -> StateGraph:
        """ Builds the complete LangGraph workflow
        
        """
        workflow = StateGraph(AgentState)
        
        # Add all the nodes
        workflow.add_node("analyze", self._analyze_node)
        workflow.add_node("update_requirements", self._update_requirements_node)
        workflow.add_node("check_completion", self._check_completion_node)
        workflow.add_node("generate_question", self._generate_question_node)

        # Set entry point
        workflow.set_entry_point("analyze")
        
        # Add edges
        workflow.add_edge("analyze", "update_requirements")
        workflow.add_edge("update_requirements", "check_completion")

        # Add conditional edge to check for completion
        workflow.add_conditional_edges(
            "check_completion",
            self._should_continue,
            {
                "continue": "generate_question",
                "complete": END
            }
        )
        
        workflow.add_edge("generate_question", END)
        print("=== Graph built successfully ===")
        return workflow.compile()
    
    async def _analyze_node(self, state: AgentState) -> AgentState:
        """ Node 1: Analyzes the current state and conversation history.
        
        This node analyzes what has been discussed and what needs to be added.
        It does not mutate the state, but rather provide context for the next node.
        """
        print("NODE 1: ANALYZE")
        
        # Get conversation history for context
        conv_history = format_conversation_history(
            [{"role": m.type, "content": m.content} for m in state["messages"]]
        )
        
        # If this is the very first message (just system + user), skip analysis
        if len(state["messages"]) <= 1:
            print("   → First message, skipping deep analysis")
            return state

        
        # Create analysis prompt with current context, uses custom ANALYSIS_PROMPT
        analysis_prompt = ANALYSIS_PROMPT.format(
            requirements_json=state["requirements"].model_dump_json(indent=2),
            conversation_history=conv_history
        )
        
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=analysis_prompt)
        ]

        response = await self.llm.ainvoke(messages)
        print(f"   → Analysis: {response.content[:150]}...")
        
        # State passes through unchanged (analysis informs next nodes)
        return state

    async def _update_requirements_node(self, state: AgentState) -> AgentState:
        """ Node 2: Updates the requirements state based on the previous nodes
        context, and the user prompt
        
        Updates the states requirement state.
        """
        print("NODE 2: UPDATE")
        
        # Get the last user message
        user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
        if not user_messages:
            print("   → No user message to process")
            return state
        
        last_user_message = user_messages[-1].content
        print(f"   → Processing: '{last_user_message[:80]}...'")
        
        # Convert using custom update prompt
        update_prompt = UPDATE_PROMPT.format(
            requirements_json=state["requirements"].model_dump_json(indent=2),
            user_message=last_user_message
        )
        
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=update_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            # Extracts and updates JSON requirement state 
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            updated_reqs = json.loads(content.strip())
            
            # Get current requirements as dict
            current_dict = state["requirements"].model_dump()
            
            # MERGE strategy: Only update non-empty values
            merged_count = 0
            for key, value in updated_reqs.items():
                if value is not None and value != [] and value != "":
                    # For lists, extend rather than replace (avoid duplicates)
                    if isinstance(value, list) and key in current_dict:
                        existing = current_dict.get(key, [])
                        if isinstance(existing, list):
                            # Merge and deduplicate
                            current_dict[key] = list(set(existing + value))
                        else:
                            current_dict[key] = value
                    else:
                        current_dict[key] = value
                    merged_count += 1
            
            # Update the state with new RequirementsState instance
            state["requirements"] = RequirementsState(**current_dict)
            
            print(f"Merged {merged_count} requirement updates")

        except (json.JSONDecodeError, ValueError) as e:
            print(f" Failed to parse/merge requirements: {e}")
            print(f" Response was: {response.content[:200]}")
        
        return state

    async def _check_completion_node(self, state: AgentState) -> AgentState:
        """ Node 3: Checks and updates the completion status based on the changes.
        
        """
        print("NODE 3: CHECK")
        completion_prompt = COMPLETION_CHECK_PROMPT.format(
            requirements_json=state["requirements"].model_dump_json(indent=2)
        )
        
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=completion_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            # Extract JSON from response
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            completion_data = json.loads(content.strip())
            
            # Update the RequirementsState with completion info
            current_dict = state["requirements"].model_dump()
            current_dict["is_complete"] = completion_data.get("is_complete", False)
            current_dict["progress"] = completion_data.get("completeness_score", 0.0)
            
            # Create new RequirementsState instance
            state["requirements"] = RequirementsState(**current_dict)
            
            print(f"Progress: {state['requirements'].progress:.0%}")
            print(f"Complete: {state['requirements'].is_complete}")
            
            if not state["requirements"].is_complete:
                missing = completion_data.get("missing_critical_info", [])
                if missing:
                    print(f"Still need: {', '.join(missing[:3])}")
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to parse completion check: {e}")
            # Default to incomplete, increment progress slightly
            current_dict = state["requirements"].model_dump()
            current_dict["is_complete"] = False
            current_dict["progress"] = min(0.8, current_dict.get("progress", 0.0) + 0.1)
            state["requirements"] = RequirementsState(**current_dict)
        
        return state
    
    async def _generate_question_node(self, state: AgentState) -> AgentState:
        """ Node 4: Generates next question if needed.
        
        Only generates one precise and focused question. Question is added to the
        message history as a helper message.
        """
        print("NODE 4: QUESTION")
        
        conv_history = format_conversation_history(
            [{"role": m.type, "content": m.content} for m in state["messages"]]
        )
        
        question_prompt = f"""Based on the current requirements and conversation, generate the NEXT SINGLE QUESTION to ask.

        Current Requirements:
        {state["requirements"].model_dump_json(indent=2)}

        Recent Conversation:
        {conv_history}

        Generate ONE clear, focused question that will help gather the most important missing information.
        Make it conversational and natural. Build on what you already know.
        Return ONLY the question text, nothing else."""
        
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=question_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        question = response.content.strip()
        
        # Clean up any quotes or extra formatting
        question = question.strip('"\'')
        
        state["next_question"] = question
        
        # Add the question to conversation history as assistant message
        state["messages"].append(AIMessage(content=question))
        
        print(f"Question: '{question[:100]}...'")
        
        return state

    def _should_continue(self, state: AgentState) -> str:
        """Determine if we should continue asking questions or end.
        
        """
        if state["requirements"].is_complete or state["requirements"].progress >= 0.85:
            print("Requirements gathering complete!")
            return "complete"
        
        print(f"Continuing (progress: {state['requirements'].progress:.0%})...")
        return "continue"

    
    async def process_message(
        self,
        user_message: str,
        current_requirements: RequirementsState,
        conversation_history: list[ChatMessage]
    ) -> dict:
        """Process a user message and return the agent's response.
        
        This is the main entry point for the agent. It does the following:
        
        1. Converts and adds converted LangChain messages
        2. Initializes the graph
        3. Runs the workflow through the steps above
        4. Returns a JSON response
        
        """
        print(f"\n{'='*60}")
        print(f"Processing message: '{user_message[:50]}...'")
        print(f"{'='*60}")
        
        # Convert conversation history to LangChain messages
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        
        for msg in conversation_history[-10:]:  # Keep last 10 for context
            if msg.role == MessageRole.USER:
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                messages.append(AIMessage(content=msg.content))
        
        # Add the new user message
        messages.append(HumanMessage(content=user_message))
        
        # Initialize the graph state with RequirementsState instance
        initial_state = {
            "messages": messages,
            "requirements": current_requirements,
            "decisions": [],
            "assumptions": [],
            "next_question": ""
        }
        
        # Run the workflow graph
        try:
            final_state = await self.graph.ainvoke(initial_state)
        except Exception as e:
            print(f"Error in graph execution: {e}")
            raise
        
        print(f"{'='*60}\n")
        
        # Return structured response
        return {
            "response": final_state["next_question"],
            "requirements": final_state["requirements"],
            "is_complete": final_state["requirements"].is_complete,
            "progress": final_state["requirements"].progress,
            "decisions": final_state["decisions"],
            "assumptions": final_state["assumptions"]
        }


# Singleton instance for the agent
_agent_instance = None


def get_agent() -> RequirementsAgent:
    """Gets or creates the RequirementsAgent to ensure no duplicates and redundancy
    
    Returns:
        RequirementsAgent: The singleton agent instance
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = RequirementsAgent()
    return _agent_instance


