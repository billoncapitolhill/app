import os
import json
import logging
from typing import Dict
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class AIService:
    """Service for generating AI summaries and analysis."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            logger.error("OpenAI API key is required")
            raise ValueError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        logger.info("Successfully initialized OpenAI client")

        self.system_prompt = """You are Milton Friedman, the renowned economist and champion of free markets and individual liberty. 
        Analyze this legislative text from your perspective, focusing on:
        1. The potential impact on economic freedom and market efficiency
        2. Any expansion of government power or bureaucracy
        3. The fiscal implications and potential waste of taxpayer money
        4. Effects on individual liberty and property rights
        
        Maintain your characteristic skepticism of government intervention while providing clear, data-driven analysis."""

    async def generate_bill_summary(self, bill_data: Dict) -> Dict:
        """Generate an AI summary and analysis for a bill."""
        try:
            # Prepare the prompt
            prompt = f"""Analyze the following bill and provide a comprehensive summary and analysis:

Title: {bill_data.get('title', 'N/A')}
Description: {bill_data.get('summary', 'N/A')}
Latest Action: {bill_data.get('latestAction', {}).get('text', 'N/A')}

Please provide a detailed analysis from Milton Friedman's perspective, focusing on free market principles and limited government. Format your response as JSON with the following structure:
{{
    "summary": "A concise 2-3 sentence summary of the bill's main points",
    "perspective": "Milton Friedman's free market perspective",
    "key_points": ["key point 1", "key point 2", ...],
    "estimated_cost_impact": "Detailed analysis of fiscal impact on taxpayers and federal budget",
    "government_growth_analysis": "Analysis of how this bill might expand or contract government power and bureaucracy",
    "market_impact_analysis": "Analysis of effects on market efficiency, competition, and economic freedom",
    "liberty_impact_analysis": "Analysis of implications for individual liberty and property rights"
}}"""

            # Generate the summary using GPT-4
            response = await self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            # Parse the response
            if not response.choices:
                raise Exception("No response from OpenAI")
            
            summary = response.choices[0].message.content
            if not summary:
                raise Exception("Empty response from OpenAI")
            
            try:
                summary_dict = json.loads(summary)
                logger.info("Successfully generated AI summary for bill %s", bill_data.get("title"))
                return summary_dict
            except json.JSONDecodeError as e:
                logger.error("Failed to parse OpenAI response: %s", str(e))
                raise
            
        except Exception as e:
            logger.error("Error generating bill summary: %s", str(e))
            raise 