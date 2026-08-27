import os

class FeatureFlags:
    """
    Provides a centralized feature flag system to gracefully degrade features
    during high load or partial outages without dropping the entire platform.
    
    In a real system, these would read from a remote config like LaunchDarkly,
    Redis, or an internal Admin DB. Here we mock them via environment variables.
    """
    
    @staticmethod
    def is_ai_enabled() -> bool:
        """If False, the AI Gateway returns a fallback 'under maintenance' message."""
        return os.getenv("FEATURE_AI_ENABLED", "True").lower() == "true"
        
    @staticmethod
    def is_food_vision_enabled() -> bool:
        """If False, food image uploads are temporarily disabled to save GPU/API costs."""
        return os.getenv("FEATURE_FOOD_VISION_ENABLED", "True").lower() == "true"
        
    @staticmethod
    def is_wearable_sync_enabled() -> bool:
        """If False, background syncing is paused to relieve database pressure."""
        return os.getenv("FEATURE_WEARABLE_SYNC_ENABLED", "True").lower() == "true"
        
    @staticmethod
    def is_longitudinal_insights_enabled() -> bool:
        """If False, complex daily aggregations are skipped to preserve DB CPU."""
        return os.getenv("FEATURE_INSIGHTS_ENABLED", "True").lower() == "true"
