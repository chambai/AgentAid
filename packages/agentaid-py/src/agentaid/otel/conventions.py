from __future__ import annotations

from enum import StrEnum


class GenAI(StrEnum):
    SYSTEM = "gen_ai.system"
    REQUEST_MODEL = "gen_ai.request.model"
    RESPONSE_MODEL = "gen_ai.response.model"
    USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
    USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
    OPERATION_NAME = "gen_ai.operation.name"
    TOOL_NAME = "gen_ai.tool.name"
    TOOL_CALL_ID = "gen_ai.tool.call.id"

class AgentAid(StrEnum):
    """AgentAid-specific extensions."""
    RUN_ID = "agentaid.run_id"
    ROLE = "agentaid.role"
    PROMPT_SHA = "agentaid.prompt_sha"
    AGENT_NAME = "agentaid.agent_name"
    EVAL_RESULT = "agentaid.eval_result"
    INPUT = "agentaid.input"
    OUTPUT = "agentaid.output"
