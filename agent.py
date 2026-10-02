import anthropic
import json
from config import ANTHROPIC_API_KEY, MODEL, AGENT_NAME, MAX_TOKENS
from tools.file_tool import read_file, list_directory
from tools.search_tool import search_web

# Initialize the Anthropic client once when the agent starts
# This creates a persistent connection we reuse for every message
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Define the tools Claude can use
# This is the MCP layer — we describe each tool in a standard format
# Claude reads these descriptions to know WHAT tools exist and WHEN to use them
# It never sees the actual Python code — only these descriptions
TOOLS = [
    {
        "name": "read_file",
        "description": "Reads the contents of a file from the local filesystem. Use this when the user asks about a specific file or wants you to analyze something on their computer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to read, e.g. '~/resume.txt' or './notes.md'"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_directory",
        "description": "Lists all files and folders in a directory. Use this when the user wants to know what files exist in a location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path to list, e.g. '.' for current directory or '~/Documents'"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "search_web",
        "description": "Searches the web for current information. Use this when the user asks about recent events, needs facts you might not know, or wants to research something.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query, e.g. 'Meta SWE interview tips 2026'"
                }
            },
            "required": ["query"]
        }
    }
]

# Maps tool names (strings) to actual Python functions
# When Claude says "call read_file", we look it up here and run it
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_directory": list_directory,
    "search_web": search_web
}

def run_tool(tool_name: str, tool_input: dict) -> str:
    """
    Executes a tool by name with the given inputs.
    
    This is the bridge between Claude's decisions and real Python execution.
    Claude decides WHAT to call. This function actually RUNS it.
    
    Args:
        tool_name: The name of the tool to run
        tool_input: The arguments to pass to the tool
        
    Returns:
        The tool's output as a string
    """
    if tool_name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool '{tool_name}'"
    
    # Look up the function and call it with the provided arguments
    # **tool_input unpacks the dict as keyword arguments
    # e.g. {"path": "~/resume.txt"} becomes read_file(path="~/resume.txt")
    tool_function = TOOL_FUNCTIONS[tool_name]
    return tool_function(**tool_input)

def chat(user_message: str, conversation_history: list) -> tuple[str, list]:
    """
    Sends a message to Claude and handles the full agentic loop.
    
    The agentic loop works like this:
    1. Send message to Claude with available tools
    2. Claude responds — either with text OR a tool call
    3. If tool call: run the tool, send result back to Claude
    4. Claude responds again — repeat until Claude gives final text answer
    5. Return the final answer
    
    Args:
        user_message: What the user typed
        conversation_history: All previous messages (so Claude has context)
        
    Returns:
        Tuple of (Claude's response text, updated conversation history)
    """
    # Add the user's message to conversation history
    # We keep history so Claude remembers what was said earlier in the session
    conversation_history.append({
        "role": "user",
        "content": user_message
    })
    
    # The agentic loop — keeps running until Claude gives a final text response
    while True:
        # Send the conversation to Claude with our tool definitions
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=f"""You are {AGENT_NAME}, a helpful AI assistant that lives in the terminal.
You have access to tools that let you read files and search the web.
Be concise and direct. When you use a tool, explain what you found.
If the user asks about files, use list_directory first to see what exists.""",
            messages=conversation_history,
            tools=TOOLS
        )
        
        # Check why Claude stopped generating
        # "end_turn" = Claude finished with a text answer
        # "tool_use" = Claude wants to call a tool
        if response.stop_reason == "end_turn":
            # Extract the text from Claude's response
            assistant_message = response.content[0].text
            
            # Add Claude's response to history for next turn
            conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message, conversation_history
        
        elif response.stop_reason == "tool_use":
            # Claude wants to use one or more tools
            # Add Claude's full response to history (including the tool call)
            conversation_history.append({
                "role": "assistant",
                "content": response.content
            })
            
            # Process each tool call Claude requested
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"\n  🔧 Using tool: {block.name}({json.dumps(block.input)})")
                    
                    # Run the actual Python function
                    result = run_tool(block.name, block.input)
                    
                    # Format the result in the way Anthropic's API expects
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,  # Links result to the specific tool call
                        "content": result
                    })
            
            # Send tool results back to Claude so it can reason about them
            conversation_history.append({
                "role": "user",
                "content": tool_results
            })
            # Loop continues — Claude will now respond with either more tool calls or final answer
        
        else:
            # Unexpected stop reason — break to avoid infinite loop
            break
    
    return "I encountered an unexpected error.", conversation_history


def main():
    """
    The main entry point — starts the interactive CLI session.
    Runs a loop that takes user input and prints Claude's responses.
    """
    print(f"\n{'='*50}")
    print(f"  {AGENT_NAME} — Your AI Terminal Assistant")
    print(f"{'='*50}")
    print("  Commands: 'quit' or 'exit' to stop")
    print("  Try: 'list my files' or 'search for Meta SWE tips'")
    print(f"{'='*50}\n")
    
    # Conversation history persists across the session
    # This is what makes it feel like a real conversation, not isolated Q&A
    conversation_history = []
    
    while True:
        try:
            # Get input from the user
            # The '▶ ' is just a visual prompt so you know where to type
            user_input = input("▶  You: ").strip()
            
            # Skip empty input
            if not user_input:
                continue
            
            # Exit commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print(f"\n  Goodbye! 👋\n")
                break
            
            print(f"\n  {AGENT_NAME} is thinking...\n")
            
            # Send to Claude and get response
            response, conversation_history = chat(user_input, conversation_history)
            
            print(f"  {AGENT_NAME}: {response}\n")
            
        except KeyboardInterrupt:
            # Handles Ctrl+C gracefully instead of showing an ugly error
            print(f"\n\n  Goodbye! 👋\n")
            break


# This is standard Python — only run main() if this file is executed directly
# Not when it's imported by another file
if __name__ == "__main__":
    main()