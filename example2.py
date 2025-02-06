import asyncio
import json
import os
import openai
from src.client import DeepSeek as DeepSeekSync
from src.client import OpenAI as OpenAISync
from src.prompt import TOP_LEVEL_SOFTWARE_ENGINEER_SYSTEM_PROMPT
from src.type import Agent
from src.tools import explore_directory, search_in_files, file_read, file_write, make_dirs, complete
from src.function_call import LLMToolManager
from src.async_client import DeepSeekToolUse, OpenAIToolUse

"""
コードエージェント:
  - DynaSaurの方針に従い、あらかじめ定義したツールセット（固定的な関数呼び出し）だけでなく、
    必要に応じて新しいコード（Python関数）を生成して実行し、
    その結果を再利用できるようにする。
  - 細かな仕組みは環境によって異なるが、ここでは一例として、
    生成されたコードを動的に実行するためのexecを用いる例を示す。
  - 実際には、セキュリティ上の理由から安全なコンテナ環境で実行するなどの工夫が望ましい。
"""

def clip_string(string: str, max_length: int):
    if len(string) > max_length:
        return string[:max_length - 3] + "\n output is too long ..."
    return string

class DynamicCodeRegistry:
    """
    生成したコード(関数)を登録し再利用する仕組みを簡易的に表現。
    実際はDockerなどでサンドボックス化した上で連携することが推奨される。
    """
    def __init__(self):
        self.functions = {}  # {関数名: 関数の文字列定義}

    def add_function(self, func_name: str, func_code: str):
        self.functions[func_name] = func_code

    def get_function_names(self):
        return list(self.functions.keys())

    def execute_function(self, func_name: str, *args, **kwargs):
        """動的に登録された関数をexecで実行する例。"""
        if func_name not in self.functions:
            return f"関数 {func_name} は未登録です。"
        code_str = self.functions[func_name]

        # 安全のため、ここではexecを直接使わず、コンテナや専用の環境で実行する想定。
        try:
            # 関数を一時モジュールのようにして実行し、戻り値を取得する簡易例
            local_env = {}
            exec(code_str, {}, local_env)
            if func_name in local_env:
                return local_env[func_name](*args, **kwargs)
            else:
                return f"関数 {func_name} が見つかりません。"
        except Exception as e:
            return f"関数実行中にエラーが発生しました: {e}"

async def code_agent_execute(coder, tool_manager: LLMToolManager, code_registry: DynamicCodeRegistry, goal: str, max_steps: int):
    """
    コードエージェント版:
      1. goalをもとにモデルに問い合わせ
      2. 返信中に "新しいコード" として関数定義があったら DynamicCodeRegistry に登録
      3. 必要に応じて登録された関数を再利用
    """
    next_prompt = goal
    for i in range(max_steps):
        print(f"==== Step: {i} ====")
        res = await coder.tool(next_prompt, tool_manager.tools)
        message, function_calls = res
        print("LLM応答:")
        print(message)

        # もし、新しいコード(新関数)を文字列として埋め込んでいる場合
        # ここでは簡単に "def 関数名(〜): .." という部分を抽出してみる
        # 実際にはもう少しパーサーなどを用いた適切な処理が望ましい
        if "def " in message:
            # 例: def sample_func(x): return x+1
            # 簡単に正規表現などで拾い上げる
            import re
            pattern = r"(def\s+[\w_]+\(.*?\):[\s\S]+?(?=\ndef|$))"
            found_funcs = re.findall(pattern, message)
            for f_def in found_funcs:
                # 関数名を抜き出し、DynamicCodeRegistryに登録
                head = f_def.split("\n")[0]
                # たとえば: "def sample_func(x):"
                fname = head.split("(")[0].replace("def", "").strip()
                code_registry.add_function(fname, f_def)
                print(f"新しい関数 {fname} を登録しました。")

        # function_callsがある場合はツール呼び出し
        # ただし動的関数実行も含む
        if function_calls is None:
            # 次の指示を受け付ける想定
            # (ここでは自動化のためにダミーの継続指示を生成)
            next_prompt = "次にどうしますか？用途に合った関数を試してください。"
        else:
            for f_call in function_calls:
                func_name = f_call.function.name
                func_args = f_call.function.arguments
                print(f"実行する関数: {func_name}")
                print(f"引数: {func_args}")

                # DynamicCodeRegistry内にある関数かどうかを確認
                if func_name in code_registry.functions:
                    # 動的関数の実行
                    res = code_registry.execute_function(func_name, **func_args)
                    print("実行結果:", res)
                    # 実行結果をLLMにも渡す
                    coder.append_message({
                        "role": "tool",
                        "tool_call_id": f_call.id,
                        "content": json.dumps(str(res))
                    })
                    next_prompt = "上記の結果を踏まえて次のアクションを考えてください。"
                else:
                    # 通常の既存ツールはLLMToolManagerに実装済みとする
                    try:
                        func_res = tool_manager.exec(f_call.function)
                        print("実行結果:")
                        print(func_res)
                        if func_res == "COMPLETE":
                            print("COMPLETE")
                            return
                        coder.append_message({
                            "role": "tool",
                            "tool_call_id": f_call.id,
                            "content": json.dumps(func_res)
                        })
                        next_prompt = "上記の結果を踏まえて次のアクションを考えてください。"
                    except Exception as e:
                        print("ツール実行時エラー:", e)
                        coder.pop_message()
                        next_prompt = f"Error following: {e}"

async def main():
    # 適当なエンジニアエージェント
    engineer = OpenAIToolUse("gpt-4o", TOP_LEVEL_SOFTWARE_ENGINEER_SYSTEM_PROMPT)
    
    tool_manager = LLMToolManager()
    # 固定ツールを登録(DynaSaurにおける外部ツール)
    tool_manager.register(file_write)
    tool_manager.register(file_read)
    tool_manager.register(explore_directory)
    tool_manager.register(search_in_files)
    tool_manager.register(complete)
    tool_manager.register(make_dirs)

    # コードを動的に登録・実行するためのレジストリ
    code_registry = DynamicCodeRegistry()

    # サンプルのゴール
    goal = "Excelファイルを読み込み、特定の処理をして結果を得たい。必要に応じてPython関数を作りながら進めてください。"

    await code_agent_execute(
        coder=engineer,
        tool_manager=tool_manager,
        code_registry=code_registry,
        goal=goal,
        max_steps=10
    )


if __name__ == "__main__":
    asyncio.run(main())