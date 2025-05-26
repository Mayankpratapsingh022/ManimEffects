from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
from typing import Optional, List, Dict, Any
import subprocess
import tempfile
import json
from pathlib import Path
from dotenv import load_dotenv
import re
from fastapi.responses import FileResponse

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

class ApiKeyRequest(BaseModel):
    api_key: str

class AnimationRequest(BaseModel):
    code: str
    quality: str = "medium"  # low, medium, high
    format: str = "mp4"  # mp4, gif

class AnimationResponse(BaseModel):
    output_path: str
    duration: float

class CodeGenerationRequest(BaseModel):
    prompt: str
    api_key: Optional[str] = None

class CodeGenerationResponse(BaseModel):
    code: str
    metadata: List[Dict[str, Any]]

class UpdateCodeRequest(BaseModel):
    code: str
    properties: dict
    history: Optional[list] = None

async def validate_api_key(api_key: str) -> bool:
    try:
        client = openai.AsyncOpenAI(api_key=api_key)
        # Make a simple API call to validate the key
        await client.models.list()
        return True
    except Exception:
        return False

@app.post("/api/validate-key")
async def validate_key(request: ApiKeyRequest):
    api_key = request.api_key or os.getenv("OPENAI_API_KEY")
    try:
        client = openai.AsyncOpenAI(api_key=api_key)
        await client.models.list()
        return {"status": "valid"}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.post("/api/generate-code")
async def generate_code(request: CodeGenerationRequest):
    print("Received /api/generate-code request:", request.dict())
    api_key = request.api_key or os.getenv("OPENAI_API_KEY")
    client = openai.AsyncOpenAI(api_key=api_key)
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a Manim code generator. Generate Manim code based on the user's description.\n"
                        "\n"
                        "- Always return your response in two blocks:\n"
                        "  1. A Python code block (```python) with the Manim code.\n"
                        "     - Always start with 'from manim import *' to import everything from manim.\n"
                        "     - For any property that should be editable (like font size, color, position, etc.), define a variable at the top (e.g., font_size = 48) make sure to always add position,scaling, rotation and opacity to each manim item, and use it in the code (e.g., font_size=font_size).\n"
                        "     - Use f-strings only for string properties that should be editable.\n"
                        "     - Always import all constants, classes, and animations you use, including color constants (e.g., BLUE, RED), animation classes (e.g., Create, Write), and any other required objects from manim.\n"
                        "  2. A JSON code block (```json) with the metadata for each animation component, including all properties and their types, values, and constraints.\n"
                        "     - The JSON should match this format:\n"
                        "       [\n"
                        "         {\n"
                        "           'id': 'unique_id',\n"
                        "           'type': 'text|shape|transform',\n"
                        "           'start': start_time,\n"
                        "           'duration': duration,\n"
                        "           'properties': {\n"
                        "             'property_name': {\n"
                        "               'position': 'x,y,z',\n"
                        "               'scaling': 'x,y,z',\n"
                        "               'rotation': 'x,y,z',\n"
                        "               'opacity': '0.0-1.0',\n"
                        "               'color': 'color_name',\n"
                        "               'type': 'number|string|color|boolean|position',\n"
                        "               'value': value,\n"
                        "               'min': min_value,  # optional\n"
                        "               'max': max_value,  # optional\n"
                        "               'step': step_value  # optional\n"
                        "               'options': ['option1', 'option2']  # optional\n"
                        "               'multiline': True  # optional\n"
                        "               'label': 'Label'  # optional\n"
                        "             }\n"
                        "           }\n"
                        "         }\n"
                        "       ]\n"
                        "- Always return both the code and the JSON metadata."
                    )
                },
                {
                    "role": "user",
                    "content": request.prompt
                }
            ],
            temperature=0.7,
        )
        content = response.choices[0].message.content
        code_start = content.find("```python")
        code_end = content.find("```", code_start + 8)
        if code_start == -1 or code_end == -1:
            raise HTTPException(status_code=500, detail="Failed to extract code from response")
        code = content[code_start + 8:code_end].strip()
        # Remove any leading characters before 'from manim import'
        manim_index = code.find('from manim import')
        if manim_index != -1:
            code = code[manim_index:]
        print("Final code to render:\n", code)
        
        # Extract metadata
        metadata_start = content.find("```json")
        metadata_end = content.find("```", metadata_start + 7)
        
        if metadata_start == -1 or metadata_end == -1:
            metadata = []
        else:
            try:
                metadata = json.loads(content[metadata_start + 7:metadata_end].strip())
            except json.JSONDecodeError:
                metadata = []

        return {
            "code": code,
            "metadata": metadata
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate code: {str(e)}"
        )

