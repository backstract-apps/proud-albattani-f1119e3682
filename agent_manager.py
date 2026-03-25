"""
AgentManager — thread-safe, per-tenant agent registry.

Each unique combination of (tenant_id, agent_name, model, llm_key, system_prompt)
maps to exactly one cached Agent instance.  When any of those attributes change
the old entry is evicted and a fresh Agent is created on the next call.
"""
# import hashlib
# import threading
# from dataclasses import dataclass, field
import time
import json
import re
from typing import Optional, Any, Callable, List
from pydantic import BaseModel
from enum import Enum
from agents import (
    Agent,
    Model,
    ModelProvider,
    OpenAIChatCompletionsModel,
    RunConfig,
    Runner,
    ModelSettings,
    RunContextWrapper,
    GuardrailFunctionOutput,
    AsyncOpenAI,
    function_tool,
)
import os
import requests
from bs4 import BeautifulSoup
import urllib.parse
from duckduckgo_search import DDGS
import csv



DEFAULT_MODEL = "google/gemini-3.1-flash-lite-preview"

global_client: AsyncOpenAI = None

# ---------------------------------------------------------------------------
#   AGENT DEFINITION
# ---------------------------------------------------------------------------

class AgentBaseDto(BaseModel):
    agent_name: str
    agent_description: Optional[str]
    model_name: str
    system_prompt: str
    temperature: float
    input_guardrails: List = []
    output_guardrails: List = []
    tools: List = []


def create_agent(dto: AgentBaseDto) -> Agent:
    return Agent(
        name=dto.agent_name,
        handoff_description=dto.agent_description,
        model=dto.model_name,
        model_settings=ModelSettings(
            temperature=dto.temperature
        ),
        instructions=dto.system_prompt,
        # tools=
        # input_guardrails=
        # output_guardrails=
    )


class LLMProviderBaseURLs(str, Enum):
    # Official OpenAI API
    OPENAI = "https://api.openai.com/v1"
    
    # OpenRouter (Aggregator for Anthropic, OpenAI, Meta, etc.)
    OPENROUTER = "https://openrouter.ai/api/v1"
    
    # Google Gemini (Official OpenAI compatibility endpoint)
    GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai/"
    
    # Additional fast/popular OpenAI-compatible providers
    GROQ = "https://api.groq.com/openai/v1"
    TOGETHER = "https://api.together.xyz/v1"
    MISTRAL = "https://api.mistral.ai/v1"
    DEEPSEEK = "https://api.deepseek.com/v1"
    PERPLEXITY = "https://api.perplexity.ai"


def get_provider_client(api_provider: str, api_key: str) -> Optional[AsyncOpenAI]:
    """
    Returns an AsyncOpenAI client configured for the requested provider.
    """
    if not api_provider:
        print("Error: LLM Provider is not set.")
        return None

    if not api_key:
        print(f"Error: API Key is not set for provider '{api_provider}'.")
        return None

    # Normalize the string (e.g., "openai", "OpenAI", and " OPENAI " all become "OPENAI")
    provider_key = api_provider.strip().upper()

    # Validate that the provider exists in our Enum
    if provider_key not in LLMProviderBaseURLs.__members__:
        valid_providers = ", ".join(LLMProviderBaseURLs.__members__.keys())
        print(f"Error: Unsupported provider '{api_provider}'. Valid options are: {valid_providers}")
        return None

    # Get the correct base URL
    base_url = LLMProviderBaseURLs[provider_key].value

    # Initialize and return the AsyncOpenAI client
    async_client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    global_client = async_client
    return async_client


