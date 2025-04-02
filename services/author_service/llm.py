"""Contains helper functions to abstract away the llm"""

import requests
import json
import re
from pydantic import BaseModel, Field

# Make shared files accessible
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(PROJECT_ROOT)
from shared.keys import PERPLEXITY_AI_KEY

API_ENDPOINT = "https://api.perplexity.ai/chat/completions"
SYSTEM_PROMPT = """
You are a professional author that writes articles on businesses. The purpose of the article is to convince readers that the business is a good place to host a meetup with friends or family.

Respond in JSON format with the following structure:
{
  'slug': 'filename for',
  'title': '',
  "seo_meta": '',
  'general_summary': '',
  'reviews_summary': '',
  'detailed_info': ''
}

Below is a description of what each json field contain:
slug: filename of the article. use hyphens not spaces
title: Short description of the business that will entice users to visit the page
seo_meta: Short description of the business that will entice users to visit the page
general_summary: minimum 200 words. Describe what makes this business a great place to meet up with friends. Include a few highlights about the place
reviews_summary: minimum 200 words. Summarize what users from reviews thought, in another paragraph talk about what positive reviews mentioned, and a paragraph summarizing the negative reviews. Then a short conclusion on the reviews
detailed_info: Write at least 1000 words. Ensure the response is a minimum of 1000 words, and do not stop before reaching that length. Start this section with with a paragraph (200 words) that answers the question "Why rally at this place with your friends?" Then, list out in detail what activities there are and why the place is perfect for a group meetup. Make each paragraph at least five sentences (150 words) and make section headers questions that closely match queries users might actually type. This field should be written in markdown
""".strip()
USER_PROMPT = "Write an article on the following business:\n"


class AnswerFormat(BaseModel):
    slug: str = Field(description="filename of the article. use hyphens not spaces")
    title: str = Field(description="Descriptive title that captivates readers to read further")
    general_summary: str = Field(description="minimum 200 words. Describe what makes this business a great place to meet up with friends. Include a few highlights about the place")
    reviews_summary: str = Field(description="minimum 200 words. Summarize what users from reviews thought, in another paragraph talk about what positive reviews mentioned, and a paragraph summarizing the negative reviews. Then a short conclusion")
    seo_meta: str = Field(description="Short description of the business to entice users to visit the page")
    detailed_info: str = Field(description="Write at least 1000 words. Ensure the response is a minimum of 1000 words, and do not stop before reaching that length. Start this section with with a paragraph (200 words) that answers the question Why rally at this place with your friends? Then, list out in detail what activities there are and why the place is perfect for a group meetup. Make each paragraph at least five sentences (150 words) and make section headers questions that closely match queries users might actually type. This section should be written in markdown")


def generate_article_content(name: str, rating: float, review_count: int, summary:str=None,address:str=None, website:str=None) -> dict:
    """
    Send a prompt to Perplexity API and parse the response.
        
    Returns:
        dict: JSON response with keys 'slug', 'seo_meta', 'title', 'summary', 'reviews_summary', 'detailed_info', and 'sources'.
    """
    business_data = f"""Name: {name}{"\nAddress: " + address if address!=None else ""}
Rating: {rating} ({review_count} reviews){"\nWebsite: " + website if website!=None else ""}{"\nSummary: " + summary if summary!=None else ""}"""
    
    user_prompt = (USER_PROMPT + business_data).strip()

    headers = {"Authorization": f"Bearer {PERPLEXITY_AI_KEY}"}
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"schema": AnswerFormat.model_json_schema()},
        },
        "max_tokens": 3000,
        "strip_whitespace": True
    }

    try:
        response = requests.post(API_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        citations = result.get("citations", [])
        
        if "choices" in result and result["choices"] and "message" in result["choices"][0]:
            content = result["choices"][0]["message"]["content"]
            try:
                parsed = AnswerFormat.model_validate_json(content).model_dump()
                if citations and 'sources' not in parsed:
                    parsed['sources'] = citations
                return parsed
            except KeyError as e:
                return {"error": f"Failed to parse structured output: {str(e)}", "raw_response": content, "sources": citations}
            
        return {"error": "Unexpected API response format", "raw_response": result}
            
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Failed to parse API response as JSON"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
