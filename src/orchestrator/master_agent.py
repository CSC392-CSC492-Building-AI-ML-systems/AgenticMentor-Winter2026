#Psuedocode

class MasterOrchestrator:
    def __init__(self, state_manager, agent_registry):
        self.state = state_manager
        self.agents = agent_registry
        self.intent_classifier = IntentClassifier()
    
    async def process_request(self, user_input: str, session_id: str):
        """
        Main orchestration loop
        """
        # STEP 1: Load current project state
        project_state = await self.state.load(session_id)
        
        # STEP 2: Classify user intent
        intent = self.intent_classifier.analyze(
            user_input, 
            project_state.current_phase
        )
        # Returns: {
        #   "primary_intent": "requirements_gathering",
        #   "requires_agents": ["requirements_collector"],
        #   "context_fragments": ["project_goals", "constraints"],
        #   "confidence": 0.92
        # }
        
        # STEP 3: Route to agent(s)
        execution_plan = self._build_execution_plan(intent, project_state)
        
        # STEP 4: Execute agents sequentially or in parallel
        results = []
        for agent_task in execution_plan.tasks:
            agent = self.agents.get(agent_task.agent_name)
            
            # Extract only relevant state fragments (token optimization)
            context = self._extract_context(
                project_state, 
                agent_task.required_context
            )
            
            # Execute agent with inline review
            output = await agent.execute(
                input=agent_task.prompt,
                context=context,
                tools=agent_task.tools
            )
            
            # Update shared state
            await self.state.update(session_id, output.state_delta)
            results.append(output)
        
        # STEP 5: Synthesize response
        response = self._synthesize_response(results)
        
        return response
    
    def _build_execution_plan(self, intent, state):
        """
        Decision tree for multi-agent coordination
        """
        plan = ExecutionPlan()
        
        if intent.primary_intent == "requirements_gathering":
            plan.add_task(
                agent="requirements_collector",
                prompt=intent.user_input,
                required_context=["existing_requirements"],
                tools=["question_generator", "gap_analyzer"]
            )
        
        elif intent.primary_intent == "architecture_design":
            # Parallel execution example
            plan.add_parallel_tasks([
                Task(
                    agent="project_architect",
                    required_context=["requirements", "constraints"],
                    tools=["generate_mermaid", "query_vector_store"]
                ),
                Task(
                    agent="mockup_agent",
                    required_context=["requirements.ui_specs"],
                    tools=["ui_wireframe"]
                )
            ])
        
        elif intent.primary_intent == "export":
            plan.add_task(
                agent="exporter",
                required_context=["*"],  # Full state
                tools=["markdown_formatter", "pdf_exporter"]
            )
        
        return plan