# ══════════════════════════════════════════════════════════════════════════════
#  PLATFORM TOOLS
# ══════════════════════════════════════════════════════════════════════════════
@function_tool
def tool_scraper(url: str, max_length: int = 200) -> str:
    """
    Fetches the HTML content from a given URL and extracts the readable text.
    Use this to read the contents of an article or webpage after finding its URL.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
            
        # Get text and clean up whitespace
        text = soup.get_text(separator='\n')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        if len(text) > max_length:
            return text[:max_length] + f"\n\n...[Content truncated to {max_length} characters]..."
            
        return text if text else "Page fetched, but no readable text found."
        
    except Exception as e:
        return f"Error fetching webpage: {str(e)}"
    

@function_tool
def tool_reader(file_path: str) -> str:
    """
    Reads and returns the contents of a local file.
    Use this to inspect code, read configuration files, or analyze local data.
    """
    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' does not exist."
        
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Optional: Prevent massive files from blowing up the context window
        if len(content) > 10000:
            return content[:10000] + "\n\n...[File too large, content truncated]..."
            
        return content
    except UnicodeDecodeError:
        return f"Error: '{file_path}' appears to be a binary file and cannot be read as text."
    except Exception as e:
        return f"Error reading file: {str(e)}"


@function_tool
def tool_weather(location: str) -> str:
    """
    Gets the current weather and short forecast for a specific city or location.
    """
    try:
        # format=3 gives a nice single-line summary. format=j gives JSON.
        # We use format=0T for a rich but text-only terminal output
        safe_location = urllib.parse.quote(location)
        url = f"https://wttr.in/{safe_location}?0T"
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        return response.text
    except Exception as e:
        return f"Could not fetch weather for {location}. Error: {str(e)}"


@function_tool
def tool_summarize(text: str) -> str:
    resp = global_client.responses.create(
        model=DEFAULT_MODEL,
        input=f"Summarize:\n{text[:6000]}"
    )

    return resp.output_text


@function_tool
def tool_checker(claim: str, max_sources: int = 5) -> str:
    """
    Verify factual accuracy of a claim using web evidence + LLM reasoning.
    """

    with DDGS() as ddgs:
        results = list(ddgs.text(claim, max_results=max_sources))

    if not results:
        return "No evidence found."

    evidence_text = "\n\n".join(
        f"{r.get('title')}\n{r.get('body')}\nURL:{r.get('href')}"
        for r in results
    )

    prompt = f"""You are a fact verification system.

Claim:
{claim}

Evidence:
{evidence_text}

Return:

