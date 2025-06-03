from fastapi import FastAPI
from .routers import circuit

# Add these imports for CORS
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="QuantumCanvas API",
    version="0.1.0",
    description="API for QuantumCanvas circuit parsing, optimization, and benchmarking.",
)

# CORS Configuration
origins = [
    "http://localhost:5173", # Your frontend development server
    "http://localhost:3000", # Common alternative for React dev servers
    # Add any other origins you need to allow (e.g., your deployed frontend URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)

@app.get("/")
async def root():
    return {"message": "Welcome to QuantumCanvas API"}

app.include_router(circuit.router)