import os
from typing import Protocol, List
from pydantic import BaseModel
import google.generativeai as genai
from PIL import Image
import io

class FoodCandidate(BaseModel):
    name: str
    estimated_quantity: str # e.g., "1 bowl", "2 pieces"
    confidence: str # "HIGH", "MEDIUM", "LOW"

class VisionProvider(Protocol):
    """
    Protocol for multimodal AI vision analysis.
    """
    def identify_food(self, image_bytes: bytes) -> List[FoodCandidate]:
        ...

class GeminiVisionProvider:
    """
    Implementation using Gemini Pro Vision (or gemini-1.5-flash/pro).
    """
    def __init__(self, api_key: str = None, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
            
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)

    def identify_food(self, image_bytes: bytes) -> List[FoodCandidate]:
        image = Image.open(io.BytesIO(image_bytes))
        
        prompt = """
        Analyze this image of food. Identify all the distinct food items present.
        For each item, provide:
        1. Name (e.g., "Roti", "Dal", "Salad")
        2. Estimated portion/quantity (e.g., "2 pieces", "1 bowl")
        3. Confidence level (HIGH, MEDIUM, LOW)
        
        Return ONLY valid JSON in this exact structure:
        [
            {"name": "string", "estimated_quantity": "string", "confidence": "string"}
        ]
        Do not include markdown blocks or any other text.
        """
        
        try:
            response = self.model.generate_content(
                [prompt, image],
                generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
            )
            import json
            data = json.loads(response.text)
            return [FoodCandidate(**item) for item in data]
        except Exception as e:
            print(f"Vision API Error: {e}")
            return []

def get_vision_provider() -> VisionProvider:
    return GeminiVisionProvider()
