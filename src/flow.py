import subprocess
from typing import List, Dict
from .client import CodeGenerator
from .type import Code, Agent

class CodeInterpreterFlow:
    @staticmethod
    def get_next_prompt(response: Code) -> str:
        """
        response の内容に応じて次のプロンプト文字列を生成する。
        (副作用: input や subprocess.run を行う)
        """
        # action が "wait" なら、ユーザから追加入力を受け取りたいケース
        if response.action == "wait":
            # 先にエージェントの回答 (response.answer) があるなら表示
            if response.answer:
                print("Agent:", response.answer)
            return input("次の指示を入力してください: ")

        # action が "code" の場合は、response.code を bash として実行し、その結果を返す
        if response.action == "code" and response.language == "bash":
            cmd = response.code
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.stderr:
                return "実行結果です。\n" + result.stderr
            return "実行結果です。\n" + result.stdout

        # 上記以外の場合 (action が "answer" 等) は単純に answer を返す
        return response.answer

    @staticmethod
    def run(agent: CodeGenerator, purpose: str) -> str:
        """
        フロー全体を制御する静的メソッド。
        agent, purpose はすべて引数で受け取り、内部状態を持たない。
        """
        # はじめに agent に問い合わせて初回のレスポンスを取得
        response = agent.code(purpose)

        while True:
            # 生成されたコード (response.code) があれば表示しておく
            if response.code:
                print("生成されたコード:")
                print(response.code)

                # （コード実行 or 次に進む）か確認する
                # 「コードを実行してよいですか？」や「次の指示に進みますか？」など
                yN = input("次へ進みますか？（y/N）: ")
                if yN.upper() != "Y":
                    print("フローを終了します。")
                    break
            elif response.action == "complete":
                print("完了しました:", response.answer)
                break
            else:
                print("Agent:", response.answer)
                print("response", response)
                break


            # 次の問い合わせ内容を生成
            next_prompt = CodeInterpreterFlow.get_next_prompt(response)

            # ここで次の問い合わせを agent に投げて、新たな response を得る
            response = agent.code(next_prompt)
        return response.model_dump()


def chat_prompts(agent, prompts):
    for prompt in prompts:
        _ = agent.chat(prompt)

def flow(agents: List[Agent], prompt: str) -> List[str]:
    """
    複数のエージェントに対して、それぞれのプロンプトを順番に投げる。
    """
    res = agents[0].chat(prompt)
    for agent in agents[1:]:
        res = agent.chat(res)
    return res

class SelfRefineFlow:
    @staticmethod
    def run(agent: Agent, purpose: str, improve_prompt: str, improve_count: int) -> str:
        """
        SelfRefineFlow のフロー（静的メソッド版）。
        """
        # 最初に purpose を問い合わせ
        agent.chat(purpose)
        # improve_count 回、improve_prompt を投げる
        return chat_prompts(agent, improve_count * [improve_prompt])

class TreeFlow:
    @staticmethod
    def merge_answers(answers: List[str], roles: List[str]) -> str:
        """
        回答を合成する静的メソッド。
        """
        return "\n\n\n".join([ f"{role}の回答\n" + ans for ans, role in zip(answers,roles)])

    @staticmethod
    def run(commander:Agent, agents: Dict[str, Agent], manager:Agent, purpose) -> str:
        """
        TreeFlow のフロー（静的メソッド版）。
        """
        # commander に最初の目的を問い合わせ
        response = commander.chat(purpose)
        answers = []
        roles = []
        # 全エージェントに対して、前の応答を入力としてチャットさせる
        for role, agent in agents.items():
            agent.chat(response)
            response = agent._messages[-1]["content"]
            answers.append(response)
            roles.append(role)
        # まとめた回答を合成
        next_prompt = TreeFlow.merge_answers(answers, roles)
        # manager に渡して終了
        return manager.chat(next_prompt)