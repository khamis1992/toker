"""Interactive features controller for TikTok bot."""
import asyncio
import random
import time
from typing import Dict, List, Optional
from playwright.async_api import Page
from comment_generator import comment_generator
from reaction_system import reaction_system, ReactionType
from content_analyzer import content_analyzer


class InteractiveController:
    """Controls interactive features like commenting and reactions."""
    
    def __init__(self, viewer_id: int):
        self.viewer_id = viewer_id
        self.active = True
        self.last_comment_time = 0
        self.last_reaction_time = 0
        self.engagement_profile = "moderate"  # Can be "active", "moderate", "passive"
        self.interaction_stats = {
            "comments_sent": 0,
            "reactions_made": 0,
            "questions_asked": 0,
        }
        
    async def send_comment(self, page: Page, comment: str) -> bool:
        """Send a comment to the live stream."""
        try:
            # Look for comment input field
            comment_selectors = [
                'textarea[data-testid="dm-form-input"]',  # Direct message
                'textarea[placeholder*="comment"]',
                'textarea[placeholder*="Comment"]',
                'textarea[class*="comment"]',
                'input[placeholder*="comment"]',
                'input[placeholder*="Comment"]',
            ]
            
            comment_input = None
            for selector in comment_selectors:
                try:
                    comment_input = await page.query_selector(selector)
                    if comment_input:
                        break
                except:
                    continue
            
            if not comment_input:
                print(f"Viewer {self.viewer_id}: Comment input not found")
                return False
                
            # Fill and submit comment
            await comment_input.fill(comment)
            await asyncio.sleep(random.uniform(0.5, 1.5))  # Human-like typing delay
            
            # Try to find and click submit button
            submit_selectors = [
                'button[type="submit"]',
                'button[data-testid*="send"]',
                'button[class*="send"]',
                'button[class*="submit"]',
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = await page.query_selector(selector)
                    if submit_button:
                        break
                except:
                    continue
            
            if submit_button:
                await submit_button.click()
            else:
                # Try pressing Enter
                await comment_input.press('Enter')
            
            await asyncio.sleep(random.uniform(1, 3))  # Wait for submission
            
            self.interaction_stats["comments_sent"] += 1
            self.last_comment_time = time.time()
            
            print(f"Viewer {self.viewer_id}: Comment sent: '{comment}'")
            return True
            
        except Exception as e:
            print(f"Viewer {self.viewer_id}: Failed to send comment: {e}")
            return False
    
    async def send_reaction(self, page: Page, reaction_type: ReactionType) -> bool:
        """Send a reaction to the live stream."""
        try:
            # Look for reaction buttons
            reaction_selectors = {
                ReactionType.LIKE: [
                    'button[aria-label*="like"]',
                    'button[aria-label*="Like"]',
                    'svg[aria-label*="like"]',
                    'div[role="button"][data-e2e*="like"]',
                ],
                ReactionType.HEART: [
                    'button[aria-label*="heart"]',
                    'button[aria-label*="Heart"]',
                    'svg[aria-label*="heart"]',
                ],
                ReactionType.FIRE: [
                    'button[aria-label*="fire"]',
                    'button[aria-label*="Fire"]',
                ]
            }
            
            selectors = reaction_selectors.get(reaction_type, reaction_selectors[ReactionType.LIKE])
            reaction_button = None
            
            for selector in selectors:
                try:
                    reaction_button = await page.query_selector(selector)
                    if reaction_button:
                        break
                except:
                    continue
            
            if not reaction_button:
                print(f"Viewer {self.viewer_id}: Reaction button not found for {reaction_type.value}")
                return False
                
            # Click the reaction button
            await reaction_button.click()
            await asyncio.sleep(random.uniform(0.5, 2))  # Brief pause
            
            reaction_system.record_reaction(reaction_type)
            self.interaction_stats["reactions_made"] += 1
            self.last_reaction_time = time.time()
            
            print(f"Viewer {self.viewer_id}: Sent reaction: {reaction_type.value}")
            return True
            
        except Exception as e:
            print(f"Viewer {self.viewer_id}: Failed to send reaction: {e}")
            return False
    
    async def generate_and_send_comment(self, page: Page, recent_content: str = "") -> bool:
        """Generate and send a contextual comment."""
        # Check if we can comment (rate limiting)
        current_time = time.time()
        if current_time - self.last_comment_time < 30:  # Minimum 30 seconds between comments
            return False
            
        # Generate comment based on content
        comment_type = random.choices(
            ["reaction", "question"], 
            weights=[0.7, 0.3],  # Mostly reactions, some questions
            k=1
        )[0]
        
        comment = comment_generator.generate_contextual_comment(recent_content, comment_type)
        
        if comment:
            success = await self.send_comment(page, comment)
            if success:
                if comment_type == "question":
                    self.interaction_stats["questions_asked"] += 1
            return success
        
        return False
    
    async def auto_interact(self, page: Page, context: Dict = None) -> None:
        """Automatically interact with the live stream."""
        if not self.active:
            return
            
        try:
            # Get recent content for context (would come from live stream analysis)
            recent_content = ""  # This would be populated with actual stream content
            
            # Decide whether to react
            if reaction_system.should_react(context, self.engagement_profile):
                reaction_type = reaction_system.choose_reaction_type(context)
                await self.send_reaction(page, reaction_type)
            
            # Occasionally send comments (less frequent than reactions)
            if random.random() < 0.3:  # 30% chance to comment
                await asyncio.sleep(random.uniform(5, 15))  # Wait a bit before commenting
                await self.generate_and_send_comment(page, recent_content)
                
        except Exception as e:
            print(f"Viewer {self.viewer_id}: Auto-interact error: {e}")
    
    def set_engagement_profile(self, profile: str) -> None:
        """Set the engagement profile for this viewer."""
        if profile in ["active", "moderate", "passive"]:
            self.engagement_profile = profile
            print(f"Viewer {self.viewer_id}: Engagement profile set to {profile}")
    
    def get_interaction_stats(self) -> Dict:
        """Get interaction statistics for this viewer."""
        stats = self.interaction_stats.copy()
        stats.update(reaction_system.get_reaction_stats())
        return stats
    
    def stop_interactions(self) -> None:
        """Stop all interactive activities."""
        self.active = False
        print(f"Viewer {self.viewer_id}: Interactions stopped")


# Example usage function
async def demo_interactive_features():
    """Demo the interactive features (for testing)."""
    print("Demo: Interactive Features for TikTok Bot")
    print("=" * 40)
    
    # Create controller
    controller = InteractiveController(viewer_id=1)
    
    # Demo comment generation
    sample_context = "Today I'm going to show you how to make the perfect pasta dish. This recipe has been passed down in my family for generations."
    context = content_analyzer.generate_context_summary(sample_context)
    
    print("\nGenerated Comments:")
    comments = comment_generator.generate_varied_comment_sequence([sample_context], 3)
    for i, comment in enumerate(comments, 1):
        # Remove emojis for display to avoid encoding issues
        clean_comment = ''.join(char if ord(char) < 128 else '?' for char in comment)
        print(f"  {i}. {clean_comment}")
    
    print("\nReaction Selection:")
    reaction = reaction_system.choose_reaction_type(context)
    print(f"  Selected reaction: {reaction.value}")
    
    print("\nTiming Analysis:")
    timing = reaction_system.generate_reaction_timing(context)
    print(f"  Recommended delay: {timing:.1f} seconds")
    
    print("\nEngagement Stats:")
    stats = controller.get_interaction_stats()
    print(f"  Comments sent: {stats.get('comments_sent', 0)}")
    print(f"  Reactions made: {stats.get('reactions_made', 0)}")
    
    print("\nDemo complete!")


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_interactive_features())