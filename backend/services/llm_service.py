from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Dict
import os

# Base System Prompt from academic-writing skill
ACADEMIC_SYSTEM_PROMPT = """
You are a senior academic writer and researcher. Your goal is to produce rigorous, readable, and evidence-backed academic writing.
Follow these non-negotiable rules:
1. Never invent citations, quotations, page numbers, datasets, equations, theorem names, results, authors, journals, dates, DOIs, URLs, or consensus.
2. Cite only sources provided to you.
3. Separate facts, inferences, interpretations, and writing suggestions.
4. Prefer clarity over ornament. Precise, not inflated.
5. Do not overclaim. Use calibrated verbs (suggests, indicates, supports, implies, contradicts).
6. State assumptions, variables, domains, and constraints explicitly.
7. If evidence is missing, mark with [citation needed].
8. Maintain discipline-appropriate register.
"""

class LLMService:
    def __init__(self, model_name: str = None):
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_api_key:
            # Use OpenRouter
            model = model_name or "google/gemini-2.0-flash-001"
            self.llm = ChatOpenAI(
                model=model,
                openai_api_key=openrouter_api_key,
                openai_api_base="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com/google-gemini/gemini-cli", # Optional
                    "X-Title": "Academic Writer", # Optional
                },
                temperature=0.2
            )
        else:
            # Fallback to direct Google Gemini
            model = model_name or "gemini-2.0-flash"
            self.llm = ChatGoogleGenerativeAI(model=model, temperature=0.2)

    async def summarize_paper(self, text: str) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Summarize this academic paper focusing on purpose, methods, key findings, and limitations. Provide a structured note."),
            ("user", "{text}")
        ])
        chain = prompt | self.llm
        # Gemini usually has a larger context window, but we still truncate for safety
        response = await chain.ainvoke({"text": text[:30000]})
        return response.content

    async def analyze_data_snippet(self, data_summary: str, topic: str) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a senior data scientist and research analyst. Analyze the following data summary (CSV/Excel snippet) in the context of the research topic. Identify trends, anomalies, and key quantitative insights. DO NOT invent data."),
            ("user", "Research Topic: {topic}\nData Summary:\n{data_summary}")
        ])
        chain = prompt | self.llm
        response = await chain.ainvoke({
            "topic": topic,
            "data_summary": data_summary
        })
        return response.content

    async def generate_dynamic_outline(self, topic: str, context_notes: List[str], optimization_prompt: str) -> List[str]:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert research architect. Based on the topic, uploaded source summaries (including any data analysis), and optimization instructions, generate a detailed hierarchical research outline. If quantitative data was provided, ensure there is a dedicated 'Empirical Analysis' or 'Data Results' section. Return ONLY a list of section titles, one per line."),
            ("user", "Topic: {topic}\nUploaded Context & Data Insights: {context}\nOptimization Instructions: {optimization_prompt}")
        ])
        chain = prompt | self.llm
        response = await chain.ainvoke({
            "topic": topic,
            "context": "\n---\n".join(context_notes),
            "optimization_prompt": optimization_prompt
        })
        return [line.strip().replace("- ", "").replace("* ", "") for line in response.content.split("\n") if line.strip() and not line.startswith("#")]

    async def draft_section(self, section_title: str, notes: List[str], job_info: Dict, optimization_prompt: str = "") -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", ACADEMIC_SYSTEM_PROMPT + "\nDraft the following section. PRIORITY: Use uploaded files as primary ground truth. Supplement with web sources where needed. Optimization Prompt: {optimization_prompt}\nSection Title: {section_title}"),
            ("user", "Evidence Notes: {notes}\nContext: {job_info}")
        ])
        chain = prompt | self.llm
        response = await chain.ainvoke({
            "section_title": section_title,
            "notes": "\n---\n".join(notes),
            "job_info": str(job_info),
            "optimization_prompt": optimization_prompt
        })
        return response.content

    async def generate_queries(self, topic: str) -> List[str]:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Generate 3 highly optimized Boolean search queries for the following topic. Use concept groups, synonyms, and academic constraints like 'filetype:pdf' or 'site:arxiv.org'."),
            ("user", "{topic}")
        ])
        chain = prompt | self.llm
        response = await chain.ainvoke({"topic": topic})
        # Basic parsing: assume one query per line
        return [q.strip() for q in response.content.split("\n") if q.strip()][:3]
