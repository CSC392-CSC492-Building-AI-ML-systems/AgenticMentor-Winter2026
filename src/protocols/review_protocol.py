
class ReviewProtocol:
    def __init__(self, config: dict):
        self.validators = [
            FeasibilityValidator(),
            ClarityValidator(),
            CompletenessValidator(),
            ConsistencyValidator()
        ]
        self.min_score = config.get("min_score", 0.75)
    
    async def validate(self, output: str, context: dict, quality_criteria: dict):
        """
        Multi-dimensional validation
        """
        scores = {}
        feedback = []
        
        for validator in self.validators:
            result = validator.check(output, context, quality_criteria)
            scores[validator.name] = result.score
            if result.issues:
                feedback.extend(result.issues)
        
        # Weighted average
        total_score = self._calculate_weighted_score(scores, quality_criteria)
        
        return ReviewResult(
            is_valid=(total_score >= self.min_score and not feedback),
            score=total_score,
            feedback=feedback,
            detailed_scores=scores
        )

# Example validator
class FeasibilityValidator:
    def check(self, output, context, criteria):
        """
        Checks for technical feasibility markers
        """
        issues = []
        
        # Check for undefined technologies
        tech_stack = extract_technologies(output)
        for tech in tech_stack:
            if not is_real_technology(tech):
                issues.append(f"Unknown technology: {tech}")
        
        # Check for resource conflicts
        if "database" in context and "database" in output:
            if context["database"] != output["database"]:
                issues.append("Database inconsistency detected")
        
        score = 1.0 - (len(issues) * 0.2)
        return ValidationResult(score=max(0, score), issues=issues)