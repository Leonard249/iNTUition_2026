from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import base64
import asyncio
import httpx
import uuid
from typing import Optional
from PIL import Image
import io

# Import settings
try:
    from config import settings
except ImportError:
    # Default settings
    class Settings:
        OLLAMA_BASE_URL = "http://localhost:11434"
        OLLAMA_MODEL = "qwen2.5vl:7b"
        HOST = "0.0.0.0"
        PORT = 8000
        CORS_ORIGINS = ["*"]
    
    settings = Settings()

app = FastAPI(title="A11y Overlay API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = {}
client = httpx.AsyncClient(timeout=30.0)

# ========== HELPER FUNCTIONS ==========

async def image_to_base64(image_file: UploadFile) -> str:
    """Convert uploaded image to base64 for Ollama"""
    # Read image file
    contents = await image_file.read()
    
    # Open with PIL to validate and optionally resize
    image = Image.open(io.BytesIO(contents))
    
    # Convert to RGB if needed
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Resize if too large (Ollama works better with smaller images)
    max_size = 1024
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = tuple(int(dim * ratio) for dim in image.size)
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    # Convert to base64
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return img_str

async def analyze_with_ollama(image_base64: str, dom_elements: list) -> dict:
    """Send to Ollama for analysis"""
    messages = [
        {
            "role": "user",
            "content": f"""
            Analyze this webpage screenshot and suggest top 3 user actions.
            
            Interactive elements: {json.dumps(dom_elements[:10], indent=2)}
            
            Return JSON:
            {{
                "page_type": "ecommerce|form|dashboard|etc",
                "page_summary": "brief description",
                "actions": [
                    {{
                        "id": "action_1",
                        "label": "Clear action label",
                        "description": "What this does",
                        "element_index": 0,
                        "confidence": 0.95
                    }}
                ]
            }}
            """,
            "images": [image_base64]
        }
    ]
    
    try:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.3}
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result["message"]["content"]
            
            try:
                return json.loads(content)
            except:
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except:
                        pass
        
        # Fallback
        return create_fallback_analysis(dom_elements)
        
    except Exception as e:
        print(f"Ollama error: {e}")
        return create_fallback_analysis(dom_elements)

def create_fallback_analysis(dom_elements: list) -> dict:
    """Fallback when Ollama fails"""
    actions = []
    for i, elem in enumerate(dom_elements[:3]):
        actions.append({
            "id": f"action_{i}",
            "label": elem.get('text', f"Action {i}"),
            "description": f"Click {elem.get('tag', 'element')}",
            "element_index": i,
            "confidence": 0.7
        })
    
    return {
        "page_type": "generic",
        "page_summary": "Fallback analysis",
        "actions": actions
    }

# ========== ENDPOINTS ==========

@app.get("/")
async def root():
    return {"message": "A11y Overlay API"}

@app.get("/health")
async def health_check():
    """Check backend and Ollama"""
    try:
        response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
        ollama_ok = response.status_code == 200
    except:
        ollama_ok = False
    
    return {
        "status": "healthy" if ollama_ok else "degraded",
        "ollama_connected": ollama_ok,
        "ollama_model": settings.OLLAMA_MODEL
    }

# ========== MAIN ENDPOINT WITH FILE UPLOAD ==========

