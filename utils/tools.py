from utils.dropbox_file_manager import download_file, download_file_with_size_limit, MAX_DOWNLOAD_SIZE, PARTIAL_DOWNLOAD_SIZE
from utils.dropbox_folder_manager import list_folder_complete
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

def check_file_contents(dropbox_path: str, select_user=None, max_size_bytes=PARTIAL_DOWNLOAD_SIZE) -> str:
    """
    Downloads a file from Dropbox, sends it to the OpenAI API with an appropriate prompt 
    based on file type (especially for Excel), and asks about its content.
    Returns the response from the API.
    Cleans up the downloaded file after use.
    Files larger than 5MB will not be downloaded.
    
    Args:
        dropbox_path (str): The path of the file in Dropbox
        select_user (str, optional): Team member ID to operate as
        max_size_bytes (int): Maximum file size to download (default: 1MB)
        
    Returns:
        str: API response with file content analysis or error message for oversized files
    """
    from utils.openai_api_call import ask_with_base64_file
    
    # Use size-limited download to prevent timeouts
    try:
        local_path, is_truncated, total_size, too_large = download_file_with_size_limit(
            dropbox_path, select_user=select_user, max_size_bytes=max_size_bytes
        )
        
        # Handle case when file is too large to download (>5MB)
        if too_large:
            size_mb = total_size / (1024 * 1024)
            max_size_mb = MAX_DOWNLOAD_SIZE / (1024 * 1024)
            return f"⚠️ This file is too large to process: {size_mb:.1f} MB exceeds the {max_size_mb:.0f} MB limit. Please try a smaller file or ask for basic metadata about this file instead."
        
        prompt = "What is in this file?"
        
        # Add information about truncation if needed
        if is_truncated:
            truncation_notice = f"NOTE: This file is {total_size/1024/1024:.1f} MB, but only the first {max_size_bytes/1024/1024:.1f} MB were analyzed due to size constraints."
            prompt = f"{prompt}\n\n{truncation_notice}"
            logger.warning(truncation_notice)
        
        # Check file extension for Excel files
        _, file_extension = os.path.splitext(local_path)
        if file_extension.lower() in ['.xlsx', '.xls']:
            excel_prompt = "This is an Excel spreadsheet. Please summarize its main content, key data tables, sheet names, or overall purpose."
            prompt = excel_prompt if not is_truncated else f"{excel_prompt}\n\n{truncation_notice}"
            
        try:
            response = ask_with_base64_file(local_path, prompt)
            
            # Add truncation notice to response if file was truncated
            if is_truncated:
                response += f"\n\n[NOTE: This file is {total_size/1024/1024:.1f} MB in total, but only the first {max_size_bytes/1024/1024:.1f} MB were analyzed due to size constraints.]"
        finally:
            try:
                os.remove(local_path)
                logger.info(f"Temporary file deleted: {local_path}")
            except Exception as e:
                logger.error(f"Error removing temporary file {local_path}: {e}")
                pass # Continue anyway
        return response
    
    except ValueError as e:
        # Handle the case where the file is too large
        if "too large to download" in str(e):
            return str(e)
        else:
            raise
    except Exception as e:
        logger.error(f"Error in check_file_contents: {e}")
        return f"Error processing file: {str(e)}"

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
