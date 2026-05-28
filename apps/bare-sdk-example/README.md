# bare-sdk-example

Minimal agent loop using the Anthropic SDK directly + manual OpenTelemetry/GenAI instrumentation. Sends spans to AgentAid via the same ingestion path as the Pydantic-AI reference agent — proof of framework-agnostic ingestion.

Run (with the AgentAid server up at port 8000):

```
AGENTAID_ENDPOINT=http://localhost:8000/ingest \
  uv run python -m bare_sdk_example.example
```
