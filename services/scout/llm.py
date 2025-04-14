"""Contains helper functions to abstract away the llm"""

import requests
import json
from pydantic import BaseModel, Field

# Make shared files accessible
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(PROJECT_ROOT)
from shared.schema import PlaceData

# Constants
PERPLEXITY_AI_KEY = os.getenv("PERPLEXITY_AI_KEY")
API_ENDPOINT = "https://api.perplexity.ai/chat/completions"
SYSTEM_PROMPT = """
Given a list of places, your job is to filter places that would be bad for group hang outs with friends or family. We want to filter out places like chain restaurants, take-out only restaurants or place no one would go to for a meetup. Only filter out places that with something specific that forces them to be removed. A restaurant with mixed reviews should still be included as people might want to meetup there.

Each business in the provided list will have an index given with it.
Respond in JSON format with the following structure:
{
  'filtered_places': [index_1, index_2, index_3]
}
In the output, only include the indexes of businesses that would be good for group meetups.
""".strip()
USER_PROMPT = "From the following list of businesses, choose the ones suitable for group meetups:\n"


class AnswerFormat(BaseModel):
    filtered_places: list[int] = Field(description="list of places suitable for group meetups")


def filter_places(potential_places: list[PlaceData]) -> list[int]:
    """
    Send a prompt to Perplexity API and parse the response.
        
    Returns:
        list[str]: This list contains the place_ids of the businesses suitable for group meetups
    """
    user_prompt = USER_PROMPT
    for idx, place in enumerate(potential_places):
        user_prompt += f"\nIndex: {idx}\nName: {place.place_name}\nWebsite: {place.business_url}\nRating: {place.rating}\nReviews Count: {place.reviews_count}\n{f"Summary: {place.general_summary}\n" if place.general_summary else ""}"

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
        "max_tokens": 2000,
        "strip_whitespace": True
    }

    try:
        response = requests.post(API_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and result["choices"] and "message" in result["choices"][0]:
            content = result["choices"][0]["message"]["content"]
            try:
                parsed = AnswerFormat.model_validate_json(content).model_dump()
                output = []
                for idx in parsed['filtered_places']:
                    output.append(potential_places[idx].place_id)
                return output
            except KeyError as e:
                return {"error": f"Failed to parse structured output: {str(e)}", "raw_response": content}
            
        return {"error": "Unexpected API response format", "raw_response": result}
            
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Failed to parse API response as JSON"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
