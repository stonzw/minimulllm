import asyncio
import logging
import json
import time
import argparse
from src.async_client import OpenAI
from src.prompt import TOP_LEVEL_SOFTWARE_ENGINEER_SYSTEM_PROMPT
from src.tools import file_write, file_read, explore_directory, search_in_files, complete, make_dirs
from src.function_call import LLMToolManager
from src.code_interpreter import CodeInterpreter

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

async def generate_and_execute_code(goal: str):
    logging.debug("Starting generate_and_execute_code with goal: %s", goal)
    # Initialize the LLM client with system prompt
    deep_seek_engineer = OpenAI("o3-mini", TOP_LEVEL_SOFTWARE_ENGINEER_SYSTEM_PROMPT)
    
    logging.debug("Initializing tool manager and registering available functions")
    tool_manager = LLMToolManager()
    tool_manager.register(file_write)
    tool_manager.register(file_read)
    tool_manager.register(explore_directory)
    tool_manager.register(search_in_files)
    tool_manager.register(complete)
    tool_manager.register(make_dirs)
    
    logging.debug("Initializing CodeInterpreter with registered tools")
    code_interpreter = CodeInterpreter(functions=tool_manager.functions)
    pre_execute_code = "state = {}"
    current_state = code_interpreter.parse_and_execute(pre_execute_code)
    
    # Define a structured prompt for code generation
    prompt = f"""You are tasked with generating executable Python code snippets to fulfill a specific goal using the CodeInterpreter system. The CodeInterpreter operates under the following guidelines:
1. Execution Environment:
   - Utilizes Python's InteractiveInterpreter.
   - Supports predefined tool functions registered for execution.
   - Maintains a "state" variable showing the current state of the execution.
   - If you complete the goal, set the "state" variable to "completed".

2. Code Execution Specifications:
   - Provide code snippets as independent operations.
   - Each snippet may manipulate or utilize the "state" object as needed.
   - Execute inputs using the `parse_and_execute` method.

3. Expected Execution Results:
   - Returns a dictionary containing:
     - "status": {"success", "error"}
     - "code": string of the executed code
     - "state": current state object
     - "message": error message if any

4. Response Format:
   - Return code snippets in JSON:
     {{
       "code_snippets": [
         "snippet_1",
         "snippet_2",
         ...
       ]
     }}
   - Make sure snippets are valid Python code ready for execution.

5. Execution Flow:
   - Each snippet execution requires prior human confirmation.
   - Aim to effectively achieve the specified goal with these snippets.

Please write code snippets to achieve the following goal: {goal}

## Available tools
{json.dumps(tool_manager.tools, indent=2, ensure_ascii=False)}

## Current state

already executed code:
{json.dumps(code_interpreter.history, indent=2, ensure_ascii=False)}
"""

    logging.debug("Requesting the LLM to generate code")
    response = await deep_seek_engineer.chat(prompt.strip())
    logging.debug("Raw LLM Response: %s", response)
    
    # Extract code snippets from response
    try:
        response_data = json.loads(response)
        code_snippets = response_data.get("code_snippets", [])
    except json.JSONDecodeError as e:
        logging.error("Failed to parse LLM response: %s", e)
        return

    logging.debug("Iterating and executing code snippets with user confirmation")
    while True:
      for code_snippet in code_snippets:
          logging.debug("Generated code snippet: %s", code_snippet)
          confirm = input("Do you want to execute this code snippet? (y/n): ")
          if confirm.lower() == 'y':
              logging.debug("Executing code snippet")
              code_result = code_interpreter.parse_and_execute(code_snippet)
              logging.debug("Execution result: %s", code_result)
              next_prompt = "Execution result: " + json.dumps(code_result, indent=2, ensure_ascii=False)
              if code_result == "completed":
                logging.debug("Goal completed")
                return
          else:
            next_prompt = input("Enter next instruction: ")
          logging.debug("Requesting the LLM with next prompt")
          response = await deep_seek_engineer.chat(next_prompt)
      try:
          response_data = json.loads(response)
          code_snippets = response_data.get("code_snippets", [])
      except json.JSONDecodeError as e:
          logging.error("Failed to parse LLM response: %s", e)
          return
      time.sleep(1)
        

async def main():
    parser = argparse.ArgumentParser(description="Execute code generated for a specific goal.")
    parser.add_argument('--goal', type=str, required=True, help='The goal to be achieved through code execution.')
    args = parser.parse_args()
    
    await generate_and_execute_code(args.goal)

if __name__ == "__main__":
    asyncio.run(main())
