"""
LLM utilities for processing documents with AI models.

Supports multiple LLM providers with a unified interface.
"""

import os
from typing import Optional, Dict, Any
from enum import Enum

import google.generativeai as genai

from config import settings


class LLMProvider(Enum):
    """Supported LLM providers"""
    GEMINI = "gemini"
    # Add more providers as needed
    # OPENAI = "openai"
    # ANTHROPIC = "anthropic"


class LLMTask(Enum):
    """Predefined LLM tasks with system prompts"""
    
    TRANSCRIPT_TO_MARKDOWN = "transcript_to_markdown"
    # Add more tasks as needed
    # EXTRACT_VOTES = "extract_votes"
    # SUMMARIZE_MEETING = "summarize_meeting"


# System prompts for different tasks
SYSTEM_PROMPTS: Dict[LLMTask, str] = {
    LLMTask.TRANSCRIPT_TO_MARKDOWN: """# HTML Transcript to Markdown Converter Prompt

You are converting HTML transcripts verbatim to markdown with timestamps as footnotes.

## Extraction
1. Extract only inner (visible) text content
2. Strip all HTML tags (`<span>`, `<font>`, `<br>`, etc.)
3. Decode entities: `&nbsp;` → space, `&lt;` → `<`, `&gt;` → `>`, `&amp;` → `&`
4. Remove Google Translate widget and script markup

## Timestamps
- Format: `HH:MM:SS` (e.g., `00:15:42`, `01:32:36`)
- Extract from `<span id="HH:MM:SS">` elements
- Map each timestamp to the text that follows it
- Use earliest timestamp for each speaker segment

## Markdown Structure
- Main title: `# Meeting Title`
- Major sections: `## Section Name` (Opening, Elections, Public Comment, etc.)
- Subsections: `### Subsection Name` (Individual speakers, nominees, etc.)
- Use descriptive, natural heading names

## Footnote System
- Place `[^HH-MM-SS]` after each text segment (convert colons to hyphens: `00-15-42`)
- List all footnotes at end in chronological order:
  ```
  [^00-15-42]: 00:15:42
  [^01-32-36]: 01:32:36
  ```

## Content Patterns
- **Speaker indicators**: Lines with `>>` or `Speaker Name:` 
- **Stage directions**: Text in `[brackets]` like `[Applause]`, `[Inaudible]`
- **Prepared remarks**: Keep quotation marks and preserve structure
- **Lists**: Roll calls, votes → simple text format with timestamps
- **Long speeches**: Break into logical paragraphs, use first timestamp only

## Quality Checks
- Timestamps in ascending order
- All speakers clearly identified
- Section headings descriptive
- Footnote references match definitions
- No orphaned timestamps
- Consistent formatting throughout
- The text should be outputted verbatim

## Output Format
```markdown
# [Title]

## [Section]

[Text paragraph][^HH-MM-SS]

### [Subsection]

[More text][^HH-MM-SS]

---

[^HH-MM-SS]: HH:MM:SS
[^HH-MM-SS]: HH:MM:SS
```
"""
}


class LLMClient:
    """
    Unified LLM client supporting multiple providers.
    
    Usage:
        client = LLMClient(provider=LLMProvider.GEMINI)
        result = client.generate(
            task=LLMTask.TRANSCRIPT_TO_MARKDOWN,
            user_prompt="<html>...</html>"
        )
    """
    
    def __init__(
        self,
        provider: LLMProvider = LLMProvider.GEMINI,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize LLM client.
        
        Args:
            provider: LLM provider to use
            api_key: API key (defaults to config)
            model: Model name (defaults to config)
        """
        self.provider = provider
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        
        if not self.api_key:
            raise ValueError(f"API key not configured for {provider.value}")
        
        # Initialize provider-specific client
        if provider == LLMProvider.GEMINI:
            self._init_gemini()
        else:
            raise ValueError(f"Unsupported provider: {provider.value}")
    
    def _init_gemini(self):
        """Initialize Gemini client"""
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model)
    
    def generate(
        self,
        task: LLMTask,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate text using the LLM.
        
        Args:
            task: Predefined task (provides default system prompt)
            user_prompt: User input/content to process
            system_prompt: Override default system prompt for task
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text
        """
        # Get system prompt
        if system_prompt is None:
            system_prompt = SYSTEM_PROMPTS.get(task, "")
        
        # Combine prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
        
        # Generate based on provider
        if self.provider == LLMProvider.GEMINI:
            return self._generate_gemini(full_prompt, **kwargs)
        else:
            raise ValueError(f"Unsupported provider: {self.provider.value}")
    
    def _generate_gemini(self, prompt: str, **kwargs) -> str:
        """
        Generate text using Gemini.
        
        Args:
            prompt: Full prompt (system + user)
            **kwargs: Additional Gemini parameters (temperature, max_tokens, etc.)
            
        Returns:
            Generated text
        """
        generation_config = {
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.95),
            "top_k": kwargs.get("top_k", 40),
            "max_output_tokens": kwargs.get("max_output_tokens", 8192),
        }
        
        response = self.client.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        return response.text


def convert_transcript_to_markdown(html_content: str) -> str:
    """
    Convert HTML transcript to markdown using LLM.
    
    This is a convenience function for the common task of converting
    transcripts to markdown.
    
    Args:
        html_content: HTML content to convert
        
    Returns:
        Markdown formatted text
    """
    client = LLMClient(provider=LLMProvider.GEMINI)
    return client.generate(
        task=LLMTask.TRANSCRIPT_TO_MARKDOWN,
        user_prompt=html_content
    )

