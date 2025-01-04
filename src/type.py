from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Optional, List, Any

class Code(BaseModel):
    answer: str = Field(description="answer.")
    action: str = Field(description="action is wait or code or complete.")
    code: Optional[str] = Field(description="if execute code.write code to execute.code only.")
    language: Optional[str] = Field(description="The language of the code.python or bash.")

class Message(BaseModel):
    """標準化されたメッセージ型"""
    role: str = Field(description="メッセージの役割 (system/user/assistant)")
    content: str = Field(description="メッセージの内容")
    raw: Optional[Any] = Field(
        default=None, 
        description="raw message data (e.g. OpenAI API response)"
    )


class Agent(ABC):
    """
    全てのエージェントクラスが実装すべきインターフェースを定義した抽象クラス。
    """
    @abstractmethod
    def chat(self, message: str)->str:
        """
        ユーザーからの入力（message）を受け取り、適切な応答を返すメソッド。
        """
        pass

    @property
    @abstractmethod
    def messages(self) -> List[Message]:
        """
        チャット履歴を返すプロパティ
        """
        pass

class CodeGenerator(Agent):
    @abstractmethod
    def code(self, message: str)->Code:
        """
        ユーザーからの入力（message）を受け取り、適切な応答を返すメソッド。
        """
        pass