Verdict: TRUE / FALSE / MIXED / UNKNOWN
Confidence: 0-100
Reasoning: short"""

    resp = global_client.responses.create(
        model=DEFAULT_MODEL,
        input=prompt
    )

    return resp.output_text


@function_tool
def tool_csv(path: str, rows: int = 5) -> str:
    try:
        output = []

        with open(path) as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i >= rows:
                    break
                output.append(", ".join(row))

        return "\n".join(output)

    except Exception as e:
        return f"CSV error: {str(e)}"

# ══════════════════════════════════════════════════════════════════════════════
#  PLATFORM GUARDRAILS
# ══════════════════════════════════════════════════════════════════════════════

async def guardrail_pii(ctx, agent, output):
    """Block output containing emails / phone numbers / API keys."""
    text = str(output)

    patterns = [
        r"\b[\w\.-]+@[\w\.-]+\.\w+\b",      # email
        r"\b\d{10,13}\b",                   # phone
        r"sk-[A-Za-z0-9]{20,}",             # api key like
    ]

    triggered = any(re.search(p, text) for p in patterns)

    return GuardrailFunctionOutput(
        output_info={"pii_detected": triggered},
        tripwire_triggered=triggered,
    )

async def guardrail_profanity(
    ctx: RunContextWrapper, agent: Agent, input: Any
) -> GuardrailFunctionOutput:
    """Block obvious profanity in input using comprehensive regex filters."""
    
    profanity_patterns = [
        '((bul+|dip|horse|jack).?)?sh(\\?\\*|[ai]|(?!(eets?|iites?)\\b)[ei]{2,})(\\?\\*|t)e?(bag|dick|head|load|lord|post|stain|ter|ting|ty)?s?', 
        '((dumb|jack|smart|wise).?)?a(rse|ss)(.?(clown|fuck|hat|hole|munch|sex|tard|tastic|wipe))?(e?s)?', 
        '(?!(?-i:Cockburns?\\b))cock(?!amamie|apoo|atiel|atoo|ed\\b|er\\b|erels?\\b|eyed|iness|les|ney|pit|rell|roach|sure|tail|ups?\\b|y\\b)\\w[\\w-]*', 
        '(?#ES)(cabr[oó]n(e?s)?|chinga\\W?(te)?|g[uü]ey|mierda|no mames|pendejos?|pinche|put[ao]s?)', 
        '(?<!\\b(moby|tom,) )(?!(?-i:Dick [A-Z][a-z]+\\b))dick(?!\\W?(and jane|cavett|cheney|dastardly|grayson|s?\\W? sporting good|tracy))s?', 
        '(cock|dick|penis|prick)\\W?(bag|head|hole|ish|less|suck|wad|weed|wheel)\\w*', 
        '(f(?!g\\b|gts\\b)|ph)[\\x40a]?h?g(?!\\W(and a pint|ash|break|butt|end|packet|paper|smok\\w*)s?\\b)g?h?([0aeiou]?tt?)?(ed|in[\\Wg]?|r?y)?s?', 
        '(m[oua]th(a|er).?)?f(?!uch|uku)(\\?\\*|u|oo)+(\\?\\*|[ckq])+\\w*', 
        '[ck]um(?!.laude)(.?shot)?(m?ing|s)?', 
        'b(\\?\\*|i)(\\?\\*|[ao])?(\\?\\*|t)(\\?\\*|c)(\\?\\*|h)(e[ds]|ing|y)?', 
        'c+u+n+t+([sy]|ing)?', 
        'cock(?!-ups?\\b|\\W(a\\Whoop|a\\Wsnook|and\\Wbull|eyed|in\\Wthe\\Whenhouse|of\\Wthe\\W(rock|roost|walk))\\b)s?', 
        'd[o0]+u[cs]he?\\W?(bag|n[0o]zzle|y)s?', 
        'piss(ed(?! off)(?<!\\bi(\\sa|\\W?)m pissed)|er?s|ing)?', 
        'pricks?', 
        'tit(t(ie|y))?s?'
    ]
    
    text = str(input)
    triggered = False
    
    # Check the text against each pattern
    for pattern in profanity_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            triggered = True
            break
            
    return GuardrailFunctionOutput(
        output_info={"checked": True, "blocked": triggered},
        tripwire_triggered=triggered,
    )

async def guardrail_length(
    ctx: RunContextWrapper, agent: Agent, output: Any
) -> GuardrailFunctionOutput:
    """Warn if output is suspiciously short (< 5 chars)."""
    too_short = isinstance(output, str) and len(output.strip()) < 5
    return GuardrailFunctionOutput(
        output_info={"length": len(str(output)), "flagged": too_short},
        tripwire_triggered=False,  # warn only, don't block
    )

async def guardrail_violence(
    ctx: RunContextWrapper, agent: Agent, output: Any
):
    """Ensure output is valid JSON."""
    try:
        json.loads(output)
        triggered = False
    except Exception:
        triggered = True

    return GuardrailFunctionOutput(
        output_info={"valid_json": not triggered},
        tripwire_triggered=triggered,
    )

async def guardrail_latency(ctx, agent, _):
    """Stop if run exceeds time budget."""
    start = ctx.state.get("start_time")
    if not start:
        return GuardrailFunctionOutput({}, False)

    elapsed = time.time() - start
    triggered = elapsed > 15

    return GuardrailFunctionOutput(
        output_info={"elapsed": elapsed},
        tripwire_triggered=triggered,
    )

# ---------------------------------------------------------------------------
#   CUSTOM GUARDRAILS
# ---------------------------------------------------------------------------

def create_llm_guardrail(client: AsyncOpenAI, rule_prompt: str, fail_closed: bool = False) -> Callable:
    """
    Takes a natural language prompt/rule and converts it into a guardrail function.
    Uses gpt-4o-mini to evaluate if the input/output violates the rule.
    
    Args:
        rule_prompt: The instruction the text must follow (e.g. "Do not give medical advice").
        fail_closed: If True, trips the wire if the OpenAI API fails. If False, allows it through.
    """
    
    # We return the actual async function expected by your agent framework
    async def dynamic_llm_guardrail(
        ctx: RunContextWrapper, agent: Agent, text_to_check: Any
    ) -> GuardrailFunctionOutput:
        
        # client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # System instructions forcing the LLM to act as a strict binary judge
        system_instruction = (
            "You are a strict guardrail judge for an AI application. "
            f"Your rule to enforce is: {rule_prompt}\n\n"
            "Evaluate the provided text. Does it VIOLATE this rule? "
            "Respond strictly with a JSON object containing two keys: "
            "'violation' (boolean true/false) and 'reason' (a short string explaining why)."
        )
        
        try:
            # Call a fast/cheap model to act as the judge
            response = await client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": str(text_to_check)}
                ],
                response_format={"type": "json_object"},
                temperature=0.0 # Keep temperature at 0 for deterministic evaluations
            )
            
            # Parse the judge's decision
            result = json.loads(response.choices[0].message.content)
            is_violation = result.get("violation", False)
            reason = result.get("reason", "No reason provided")
            
            return GuardrailFunctionOutput(
                output_info={
                    "rule_checked": rule_prompt,
                    "judge_reason": reason,
                    "violation_found": is_violation
                },
                tripwire_triggered=is_violation, # Block it if a violation is found
            )
            
        except Exception as e:
            # Handle API timeouts or JSON parsing errors
            return GuardrailFunctionOutput(
                output_info={"error": str(e), "evaluation_failed": True},
                tripwire_triggered=fail_closed,
            )

    return dynamic_llm_guardrail

# ---------------------------------------------------------------------------
#   MaysonAgentModelProvider
# ---------------------------------------------------------------------------

class MaysonAgentModelProvider(ModelProvider):
    """Routes all model requests through the selected Provider."""

    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    def get_model(self, model_name: str | None) -> Model:
        return OpenAIChatCompletionsModel(
            model=model_name,
            openai_client=self._client,
        )

async def run_query(query: str, run_config: RunConfig) -> str:
    result = await Runner.run("search_agent", query, run_config=run_config)
    return result.final_output

async def run_agent_query(agent: Agent, query: str, run_config: RunConfig) -> str:
    result = await Runner.run(agent, query, run_config=run_config)
    return result.final_output



'''
# ---------------------------------------------------------------------------
#   AgentManager
# ---------------------------------------------------------------------------

class AgentManager:
    """
    Singleton-friendly registry that creates and caches Agent instances.

    Thread-safety: a reentrant lock guards the internal registry so that
    concurrent API requests for the same tenant don't race to build the
    same agent twice.
    """

    def __init__(self) -> None:
        self._registry: dict[AgentKey, Agent] = {}
        self._lock = threading.RLock()
        logger.info("AgentManager initialised.")

    # ------------------------------------------------------------------
    #   Public interface
    # ------------------------------------------------------------------

    def get_or_create(self, descriptor: AgentDescriptor) -> Agent:
        """Return a cached Agent, creating one if it doesn't exist yet."""
        key = descriptor.to_key()
        with self._lock:
            if key not in self._registry:
                agent = self._build_agent(descriptor)
                self._registry[key] = agent
                logger.info(
                    "Created new agent '%s' for tenant '%s' (model=%s).",
                    descriptor.agent_name,
                    descriptor.tenant_id,
                    descriptor.model,
                )
            else:
                logger.debug(
                    "Reusing cached agent '%s' for tenant '%s'.",
                    descriptor.agent_name,
                    descriptor.tenant_id,
                )
            return self._registry[key]

    def evict(self, descriptor: AgentDescriptor) -> bool:
        """
        Remove an agent from the cache (e.g. after a credential rotation).
        Returns True if an entry was removed.
        """
        key = descriptor.to_key()
        with self._lock:
            removed = self._registry.pop(key, None) is not None
            if removed:
                logger.info(
                    "Evicted agent '%s' for tenant '%s'.",
                    descriptor.agent_name,
                    descriptor.tenant_id,
                )
            return removed

    def evict_tenant(self, tenant_id: str) -> int:
        """Remove every agent belonging to *tenant_id*.  Returns count removed."""
        with self._lock:
            to_remove = [k for k in self._registry if k.tenant_id == tenant_id]
            for k in to_remove:
                del self._registry[k]
            if to_remove:
                logger.info("Evicted %d agent(s) for tenant '%s'.", len(to_remove), tenant_id)
            return len(to_remove)

    def run_sync(self, descriptor: AgentDescriptor, user_prompt: str):
        """Convenience: resolve agent + run synchronously in one call."""
        agent = self.get_or_create(descriptor)
        return Runner.run_sync(agent, user_prompt)

    async def run_async(self, descriptor: AgentDescriptor, user_prompt: str):
        """Convenience: resolve agent + run asynchronously in one call."""
        agent = self.get_or_create(descriptor)
        return await Runner.run(agent, user_prompt)

    @property
    def cached_count(self) -> int:
        with self._lock:
            return len(self._registry)


    # ------------------------------------------------------------------
    #   Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_agent(descriptor: AgentDescriptor) -> Agent:
        """Construct an Agent wired to the tenant's own OpenAI key."""
        client = AsyncOpenAI(api_key=descriptor.llm_key)
        return Agent(
            name=descriptor.agent_name,
            instructions=descriptor.system_prompt,
            model=descriptor.model,
            # Pass the per-tenant client so the SDK uses the right key.
            model_settings={"openai_client": client},
        )
'''
