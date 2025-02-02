import asyncio
import json
from src.client import DeepSeek as DeepSeekSync
from src.prompt import TOP_LEVEL_SOFTWARE_ENGINEER_SYSTEM_PROMPT
from src.type import Agent
from src.tools import explore_directory, search_in_files, file_read, file_write, complete, make_dirs, user_input, Planner, CodeReviewer, TaskReviewer
from src.function_call import LLMToolManager
from src.async_client import DeepSeekToolUse, OpenAIToolUse

def clip_string(string: str, max_length: int):
    if len(string) > max_length:
        return string[:max_length - 3] + "\n output is too long ..."
    return string

async def code_generate(coder: DeepSeekToolUse, planner: Planner, code_reviewer: CodeReviewer, task_reviewer: TaskReviewer, goal: str, max_steps: int):
    tool_manager = LLMToolManager()
    tool_manager.register(file_write)
    tool_manager.register(file_read)
    tool_manager.register(explore_directory)
    tool_manager.register(search_in_files)
    tool_manager.register(complete)
    tool_manager.register(make_dirs)
    tool_manager.register(user_input)
    tool_manager.register(code_reviewer.review_code)
    tool_manager.register(task_reviewer.review_task)
    next_prompt = goal
    for i in range(max_steps):
        print(f"Step {i + 1}/{max_steps}")
        res = await coder.tool(next_prompt, tool_manager.tools)
        message, function_calls = res

        if not function_calls:
            print("No function calls generated.")
            coder.pop_message()
            next_prompt = input("Please provide next instruction: ")
        else:
            for f in function_calls:
                print(f"Executing function: {f.function.name}")
                print(f"Arguments: {f.function.arguments}")
                confirmation = input("Execute this function? (y/n): ")
                if confirmation.lower() == 'y':
                    try:
                        func_res = tool_manager.exec(f.function)
                        print("Result:", clip_string(str(func_res), 1000))
                        if func_res == "COMPLETE":
                            print("Task completed successfully!")
                            return
                        coder.append_message({
                            "role": "tool",
                            "tool_call_id": f.id,
                            "content": json.dumps(func_res)
                        })
                        next_prompt = "Please determine the next action."
                    except Exception as e:
                        print(f"Error: {str(e)}")
                        coder.pop_message()
                        next_prompt = f"Error occurred: {str(e)}"
                else:
                    coder.pop_message()
                    next_prompt = input("Please provide next instruction: ")

async def main():
    # Initialize all required components
    engineer = DeepSeekToolUse("deepseek-chat", TOP_LEVEL_SOFTWARE_ENGINEER_SYSTEM_PROMPT)
    o3_mini_engineer = OpenAIToolUse("o3-mini", TOP_LEVEL_SOFTWARE_ENGINEER_SYSTEM_PROMPT)
    
    # Create instances of required collaborators
    planner = Planner(llm=DeepSeekSync("planner-model", TOP_LEVEL_SOFTWARE_ENGINEER_SYSTEM_PROMPT))
    code_reviewer = CodeReviewer(o3_mini_engineer)
    task_reviewer = TaskReviewer(llm=DeepSeekSync("task-reviewer-model", TOP_LEVEL_SOFTWARE_ENGINEER_SYSTEM_PROMPT))

    goal = "I want to create a function that reads a file and returns the content as a string."
    
    # Execute code generation with proper parameters
    await code_generate(
        coder=engineer,
        planner=planner,
        code_reviewer=code_reviewer,
        task_reviewer=task_reviewer,
        goal=goal,
        max_steps=100
    )

if __name__ == "__main__":
    asyncio.run(main())