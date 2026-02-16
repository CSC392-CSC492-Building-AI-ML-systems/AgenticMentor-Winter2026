"""Collects and normalizes project requirements from user input."""

from __future__ import annotations
from typing import TypedDict, Annotated, Sequence, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import operator

from src.agents.base_agent import BaseAgent
from src.utils.config import settings
from src.utils.prompt import (
    SYSTEM_PROMPT,
    ANALYSIS_PROMPT,
    UPDATE_PROMPT,
    COMPLETION_CHECK_PROMPT,
    format_conversation_history
)
from src.protocols.schemas import RequirementsState, ChatMessage, MessageRole


class AgentState(TypedDict):
    """State for the requirements collection agent."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    requirements: RequirementsState
    decisions: list[str]
    assumptions: list[str]
    next_question: str


class RequirementsAgent(BaseAgent):
    """Requirements Collector Agent using LangGraph, inheriting from BaseAgent."""
    
    def __init__(self, review_config: Optional[dict] = None):
        """Initialize the agent with LLM and compile the graph."""
        llm_client = ChatGoogleGenerativeAI(
            model=settings.model_name,
            temperature=settings.model_temperature,
            max_tokens=settings.model_max_tokens,
            google_api_key=settings.gemini_api_key,
        )
        
        super().__init__(
            name="RequirementsCollector",
            llm_client=llm_client,
            review_config=review_config
        )
        
        print("Initializing Requirements Agent...")
        self.graph = self._build_graph()
        print("Agent ready")
    
    def _build_graph(self) -> StateGraph:
        """Build the complete LangGraph workflow."""
        print("Building workflow graph...")
        
        workflow = StateGraph(AgentState)
        
        workflow.add_node("analyze", self._analyze_node)
        workflow.add_node("update_requirements", self._update_requirements_node)
        workflow.add_node("check_completion", self._check_completion_node)
        workflow.add_node("generate_question", self._generate_question_node)
        
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "update_requirements")
        workflow.add_edge("update_requirements", "check_completion")
        
        workflow.add_conditional_edges(
            "check_completion",
            self._should_continue,
            {
                "continue": "generate_question",
                "complete": END
            }
        )
        workflow.add_edge("generate_question", END)
        
        print("Graph built successfully")
        return workflow.compile()
    
    async def _generate(self, input: Any, context: dict, tools: list) -> Any:
        """
        BaseAgent abstract method implementation.
        Executes the LangGraph workflow for requirements collection.
        """
        user_message = input.get("message", "") if isinstance(input, dict) else str(input)
        current_requirements = context.get("requirements", RequirementsState())
        conversation_history = context.get("conversation_history", [])
        
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        
        for msg in conversation_history[-10:]:
            if msg.role == MessageRole.USER:
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                messages.append(AIMessage(content=msg.content))
        
        messages.append(HumanMessage(content=user_message))
        
        initial_state = {
            "messages": messages,
            "requirements": current_requirements,
            "decisions": [],
            "assumptions": [],
            "next_question": ""
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        
        return {
            "response": final_state["next_question"],
            "requirements": final_state["requirements"],
            "is_complete": final_state["requirements"].is_complete,
            "progress": final_state["requirements"].progress,
            "decisions": final_state["decisions"],
            "assumptions": final_state["assumptions"]
        }
    
    def _get_quality_criteria(self) -> dict:
        """Return weighted review criteria for requirements collection."""
        return {
            "completeness": 0.3,
            "clarity": 0.25,
            "relevance": 0.25,
            "specificity": 0.2
        }
    
    async def _analyze_node(self, state: AgentState) -> AgentState:
        """Node 1: Analyze current state and conversation history."""
        print("STEP 1")
        print("[ANALYZE] Analyzing conversation context...")
        
        conv_history = format_conversation_history(
            [{"role": m.type, "content": m.content} for m in state["messages"]]
        )
        
        if len(state["messages"]) <= 1:
            print("First message, skipping deep analysis")
            return state
        
        analysis_prompt = ANALYSIS_PROMPT.format(
            requirements_json=state["requirements"].model_dump_json(indent=2),
            conversation_history=conv_history
        )
        
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=analysis_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        print(f"Analysis: {response.content[:150]}...")
        
        return state
    
    async def _update_requirements_node(self, state: AgentState) -> AgentState:
        """Node 2: Update requirements state based on user's latest response."""
        print("STEP 2")
        print("[UPDATE] Extracting and merging new requirements...")
        
        user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
        if not user_messages:
            print("No user message to process")
            return state
        
        last_user_message = user_messages[-1].content
        print(f"Processing: '{last_user_message[:80]}...'")
        
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
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            updated_reqs = json.loads(content.strip())
            current_dict = state["requirements"].model_dump()
            
            merged_count = 0
            for key, value in updated_reqs.items():
                if value is not None and value != [] and value != "":
                    if isinstance(value, list) and key in current_dict:
                        existing = current_dict.get(key, [])
                        if isinstance(existing, list):
                            current_dict[key] = list(set(existing + value))
                        else:
                            current_dict[key] = value
                    else:
                        current_dict[key] = value
                    merged_count += 1
            
            state["requirements"] = RequirementsState(**current_dict)
            print(f"Merged {merged_count} requirement updates")
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to parse/merge requirements: {e}")
        
        return state
    
    async def _check_completion_node(self, state: AgentState) -> AgentState:
        """Node 3: Check if requirements are sufficiently complete."""
        print("STEP 3")
        print("[CHECK] Evaluating requirements completeness...")
        
        completion_prompt = COMPLETION_CHECK_PROMPT.format(
            requirements_json=state["requirements"].model_dump_json(indent=2)
        )
        
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=completion_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            completion_data = json.loads(content.strip())
            
            current_dict = state["requirements"].model_dump()
            current_dict["is_complete"] = completion_data.get("is_complete", False)
            current_dict["progress"] = completion_data.get("completeness_score", 0.0)
            
            state["requirements"] = RequirementsState(**current_dict)
            
            print(f"Progress: {state['requirements'].progress:.0%}")
            print(f"Complete: {state['requirements'].is_complete}")
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to parse completion check: {e}")
            current_dict = state["requirements"].model_dump()
            current_dict["is_complete"] = False
            current_dict["progress"] = min(0.8, current_dict.get("progress", 0.0) + 0.1)
            state["requirements"] = RequirementsState(**current_dict)
        
        return state
    
    async def _generate_question_node(self, state: AgentState) -> AgentState:
        """Node 4: Generate the next question to ask the user."""
        print("STEP 4")
        print("[QUESTION] Generating next question...")
        
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
        question = response.content.strip().strip('"\'')
        
        state["next_question"] = question
        state["messages"].append(AIMessage(content=question))
        
        print(f"Question: '{question[:200]}...'")
        return state
    
    def _should_continue(self, state: AgentState) -> str:
        """Determine if we should continue asking questions or end."""
        if state["requirements"].is_complete or state["requirements"].progress >= 0.85:
            print("Requirements gathering complete")
            return "complete"
        
        print(f"Continuing (progress: {state['requirements'].progress:.0%})")
        return "continue"
    
    async def process_message(
        self,
        user_message: str,
        current_requirements: RequirementsState,
        conversation_history: list[ChatMessage]
    ) -> dict:
        """
        Process a user message and return the agent's response.
        This method maintains backward compatibility with existing code.
        """
        print(f"Processing message: '{user_message[:50]}...'")
        
        context = {
            "requirements": current_requirements,
            "conversation_history": conversation_history
        }
        
        input_data = {"message": user_message}
        
        try:
            result = await self._generate(input_data, context, [])
            return result
        except Exception as e:
            print(f"Error in graph execution: {e}")
            raise


_agent_instance = None


def get_agent() -> RequirementsAgent:
    """Get or create the singleton agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = RequirementsAgent()
    return _agent_instance