import asyncio
import json
# from minimulllm.src.client import DeepSeek, DeepSeekToolUse

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
  # tool_manager.register(planner.planning)
  tool_manager.register(code_reviewer.review_code)
  tool_manager.register(task_reviewer.review_task)
  next_prompt = goal
  for i in range(max_steps):
    print(i)
    res = await coder.tool(next_prompt, tool_manager.tools)
    print(res)
    # if i % 5 == 3:
    #   res = await coder.tool("状況を整理して計画を建ててください。詰まっていたら大胆に計画を修正してください。計画はplaningで", tool_manager.tools)
    # else:
    #   res = await coder.tool(next_prompt, tool_manager.tools)
    #   print(res)
    function_calls = res.choices[0].message.tool_calls

    if function_calls is None:
      print(res.choices[0].message.content)
      # next_prompt = "function cannot call.If finish task call complete, not finish task call next function."
      next_prompt = input("指示を入力: ")
    else:
      for f in function_calls:
        print("実行する関数:")
        print(f.function.name)
        print("引数:")
        print(f.function.arguments)
        yN = input("実行しますか?(y)次の指示を:")
        if yN == "y":
          try:
            func_res = tool_manager.exec(f.function)
            print("結果:")
            print(func_res)
            if func_res == "COMPLETE":
              print("COMPLETE")
              return 
            print(f)
            coder.append_message({
                "role": "tool",
                "tool_call_id": f.id,
                "content": json.dumps(func_res)
            })
            next_prompt = f"please think next action."
            print(len(next_prompt))
          except Exception as e:
            print(e)
            coder.pop_message()
            next_prompt = f"Error following: {e}"
        else:
          next_prompt = yN


async def main():
  engineer = DeepSeekToolUse("deepseek-chat", TOP_LEVEL_SOFTWARE_ENGINEER_SYSTEM_PROMPT)
  engineer = OpenAIToolUse("gpt-4o", TOP_LEVEL_SOFTWARE_ENGINEER_SYSTEM_PROMPT)
  # qa_ds = DeepSeek("deepseek-chat", OPEN_INTERPRETER_SYSTEM_PROMPT)
  qa_ds = DeepSeekToolUse("o1", TOP_LEVEL_SOFTWARE_ENGINEER_SYSTEM_PROMPT)
  # o1_engineer = OpenAISync("o1", TOP_LEVEL_SOFTWARE_ENGINEER_SYSTEM_PROMPT)
  r1_engineer = DeepSeekSync("reasoner", TOP_LEVEL_SOFTWARE_ENGINEER_SYSTEM_PROMPT)

  def clip_string(string: str, max_length: int):
    if len(string) > max_length:
      return string[:max_length - 3] + "\n output is too long ..."
    return string

  reviewer = CodeReviewer(r1_engineer)
  goal = "I want to create a function that reads a file and returns the content as a string."
  res = await code_generate(engineer, reviewer, goal, 100)

if __name__ == "__main__":
  asyncio.run(main())