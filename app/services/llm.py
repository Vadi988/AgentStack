from typing import Any, Dict, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from openai import APIError, APITimeoutError, OpenAIError, RateLimitError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


from app.core.config import settings
from app.core.config.logging import get_logger
logger = get_logger(__name__)

# ==================================================
# LLM Registry
# ==================================================
class LLMRegistry:
    """
    Registry of available LLM models.
    This allows us to switch "Brains" on the fly without changing code.
    """
    
    # We pre-configure models with different capabilities/costs
    LLMS: List[Dict[str, Any]] = [
        {
            "name": "gpt-5-mini", # Hypothetical or specific model alias
            "llm": ChatOpenAI(
                model="gpt-5-mini",
                api_key=settings.OPENAI_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                # New "reasoning" feature in newer models
                reasoning={"effort": "low"}, 
            ),
        },
        {
            "name": "gpt-4o",
            "llm": ChatOpenAI(
                model="gpt-4o",
                temperature=settings.DEFAULT_LLM_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY,
                max_tokens=settings.MAX_TOKENS,
            ),
        },
        {
            "name": "gpt-4o-mini", # Cheaper fallback
            "llm": ChatOpenAI(
                model="gpt-4o-mini",
                temperature=settings.DEFAULT_LLM_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY,
            ),
        },
    ]

    # --------------------------------------------------
    # Get a specific model instance by name
    # --------------------------------------------------
    @classmethod
    def get(cls, model_name: str) -> BaseChatModel:
        """Retrieve a specific model instance by name."""
        for entry in cls.LLMS:
            if entry["name"] == model_name:
                return entry["llm"]
        # Default to first if not found
        return cls.LLMS[0]["llm"]

    # --------------------------------------------------
    # Get all model names
    # --------------------------------------------------
    @classmethod
    def get_all_names(cls) -> List[str]:
        return [entry["name"] for entry in cls.LLMS]


# ==================================================
# LLM Service (The Resilience Layer)
# ==================================================

class LLMService:
    """
    Manages LLM calls with automatic retries and fallback logic.
    """

    def __init__(self):
        self._llm: Optional[BaseChatModel] = None
        self._current_model_index: int = 0
        
        # Initialize with the default model from settings
        try:
            self._llm = LLMRegistry.get(settings.DEFAULT_LLM_MODEL)
            all_names = LLMRegistry.get_all_names()
            self._current_model_index = all_names.index(settings.DEFAULT_LLM_MODEL)
        except ValueError:
            # Fallback safety
            self._llm = LLMRegistry.LLMS[0]["llm"]

    def _switch_to_next_model(self) -> bool:
        """
        Circular Fallback: Switches to the next available model in the registry.
        Returns True if successful.
        """
        try:
            next_index = (self._current_model_index + 1) % len(LLMRegistry.LLMS)
            next_model_entry = LLMRegistry.LLMS[next_index]
            
            logger.warning(
                "switching_model_fallback", 
                old_index=self._current_model_index, 
                new_model=next_model_entry["name"]
            )
            self._current_model_index = next_index
            self._llm = next_model_entry["llm"]
            return True
        except Exception as e:
            logger.error("model_switch_failed", error=str(e))
            return False

    # --------------------------------------------------
    # The Retry Decorator
    # --------------------------------------------------
    # This is the magic. If the function raises specific exceptions,
    # Tenacity will wait (exponentially) and try again.
    @retry(
        stop=stop_after_attempt(settings.MAX_LLM_CALL_RETRIES), # Stop after 3 tries
        wait=wait_exponential(multiplier=1, min=2, max=10),     # Wait 2s, 4s, 8s...
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIError)),
        before_sleep=before_sleep_log(logger, "WARNING"),       # Log before waiting
        reraise=True,
    )

    async def _call_with_retry(self, messages: List[BaseMessage]) -> BaseMessage:
        """Internal method that executes the actual API call."""
        if not self._llm:
            raise RuntimeError("LLM not initialized")
        return await self._llm.ainvoke(messages)

    async def call(self, messages: List[BaseMessage]) -> BaseMessage:
        """
        Public interface. Wraps the retry logic with a Fallback loop.
        If 'gpt-4o' fails 3 times, we switch to 'gpt-4o-mini' and try again.
        """
        total_models = len(LLMRegistry.LLMS)
        models_tried = 0
        
        while models_tried < total_models:
            try:
                # Attempt to generate response
                return await self._call_with_retry(messages)
            
            except OpenAIError as e:
                # If we exhausted retries for THIS model, log and switch
                models_tried += 1
                logger.error(
                    "model_failed_exhausted_retries", 
                    model=LLMRegistry.LLMS[self._current_model_index]["name"],
                    error=str(e)
                )
                
                if models_tried >= total_models:
                    # We tried everything. The world is probably ending.
                    break
                
                self._switch_to_next_model()
        raise RuntimeError("Failed to get response from any LLM after exhausting all options.")

    def get_llm(self) -> BaseChatModel:
        return self._llm
    

    def bind_tools(self, tools: List) -> "LLMService":
        """Bind tools to the current LLM instance."""
        if self._llm:
            self._llm = self._llm.bind_tools(tools)
        return self


# Create global instance
llm_service = LLMService()  