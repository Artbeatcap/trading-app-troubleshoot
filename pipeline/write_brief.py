"""
Two-stage Market Brief writer to reduce input tokens by ~90%.
Stage A: Condense with mini model using compact inputs
Stage B: Optional polish with voice model
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI

from schemas.brief_input import BriefInput
from pipeline.prepare_inputs import prepare_brief_input, minify_brief_input, get_brief_input_stats

logger = logging.getLogger(__name__)

# Environment variables with defaults
MODEL_BRIEF_STAGE_A = os.getenv("MODEL_BRIEF_STAGE_A", "gpt-4o-mini")
MODEL_BRIEF_STAGE_B = os.getenv("MODEL_BRIEF_STAGE_B", "gpt-4o-mini")
MAX_INPUT_TOKENS_SOFT = int(os.getenv("MAX_INPUT_TOKENS_SOFT", "80000"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "1200"))
BRIEF_POLISH = os.getenv("BRIEF_POLISH", "true").lower() == "true"

# System prompts for each stage
STAGE_A_SYSTEM_PROMPT = """You are a professional market strategist creating a concise morning brief for options traders.

TASK: Generate a structured morning brief using ONLY the provided market data. Return plain text markdown, no HTML.

STRUCTURE:
1. **Market Overview** (2-3 sentences on overnight action)
2. **Key Levels** (SPY/QQQ support/resistance)  
3. **Economic Calendar** (today's events)
4. **Stock Movers** (gapping stocks with catalysts)
5. **Trading Plan** (actionable levels and triggers)

RULES:
- Use ONLY data from the input JSON
- Keep each section concise (2-4 sentences)
- Focus on actionable trading levels
- No speculation beyond provided data
- Return markdown only, no HTML/CSS"""

STAGE_A_WEEKLY_SYSTEM_PROMPT = """You are a professional market strategist creating a concise weekly brief for options traders.

TASK: Generate a structured weekly brief using ONLY the provided market data. Return plain text markdown, no HTML.

STRUCTURE:
1. **Weekly Executive Summary** (2-3 sentences on week's performance)
2. **Last Week in Review** (key market moves and catalysts)
3. **Week Ahead** (upcoming data, earnings, events)
4. **Key Levels** (SPY/QQQ support/resistance for the week)
5. **Trading Plan** (weekly outlook and key levels)

RULES:
- Use ONLY data from the input JSON
- Keep each section concise (2-4 sentences)
- Focus on weekly perspective and levels
- No speculation beyond provided data
- Return markdown only, no HTML/CSS"""

STAGE_B_SYSTEM_PROMPT = """You are a precise editor polishing a market brief for professional traders.

TASK: Polish the provided morning brief draft to match the author's voice while preserving all facts and structure.

RULES:
- Preserve every factual detail (tickers, levels, numbers, dates)
- Maintain the exact same structure and sections
- Improve flow and readability
- Match the author's professional, direct tone
- Keep it concise and actionable
- Return markdown only, no HTML/CSS

AUTHOR VOICE: Professional, direct, trader-focused. Clear and actionable without fluff."""


def token_meter(usage: Any, stage: str) -> None:
    """
    Log token usage for a stage and warn if inputs exceed soft limit.
    
    Args:
        usage: OpenAI usage object
        stage: Stage name for logging
    """
    input_tokens = getattr(usage, 'prompt_tokens', 0)
    output_tokens = getattr(usage, 'completion_tokens', 0)
    total_tokens = getattr(usage, 'total_tokens', input_tokens + output_tokens)
    
    logger.info(f"[TOKENS] {stage}: input={input_tokens}, output={output_tokens}, total={total_tokens}")
    
    if input_tokens > MAX_INPUT_TOKENS_SOFT:
        logger.warning(f"[TOKENS] {stage} input tokens ({input_tokens}) exceed soft limit ({MAX_INPUT_TOKENS_SOFT})")


def stage_a_condense(brief_input: BriefInput, api_key: str, is_weekly: bool = False) -> str:
    """
    Stage A: Generate initial brief using compact inputs and mini model.
    
    Args:
        brief_input: Compact BriefInput object
        api_key: OpenAI API key
        
    Returns:
        str: Initial brief markdown
    """
    logger.info("Starting Stage A: Condense with mini model")
    
    client = OpenAI(api_key=api_key)
    mini_json = minify_brief_input(brief_input)
    
    # Log input statistics
    stats = get_brief_input_stats(brief_input)
    logger.info(f"Stage A input: {stats['minified_json_length']} chars, "
                f"{stats['total_symbols']} symbols, {stats['total_arrays']} arrays")
    
    try:
        # Choose appropriate system prompt
        system_prompt = STAGE_A_WEEKLY_SYSTEM_PROMPT if is_weekly else STAGE_A_SYSTEM_PROMPT
        
        response = client.chat.completions.create(
            model=MODEL_BRIEF_STAGE_A,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Market data for {brief_input.date}:\n\n{mini_json}"}
            ],
            max_completion_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.2
        )
        
        # Log token usage
        if hasattr(response, 'usage') and response.usage:
            token_meter(response.usage, "Stage A")
        
        content = response.choices[0].message.content if response and response.choices else ""
        if not content:
            raise ValueError("Stage A returned empty content")
        
        logger.info("Stage A completed successfully")
        return content.strip()
        
    except Exception as e:
        logger.error(f"Stage A failed: {e}")
        raise


def stage_b_polish(draft: str, api_key: str) -> str:
    """
    Stage B: Polish the brief with voice model (optional).
    
    Args:
        draft: Stage A output
        api_key: OpenAI API key
        
    Returns:
        str: Polished brief markdown
    """
    logger.info("Starting Stage B: Polish with voice model")
    
    client = OpenAI(api_key=api_key)
    
    try:
        response = client.chat.completions.create(
            model=MODEL_BRIEF_STAGE_B,
            messages=[
                {"role": "system", "content": STAGE_B_SYSTEM_PROMPT},
                {"role": "user", "content": f"Polish this morning brief draft:\n\n{draft}"}
            ],
            max_completion_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.3
        )
        
        # Log token usage
        if hasattr(response, 'usage') and response.usage:
            token_meter(response.usage, "Stage B")
        
        content = response.choices[0].message.content if response and response.choices else ""
        if not content:
            logger.warning("Stage B returned empty content, using Stage A output")
            return draft
        
        logger.info("Stage B completed successfully")
        return content.strip()
        
    except Exception as e:
        logger.error(f"Stage B failed: {e}")
        logger.warning("Using Stage A output due to Stage B failure")
        return draft


def build_brief(raw_inputs: Dict[str, Any], polish: bool = None, is_weekly: bool = False) -> str:
    """
    Main function to build Market Brief using two-stage pipeline.
    
    Args:
        raw_inputs: Raw market data dict from AV/Tradier/etc
        polish: Whether to run Stage B polish (defaults to BRIEF_POLISH env var)
        
    Returns:
        str: Final brief markdown (plain text, no HTML)
    """
    if polish is None:
        polish = BRIEF_POLISH
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    logger.info("Building Market Brief with optimized pipeline")
    
    # Prepare compact inputs
    brief_input = prepare_brief_input(raw_inputs)
    
    # Stage A: Condense with mini model
    stage_a_output = stage_a_condense(brief_input, api_key, is_weekly)
    
    # Stage B: Optional polish
    if polish:
        final_output = stage_b_polish(stage_a_output, api_key)
    else:
        final_output = stage_a_output
        logger.info("Stage B polish skipped (BRIEF_POLISH=false)")
    
    logger.info("Market Brief pipeline completed successfully")
    return final_output


def get_pipeline_stats() -> Dict[str, Any]:
    """Get current pipeline configuration for logging."""
    return {
        "model_stage_a": MODEL_BRIEF_STAGE_A,
        "model_stage_b": MODEL_BRIEF_STAGE_B,
        "max_input_tokens_soft": MAX_INPUT_TOKENS_SOFT,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "brief_polish": BRIEF_POLISH
    }
