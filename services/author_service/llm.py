"""Contains helper functions to abstract away the llm"""

import requests
import json
import re

# Make shared files accessible
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(PROJECT_ROOT)
from shared.keys import PERPLEXITY_AI_KEY

API_ENDPOINT = "https://api.perplexity.ai/chat/completions"
ARTICLE_PROMPT = """
You are author that wrotes articles on businesses. The purpose of the article is to convince readers that the business is a good place to host a meetup with friends or family. Start by performing a search to pull information on the business. I will also provide information you can pull from about the business. Generate the following fields and provide only valid JSON output.
The JSON object must have exactly six keys: "Slug", "SEOMetaDescription", "Title", "Summary", "ReviewsSummary", and "DetailedInfo".
For example:
{
  "Slug": "filename of the article. use hyphens not spaces",
  "SEOMetaDescription": "Short description of the business that will entice users to visit the page",
  "Title": "Descriptive title that captivates readers to read further",
  "Summary": "minimum 200 words. Describe what makes this business a great place to meet up with friends. Include a few highlights about the place",
  "ReviewsSummary": "minimum 200 words. Summarize what users from reviews thought, in another paragraph talk about what positive reviews mentioned, and a paragraph summarizing the negative reviews. Then a short conclusion on the reviews",
  "DetailedInfo": "Write at least 1000 words. Ensure the response is a minimum of 1000 words, and do not stop before reaching that length. Start this section with with a paragraph (200 words) that answers the question "Why rally at this place with your friends?" Then, list out in detail what activities there are and why the place is perfect for a group meetup. Make each paragraph at least five sentences (150 words) and make section headers questions that closely match queries users might actually type. This section should be written in markdown"
}
Here is the business data:
"""

def generate_article_content(name: str, rating: float, review_count: int, summary:str=None,address:str=None, website:str=None) -> dict:
    """
    Send a prompt to Perplexity API and parse the response.
        
    Returns:
        dict: JSON response with keys 'Slug', 'SEOMetaDescription', 'Title', 'Summary', 'ReviewsSummary', 'DetailedInfo', and 'Sources'.
    """
    business_data = f"""Name: {name}{"\nAddress: " + address if address!=None else ""}
Rating: {rating} ({review_count} reviews){"\nWebsite: " + website if website!=None else ""}
"""
    prompt = (ARTICLE_PROMPT + business_data).strip()

    payload = {
        "model": "sonar",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 3000
    }

    try:
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_AI_KEY}",
            "Content-Type": "application/json"
        }
        response = requests.post(API_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        
        if result.get("choices") and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            return fix_multiline_json(content)
        else:
            print("No answer provided in the response.")
            return None

    except Exception as e:
        print(f"Error: {e}")
        return None


def fix_multiline_json(llm_output: str) -> None:
    """
    Fixes invalid JSON with unescaped newlines inside string values.
    - Ensures newlines inside strings are properly escaped.
    - Removes any extra text before/after JSON.
    """
    try:
        # Strip markdown formatting
        cleaned_json = strip_json_formatting(llm_output)

        # Fix multi-line strings by escaping unescaped newlines
        def escape_newlines(match):
            return match.group(0).replace("\n", "\\n")

        cleaned_json = re.sub(r'".*?"', escape_newlines, cleaned_json, flags=re.DOTALL)

        # Parse JSON safely
        parsed_data = json.loads(cleaned_json)
        return parsed_data

    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
        return None


def strip_json_formatting(llm_output: str):
    """
    Strips ```json ... ``` formatting from LLM output if present.
    """
    # Match and remove markdown-style JSON block
    json_match = re.search(r'```json\s*(.*?)\s*```', llm_output, re.DOTALL)
    return json_match.group(1) if json_match else llm_output  # Return stripped JSON or original if no match

print(fix_multiline_json(OUTPUT)["DetailedInfo"])