@app.post("/api/generate-animation", response_model=AnimationResponse)
async def generate_animation(request: AnimationRequest):
    with tempfile.TemporaryDirectory() as temp_dir:
        code_file = Path(temp_dir) / "animation.py"
        code_file.write_text(request.code)
        quality_settings = {
            "low": "-ql",
            "medium": "-qm",
            "high": "-qh",
            "production": "-qp",
            "4k": "-qk",
        }
        # Extract scene class name
        scene_match = re.search(r'class\s+(\w+)\(Scene\):', request.code)
        scene_name = scene_match.group(1) if scene_match else None
        if not scene_name:
            raise HTTPException(status_code=500, detail="Could not find a Scene class in the code.")
        try:
            cmd = f"manim {quality_settings.get(request.quality, '-qm')} -o animation {code_file} {scene_name}"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=temp_dir
            )

            if result.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"Manim error: {result.stderr}"
                )

            # Find the output file (search recursively)
            output_files = list(Path(temp_dir).rglob(f"animation*.{request.format}"))
            if not output_files:
                # Print directory tree for debugging
                for path in Path(temp_dir).rglob("*"):
                    print(path)
                raise HTTPException(
                    status_code=500,
                    detail="No output file generated"
                )
            output_file = output_files[0]
            
            # Read the scene duration from the JSON file
            json_file = Path(temp_dir) / "animation.json"
            if json_file.exists():
                with open(json_file) as f:
                    scene_data = json.load(f)
                    duration = scene_data.get("duration", 0)
            else:
                duration = 0

            # Move the output file to a permanent location
            output_dir = Path("outputs")
            output_dir.mkdir(exist_ok=True)
            final_path = output_dir / output_file.name
            output_file.rename(final_path)

            return AnimationResponse(
                output_path=str(final_path),
                duration=duration
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Animation generation failed: {str(e)}"
            )

@app.get("/outputs/{filename}")
def get_output_file(filename: str):
    file_path = Path("outputs") / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="video/mp4")

@app.post("/api/update-code")
async def update_code(request: UpdateCodeRequest):
    api_key = os.getenv("OPENAI_API_KEY")
    client = openai.AsyncOpenAI(api_key=api_key)
    prompt = "You are a Manim code editor. Given the following Manim code and a JSON object of updated property values, update the code so that the property values match the JSON. Only change the values, do not change the structure or add new properties.\n\n"
    if request.history:
        prompt += "Here is the previous code history for context:\n"
        for idx, prev_code in enumerate(request.history):
            prompt += f"Previous code version {idx+1}:\n{prev_code}\n\n"
    prompt += f"Manim code:\n{request.code}\n\n"
    prompt += f"Updated properties:\n{json.dumps(request.properties, indent=2)}\n\n"
    prompt += "Return only the updated Manim code."
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt}
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content
        code_start = content.find("```python")
        code_end = content.find("```", code_start + 8)
        if code_start != -1 and code_end != -1:
            code = content[code_start + 8:code_end].strip()
            # Remove any lines before 'from manim import'
            lines = code.splitlines()
            for i, line in enumerate(lines):
                if line.strip().startswith('from manim import'):
                    code = '\n'.join(lines[i:])
                    break
        else:
            code = content.strip()
        return {"code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update code: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 