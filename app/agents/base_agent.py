"""Base agent class for all AI agents.

This module defines the foundational architecture for all AI agents in the Arbitrator AI system.
Every agent inherits from BaseAgent to ensure consistent behavior and interfaces.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

# Configure logger for this module
logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class that defines the contract for all AI agents.

    This class serves as the foundation for all agents in the system, providing:
    - Common initialization patterns
    - Memory management through conversation history
    - Abstract methods that all agents must implement
    - Consistent logging and error handling patterns

    Think of this as the "DNA" that all agents share, ensuring they can work
    together seamlessly in the multi-agent system.
    """

    def __init__(self, name: str, model_config: Dict[str, Any]):
        """Initialize the base agent with essential components.

        Args:
            name: Unique identifier for this agent (e.g., "ArbitratorAgent")
            model_config: Configuration for the AI model (temperature, max_tokens, etc.)
        """
        # Agent identity - used for logging, debugging, and routing
        self.name = name

        # AI model configuration (temperature, max_tokens, model_name, etc.)
        # This allows each agent to have different "personalities" and behaviors
        self.model_config = model_config

        # Timestamp when this agent instance was created
        # Useful for monitoring agent lifecycle and performance
        self.created_at = datetime.utcnow()

        # Memory system - stores conversation history for context
        # This allows agents to:
        # - Remember previous interactions
        # - Build on previous responses
        # - Maintain conversation flow
        # - Learn from past decisions
        self.conversation_history: List[Dict[str, Any]] = []

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing method that defines what the agent does.

        This is the "brain" of the agent - where all the intelligence happens.
        Every agent must implement this method to define their specific behavior.

        Args:
            input_data: Dictionary containing the request data and context
                       (e.g., dispute details, contract IDs, user queries)

        Returns:
            Dictionary containing the agent's response, analysis, and metadata

        Note:
            This method is async to support:
            - Non-blocking I/O operations (API calls, database queries)
            - Concurrent processing of multiple requests
            - Integration with async web frameworks like FastAPI
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Define the agent's personality, expertise, and behavior.

        This prompt is sent to the AI model to establish:
        - The agent's role and expertise
        - How it should behave and respond
        - What knowledge and capabilities it has
        - The tone and style of responses

        Think of this as the agent's "job description" that tells the AI
        what kind of expert it should be.

        Returns:
            String containing the system prompt that defines this agent's behavior
        """
        pass

    def add_to_history(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the agent's conversation history.

        This method implements the agent's memory system, allowing it to:
        - Remember previous questions and answers
        - Build context for follow-up questions
        - Learn from past interactions
        - Maintain conversation continuity

        Args:
            role: Who sent the message ("user" or "assistant")
            content: The actual message content
            metadata: Additional context (request IDs, timestamps, etc.)
        """
        # Create a structured memory entry
        history_entry = {
            "role": role,  # Who said it
            "content": content,  # What was said
            "timestamp": datetime.utcnow().isoformat(),  # When it was said
            "metadata": metadata or {}  # Additional context
        }

        # Add to the agent's memory
        self.conversation_history.append(history_entry)

        # Log the memory addition for debugging
        logger.debug(
            f"Added to {self.name} history: {role} message "
            f"({len(content)} chars) at {history_entry['timestamp']}"
        )

    def clear_history(self):
        """Clear the agent's conversation history.

        This is useful for:
        - Starting fresh conversations
        - Managing memory usage
        - Privacy compliance (removing old data)
        - Testing and debugging
        """
        # Store count for logging
        cleared_count = len(self.conversation_history)

        # Clear the memory
        self.conversation_history.clear()

        # Log the action for monitoring
        logger.info(
            f"Cleared conversation history for agent: {self.name} "
            f"(removed {cleared_count} messages)"
        )

    def get_history_summary(self) -> Dict[str, Any]:
        """Get a summary of the agent's conversation history.

        Returns:
            Dictionary containing history statistics and metadata
        """
        if not self.conversation_history:
            return {
                "total_messages": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "first_interaction": None,
                "last_interaction": None
            }

        # Count messages by role
        user_count = sum(1 for msg in self.conversation_history if msg["role"] == "user")
        assistant_count = sum(1 for msg in self.conversation_history if msg["role"] == "assistant")

        return {
            "total_messages": len(self.conversation_history),
            "user_messages": user_count,
            "assistant_messages": assistant_count,
            "first_interaction": self.conversation_history[0]["timestamp"],
            "last_interaction": self.conversation_history[-1]["timestamp"],
            "agent_name": self.name,
            "agent_created": self.created_at.isoformat()
        }
