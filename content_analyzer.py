"""Content analysis for TikTok live streams."""
import re
import time
from typing import Dict, List, Tuple
from collections import defaultdict
from textblob import TextBlob


class ContentAnalyzer:
    """Analyzes content from TikTok live streams for contextual understanding."""
    
    def __init__(self):
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
        self.positive_keywords = {
            'love', 'awesome', 'great', 'amazing', 'fantastic', 'wow', 'cool', 
            'beautiful', 'perfect', 'incredible', 'brilliant', 'excellent'
        }
        self.negative_keywords = {
            'hate', 'terrible', 'awful', 'horrible', 'worst', 'boring', 'stupid'
        }
        self.topic_keywords = defaultdict(int)
        self.last_analysis = {}
        
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract relevant keywords from text."""
        if not text:
            return []
            
        # Clean and split into words
        text = re.sub(r'[^\w\s]', '', text.lower())
        words = text.split()
        
        # Remove stopwords and short words
        keywords = [
            word for word in words 
            if word not in self.stop_words and len(word) > 3
        ]
        
        # Count frequency and return top keywords
        word_count = {}
        for word in keywords:
            word_count[word] = word_count.get(word, 0) + 1
            
        # Sort by frequency and return top keywords
        sorted_keywords = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_keywords[:max_keywords]]
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text."""
        if not text:
            return {"polarity": 0.0, "subjectivity": 0.0}
            
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        subjectivity = blob.sentiment.subjectivity  # 0 to 1
        
        return {
            "polarity": polarity,
            "subjectivity": subjectivity
        }
    
    def detect_topics(self, text: str) -> List[str]:
        """Detect topics from text."""
        keywords = self.extract_keywords(text, 5)
        
        # Update topic frequency tracking
        for keyword in keywords:
            self.topic_keywords[keyword] += 1
            
        return keywords
    
    def get_emotion_from_sentiment(self, sentiment: Dict[str, float]) -> str:
        """Convert sentiment to emotional reaction."""
        polarity = sentiment["polarity"]
        
        if polarity > 0.5:
            return "excited"
        elif polarity > 0.1:
            return "happy"
        elif polarity > -0.1:
            return "neutral"
        elif polarity > -0.5:
            return "concerned"
        else:
            return "disappointed"
    
    def generate_context_summary(self, recent_text: str, recent_comments: List[str] = None) -> Dict:
        """Generate a comprehensive context summary."""
        if not recent_text:
            return {
                "keywords": [],
                "sentiment": {"polarity": 0.0, "subjectivity": 0.0},
                "emotion": "neutral",
                "topics": [],
                "recent_comment_count": len(recent_comments) if recent_comments else 0
            }
        
        # Extract keywords
        keywords = self.extract_keywords(recent_text)
        
        # Analyze sentiment
        sentiment = self.analyze_sentiment(recent_text)
        
        # Determine emotion
        emotion = self.get_emotion_from_sentiment(sentiment)
        
        # Detect topics
        topics = self.detect_topics(recent_text)
        
        return {
            "keywords": keywords[:5],
            "sentiment": sentiment,
            "emotion": emotion,
            "topics": topics[:3],
            "recent_comment_count": len(recent_comments) if recent_comments else 0
        }


# Global analyzer instance
content_analyzer = ContentAnalyzer()