# Running the Application

Here's how I've set up the application to run both locally and with Docker. The setup is straightforward and requires minimal configuration.

## Local Deployment

Create a virtual environment with conda and install the dependencies:

```bash
conda create -p venv python=3.9
conda activate venv
```

Install the dependencies:

```bash
pip install -r requirements.txt
```



### Running the API and Gradio Interface Separately
From the project root directory:

**Linux/Mac:**
```bash
# Run FastAPI
uvicorn src.api.api:app --host 0.0.0.0 --port 8000

# Run Gradio (in a different terminal)
python src/gradio/app.py
```

**Windows:**
```powershell
# Run FastAPI
uvicorn src.api.api:app --host 0.0.0.0 --port 8000

# Run Gradio (in a different terminal)
python -m src.gradio.app
```

The services will be available at:
- API: `http://localhost:8000`
- Gradio Interface: `http://localhost:7860`

## Docker Deployment

I've containerized both services into a single container for easier deployment:

```bash
# Build the image
docker build -t movie-recommender .

# Run the container
docker run -d -p 8000:8000 -p 7860:7860 movie-recommender
```

That's it! The services will be available at:
- API: `http://localhost:8000`
- Gradio Interface: `http://localhost:7860`

No additional configuration or environment variables are needed - I've set sensible defaults for local development.