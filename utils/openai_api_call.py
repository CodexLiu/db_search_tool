from openai import OpenAI
import os
from pathlib import Path
import base64
from utils.tools import check_file_contents, list_folder_contents, store_important_memory, end_conversation
import json

# Get the parent directory of the current file
current_dir = Path(__file__).parent
env_path = current_dir.parent / '.env'

# Load environment variables from the .env file in the parent directory
from dotenv import load_dotenv
load_dotenv(env_path)

print("Loaded OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# OpenAI function calling tools array
tools = [
    {
        "type": "function",
        "function": {
            "name": "check_file_contents",
            "description": "Downloads a file from Dropbox and summarizes its content using the OpenAI API. Provides specific summaries for Excel files (.xlsx, .xls).",
            "parameters": {
                "type": "object",
                "properties": {
                    "dropbox_path": {"type": "string", "description": "The path to the file in Dropbox."},
                    "select_user": {"type": ["string", "null"], "description": "Team member ID to operate as. Optional."}
                },
                "required": ["dropbox_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_folder_contents",
            "description": "Lists all contents of a Dropbox folder given its path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dropbox_path": {"type": "string", "description": "The path to the folder in Dropbox to list."},
                    "select_user": {"type": ["string", "null"], "description": "Team member ID to operate as. Optional."},
                    "recursive": {"type": "boolean", "description": "Whether to list subfolders recursively. Optional.", "default": False}
                },
                "required": ["dropbox_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "store_important_memory",
            "description": "**Mandatory use.** Stores critical findings about Dropbox file structure or user-provided information. Call this tool: 1) After listing folder contents (summarize findings). 2) After receiving specific file details from the user (store the detail). 3) When identifying a likely file location. 4) When a search successfully concludes (store the final path). 5) When a search fails (summarize attempts). This builds essential long-term knowledge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory": {"type": "string", "description": "The important information to store."}
                },
                "required": ["memory"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "end_conversation",
            "description": "Call this ONLY when the user confirms the task is complete to signal the end of the conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Brief reason for ending (e.g., 'User confirmed file found')."}
                },
                "required": ["reason"]
            }
        }
    }
]

def ask_with_base64_file(file_path: str, prompt: str, model: str = "gpt-4.1") -> str:
    """
    Sends a file (as base64) and a prompt to the OpenAI API and returns the response text.
    Args:
        file_path (str): Path to the file to send.
        prompt (str): The prompt/question to ask about the file.
        model (str): The model to use (default: "gpt-4.1").
    Returns:
        str: The response from the model.
    """
    with open(file_path, "rb") as f:
        data = f.read()
    base64_string = base64.b64encode(data).decode("utf-8")

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "filename": os.path.basename(file_path),
                        "file_data": f"data:application/pdf;base64,{base64_string}",
                    },
                    {
                        "type": "input_text",
                        "text": prompt,
                    },
                ],
            },
        ]
    )
    return response.output_text

def handle_conversation(history, model="gpt-4.1"):
    """
    Handles a full turn of conversation with the OpenAI API, including potential nested tool calls.

    Args:
        history (list): The conversation history *before* this turn.
        model (str): The model to use for the API calls.

    Returns:
        tuple: (updated_history, should_end)
            - updated_history: The history *after* this full turn.
            - should_end: Boolean indicating if the `end_conversation` tool was called.
    """
    current_history = list(history) # Work on a copy
    should_end = False # Flag to signal conversation end

    while True: # Loop to handle potential sequences of tool calls
        # Make the API call
        response = client.chat.completions.create(
            model=model,
            messages=current_history,
            tools=tools,
            tool_choice="auto",
            max_tokens=2048,
        )
        msg = response.choices[0].message

        # Append the assistant's response message.
        assistant_message = {"role": msg.role}
        if msg.tool_calls:
            assistant_message["content"] = None
            # Convert tool calls to dicts for JSON serialization later
            assistant_message["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls] 
        else:
            assistant_message["content"] = msg.content or ""
        current_history.append(assistant_message)

        # If there are no tool calls, this turn is over.
        if not msg.tool_calls:
            break # Exit the while loop

        # --- Tool Call Execution --- 
        # If we reach here, msg.tool_calls is not empty.
        tool_calls_to_process = msg.tool_calls # Use the actual objects here
        
        for tool_call in tool_calls_to_process:
            tool_name = tool_call.function.name
            tool_call_id = tool_call.id
            args = json.loads(tool_call.function.arguments)
            tool_result = ""

            try:
                if tool_name == "list_folder_contents":
                    entries = list_folder_contents(**args)
                    summary = f"Folder '{args.get('dropbox_path','')}' contains: " + ", ".join([
                        f"[{e.__class__.__name__.replace('Metadata','')}] {getattr(e, 'name', 'Unknown')}" for e in entries
                    ])
                    tool_result = summary
                elif tool_name == "check_file_contents":
                    tool_result = check_file_contents(**args)
                elif tool_name == "store_important_memory":
                    tool_result = store_important_memory(**args)
                elif tool_name == "end_conversation":
                    tool_result = end_conversation(**args)
                    should_end = True # Set the flag to end the conversation
                else:
                    tool_result = f"Tool '{tool_name}' not implemented."
            except Exception as e:
                # print(f"Error executing tool {tool_name}: {e}")
                tool_result = f"Error executing tool {tool_name}: {e}"

            # Append tool result message
            current_history.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": str(tool_result) # Ensure content is a string
            })
        
        # After processing all tool calls for this step, 
        # loop back to call the API again with the tool results included.
        # The loop continues until the API responds without tool calls.
        
    return current_history, should_end # Return the end flag

