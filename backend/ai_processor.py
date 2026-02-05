import httpx
import json
import base64
from typing import List, Dict, Any
from PIL import Image
import io
from .screenshot_utils import ScreenshotProcessor

class AIProcessor:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url  # Your friend's Ollama server
        self.client = httpx.AsyncClient(timeout=30.0)  # HTTP client for API calls
        self.screenshot_processor = ScreenshotProcessor()
    
    async def analyze_screenshot(self, screenshot_data: str, dom_elements: List[Dict]) -> Dict[str, Any]:
        """
        MAIN FUNCTION: Analyze webpage screenshot + DOM elements
        Input: base64 screenshot + list of interactive elements
        Output: {"page_type": "ecommerce", "actions": [...], "page_summary": "..."}
        """
        
        # 1. Prepare image for Ollama
        image = self.screenshot_processor.decode_base64_screenshot(screenshot_data)
        processed_img = self.screenshot_processor.preprocess_image_for_llm(image)
        
        # 2. Create readable summary of DOM elements
        dom_summary = self._summarize_dom_elements(dom_elements)
        
        # 3. Create prompt for Qwen 2.5 (with vision capabilities)
        vision_prompt = f"""
        You are analyzing a webpage screenshot. 
        
        Here are the interactive elements found on the page:
        {dom_summary}
        
        Based on the VISUAL CONTENT (screenshot) and these elements:
        1. What type of page is this? (e-commerce, login form, article, dashboard, etc.)
        2. What are the 3 most important actions a user would want to do?
        3. For each action, which DOM element should be used? (use the index numbers above)
        
        Return ONLY JSON with this exact structure:
        {{
            "page_type": "string",
            "actions": [
                {{
                    "id": "action_1",
                    "label": "Clear action label",
                    "description": "What this does",
                    "element_index": 0,  // MATCHES INDEX IN DOM SUMMARY
                    "confidence": 0.95,
                    "reasoning": "Why this is important"
                }},
                // ... 2 more actions
            ],
            "page_summary": "Brief summary"
        }}
        """
        
        # 4. Call Ollama Qwen 2.5 with image
        messages = [
            {
                "role": "user",
                "content": vision_prompt,
                "images": [processed_img["image"]]  # Ollama vision format
            }
        ]
        
        response = await self.client.post(
            f"{self.ollama_url}/api/chat",  # Ollama chat endpoint
            json={
                "model": "qwen2.5vl:7b",
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower = more deterministic
                    "num_predict": 1000   # Max tokens to generate
                }
            }
        )
        
        # 5. Parse Ollama's response
        if response.status_code == 200:
            result = response.json()
            content = result["message"]["content"]
            
            try:
                parsed = json.loads(content)  # Try to parse as JSON
                # Add actual element selectors to actions
                parsed = self._enrich_with_element_data(parsed, dom_elements)
                return parsed
            except json.JSONDecodeError:
                # If Ollama doesn't return clean JSON, extract it
                return self._extract_json_from_text(content, dom_elements)
        else:
            # Fallback if Ollama fails
            return await self._fallback_analysis(dom_elements)
    
    async def interpret_user_command(self, user_command: str, page_context: Dict, available_actions: List[Dict]) -> Dict:
        """
        Match user's voice command to available actions
        Input: "search for laptops", page analysis, available actions
        Output: {"selected_action_id": "action_1", "confidence": 0.9, ...}
        """
        
        prompt = f"""
        User said: "{user_command}"
        
        Current Page: {page_context.get('page_type', 'unknown')}
        Page Summary: {page_context.get('page_summary', '')}
        
        Available Actions on this page:
        {json.dumps(available_actions, indent=2)}
        
        Which action does the user want? Return JSON:
        {{
            "selected_action_id": "action_id or null",
            "confidence": 0.0 to 1.0,
            "clarification_needed": true/false,
            "clarification_question": "question if needed",
            "reasoning": "brief explanation"
        }}
        """
        
        # Call Ollama for text-only reasoning
        response = await self.client.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": "qwen2.5vl:7b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2}
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result["response"]
            
            try:
                return json.loads(content)
            except:
                # Simple keyword matching fallback
                return self._keyword_match(user_command, available_actions)
    
    def _summarize_dom_elements(self, elements: List[Dict]) -> str:
        """Format DOM elements for the LLM prompt"""
        summary = []
        for i, elem in enumerate(elements[:20]):  # Limit to 20 elements
            summary.append(f"{i}. {elem.get('tag', '')} - Text: '{elem.get('text', '')}' - Type: {elem.get('type', '')}")
        return "\n".join(summary)
    
    def _enrich_with_element_data(self, analysis: Dict, dom_elements: List[Dict]) -> Dict:
        """Add real CSS selectors and bounds to actions"""
        for action in analysis.get("actions", []):
            idx = action.get("element_index", 0)
            if 0 <= idx < len(dom_elements):
                elem = dom_elements[idx]
                action["selector"] = elem.get("selector", "")  # CSS selector
                action["element_type"] = elem.get("tag", "")
                action["bounds"] = elem.get("bounds", {})  # Screen position
        return analysis
    
    def _extract_json_from_text(self, text: str, dom_elements: List[Dict]) -> Dict:
        """Fallback: try to find JSON in Ollama's text response"""
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # Ultimate fallback: just pick first 3 elements
        return self._create_fallback_analysis(dom_elements)
    
    def _create_fallback_analysis(self, dom_elements: List[Dict]) -> Dict:
        """Create basic analysis when everything else fails"""
        actions = []
        for i, elem in enumerate(dom_elements[:3]):
            actions.append({
                "id": f"fallback_{i}",
                "label": elem.get('text', f"Action {i}")[:50],
                "element_index": i,
                "confidence": 0.7 - (i * 0.1)
            })
        
        return {
            "page_type": "generic",
            "actions": actions,
            "page_summary": "Fallback analysis"
        }
    
    def _keyword_match(self, command: str, actions: List[Dict]) -> Dict:
        """Simple word matching if Ollama fails"""
        command_lower = command.lower()
        best_match = None
        best_score = 0
        
        for action in actions:
            label = action.get("label", "").lower()
            # Count overlapping words
            score = len(set(command_lower.split()) & set(label.split()))
            if score > best_score:
                best_score = score
                best_match = action
        
        if best_match and best_score > 0:
            return {
                "selected_action_id": best_match["id"],
                "confidence": min(0.3 + (best_score * 0.2), 0.9),
                "clarification_needed": False,
                "reasoning": f"Keyword match: {best_score} words"
            }
        
        return {
            "selected_action_id": None,
            "confidence": 0.0,
            "clarification_needed": True,
            "clarification_question": "I'm not sure what you want. Could you be more specific?"
        }