"""
Configurable LLM Provider Interface for NIVA.
Supports Google Gemini, OpenAI, Anthropic, Ollama/Local, and an intelligent offline fallback.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger("NIVA.LLM")


class LLMProvider:
    """Dispatches reasoning queries to configured AI backends."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "gemini")).lower()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3:latest")

    def is_configured(self) -> bool:
        """Checks if a cloud or local API key is configured."""
        if self.provider == "gemini" and self.gemini_key:
            return True
        if self.provider == "openai" and self.openai_key:
            return True
        if self.provider == "anthropic" and self.anthropic_key:
            return True
        if self.provider in ["ollama", "local"]:
            return True
        return False

    def generate_conversational_response(self, user_prompt: str, context_summary: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Generates a direct, concise spoken reply for conversational questions using configured LLM.
        """
        system_prompt = (
            "You are NIVA, an intelligent, helpful, voice-first AI assistant for Windows computer control. "
            "Provide a concise, clear, and direct spoken answer to the user's question. "
            "Keep answers natural, conversational, and suitable for text-to-speech reading (1 to 3 sentences). "
            "Do not use markdown headers, bullet points, asterisks, or code blocks."
        )

        # 1. Try Gemini
        if self.provider == "gemini" and self.gemini_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.gemini_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[system_prompt, f"User Question: {user_prompt}"],
                )
                text = (response.text or "").strip()
                if text:
                    return text
            except Exception as e:
                logger.warning(f"Gemini conversational API call failed: {e}")

        # 2. Try OpenAI
        if self.provider == "openai" and self.openai_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_key)
                resp = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=200
                )
                text = (resp.choices[0].message.content or "").strip()
                if text:
                    return text
            except Exception as e:
                logger.warning(f"OpenAI conversational API call failed: {e}")

        # 3. Try Ollama Local
        if self.provider in ["ollama", "local"]:
            try:
                resp = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": f"{system_prompt}\nUser Question: {user_prompt}\nAssistant:",
                        "stream": False
                    },
                    timeout=10
                )
                if resp.status_code == 200:
                    text = resp.json().get("response", "").strip()
                    if text:
                        return text
            except Exception as e:
                logger.debug(f"Local Ollama conversational connection failed: {e}")

        return None

    def generate_plan(self, user_prompt: str, available_tools: List[Dict[str, Any]], context_summary: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Requests the AI model to generate a structured JSON plan consisting of tool calls.
        Returns a list of step dictionaries, or None if fallback should be used.
        """
        system_prompt = f"""
You are the AI Task Planner for NIVA, an autonomous Windows computer control agent.
Given a user's natural language request, break it down into an ordered execution plan of tool calls.

Available Tools:
{json.dumps([{t['name']: t['description']} for t in available_tools], indent=2)}

System Context:
{json.dumps(context_summary, indent=2)}

Rules:
1. Return ONLY a valid JSON list of step objects.
2. Each step object MUST have:
   - "description": clear human description of what this step does
   - "tool_name": one of the available tool names
   - "parameters": dictionary matching the tool's parameter schema
3. Plan all steps necessary to fulfill the request end-to-end.
4. If the task is single-step, return a list with 1 item.
"""
        # 1. Try Gemini
        if self.provider == "gemini" and self.gemini_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.gemini_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[system_prompt, f"User Request: {user_prompt}"],
                )
                text = response.text or ""
                return self._extract_json_plan(text)
            except Exception as e:
                logger.warning(f"Gemini API call failed: {e}. Falling back...")

        # 2. Try OpenAI
        if self.provider == "openai" and self.openai_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_key)
                resp = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2
                )
                text = resp.choices[0].message.content or ""
                return self._extract_json_plan(text)
            except Exception as e:
                logger.warning(f"OpenAI API call failed: {e}. Falling back...")

        # 3. Try Ollama Local
        if self.provider in ["ollama", "local"]:
            try:
                resp = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": f"{system_prompt}\nUser Request: {user_prompt}\nJSON Response:",
                        "stream": False,
                        "format": "json"
                    },
                    timeout=10
                )
                if resp.status_code == 200:
                    text = resp.json().get("response", "")
                    return self._extract_json_plan(text)
            except Exception as e:
                logger.debug(f"Local Ollama connection failed: {e}")

        # Return None to trigger built-in offline NLP planner
        return None

    @classmethod
    def _extract_json_plan(cls, text: str) -> Optional[List[Dict[str, Any]]]:
        """Extracts JSON list from markdown or raw text."""
        cleaned = text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(cleaned)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "steps" in data:
                return data["steps"]
        except Exception as e:
            logger.error(f"Failed to parse LLM JSON plan: {e}")
        return None
