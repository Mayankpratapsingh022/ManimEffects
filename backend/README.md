# Manim Effects Backend

This is the backend server for the Manim Effects application, built with FastAPI and Manim.

## Prerequisites

- Python 3.8 or higher
- FFmpeg (required for Manim)
- LaTeX (required for Manim)

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create an `outputs` directory:
```bash
mkdir outputs
```

## Running the Server

To start the development server:

```bash
python run.py
```

The server will be available at `http://localhost:8000`.

## API Endpoints

### POST /api/validate-key
Validates an OpenAI API key.

Request body:
```json
{
  "api_key": "your-api-key"
}
```

### POST /api/generate-animation
Generates an animation using Manim.

Request body:
```json
{
  "code": "your-manim-code",
  "quality": "low|medium|high",
  "format": "mp4|gif"
}
```

Response:
```json
{
  "output_path": "path/to/generated/animation",
  "duration": 5.0
}
```

## Development

The backend uses FastAPI's hot reload feature, so any changes to the code will automatically restart the server.

## License

MIT 