import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RiskEngine:
    """
    Computes weighted automation risk scores to prevent reckless submissions.
    """
    
    @staticmethod
    def calculate_anti_bot_risk(adapter_metrics: Dict[str, Any]) -> float:
        """
        Calculate risk based on recent CAPTCHA occurrences and proxy drops.
        Returns a score from 0.0 to 1.0 (1.0 = highly likely to be blocked).
        """
        captcha_count = adapter_metrics.get("captcha_incidents", 0)
        recent_failures = adapter_metrics.get("recent_failures", 0)
        
        score = 0.0
        if captcha_count > 0:
            score += min(captcha_count * 0.3, 0.6)
        if recent_failures > 3:
            score += 0.4
            
        return min(score, 1.0)

    @staticmethod
    def calculate_automation_confidence(field_success_rate: float, dom_divergence: float) -> float:
        """
        Calculate confidence that the automation is correctly interpreting the page.
        Returns a score from 0.0 to 1.0 (1.0 = absolute certainty).
        """
        confidence = 1.0
        
        # Penalize if historically successful selectors are failing
        confidence -= (1.0 - field_success_rate) * 0.5
        
        # Penalize if the page looks drastically different than expected (e.g., unexpected forms)
        confidence -= min(dom_divergence * 0.5, 0.8)
        
        return max(confidence, 0.0)

    @classmethod
    def evaluate_submission_safety(cls, adapter_metrics: Dict[str, Any], field_success_rate: float, dom_divergence: float) -> bool:
        """
        Returns True if safe to submit, False if it should escalate to requires_human.
        """
        anti_bot_risk = cls.calculate_anti_bot_risk(adapter_metrics)
        confidence = cls.calculate_automation_confidence(field_success_rate, dom_divergence)
        
        logger.info(f"Risk Engine: Anti-bot risk = {anti_bot_risk:.2f}, Confidence = {confidence:.2f}")
        
        # Thresholds
        if anti_bot_risk > 0.7:
            logger.warning("Risk Engine: High anti-bot risk. Escalate to human.")
            return False
            
        if confidence < 0.6:
            logger.warning("Risk Engine: Low automation confidence. Escalate to human.")
            return False
            
        return True
