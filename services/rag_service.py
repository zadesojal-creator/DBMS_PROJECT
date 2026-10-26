"""
RAG Service (services/rag_service.py)
Retrieves role-specific view schemas, targeted business rules, and relevant few-shot examples
without consuming external API quota or requiring heavy vector databases.
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "rag_knowledge"

ROLE_ALLOWED_VIEWS = {
    "INVESTOR": ["v_investor_portfolio", "v_investor_transactions", "v_market_latest"],
    "BROKER": ["v_broker_client_transactions", "v_broker_commissions", "v_broker_client_summary", "v_market_latest"],
    "ADMIN": ["v_admin_trade_facts", "v_admin_user_audit", "v_admin_audit_logs", "v_market_latest", "Stocks", "Commission_Rules"]
}

class RAGService:
    _cached_schemas: Dict[str, str] = {}
    _cached_rules: List[Dict[str, str]] = []
    _cached_examples: List[Dict[str, str]] = []
    _initialized: bool = False

    @classmethod
    def _init_knowledge_base(cls, force: bool = False) -> None:
        if cls._initialized and not force:
            return

        cls._cached_schemas = {}
        cls._cached_rules = []
        cls._cached_examples = []

        schema_file = KNOWLEDGE_DIR / "schema_documentation.md"
        rules_file = KNOWLEDGE_DIR / "business_rules.md"
        examples_file = KNOWLEDGE_DIR / "sql_examples.md"

        # 1. Parse schemas by view/table name
        if schema_file.exists():
            content = schema_file.read_text(encoding="utf-8")
            # Split sections starting with ### or ##
            sections = re.split(r'\n(?=###?\s+)', content)
            for sec in sections:
                header_match = re.search(r'###?\s+([a-zA-Z0-9_]+)', sec)
                if header_match:
                    tbl_name = header_match.group(1).lower()
                    cls._cached_schemas[tbl_name] = sec.strip()

        # 2. Parse business rules
        if rules_file.exists():
            content = rules_file.read_text(encoding="utf-8")
            rule_blocks = re.split(r'\n(?=\d+\.\s+\*\*)', content)
            for rb in rule_blocks:
                rb_clean = rb.strip()
                if rb_clean:
                    cls._cached_rules.append({
                        "text": rb_clean,
                        "keywords": set(re.findall(r'\w+', rb_clean.lower()))
                    })

        # 3. Parse few-shot examples
        if examples_file.exists():
            content = examples_file.read_text(encoding="utf-8")
            current_role = "INVESTOR"
            lines = content.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("## 1. Investor"):
                    current_role = "INVESTOR"
                elif line.startswith("## 2. Broker"):
                    current_role = "BROKER"
                elif line.startswith("## 3. Admin"):
                    current_role = "ADMIN"
                elif line.startswith("- **"):
                    q_match = re.search(r'\-\s+\*\*(.*?)\*\*', line)
                    if q_match:
                        q_text = q_match.group(1)
                        sql_lines = []
                        i += 1
                        while i < len(lines) and not lines[i].strip().startswith("```sql"):
                            i += 1
                        i += 1
                        while i < len(lines) and not lines[i].strip().startswith("```"):
                            sql_lines.append(lines[i])
                            i += 1
                        sql_text = "\n".join(sql_lines).strip()
                        cls._cached_examples.append({
                            "role": current_role,
                            "question": q_text,
                            "sql": sql_text,
                            "keywords": set(re.findall(r'\w+', q_text.lower()))
                        })
                i += 1

        cls._initialized = True

    @staticmethod
    def get_context_for_role(role: str, question: Optional[str] = None, intent: Optional[Any] = None) -> str:
        """
        Retrieves targeted, role-authorized schema specifications, relevant business rules,
        intent guidance, and few-shot SQL examples.
        """
        RAGService._init_knowledge_base()
        r = role.upper()
        allowed = ROLE_ALLOWED_VIEWS.get(r, [])
        user_words = set(re.findall(r'\w+', question.lower())) if question else set()

        # 1. Retrieve role-allowed schemas only
        selected_schemas = []
        for v in allowed:
            v_lower = v.lower()
            if v_lower in RAGService._cached_schemas:
                selected_schemas.append(RAGService._cached_schemas[v_lower])
        schema_text = "\n\n".join(selected_schemas)

        # 2. Retrieve relevant business rules
        selected_rules = []
        for rule in RAGService._cached_rules:
            if not user_words or "security" in rule["text"].lower() or len(user_words.intersection(rule["keywords"])) > 0:
                selected_rules.append(rule["text"])
        if not selected_rules:
            selected_rules = [r["text"] for r in RAGService._cached_rules]
        rules_text = "\n\n".join(selected_rules)

        # 3. Retrieve top matching few-shot examples for this role
        role_examples = [ex for ex in RAGService._cached_examples if ex["role"] == r]
        if user_words and role_examples:
            scored = []
            for ex in role_examples:
                overlap = len(user_words.intersection(ex["keywords"]))
                scored.append((overlap, ex))
            scored.sort(key=lambda x: x[0], reverse=True)
            chosen_examples = [s[1] for s in scored[:3]]
        else:
            chosen_examples = role_examples[:3]

        example_snippets = []
        for ex in chosen_examples:
            example_snippets.append(f"- **{ex['question']}**:\n  ```sql\n  {ex['sql']}\n  ```")
        examples_text = "\n\n".join(example_snippets)

        # 4. Intent Guidance
        guidance = ""
        if intent:
            guidance = f"""
--- DETECTED INTENT SPECIFICATIONS ---
Target Domain: {intent.domain}
Recommended View: {intent.target_view}
Entity / Sector: {intent.sector or 'None'}
Symbol: {intent.symbol or 'None'}
Scope: {intent.scope} {f'(LIMIT {intent.limit})' if intent.limit else '(Do NOT clamp with arbitrary LIMIT)'}
Time Bound: {intent.time_filter or 'None'}
Operation: {intent.operation}
CRITICAL: Do NOT substitute a generic top-stocks query if a specific subject or sector was requested!
"""

        return f"""ROLE: {r}
ALLOWED VIEWS/TABLES ONLY: {', '.join(allowed)}

--- SCHEMA SPECIFICATIONS (Role-Authorized) ---
{schema_text}
{guidance}
--- APPLICABLE BUSINESS RULES ---
{rules_text}

--- TARGETED VERIFIED QUERY EXAMPLES ---
{examples_text}
"""

    @staticmethod
    def get_template_fallback(role: str, question: str) -> Dict[str, Any]:
        """Provides verified, intent-preserving fallback queries when no external LLM provider is reachable."""
        from services.intent_service import IntentService
        resolver = IntentService.get_instance()
        intent = resolver.resolve_intent(question, role)
        return resolver.generate_sql(intent, role)
