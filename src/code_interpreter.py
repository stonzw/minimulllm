from typing import Callable, Dict, Any
from code import InteractiveInterpreter

class CodeInterpreter:
    """
    A minimal code agent that executes tool calls formulated in code format.
    This agent executes code snippets independently without state persistence.
    """
    def __init__(self, functions: Dict[str, Callable]):
        self.interpreter = InteractiveInterpreter()
        for name, func in functions.items():
            self.interpreter.locals[name] = func
        self.history = []  # To store the executed code and outputs

    def parse_and_execute(self, code: str) -> Any:
        """
        Parses and executes the given code independently.

        Args:
            code (str): Code input representing logic and tool usage.

        Returns:
            Any: A dictionary containing a status message, any printed output, and state changes.
        """
        complete_code = code.strip()
        try:
            self.interpreter.runcode(complete_code)
            result = {
                "status": "success",
                "code": complete_code,
                "state": self.interpreter.locals["state"],
            }
        except Exception as e:
            result = {
                "status": "error",
                "code": complete_code,
                "state": self.interpreter.locals["state"],
                "message": str(e),
            }
        self.history.append(result)
        return result
if __name__ == "__main__":
    from function_call import LLMToolManager
    # Example initial tools setup for the agent
    def multiply_by_two(x: int) -> int:
        """
        xを2倍して返すツール関数です。

        Args:
            x (int): 整数x

        Returns:
            int: x * 2の結果
        """
        return x * 2

    def addition_tool_function(a: int, b: int) -> int:
        """
        aとbを足して返すツール関数です。

        Args:
            a (int): 整数a
            b (int): 整数b

        Returns:
            int: a + bの結果
        """
        return a + b

    tool_manager = LLMToolManager()
    tool_manager.register(multiply_by_two)
    tool_manager.register(addition_tool_function)

    # Initialize the agent with predefined tools
    agent = CodeInterpreter(functions=tool_manager.functions)

    # Example of agent receiving a code snippet to execute
    tool_commands = [
        "state = {}",
        "result1 = multiply_by_two(5)",
        "state['result1'] = result1",
        "result2 = addition_tool_function(result1, 10)",
        "state['result2'] = result2",
        "final_result = multiply_by_two(result2)",
        "state['final_result'] = final_result",
        "print(final_result)"
    ]
    for tool_command in tool_commands:
        result = agent.parse_and_execute(tool_command)
        print(result)
