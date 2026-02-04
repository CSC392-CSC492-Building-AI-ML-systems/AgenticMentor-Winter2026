
class StateManager:
    def __init__(self, persistence_adapter):
        self.db = persistence_adapter
        self.cache = {}  # In-memory cache for active sessions
    
    async def load(self, session_id: str) -> ProjectState:
        """Load state with caching"""
        if session_id in self.cache:
            return self.cache[session_id]
        
        state_dict = await self.db.get(session_id)
        state = ProjectState(**state_dict) if state_dict else ProjectState(session_id=session_id)
        self.cache[session_id] = state
        return state
    
    async def update(self, session_id: str, delta: dict):
        """
        Atomic state updates with conflict resolution
        """
        state = await self.load(session_id)
        
        # Apply delta (deep merge)
        for key, value in delta.items():
            if hasattr(state, key):
                current = getattr(state, key)
                if isinstance(current, list):
                    current.extend(value if isinstance(value, list) else [value])
                elif isinstance(current, dict):
                    current.update(value)
                else:
                    setattr(state, key, value)
        
        state.updated_at = datetime.utcnow()
        
        # Persist
        await self.db.save(session_id, state.dict())
        self.cache[session_id] = state
    
    async def get_fragment(self, session_id: str, path: str):
        """
        Extract specific state fragment for token optimization
        Example: get_fragment("session_123", "architecture.tech_stack")
        """
        state = await self.load(session_id)
        keys = path.split(".")
        value = state
        for key in keys:
            value = getattr(value, key)
        return value