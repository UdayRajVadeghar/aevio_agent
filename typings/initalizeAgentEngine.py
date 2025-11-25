from google.adk.memory import VertexAiMemoryBankService
import vertexai
from vertexai import types as vertexai_types

client = vertexai.Client(
  project="PROJECT_ID",
  location="LOCATION"
)
# If you don't have an Agent Engine instance already, create an Agent Engine
# Memory Bank instance using the default configuration.
agent_engine = client.agent_engines.create(
    config=vertexai_types.AgentEngineConfig(display_name="aevio_memory_bank")
)


print(agent_engine.api_resource.name)

agent_engine_id = agent_engine.api_resource.name.split("/")[-1]

memory_service = VertexAiMemoryBankService(
    project="PROJECT_ID",
    location="LOCATION",
    agent_engine_id=agent_engine_id
)