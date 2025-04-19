import os
import json
from datetime import datetime
from openai.types.chat import ChatCompletionMessageToolCall

AGENT_PROMPT_PATH = os.path.join("agent", "agent_prompt.txt")
FOLDER_KNOWLEDGE_PATH = os.path.join("agent", "general_folder_knowledge.txt")
RUNNING_MEMORY_PATH = os.path.join("agent", "running_memory.txt")

def load_agent_prompt():
    prompt = ""
    # Load base prompt
    if os.path.exists(AGENT_PROMPT_PATH):
        with open(AGENT_PROMPT_PATH, "r") as f:
            prompt = f.read().strip()
    
    # Append folder knowledge if exists
    if os.path.exists(FOLDER_KNOWLEDGE_PATH):
        with open(FOLDER_KNOWLEDGE_PATH, "r") as f:
            knowledge = f.read().strip()
            if prompt: # Add newline separator if base prompt exists
                prompt += "\n\n" + knowledge
            else:
                prompt = knowledge
    
    # Append running memory if exists
    if os.path.exists(RUNNING_MEMORY_PATH) and os.path.getsize(RUNNING_MEMORY_PATH) > 0:
        with open(RUNNING_MEMORY_PATH, "r") as f:
            memory = f.read().strip()
            if memory:
                # Add the disclaimer before the memory content
                disclaimer = "Note: The following memories are from previous sessions. They might be helpful, but often will not be relevant to the current search. Use your judgment."
                memory_header = "### Accumulated Knowledge ###"
                # Combine disclaimer, header, and memory, ensuring proper spacing
                memory_section = f"\n\n{disclaimer}\n{memory_header}\n{memory}"

                if prompt:  # Append to existing prompt
                    prompt += memory_section
                else:
                    # If no base prompt, start with the memory section, removing leading newline
                    prompt = memory_section.lstrip()
    
    return prompt

from utils.openai_api_call import client, tools, handle_conversation

HISTORY_DIR = "history"
os.makedirs(HISTORY_DIR, exist_ok=True)

# ANSI escape codes for colors
USER_COLOR = "\033[92m"  # Bright Green
AGENT_COLOR = "\033[96m" # Bright Cyan
SYSTEM_COLOR = "\033[93m" # Yellow
RESET_COLOR = "\033[0m"

MODEL = "gpt-4.1"  # Per user instructions

# Custom JSON serializer function
def default_serializer(obj):
    if isinstance(obj, ChatCompletionMessageToolCall):
        # Convert the Pydantic model to a dictionary
        return obj.model_dump() 
    # Let the default encoder handle other types or raise an error
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

def save_conversation(history, session_id):
    path = os.path.join(HISTORY_DIR, f"{session_id}.json")
    try:
        with open(path, "w") as f:
            # Use the custom serializer with json.dump
            json.dump(history, f, indent=2, default=default_serializer)
    except TypeError as e:
        print(f"Error saving conversation: {e}")


def get_new_session_id():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    # Use SYSTEM_COLOR for initial messages
    print(f"{SYSTEM_COLOR}Welcome! Describe the file you're looking for in Dropbox (be as vague as you want):{RESET_COLOR}")
    # Use USER_COLOR for the user prompt indicator
    user_prompt = input(f"{USER_COLOR}User: {RESET_COLOR}")
    session_id = get_new_session_id()
    history = []

    # Add system prompt (now includes folder knowledge)
    system_prompt = load_agent_prompt()
    if system_prompt:
        history.append({"role": "system", "content": system_prompt})

    # Initial user message
    history.append({"role": "user", "content": user_prompt})

    found = False # Track if the agent thinks it found the file
    max_turns = 25
    turn = 0

    while turn < max_turns: # Loop primarily based on turns
        # Use the new conversation handler function
        prev_len = len(history)
        # handle_conversation returns the updated history and whether the *last* assistant message indicated finding the file
        history, current_turn_found = handle_conversation(history, model=MODEL) 
        found = current_turn_found # Update the overall found status
        
        # Save conversation history immediately after the API call and processing
        save_conversation(history, session_id)
        
        # Determine what to show to the user from the new messages
        new_messages = history[prev_len:]
        
        # Print only non-None assistant responses using AGENT_COLOR
        for msg in new_messages:
            if msg["role"] == "assistant" and msg.get("content") is not None:
                print(f"{AGENT_COLOR}Agent: {msg.get('content', '')}{RESET_COLOR}")
        
        # Check if max turns reached AFTER processing the turn using SYSTEM_COLOR
        if turn >= max_turns - 1:
            print(f"\n{SYSTEM_COLOR}Maximum conversation turns reached.{RESET_COLOR}")
            break
        
        # Always get user input unless max turns reached, use USER_COLOR
        user_input = input(f"{USER_COLOR}User (type 'exit' to end): {RESET_COLOR}")
        
        # Allow user to exit manually, use SYSTEM_COLOR for the message
        if user_input.lower() in ["exit", "quit", "stop"]:
            print(f"{SYSTEM_COLOR}Session ended by user.{RESET_COLOR}")
            break
            
        history.append({"role": "user", "content": user_input})
        
        turn += 1

    # Use SYSTEM_COLOR for the final message
    print(f"\n{SYSTEM_COLOR}Conversation saved to {os.path.join(HISTORY_DIR, session_id + '.json')}{RESET_COLOR}")

if __name__ == "__main__":
    main()
