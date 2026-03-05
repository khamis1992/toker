"""Reaction system for TikTok interactions."""
import random
import time
from typing import Dict, List
from enum import Enum


class ReactionType(Enum):
    LIKE = "like"
    HEART = "heart"
    FIRE = "fire"
    HAHA = "haha"
    WOW = "wow"
    SAD = "sad"
    ANGRY = "angry"


class ReactionSystem:
    """Manages reactions and interactive responses for TikTok live streams."""
    
    def __init__(self):
        # Reaction probabilities based on content
        self.reaction_probabilities = {
            "exciting_content": 0.8,
            "normal_content": 0.4,
            "slow_period": 0.2,
            "first_minute": 0.9,
        }
        
        # Timing patterns to simulate human behavior
        self.timing_patterns = {
            "early_engagement": (5, 15),    # 5-15 seconds after stream start
            "regular_pacing": (30, 120),    # 30 seconds to 2 minutes between reactions
            "burst_mode": (2, 8),          # Rapid reactions during popular moments
        }
        
        # User engagement profiles
        self.engagement_profiles = {
            "active": {"like_rate": 0.7, "comment_rate": 0.4, "reaction_diversity": 0.6},
            "moderate": {"like_rate": 0.5, "comment_rate": 0.2, "reaction_diversity": 0.4},
            "passive": {"like_rate": 0.3, "comment_rate": 0.1, "reaction_diversity": 0.2},
        }
        
        # Track reaction history to avoid spam
        self.reaction_history = []
        self.last_reaction_time = 0
        self.reactions_this_minute = 0
        
    def should_react(self, context: Dict = None, profile: str = "moderate") -> bool:
        """Determine if we should react based on context and profile."""
        # Check rate limiting
        current_time = time.time()
        if current_time - self.last_reaction_time < 2:  # Minimum 2 seconds between reactions
            return False
            
        # Reset minute counter
        if current_time - getattr(self, 'minute_start', current_time) > 60:
            self.reactions_this_minute = 0
            self.minute_start = current_time
            
        # Don't exceed 15 reactions per minute
        if self.reactions_this_minute >= 15:
            return False
            
        # Get base probability from profile
        base_prob = self.engagement_profiles[profile]["like_rate"]
        
        # Adjust based on context if provided
        if context:
            emotion = context.get("emotion", "neutral")
            if emotion == "excited":
                base_prob *= 1.5
            elif emotion == "disappointed":
                base_prob *= 0.3
            elif emotion == "neutral":
                base_prob *= 0.8
                
        # Add some randomness
        return random.random() < min(base_prob, 0.95)
    
    def choose_reaction_type(self, context: Dict = None) -> ReactionType:
        """Choose an appropriate reaction type based on context."""
        if not context:
            return ReactionType.LIKE
            
        emotion = context.get("emotion", "neutral")
        topics = context.get("topics", [])
        
        # Emotion-based reaction selection
        emotion_reactions = {
            "excited": [ReactionType.FIRE, ReactionType.HEART, ReactionType.WOW, ReactionType.LIKE],
            "happy": [ReactionType.HEART, ReactionType.HAHA, ReactionType.LIKE],
            "neutral": [ReactionType.LIKE, ReactionType.WOW],
            "concerned": [ReactionType.SAD, ReactionType.WOW],
            "disappointed": [ReactionType.SAD, ReactionType.ANGRY],
        }
        
        candidates = emotion_reactions.get(emotion, [ReactionType.LIKE])
        
        # Add topic-specific reactions
        topic_boosts = {
            "music": ReactionType.FIRE,
            "dance": ReactionType.FIRE,
            "funny": ReactionType.HAHA,
            "sad": ReactionType.SAD,
            "shocking": ReactionType.WOW,
        }
        
        for topic in topics:
            if topic in topic_boosts and topic_boosts[topic] not in candidates:
                candidates.append(topic_boosts[topic])
        
        # Weight selection toward more common reactions
        weights = []
        for reaction in candidates:
            if reaction == ReactionType.LIKE:
                weights.append(5)  # Most common
            elif reaction in [ReactionType.HEART, ReactionType.FIRE]:
                weights.append(3)
            else:
                weights.append(1)
                
        # Select weighted randomly
        return random.choices(candidates, weights=weights, k=1)[0]
    
    def generate_reaction_timing(self, context: Dict = None) -> float:
        """Generate appropriate timing for reaction."""
        current_time = time.time()
        
        if not context:
            # Regular pacing
            min_delay, max_delay = self.timing_patterns["regular_pacing"]
            return random.uniform(min_delay, max_delay)
            
        # Context-based timing
        emotion = context.get("emotion", "neutral")
        comment_count = context.get("recent_comment_count", 0)
        
        if emotion == "excited" or comment_count > 5:  # Burst mode during popular moments
            min_delay, max_delay = self.timing_patterns["burst_mode"]
            return random.uniform(min_delay, max_delay)
        elif emotion == "neutral":
            min_delay, max_delay = self.timing_patterns["regular_pacing"]
            return random.uniform(min_delay, max_delay)
        else:  # Slow period
            min_delay, max_delay = (60, 300)  # 1-5 minutes
            return random.uniform(min_delay, max_delay)
    
    def record_reaction(self, reaction_type: ReactionType, timestamp: float = None):
        """Record a reaction for history tracking."""
        if timestamp is None:
            timestamp = time.time()
            
        self.reaction_history.append({
            "type": reaction_type.value,
            "timestamp": timestamp,
            "minute": int(timestamp // 60)
        })
        
        self.last_reaction_time = timestamp
        self.reactions_this_minute += 1
    
    def get_reaction_stats(self, minutes: int = 5) -> Dict:
        """Get recent reaction statistics."""
        current_time = time.time()
        cutoff_time = current_time - (minutes * 60)
        
        recent_reactions = [
            r for r in self.reaction_history 
            if r["timestamp"] >= cutoff_time
        ]
        
        # Count by type
        type_counts = {}
        for reaction in recent_reactions:
            rtype = reaction["type"]
            type_counts[rtype] = type_counts.get(rtype, 0) + 1
            
        return {
            "total_reactions": len(recent_reactions),
            "reaction_types": type_counts,
            "reactions_per_minute": len(recent_reactions) / minutes if minutes > 0 else 0,
            "last_reaction": self.last_reaction_time,
        }


# Global reaction system instance
reaction_system = ReactionSystem()