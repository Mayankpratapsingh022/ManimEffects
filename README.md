# Manim Effects

A modern animation editor built with Manim, Electron, and shadcn/ui. Create beautiful mathematical animations using natural language and a visual timeline editor.

## Features

- 🎨 Modern UI with shadcn/ui components
- 📝 Natural language animation generation
- ⏱️ Visual timeline editor with layers
- 🎬 Real-time preview
- 📜 Manim script editor
- 🎯 Drag-and-drop timeline items
- 🎥 Export animations in various formats

## Prerequisites

- Node.js 18+ and npm/pnpm
- Python 3.8+
- Manim dependencies (see [Manim installation guide](https://docs.manim.community/en/stable/installation.html))

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/manim-effects.git
cd manim-effects
```

2. Install frontend dependencies:
```bash
cd frontend
pnpm install
```

3. Install backend dependencies:
```bash
cd ../backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Development

1. Start the backend server:
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python run.py
```

2. Start the frontend development server:
```bash
cd frontend
pnpm dev
```

## Building

1. Build the frontend:
```bash
cd frontend
pnpm build
```

2. Build the Electron app:
```bash
pnpm electron:build
```

## Usage

1. Open the application
2. Use the chat interface to describe the animation you want to create
3. Edit the generated Manim script if needed
4. Use the timeline to arrange and layer your animations
5. Preview your animation in real-time
6. Export your final animation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 