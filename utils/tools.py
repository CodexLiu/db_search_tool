from utils.dropbox_file_manager import download_file
from utils.dropbox_folder_manager import list_folder_complete
import os

def check_file_contents(dropbox_path: str, select_user=None) -> str:
    """
    Downloads a file from Dropbox, sends it to the OpenAI API with an appropriate prompt 
    based on file type (especially for Excel), and asks about its content.
    Returns the response from the API.
    Cleans up the downloaded file after use.
    """
    from utils.openai_api_call import ask_with_base64_file
    local_path = download_file(dropbox_path, select_user=select_user)
    prompt = "What is in this file?"
    
    # Check file extension for Excel files
    _, file_extension = os.path.splitext(local_path)
    if file_extension.lower() in ['.xlsx', '.xls']:
        prompt = "This is an Excel spreadsheet. Please summarize its main content, key data tables, sheet names, or overall purpose."
        
    try:
        response = ask_with_base64_file(local_path, prompt)
    finally:
        try:
            os.remove(local_path)
        except Exception as e:
            print(f"Error removing temporary file {local_path}: {e}") # Added error logging
            pass # Continue anyway
    return response

def list_folder_contents(dropbox_path: str, select_user=None, **kwargs):
    """
    Lists all contents of a Dropbox folder given its path.
    Args:
        dropbox_path (str): The path to the folder in Dropbox to list.
        select_user (str, optional): Team member ID to operate as. Defaults to None (admin context).
        **kwargs: Additional arguments for Dropbox listing (e.g., recursive=True).
    Returns:
        list: List of dropbox.files.Metadata entries in the folder.
    """
    return list_folder_complete(dropbox_path, select_user=select_user, **kwargs)

def store_important_memory(memory: str) -> str:
    """
    Stores important information in the running memory file that will be included in the system prompt.
    Use this tool frequently to record what you learn about the file structure, especially:
    
    - After exploring a folder structure and learning its organization
    - At the END of a search (successful or not) to summarize what you learned about file locations
    - When discovering patterns in the user's file organization
    - After any extensive search, even if unsuccessful, record the paths explored
    - When learning about specific file types or naming conventions the user employs
    - **Whenever the user provides specific information in response to your questions (e.g., file type, keywords, project context), store this as a standalone memory.**
    
    This information will be available in future conversations to help with file searches.
    
    Args:
        memory (str): The important information to store.
        
    Returns:
        str: Confirmation message.
    """
    memory_file = os.path.join("agent", "running_memory.txt")
    
    # Create directories if they don't exist
    os.makedirs(os.path.dirname(memory_file), exist_ok=True)
    
    # Read existing memories to avoid duplicates
    existing_memories = []
    if os.path.exists(memory_file) and os.path.getsize(memory_file) > 0:
        with open(memory_file, "r") as f:
            existing_memories = f.read().strip().split("\n")
    
    # Add timestamp to the memory
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_memory = f"[{timestamp}] {memory}"
    
    # Only add if not duplicate
    if formatted_memory not in existing_memories:
        with open(memory_file, "a") as f:
            if existing_memories:
                f.write("\n")
            f.write(formatted_memory)
        return f"Memory stored: {memory}"
    else:
        return f"Memory already exists: {memory}"

def end_conversation(reason: str) -> str:
    """
    Call this tool **ONLY** after the user has explicitly confirmed that the primary task is complete 
    and that the conversation should end. Do NOT call this just because you think the task is done;
    wait for the user's explicit confirmation.
    
    Args:
        reason (str): A brief explanation why the conversation is ending (e.g., "User confirmed file found and task complete.").
    
    Returns:
        str: A confirmation message indicating the end signal was received.
    """
    print(f"Ending conversation because: {reason}") # Optional: Log the reason
    return "Conversation end signal received."
