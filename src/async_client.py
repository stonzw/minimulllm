from openai import AsyncOpenAI
from typing import List, Dict, Any

from .type import Agent, Message
from .secret import DEEP_SEEK_API_KEY


class DeepSeek(Agent):
    def __init__(self, model, system_prompt):
        self.model = model
        self.system_prompt = system_prompt
        self._messages = [{"role": "system", "content": system_prompt}]
        # DeepSeek 用に仮想的に用意された "async" 版インターフェースを想定
        self.client = AsyncOpenAI(api_key=DEEP_SEEK_API_KEY, base_url="https://api.deepseek.com")

    async def chat(self, message) -> str:
        self._messages.append({"role": "user", "content": message})
        # 非同期版
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self._messages,
        )
        self._messages.append({
            "role": "assistant",
            "content": response.choices[0].message.content
        })
        return response.choices[0].message.content

    @property
    def messages(self) -> List[Message]:
        return [
            Message(
                role=m["role"],
                content=m["content"]
            ) for m in self._messages
        ]

class DeepSeekToolUse(DeepSeek):
    async def tool(self, message: str, tools: List[Dict[str, Any]])->str:
        self._messages.append({"role": "user", "content": message})
        # 非同期版
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self._messages,
            tools=tools
        )
        self._messages.append({
            "role": "assistant",
            "content": response.choices[0].message.content
        })
        return response