@app.post("/api/analyze-page")
async def analyze_page(
    screenshot: UploadFile = File(...),      # ← CHANGED: Now a FILE upload!
    dom_elements: str = Form(...),
    session_id: Optional[str] = Form(None)
):
    """
    Analyze webpage - UPLOAD IMAGE FILE directly!
    
    Parameters:
    - screenshot: Image file (PNG, JPG, etc.)
    - dom_elements: JSON string of interactive elements
    - session_id: Optional session ID
    """
    try:
        # Validate image file
        if not screenshot.content_type.startswith('image/'):
            raise HTTPException(400, "File must be an image")
        
        print(f"Received image: {screenshot.filename}, size: {screenshot.size}")
        
        # Generate session ID if needed
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Parse DOM elements
        try:
            elements = json.loads(dom_elements)
        except json.JSONDecodeError:
            # Try to fix JSON
            dom_elements = dom_elements.replace("'", '"')
            elements = json.loads(dom_elements)
        
        # Convert image to base64 for Ollama
        print("Converting image to base64...")
        image_base64 = await image_to_base64(screenshot)
        
        print(f"Image converted, size: {len(image_base64)} chars")
        print(f"Calling Ollama with {len(elements)} DOM elements...")
        
        # Call Ollama
        analysis = await analyze_with_ollama(image_base64, elements)
        
        # Store session
        sessions[session_id] = {
            "page_analysis": analysis,
            "dom_elements": elements,
            "image_filename": screenshot.filename
        }
        
        return {
            "session_id": session_id,
            "analysis": analysis,
            "image_info": {
                "filename": screenshot.filename,
                "content_type": screenshot.content_type,
                "size_bytes": screenshot.size
            },
            "elements_count": len(elements),
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(500, detail=str(e))

# ========== ALTERNATIVE: Base64 version (for compatibility) ==========

@app.post("/api/analyze-page-base64")
async def analyze_page_base64(
    screenshot: str = Form(...),  # Base64 string
    dom_elements: str = Form(...),
    session_id: Optional[str] = Form(None)
):
    """Alternative endpoint for base64 strings"""
    try:
        if not session_id:
            session_id = str(uuid.uuid4())
        
        elements = json.loads(dom_elements)
        
        # Clean base64 if it has data URL prefix
        if screenshot.startswith('data:image'):
            screenshot = screenshot.split(',')[1]
        
        analysis = await analyze_with_ollama(screenshot, elements)
        
        sessions[session_id] = {
            "page_analysis": analysis,
            "dom_elements": elements
        }
        
        return {
            "session_id": session_id,
            "analysis": analysis,
            "elements_count": len(elements)
        }
        
    except Exception as e:
        raise HTTPException(500, detail=str(e))

# ========== OTHER ENDPOINTS (unchanged) ==========

@app.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe audio file"""
    contents = await audio.read()
    
    return {
        "text": "search for products",  # Mock
        "language": "en",
        "file_info": {
            "filename": audio.filename,
            "size_bytes": len(contents),
            "content_type": audio.content_type
        }
    }

@app.post("/api/interpret-command")
async def interpret_command(
    command: str = Form(...),
    session_id: str = Form(...)
):
    """Interpret user command"""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    
    session = sessions[session_id]
    actions = session["page_analysis"]["actions"]
    
    # Simple keyword matching
    command_lower = command.lower()
    best_match = None
    best_score = 0
    
    for action in actions:
        label = action["label"].lower()
        score = sum(1 for word in command_lower.split() if word in label)
        if score > best_score:
            best_score = score
            best_match = action
    
    if best_match and best_score > 0:
        return {
            "selected_action_id": best_match["id"],
            "confidence": min(0.5 + (best_score * 0.1), 0.9),
            "clarification_needed": False,
            "action_details": best_match
        }
    
    return {
        "selected_action_id": None,
        "confidence": 0.0,
        "clarification_needed": True,
        "clarification_question": "What would you like to do?"
    }

@app.get("/api/test-image")
async def get_test_image():
    """Return a test image file for Postman testing"""
    # Create a simple test image
    from PIL import Image, ImageDraw
    
    # Create 400x300 test image with a button
    img = Image.new('RGB', (400, 300), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw a "button"
    draw.rectangle([50, 50, 150, 100], fill='blue', outline='black')
    draw.text((70, 70), "SEARCH", fill='white')
    
    # Draw an "input field"
    draw.rectangle([50, 120, 350, 150], fill='lightgray', outline='black')
    draw.text((60, 125), "Type here...", fill='darkgray')
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return {
        "message": "Use this test image in Postman",
        "download_url": "/api/download-test-image",
        "image_description": "400x300 test image with a button and input field"
    }

@app.get("/api/download-test-image")
async def download_test_image():
    """Download the test image file"""
    from PIL import Image, ImageDraw
    
    img = Image.new('RGB', (400, 300), color='white')
    draw = ImageDraw.Draw(img)
    
    draw.rectangle([50, 50, 150, 100], fill='blue', outline='black')
    draw.text((70, 70), "SEARCH", fill='white')
    draw.rectangle([50, 120, 350, 150], fill='lightgray', outline='black')
    draw.text((60, 125), "Type here...", fill='darkgray')
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        img_bytes,
        media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=test-page.png"}
    )

if __name__ == "__main__":
    print(f"🚀 Starting A11y Overlay API")
    print(f"📁 Upload images to: POST /api/analyze-page")
    print(f"📋 Base64 alternative: POST /api/analyze-page-base64")
    print(f"📚 Docs: http://localhost:{settings.PORT}/docs")
    
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )