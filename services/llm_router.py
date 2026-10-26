"""
Single-Model AI LLM Router (services/llm_router.py)
Dedicated to Groq / Grok Free Tier AI Model with circuit breaker and verified template failover.
All Gemini, OpenRouter, and Mistral legacy providers have been removed as requested.
"""
import os
import time
import json
import threading
from typing import List, Dict, Any, Optional
import requests

class LLMRouter:
    _instance: Optional['LLMRouter'] = None
    _lock = threading.Lock()

    def __init__(self):
        # Default to Groq with Grok compatibility
        self.provider_order = [
            p.strip().lower() for p in os.getenv("LLM_PROVIDER_ORDER", "groq,grok").split(",")
            if p.strip() and p.strip().lower() in ("groq", "grok")
        ]
        if not self.provider_order:
            self.provider_order = ["groq"]

        self.timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
        self.cooldown = int(os.getenv("LLM_COOLDOWN_SECONDS", "60"))
        
        # State tracking per provider: { 'disabled': bool, 'cooldown_until': float, 'last_error': str, 'last_success': str }
        self.state: Dict[str, Dict[str, Any]] = {
            p: {"disabled": False, "cooldown_until": 0.0, "last_error": None, "last_success": None}
            for p in ["groq", "grok"]
        }

    @classmethod
    def get_instance(cls) -> 'LLMRouter':
        with cls._lock:
            if cls._instance is None:
                cls._instance = LLMRouter()
            return cls._instance

    def _get_provider_config(self, provider: str) -> Optional[Dict[str, str]]:
        if provider == "groq":
            # Primary: Groq Cloud Free API (https://api.groq.com/openai/v1)
            key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")
            if not key:
                return None
            base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
            if not base_url.endswith("/chat/completions"):
                url = f"{base_url}/chat/completions"
            else:
                url = base_url

            model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
            return {
                "url": url,
                "key": key,
                "model": model,
                "display_name": f"Groq ({model})"
            }

        elif provider == "grok":
            # Grok (xAI) compatibility
            key = os.getenv("GROK_API_KEY") or os.getenv("GROQ_API_KEY")
            if not key:
                return None
            base_url = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1").rstrip("/")
            if not base_url.endswith("/chat/completions"):
                url = f"{base_url}/chat/completions"
            else:
                url = base_url

            model = os.getenv("GROK_MODEL", "grok-beta")
            return {
                "url": url,
                "key": key,
                "model": model,
                "display_name": f"Grok ({model})"
            }

        return None

    def chat_completion(self, messages: List[Dict[str, str]], json_mode: bool = True) -> Dict[str, Any]:
        """Alias for complete() for endpoint compatibility."""
        return self.complete(messages, json_mode=json_mode)

    def complete(self, messages: List[Dict[str, str]], json_mode: bool = True) -> Dict[str, Any]:
        """
        Executes completion against the single configured AI model.
        Returns {content: str, provider_used: str, attempts: List[Dict]}
        """
        attempts = []
        now = time.time()

        for provider in self.provider_order:
            cfg = self._get_provider_config(provider)
            if not cfg:
                continue

            p_state = self.state.get(provider, {})
            if p_state.get("disabled"):
                attempts.append({"provider": provider, "status": "disabled", "ms": 0})
                continue
            if p_state.get("cooldown_until", 0) > now:
                attempts.append({"provider": provider, "status": "cooldown", "ms": 0})
                continue

            t0 = time.time()
            try:
                headers = {
                    "Authorization": f"Bearer {cfg['key']}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": cfg["model"],
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 1024
                }
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}

                resp = requests.post(cfg["url"], headers=headers, json=payload, timeout=self.timeout)
                duration_ms = int((time.time() - t0) * 1000)

                if resp.status_code == 200:
                    try:
                        res_json = resp.json()
                        choices = res_json.get("choices", [])
                        if choices and "message" in choices[0] and "content" in choices[0]["message"]:
                            content = choices[0]["message"]["content"]
                            with self._lock:
                                p_state["last_success"] = time.strftime("%H:%M:%S")
                                p_state["last_error"] = None
                                p_state["cooldown_until"] = 0.0

                            attempts.append({"provider": provider, "status": "success", "ms": duration_ms})
                            return {
                                "content": content,
                                "provider_used": cfg.get("display_name", provider),
                                "attempts": attempts
                            }
                        else:
                            raise ValueError("Response missing choices or message content")
                    except Exception as json_err:
                        with self._lock:
                            p_state["cooldown_until"] = time.time() + self.cooldown
                            p_state["last_error"] = f"Malformed provider payload: {str(json_err)}"
                        attempts.append({"provider": provider, "status": "malformed_response", "ms": duration_ms})

                elif resp.status_code in (401, 403):
                    with self._lock:
                        p_state["disabled"] = True
                        p_state["last_error"] = f"HTTP {resp.status_code}: Unauthorized"
                    attempts.append({"provider": provider, "status": "disabled_401", "ms": duration_ms})

                elif resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", self.cooldown))
                    with self._lock:
                        p_state["cooldown_until"] = time.time() + retry_after
                        p_state["last_error"] = "HTTP 429: Rate limited"
                    attempts.append({"provider": provider, "status": "rate_limited_429", "ms": duration_ms})

                else:
                    with self._lock:
                        p_state["cooldown_until"] = time.time() + self.cooldown
                        p_state["last_error"] = f"HTTP {resp.status_code}"
                    attempts.append({"provider": provider, "status": f"error_{resp.status_code}", "ms": duration_ms})

            except Exception as ex:
                duration_ms = int((time.time() - t0) * 1000)
                with self._lock:
                    p_state["cooldown_until"] = time.time() + self.cooldown
                    p_state["last_error"] = str(ex)
                attempts.append({"provider": provider, "status": "exception", "error": str(ex), "ms": duration_ms})

        # All providers exhausted or no key configured: Fall back to local template matcher
        return {
            "content": None,
            "provider_used": "TEMPLATE_FALLBACK",
            "attempts": attempts
        }

    def get_provider_status(self) -> Dict[str, Any]:
        """Admin status of the configured Groq/Grok provider."""
        now = time.time()
        result = {}
        for p in ["groq", "grok"]:
            cfg = self._get_provider_config(p)
            st = self.state.get(p, {})
            is_configured = cfg is not None
            is_disabled = st.get("disabled", False)
            in_cooldown = st.get("cooldown_until", 0) > now
            
            status_text = "NOT_CONFIGURED"
            if is_configured:
                if is_disabled:
                    status_text = "DISABLED_AUTH"
                elif in_cooldown:
                    rem = int(st.get("cooldown_until", 0) - now)
                    status_text = f"COOLING_DOWN ({rem}s)"
                else:
                    status_text = "HEALTHY"

            result[p] = {
                "configured": is_configured,
                "status": status_text,
                "model": cfg.get("model") if cfg else None,
                "last_error": st.get("last_error"),
                "last_success": st.get("last_success")
            }
        return result
