import os
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from threading import Thread
import time

# Load environment variables from .env file
load_dotenv()

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN") # Socket Mode requires an App Token

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import necessary functions from our agent (adjust path if needed)
# Assuming utils and agent folders are accessible from where slack_bot.py is run
try:
    from utils.openai_api_call import handle_conversation, tools # Assuming tools might be needed directly later
    from main_agent import load_agent_prompt, save_conversation, get_new_session_id
    logger.info("Successfully imported agent functions.")
except ImportError as e:
    logger.error(f"Error importing agent functions: {e}. Make sure PYTHONPATH is set correctly or files are in the right place.")
    # Exit or handle error appropriately if imports fail
    exit(1)

# Initializes your app with your bot token
app = App(token=SLACK_BOT_TOKEN)

# Dictionary to store conversation states {channel_id_user_id: {'history': [], 'session_id': ''}}
# Using channel_id_user_id to support concurrent conversations in different channels/DMs by the same user
conversation_states = {}

# --- Event Handlers ---

@app.event("app_mention")
def handle_app_mention_events(body, say, logger):
    """Handles mentions (@botname) in channels."""
    event = body.get("event", {})
    user_id = event.get("user")
    channel_id = event.get("channel")
    text = event.get("text", "").strip()
    # Remove the mention itself from the text
    bot_user_id = body.get("authorizations", [{}])[0].get("user_id", "")
    user_input = text.replace(f"<@{bot_user_id}>", "").strip()
    
    if not user_id or not channel_id:
        logger.error("Could not get user_id or channel_id from mention event.")
        return

    thread_ts = event.get("ts") # Use the timestamp of the mention as the thread identifier

    logger.info(f"Received mention from user {user_id} in channel {channel_id}: {user_input}")
    
    # Use channel_id + user_id as a unique key for state
    state_key = f"{channel_id}_{user_id}"
    
    process_message(state_key, user_input, say, thread_ts)


@app.event("message")
def handle_message_events(body, say, logger):
    """Handles direct messages to the bot."""
    event = body.get("event", {})
    
    # Ignore messages from bots, message changes, and non-IM messages
    if event.get("bot_id") or event.get("subtype") == "message_changed" or event.get("channel_type") != "im":
        return

    user_id = event.get("user")
    channel_id = event.get("channel") # In DMs, this is the DM channel ID
    user_input = event.get("text", "").strip()
    
    if not user_id or not channel_id:
        logger.error("Could not get user_id or channel_id from message event.")
        return

    logger.info(f"Received DM from user {user_id}: {user_input}")
    
    # Use channel_id + user_id as the key (channel_id is the DM channel ID here)
    state_key = f"{channel_id}_{user_id}"
    # DMs don't have threads in the same way, so we don't pass thread_ts to say
    process_message(state_key, user_input, say) 

def process_message(state_key, user_input, say_func, thread_ts=None):
    """Processes incoming user messages, manages state, and calls the agent."""
    global conversation_states
    
    if state_key not in conversation_states:
        # Start a new conversation
        logger.info(f"Starting new conversation for state_key: {state_key}")
        session_id = get_new_session_id()
        system_prompt = load_agent_prompt()
        history = []
        if system_prompt:
            history.append({"role": "system", "content": system_prompt})
        history.append({"role": "user", "content": user_input})
        conversation_states[state_key] = {"history": history, "session_id": session_id}
    else:
        # Continue existing conversation
        logger.info(f"Continuing conversation for state_key: {state_key}")
        conversation_states[state_key]["history"].append({"role": "user", "content": user_input})

    current_state = conversation_states[state_key]
    history_to_send = current_state["history"]
    session_id = current_state["session_id"]

    try:
        # Add a thinking message
        thinking_message = "Thinking..."
        if thread_ts:
            say_func(text=thinking_message, thread_ts=thread_ts)
        else:
             say_func(text=thinking_message)

        # Run API call in a separate thread to avoid blocking Slack event loop
        updated_history, should_end = None, False
        
        def run_handle_conversation():
            nonlocal updated_history, should_end
            # NOTE: Ensure handle_conversation and its dependencies (API calls, etc.) are thread-safe
            # or consider using a queue/worker pattern for more complex scenarios.
            # For now, assuming OpenAI client and file operations are reasonably safe.
            updated_history, should_end = handle_conversation(history_to_send, model="gpt-4.1") # Use configured model
        
        thread = Thread(target=run_handle_conversation)
        thread.start()
        thread.join(timeout=300) # Wait for completion, adjust timeout as needed (Slack needs response < 3s for ack)

        if updated_history is None:
             raise TimeoutError("Agent response timed out.")


        current_state["history"] = updated_history # Update history in state
        
        # Extract the latest assistant response(s) to send back
        assistant_responses = [msg.get("content") for msg in updated_history if msg["role"] == "assistant" and msg.get("content")]
        response_text = "\n".join(assistant_responses).strip() if assistant_responses else "Sorry, I encountered an issue." # Default if no content

        if thread_ts:
             say_func(text=response_text, thread_ts=thread_ts)
        else:
            say_func(text=response_text)

        # Save conversation
        save_conversation(current_state["history"], session_id)

        if should_end:
            logger.info(f"Conversation ended for state_key: {state_key}. Agent signaled completion.")
            final_message = "Job Complete! Ready for a new request."
            if thread_ts:
                say_func(text=final_message, thread_ts=thread_ts)
            else:
                say_func(text=final_message)
            del conversation_states[state_key] # Clear state for next interaction

    except Exception as e:
        logger.error(f"Error processing message for {state_key}: {e}", exc_info=True)
        error_message = f"Sorry, an error occurred: {e}"
        if thread_ts:
            say_func(text=error_message, thread_ts=thread_ts)
        else:
            say_func(text=error_message)
        # Optionally clear state on error or handle differently
        if state_key in conversation_states:
            del conversation_states[state_key]


# --- Start the App ---
if __name__ == "__main__":
    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        logger.error("Missing SLACK_BOT_TOKEN or SLACK_APP_TOKEN in environment variables.")
    else:
        logger.info("Starting Slack Bolt app in Socket Mode...")
        # SocketModeHandler starts the app listening for events
        # It requires an App Token (SLACK_APP_TOKEN) starting with xapp-
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        handler.start() 