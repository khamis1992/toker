"""AI-powered comment generator for TikTok interactions."""
import random
import time
from typing import Dict, List, Optional
from content_analyzer import content_analyzer


class CommentGenerator:
    """Generates contextual comments for TikTok live streams."""
    
    def __init__(self):
        # Template-based comments organized by context
        self.comment_templates = {
            "greeting": [
                "Hi {creator}! Love your content!",
                "Hey there! Great stream as always!",
                "Hello {creator}! Happy to be here!",
                "Greetings from {location}! Loving the stream!",
            ],
            "positive_reaction": [
                "This is amazing! 🔥",
                "So cool! Keep it up!",
                "Absolutely loving this!",
                "You're killing it today!",
                "This is incredible 😍",
            ],
            "question": [
                "How long have you been doing this?",
                "Where did you learn this skill?",
                "Can you share tips for beginners?",
                "What inspired this idea?",
                "Any advice for newcomers?",
            ],
            "generic_positive": [
                "🔥🔥🔥",
                "This is awesome!",
                "So good!",
                "Amazing content!",
                "Great job!",
                "Love this!",
                "Keep going!",
                "Fantastic!",
            ],
            "topic_specific": {
                "music": [
                    "The beat is perfect!",
                    "This song choice is fire!",
                    "Great music taste!",
                    "Perfect soundtrack!",
                ],
                "dance": [
                    "Those moves are incredible!",
                    "You're so talented!",
                    "Practice makes perfect!",
                    "Smooth dancing skills!",
                ],
                "tutorial": [
                    "Very educational!",
                    "Thanks for sharing this!",
                    "Step by step is perfect!",
                    "Great teaching skills!",
                ],
                "gaming": [
                    "What game is this?",
                    "Nice gameplay!",
                    "You're really good at this!",
                    "Cool game setup!",
                ],
            }
        }
        
        # Emoji mappings for emotions
        self.emotion_emojis = {
            "excited": ["🔥", "😍", "🎉", "💯", "🚀"],
            "happy": ["😊", "👍", "😄", "❤️", "👏"],
            "neutral": ["👌", "👍", "🙂", "👀", "🤝"],
            "concerned": ["🤔", "😅", "😕", "💭", "🤷"],
            "disappointed": ["😔", "😞", "💔", "😢", "😐"],
        }
        
    def generate_greeting(self, creator_name: str = "creator") -> str:
        """Generate a greeting comment."""
        template = random.choice(self.comment_templates["greeting"])
        location = random.choice(["the neighborhood", "around the corner", "nearby", "next door"])
        return template.format(creator=creator_name, location=location)
    
    def generate_reaction_comment(self, context: Dict) -> str:
        """Generate a reaction comment based on context."""
        emotion = context.get("emotion", "neutral")
        topics = context.get("topics", [])
        keywords = context.get("keywords", [])
        
        # Choose appropriate template based on context
        if emotion in ["excited", "happy"] and random.random() < 0.7:
            comment = random.choice(self.comment_templates["positive_reaction"])
        elif topics and random.random() < 0.5:
            # Try to use topic-specific comments
            for topic in topics:
                if topic in self.comment_templates["topic_specific"]:
                    comment = random.choice(self.comment_templates["topic_specific"][topic])
                    break
            else:
                comment = random.choice(self.comment_templates["generic_positive"])
        else:
            comment = random.choice(self.comment_templates["generic_positive"])
        
        # Add emotion-appropriate emoji
        if emotion in self.emotion_emojis and random.random() < 0.8:
            chosen_emoji = random.choice(self.emotion_emojis[emotion])
            if random.random() < 0.5:  # Sometimes add emoji at the end
                comment += f" {chosen_emoji}"
            else:  # Sometimes replace with emoji only for variety
                if len(comment) > 10 and random.random() < 0.3:
                    comment = chosen_emoji * random.randint(1, 3)
        
        return comment
    
    def generate_question(self, context: Dict) -> str:
        """Generate a contextual question."""
        topics = context.get("topics", [])
        
        # Try to make question relevant to content
        if topics:
            topic_questions = {
                "music": "What song is playing right now?",
                "dance": "How long have you been practicing these moves?",
                "tutorial": "Can you explain that technique in more detail?",
                "gaming": "What game are you playing?",
                "cooking": "What ingredients are you using?",
                "art": "What tools do you use for this?",
            }
            
            for topic in topics:
                if topic in topic_questions:
                    return topic_questions[topic]
        
        # Fallback to general questions
        return random.choice(self.comment_templates["question"])
    
    def generate_contextual_comment(self, recent_text: str, comment_type: str = "reaction") -> str:
        """Generate a fully contextual comment."""
        # Analyze the content context
        context = content_analyzer.generate_context_summary(recent_text)
        
        if comment_type == "greeting":
            return self.generate_greeting()
        elif comment_type == "question":
            return self.generate_question(context)
        else:  # reaction
            return self.generate_reaction_comment(context)
    
    def generate_varied_comment_sequence(self, recent_texts: List[str], count: int = 3) -> List[str]:
        """Generate a sequence of varied comments."""
        comments = []
        used_comments = set()
        
        # Get overall context from recent texts
        combined_text = " ".join(recent_texts[-5:]) if recent_texts else ""
        context = content_analyzer.generate_context_summary(combined_text)
        
        comment_types = ["reaction", "reaction", "question"]  # Weight toward reactions
        
        for i in range(min(count, 5)):  # Limit to reasonable number
            # Choose comment type with some randomness
            if i < len(comment_types):
                ctype = comment_types[i]
            else:
                ctype = random.choice(["reaction", "reaction", "question"])  # Weight toward reactions
                
            comment = self.generate_contextual_comment(combined_text, ctype)
            
            # Avoid duplicate comments
            attempts = 0
            while comment in used_comments and attempts < 3:
                comment = self.generate_contextual_comment(combined_text, ctype)
                attempts += 1
                
            if comment:
                comments.append(comment)
                used_comments.add(comment)
                
            # Add slight delay to simulate thinking
            time.sleep(random.uniform(0.1, 0.5))
            
        return comments


# Global comment generator instance
comment_generator = CommentGenerator()