import os
import shutil
from typing import List, Dict
from pydantic import BaseModel
from .search_service import hybrid_search
from .download_service import iterative_download
from .llm_service import LLMService
from pypdf import PdfReader

from docx import Document
from PIL import Image
import pytesseract

class ResearchJob(BaseModel):
    topic: str
    word_count: int
    citation_style: str
    discipline: str
    optimization_prompt: str = ""

import pandas as pd

class Orchestrator:
    def __init__(self):
        self.llm = LLMService()
        self.workspace_root = "research_projects"
        os.makedirs(self.workspace_root, exist_ok=True)

    async def extract_text_or_data(self, file_path: str, topic: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".pdf":
                reader = PdfReader(file_path)
                return "".join([page.extract_text() for page in reader.pages])
            elif ext == ".docx":
                doc = Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs])
            elif ext in [".csv", ".xlsx", ".xls"]:
                df = pd.read_csv(file_path) if ext == ".csv" else pd.read_excel(file_path)
                summary = f"Columns: {list(df.columns)}\n"
                summary += f"Shape: {df.shape}\n"
                summary += f"Stats:\n{df.describe().to_string()}\n"
                summary += f"Head:\n{df.head(5).to_string()}"
                analysis = await self.llm.analyze_data_snippet(summary, topic)
                return f"DATASET ANALYSIS:\n{analysis}\nRAW SUMMARY:\n{summary}"
            elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
                try:
                    return pytesseract.image_to_string(Image.open(file_path))
                except Exception as ocr_err:
                    print(f"OCR not available on this server: {ocr_err}")
                    return "[OCR Error: Image could not be parsed. Ensure Tesseract is installed on the server.]"
            else:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return ""

    async def discover_datasets(self, topic: str) -> List[str]:
        # Custom logic to find datasets specifically
        dataset_queries = [
            f"{topic} dataset site:kaggle.com",
            f"{topic} raw data filetype:csv",
            f"{topic} public data site:gov OR site:org"
        ]
        all_dataset_links = []
        for q in dataset_queries:
            results = hybrid_search(q, target_count=3)
            all_dataset_links.extend([r.get('link') for r in results if r.get('link')])
        return list(set(all_dataset_links))

    async def run_research_task(self, job: ResearchJob, uploaded_files: List[str] = None):
        # 1. Setup workspace
        project_id = job.topic.lower().replace(" ", "_")[:20] + "_" + os.urandom(2).hex()
        project_dir = os.path.join(self.workspace_root, project_id)
        os.makedirs(project_dir, exist_ok=True)
        
        # 2. Process Uploaded Files (Primary Evidence & Data)
        primary_notes = []
        if uploaded_files:
            print(f"Processing {len(uploaded_files)} uploaded files...")
            for fpath in uploaded_files:
                content = await self.extract_text_or_data(fpath, job.topic)
                if content:
                    # If it was a dataset, the summary is already analytical
                    if "DATASET ANALYSIS:" in content:
                        primary_notes.append(f"UPLOADED DATA ({os.path.basename(fpath)}):\n{content}")
                    else:
                        note = await self.llm.summarize_paper(content)
                        primary_notes.append(f"UPLOADED SOURCE ({os.path.basename(fpath)}): {note}")

        # 3. Dataset Discovery (New Phase for "The Best" Research)
        print("Discovering relevant public datasets...")
        dataset_links = await self.discover_datasets(job.topic)
        if dataset_links:
            primary_notes.append(f"RECOMMENDED PUBLIC DATASETS FOR FURTHER ANALYSIS: {', '.join(dataset_links[:5])}")

        # 4. Generate Dynamic Outline
        print("Generating dynamic outline...")
        outline = await self.llm.generate_dynamic_outline(job.topic, primary_notes, job.optimization_prompt)
        if not outline:
            outline = ["Introduction", "Literature Review", "Analysis", "Conclusion"]

        # 4. Generate Queries for Supplementary Research
        print(f"Generating queries for: {job.topic}")
        queries = await self.llm.generate_queries(job.topic)
        
        # 5. Search & Download (Supplementary Evidence)
        target_sources = max(3, job.word_count // 300)
        supplementary_downloaded = []
        
        for query in queries:
            if len(supplementary_downloaded) >= target_sources:
                break
            print(f"Searching: {query}")
            results = hybrid_search(query, target_count=target_sources)
            downloaded = iterative_download(results, project_dir, target_sources - len(supplementary_downloaded))
            supplementary_downloaded.extend(downloaded)
            
        # 6. Parsing Supplementary Notes
        supplementary_notes = []
        for pdf_path in supplementary_downloaded:
            print(f"Parsing supplementary: {pdf_path}")
            text = await self.extract_text_or_data(pdf_path, job.topic)
            if text:
                note = await self.llm.summarize_paper(text)
                supplementary_notes.append(f"WEB SOURCE: {note}")
                
        # 7. Drafting
        all_evidence = primary_notes + supplementary_notes
        full_paper = f"# {job.topic}\n\n"
        
        for section in outline:
            print(f"Drafting: {section}")
            content = await self.llm.draft_section(section, all_evidence, job.dict(), job.optimization_prompt)
            full_paper += f"## {section}\n\n{content}\n\n"
            
        # 8. Save Results
        output_path = os.path.join(project_dir, "output.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_paper)
            
        return {
            "project_dir": project_dir,
            "output": full_paper,
            "sources": uploaded_files + supplementary_downloaded if uploaded_files else supplementary_downloaded
        }
