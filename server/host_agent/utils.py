import requests
from a2a_types import AgentCard

def get_agent_card(remote_agent_address: str) -> AgentCard:
  """Get the agent card."""
  try:
    agent_card = requests.get(
        f"{remote_agent_address}/.well-known/agent.json"
    )
  except Exception as e:
    print(f"Error getting agent card: {e}")
    return None
  return AgentCard(**agent_card.json())