from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import subprocess
import os
import json
from pathlib import Path
import re
import shutil
import openai
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

class AnimationRequest(BaseModel):
    code: str
    quality: str = "medium"  # low, medium, high
    format: str = "mp4"  # mp4, gif

class AnimationResponse(BaseModel):
    output_path: str
    duration: float
    error: Optional[str] = None

class CodeGenerationRequest(BaseModel):
    prompt: str
    api_key: Optional[str] = None

@app.post("/api/generate-code")
async def generate_code(request: CodeGenerationRequest):
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
                        "Always return your response in a Python code block (```python) with the Manim code."
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
        return {"code": code}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate code: {str(e)}"
        )

@app.post("/api/generate-animation", response_model=AnimationResponse)
async def generate_animation(request: AnimationRequest):
    import tempfile
    print("Received animation request!")
    print("Code received:\n", request.code)
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
        print("Scene name:", scene_name)
        if not scene_name:
            raise HTTPException(status_code=500, detail="Could not find a Scene class in the code.")
        try:
            cmd = f"manim {quality_settings.get(request.quality, '-qm')} -o animation {code_file} {scene_name}"
            print("Running command:", cmd)
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=temp_dir
            )
            print("Manim stdout:", result.stdout)
            print("Manim stderr:", result.stderr)
            print("Manim returncode:", result.returncode)

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
            output_dir = Path("outputs/temp")
            output_dir.mkdir(parents=True, exist_ok=True)
            final_path = output_dir / output_file.name
            shutil.move(str(output_file), str(final_path))
            print("Moved file to:", final_path)
            print("File exists after move?", final_path.exists())

            # Return a relative path for frontend compatibility
            return AnimationResponse(
                output_path=f"outputs/temp/{output_file.name}",
                duration=duration
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Animation generation failed: {str(e)}"
            )

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"} 