export const GenAI = {
  System: "gen_ai.system",
  RequestModel: "gen_ai.request.model",
  ResponseModel: "gen_ai.response.model",
  UsageInputTokens: "gen_ai.usage.input_tokens",
  UsageOutputTokens: "gen_ai.usage.output_tokens",
  OperationName: "gen_ai.operation.name",
  ToolName: "gen_ai.tool.name",
  ToolCallId: "gen_ai.tool.call.id",
} as const;

export const AgentAid = {
  RunId: "agentaid.run_id",
  Role: "agentaid.role",
  PromptSha: "agentaid.prompt_sha",
  AgentName: "agentaid.agent_name",
  EvalResult: "agentaid.eval_result",
  Input: "agentaid.input",
  Output: "agentaid.output",
} as const;
