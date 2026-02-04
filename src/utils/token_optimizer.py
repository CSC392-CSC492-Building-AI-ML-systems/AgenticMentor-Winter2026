# utils/token_optimizer.py

class ContextExtractor:
    """
    Intelligent context window management
    """
    
    AGENT_CONTEXT_REQUIREMENTS = {
        "requirements_collector": [
            "requirements.functional",
            "requirements.non_functional",
            "requirements.gaps"
        ],
        "project_architect": [
            "requirements.*",
            "architecture.tech_stack"
        ],
        "mockup_agent": [
            "requirements.user_stories",
            "architecture.tech_stack.frontend"
        ],
        "execution_planner_agent": [
            "requirements.*",
            "architecture.*",
            "mockups[*].screen_name"
        ],
        "exporter": ["*"]  # Full state
    }
    
    def extract(self, state: ProjectState, agent_name: str) -> dict:
        """
        Extract only relevant fragments
        """
        requirements = self.AGENT_CONTEXT_REQUIREMENTS.get(agent_name, [])
        context = {}
        
        for req in requirements:
            if req == "*":
                return state.dict()
            
            if ".*" in req:
                # Get all nested fields
                base_path = req.replace(".*", "")
                context[base_path] = self._get_nested(state, base_path)
            elif "[*]" in req:
                # Get list summary
                base_path = req.split("[*]")[0]
                items = self._get_nested(state, base_path)
                context[base_path] = [self._summarize_item(item) for item in items]
            else:
                # Direct path
                context[req] = self._get_nested(state, req)
        
        return context
    
    def _get_nested(self, obj, path: str):
        keys = path.split(".")
        value = obj
        for key in keys:
            value = getattr(value, key, None)
        return value