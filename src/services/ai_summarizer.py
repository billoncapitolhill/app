import os
from typing import Dict, List, Optional

from openai import OpenAI

class AISummarizer:
    """Service for generating AI summaries of bills and amendments."""

    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        
        self.system_prompt = """You are Milton Friedman, the renowned economist and champion of free markets and individual liberty. 
        Analyze this legislative text from your perspective, focusing on:
        1. The potential impact on economic freedom and market efficiency
        2. Any expansion of government power or bureaucracy
        3. The fiscal implications and potential waste of taxpayer money
        4. Effects on individual liberty and property rights
        
        Maintain your characteristic skepticism of government intervention while providing clear, data-driven analysis."""

    def _generate_summary(self, content: str, max_tokens: int = 1000) -> Dict:
        """Generate an AI summary of the content."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Please analyze this legislation:\n\n{content}"}
                ],
                temperature=0.7,
                max_tokens=max_tokens
            )
            
            # Extract the main points from the response
            summary = response.choices[0].message.content
            
            # Generate structured analysis
            analysis_prompt = f"""Based on the previous analysis, provide a structured response with these components:
            1. A concise 2-3 sentence summary
            2. Key points (bullet points)
            3. Estimated cost impact (high/medium/low and explanation)
            4. Government growth analysis
            5. Market impact analysis
            6. Liberty impact analysis"""
            
            structured_response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "assistant", "content": summary},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.7,
                max_tokens=max_tokens
            )
            
            structured_analysis = structured_response.choices[0].message.content
            
            # Parse the structured analysis into components
            sections = structured_analysis.split("\n\n")
            return {
                "summary": sections[0].strip(),
                "key_points": self._extract_key_points(sections[1]),
                "estimated_cost_impact": sections[2].strip(),
                "government_growth_analysis": sections[3].strip(),
                "market_impact_analysis": sections[4].strip(),
                "liberty_impact_analysis": sections[5].strip()
            }
            
        except Exception as e:
            raise Exception(f"Error generating AI summary: {str(e)}")

    def _extract_key_points(self, key_points_section: str) -> List[str]:
        """Extract key points from the bullet point section."""
        points = []
        for line in key_points_section.split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("• "):
                points.append(line[2:].strip())
        return points

    def summarize_bill(self, bill_content: str) -> Dict:
        """Generate an AI summary for a bill."""
        return self._generate_summary(bill_content)

    def summarize_amendment(self, amendment_content: str, original_bill_content: Optional[str] = None) -> Dict:
        """Generate an AI summary for an amendment."""
        if original_bill_content:
            content = f"Original Bill:\n{original_bill_content}\n\nAmendment:\n{amendment_content}"
        else:
            content = amendment_content
        return self._generate_summary(content)