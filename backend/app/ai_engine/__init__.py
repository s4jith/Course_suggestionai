"""
AI Engine package for the Academic Lesson Plan API.

Provides a hybrid AI recommendation system combining:
  - Rule-based engine  : deterministic, fast, auditable (app/ai_engine/rules/)
  - Risk analyzer      : scoring + delay prediction   (app/ai_engine/inference/)
  - Ollama LLM service : narrative enrichment layer   (app/ai_engine/services/)
  - Prompt templates   : structured JSON prompts      (app/ai_engine/prompts/)
  - Data extractor     : context snapshot builder     (app/ai_engine/utils/)
"""
