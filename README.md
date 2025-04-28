# Dropbox Search Tool

This project provides a conversational AI agent capable of searching your Dropbox files based on natural language queries. It can be interacted with directly via the command line or through a Slack bot integration.

## Features

*   **Natural Language Search:** Describe the file you're looking for, even vaguely, and the agent will try to find it in your Dropbox.
*   **Conversational Interaction:** Engage in a dialogue with the agent to refine your search or ask follow-up questions.
*   **Slack Integration:** Interact with the agent directly within your Slack workspace via DMs or mentions.
*   **Command-Line Interface:** Run the agent locally for direct interaction.
*   **Contextual Memory:** The agent maintains a running memory (see `agent/running_memory.txt`) to potentially improve responses over time, though its relevance may vary between sessions.

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd db_search_tool
    ```
2.  **Create a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate # On Windows use `venv\Scripts\activate`
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Environment Variables:**
    *   Rename `example.env` to `.env`.
    *   Fill in the required API keys and tokens in the `.env` file.

5.  **Dropbox App Setup:**
    *   Create a new Dropbox App on the [Dropbox App Console](https://www.dropbox.com/developers/apps).
    *   Choose "Scoped access" and select the following permissions (scopes) under the "Permissions" tab:
        *   `account_info.read`
        *   `files.content.read`
        *   `sharing.read`
    *   Generate an access token under the "OAuth 2" section and add it to your `.env` file as `DROPBOX_ACCESS_TOKEN`.
    *   Refer to the official Dropbox API documentation for detailed steps.

6.  **Slack Bot Setup:**
    *   Create a new Slack App on the [Slack API Website](https://api.slack.com/apps).
    *   **Bot Token:**
        *   Navigate to "OAuth & Permissions" in the sidebar.
        *   Add the following Bot Token Scopes:
            *   `app_mentions:read`
            *   `chat:write`
            *   `im:history`
            *   `im:read`
            *   `im:write`
        *   Install the app to your workspace.
        *   Copy the "Bot User OAuth Token" (starts with `xoxb-`) and add it to your `.env` file as `SLACK_BOT_TOKEN`.
    *   **App Token (for Socket Mode):**
        *   Navigate to "Basic Information" in the sidebar.
        *   Scroll down to "App-Level Tokens" and generate a new token.
        *   Give it a name (e.g., `socket-mode-token`) and add the `connections:write` scope.
        *   Copy the generated token (starts with `xapp-`) and add it to your `.env` file as `SLACK_APP_TOKEN`.
    *   **Enable Socket Mode:**
        *   Navigate to "Socket Mode" in the sidebar and enable it.
    *   **Enable Events:**
        *   Navigate to "Event Subscriptions" and enable events.
        *   Subscribe to the `app_mention` and `message.im` bot events under "Subscribe to bot events".
    *   Refer to the official Slack API documentation for detailed steps.

## Usage

### Command Line

Run the main agent directly:

```bash
source venv/bin/activate # Make sure your venv is active
python main_agent.py
```

Follow the prompts to interact with the agent.

### Slack Bot

Run the Slack bot script:

```bash
source venv/bin/activate # Make sure your venv is active
python slack_bot.py
```

The bot will connect to Slack using Socket Mode. You can then:

*   **DM the bot:** Send it a direct message with your search query.
*   **Mention the bot:** Mention the bot (`@your_bot_name`) in any channel it has been added to, followed by your query.

The bot maintains separate conversation histories for each DM channel and for each user+channel combination where it's mentioned.

## Project Structure Overview

*   `main_agent.py`: Entry point for the command-line interaction. Handles loading the prompt, managing the conversation history, and interacting with the OpenAI API via `utils.openai_api_call`.
*   `slack_bot.py`: Runs the Slack bot using `slack_bolt` and Socket Mode. Handles incoming Slack events (DMs, mentions), manages conversation state per user/channel, and interfaces with the core agent logic from `main_agent.py` and `utils.openai_api_call`.
*   `agent/`:
    *   `agent_prompt.txt`: The base system prompt for the AI agent.
    *   `general_folder_knowledge.txt`: Optional additional context about the project structure provided to the agent.
    *   `running_memory.txt`: Stores accumulated knowledge snippets from previous interactions (use with caution, may not always be relevant).
*   `utils/`:
    *   `openai_api_call.py`: (Assumed) Contains functions for making calls to the OpenAI API, defining tools (like Dropbox search), and handling the conversation flow including tool calls.
*   `history/`: Stores JSON logs of conversations, named by session ID.
*   `requirements.txt`: Python dependencies.
*   `.env`: (You create this from `example.env`) Stores your API keys and tokens.
*   `README.md`: This file.
*   `example.env`: Template for the `.env` file. 