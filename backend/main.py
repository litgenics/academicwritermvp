from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import json
from dotenv import load_dotenv
from services.orchestrator import Orchestrator, ResearchJob

load_dotenv()

app = FastAPI(title="Academic Writer API")
orchestrator = Orchestrator()

# Enable CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for job status (MVP only)
jobs = {}

@app.get("/")
async def root():
    return {"message": "Academic Writer API is running"}

@app.post("/research")
async def create_research(
    background_tasks: BackgroundTasks,
    topic: str = Form(...),
    word_count: int = Form(...),
    citation_style: str = Form(...),
    discipline: str = Form(...),
    optimization_prompt: str = Form(""),
    files: List[UploadFile] = File(None)
):
    job_id = f"job_{len(jobs) + 1}"
    jobs[job_id] = {"status": "processing", "progress": "Initializing...", "data": None}
    
    # Pre-save files to a temp location or project dir
    temp_upload_dir = os.path.join("research_projects", "temp_uploads", job_id)
    os.makedirs(temp_upload_dir, exist_ok=True)
    
    saved_file_paths = []
    if files:
        for file in files[:20]: # Limit to 20 files
            file_path = os.path.join(temp_upload_dir, file.filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            saved_file_paths.append(file_path)

    job_data = ResearchJob(
        topic=topic,
        word_count=word_count,
        citation_style=citation_style,
        discipline=discipline,
        optimization_prompt=optimization_prompt
    )
    
    def update_progress(step: str):
        if job_id in jobs:
            jobs[job_id]["progress"] = step

    async def run_task():
        try:
            result = await orchestrator.run_research_task(job_data, saved_file_paths, progress_callback=update_progress)
            jobs[job_id] = {"status": "completed", "progress": "Done!", "data": result}
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Job failed: {error_details}")
            jobs[job_id] = {"status": "failed", "progress": "Error", "error": str(e), "details": error_details}

    background_tasks.add_task(run_task)
    return {"job_id": job_id}

@app.get("/research/{job_id}")
async def get_job(job_id: str):
    return jobs.get(job_id, {"status": "not_found"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
