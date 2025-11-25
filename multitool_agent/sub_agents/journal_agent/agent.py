"""
Journal Agent - Saves and retrieves journal entries from the Vertex AI Memory Bank.
"""

from google.adk.agents import Agent
import vertexai
import os
from dotenv import load_dotenv
from typing import Dict
load_dotenv()

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION")
AGENT_ENGINE_ID = os.environ.get("AGENT_ENGINE_ID")
AGENT_ENGINE_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}"
DEFAULT_USER_ID = "journal_user_opaque_id"
APP_NAME = "aevio_memory_bank"  # Must match across save and retrieve
client = vertexai.Client(project=PROJECT_ID, location=LOCATION)

def get_journal_entry() -> str:
    """
    This function gets journal entries from the memory bank using the user's opaque id.
    Uses the same client as save_journal_entry to avoid API key conflicts.
    """
    try:
        # Use the same scope as save_journal_entry for consistency
        scope = {"app_name": APP_NAME, "user_id": DEFAULT_USER_ID}
        
        # Use client.agent_engines.memories.retrieve() - same client used for saving
        retrieved_memories = client.agent_engines.memories.retrieve(
            name=AGENT_ENGINE_NAME,
            scope=scope,
            similarity_search_params={"search_query": "*"}
        )
        
        # Process the retrieved memories
        formatted_entries = []
        for idx, retrieved_memory in enumerate(retrieved_memories, start=1):
            memory = retrieved_memory.memory
            fact = getattr(memory, "fact", None) or "[No content]"
            update_time = getattr(memory, "update_time", None)
            timestamp = update_time.isoformat() if update_time else "unknown timestamp"
            formatted_entries.append(f"Entry {idx} ({timestamp}):\n{fact}")
        
        if not formatted_entries:
            return "No journal entries found."
        
        return "\n\n".join(formatted_entries)
        
    except Exception as error:
        return f"Error fetching journal entries: {error}"

def save_journal_entry(entry: str) -> str:
    """
    This function saves a journal entry to the memory bank using two separate scopes:
    1. GenerateMemories: For intelligent, consolidated facts (runs asynchronously).
    2. CreateMemory: For raw, archival storage (runs synchronously).
    """
    
    # Ensure necessary context variables are available
    if not client or not AGENT_ENGINE_NAME:
        return "Error: Vertex AI Client or Agent Engine Name not initialized."
    
    # 1. Define the distinct scopes for separation [1-3]
    # Curated Facts: Used for agent interaction (consolidation enabled)
    # IMPORTANT: app_name must be included for retrieval to work correctly
    CURATED_FACTS_SCOPE: Dict[str, str] = {"app_name": APP_NAME, "user_id": DEFAULT_USER_ID}
    # Raw Archive: Used for static storage (bypasses consolidation)
    RAW_ARCHIVE_SCOPE: Dict[str, str] = {"app_name": APP_NAME, "user_id": DEFAULT_USER_ID, "data_type": "raw_archive"}
    
    curated_status = ""
    archive_status = ""

    # --- 1. GENERATE CURATED MEMORIES (Extraction + Consolidation) ---
    # This process is a long-running operation [4]. We run it asynchronously [5].
    try:
        # Prepare the journal entry as content events [6]
        events = [
            {
                "content": {
                    "role": "user",
                    "parts": [{"text": entry}]
                }
            }
        ]

        # Trigger GenerateMemories for extraction and consolidation [6, 7]
        client.agent_engines.memories.generate(
            name=AGENT_ENGINE_NAME,
            direct_contents_source={"events": events}, # Provide raw text as source [6]
            scope=CURATED_FACTS_SCOPE,
            config={"wait_for_completion": False} # Run asynchronously for production agents [5]
        )
        curated_status = "Curated facts generation triggered asynchronously."

    except Exception as e:
        curated_status = f"Error during curated memory generation: {e}"


    # --- 2. CREATE RAW ARCHIVE (Direct Storage) ---
    # This uploads the full text directly, bypassing extraction and consolidation [8].
    try:
        # Call CreateMemory [8, 9]
        client.agent_engines.memories.create(
            name=AGENT_ENGINE_NAME,
            fact=entry, # Store the full raw text as the fact [8]
            scope=RAW_ARCHIVE_SCOPE # Use the distinct archival scope [8]
        )
        archive_status = "Raw journal archive saved successfully (not consolidated)."

    except Exception as e:
        archive_status = f"Error during raw memory creation: {e}"

    return f"Journal entry saving complete. Curated status: {curated_status}. Archive status: {archive_status}"

journal_agent = Agent(
    name="journal_agent",
    model="gemini-2.5-flash",
    description="This agent is responsible for saving a journal entry to the memory bank.",
    instruction="You are a journal agent. You are responsible for saving a journal entry to the memory bank.",
    tools=[get_journal_entry, save_journal_entry],
)
