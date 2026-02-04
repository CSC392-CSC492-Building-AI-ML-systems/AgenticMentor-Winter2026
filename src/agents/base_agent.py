
from abc import ABC, abstractmethod
from protocols.review_protocol import ReviewProtocol

class BaseAgent(ABC):
    def __init__(self, name: str, llm_client, review_config: dict):
        self.name = name
        self.llm = llm_client
        self.reviewer = ReviewProtocol(review_config)
    
    async def execute(self, input: str, context: dict, tools: list):
        """
        Execution cycle with recursive review
        """
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            # Generate output
            raw_output = await self._generate(input, context, tools)
            
            # Review Protocol (Self-Correction Loop)
            review_result = await self.reviewer.validate(
                output=raw_output,
                context=context,
                quality_criteria=self._get_quality_criteria()
            )
            
            if review_result.is_valid:
                return AgentOutput(
                    content=raw_output,
                    state_delta=self._extract_state_delta(raw_output),
                    metadata={
                        "agent": self.name,
                        "review_score": review_result.score,
                        "attempts": attempt + 1
                    }
                )
            else:
                # Recursive correction
                input = self._build_correction_prompt(
                    original_input=input,
                    failed_output=raw_output,
                    review_feedback=review_result.feedback
                )
                attempt += 1
        
        # Fallback: Return best attempt with warning flag
        return AgentOutput(
            content=raw_output,
            state_delta={},
            metadata={"status": "degraded", "review_failures": attempt}
        )
    
    @abstractmethod
    def _generate(self, input, context, tools):
        pass
    
    @abstractmethod
    def _get_quality_criteria(self):
        pass