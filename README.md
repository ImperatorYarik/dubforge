# video-trans

A FastAPI-based application for video transcription and translation.

## Setup

### Prerequisites
- Python 3.8+
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/ImperatorYarik/video-trans.git
cd video-trans
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

The API will be available at:
- Application: http://localhost:8000
- API Documentation (Swagger UI): http://localhost:8000/docs
- Alternative Documentation (ReDoc): http://localhost:8000/redoc

## API Endpoints

- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint

## Development

The application is built with:
- FastAPI - Modern web framework for building APIs
- Uvicorn - ASGI server
- Pydantic - Data validation using Python type annotations