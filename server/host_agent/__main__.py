import os
import click
import asyncio
from .adk_host_manager import ADKHostManager
from a2a_types import Message, TextPart
from dotenv import load_dotenv
load_dotenv()

@click.command()
@click.option("--agent", multiple=True, default=[
    ], help="Base URL of the A2A agent server. Use multiple times for multiple agents.")

def main(agent):
    agent_config = os.path.join(os.path.dirname(__file__), "agent_config.json")
    with open(agent_config, "r") as f:
        config = json.load(f)
    if config['model'].startswith('gemini'):
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key is None:
            raise ValueError("GOOGLE_API_KEY is not set")
    elif config['model'].startswith('openai'):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key is None:
            raise ValueError("OPENAI_API_KEY is not set")
    host_manager = ADKHostManager(api_key)
    for agent_url in agent:
        try:
            host_manager.register_agent(agent_url)
        except Exception as e:
            print(f"[Agent Register Error] {agent_url}: {e}")
            return  
    # Test scenario
    async def test_scenario():
        # Create conversation
        conversation = host_manager.create_conversation()
        print(f"Created conversation: {conversation.conversation_id}")

        print("Type your message and press Enter. Type 'exit' to quit.")
        while True:
            user_input = input("You: ")
            if user_input.strip().lower() in ("exit", "quit"):
                print("Exiting.")
                break

            await host_manager.process_message(Message(
                parts=[TextPart(text=user_input)],
                role="user",
                metadata={"conversation_id": conversation.conversation_id}
            ))

            # Print last agent message(s)
            print("Messages so far:")
            for m in host_manager._messages:
                print(f"- {m.parts[0].text if m.parts else '[no parts]'} (role: {m.role})")
    
    # Run the test scenario
    asyncio.run(test_scenario())

if __name__ == "__main__":
    main()