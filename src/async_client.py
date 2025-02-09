import json
from pydantic import BaseModel
from openai import AsyncOpenAI
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel
import uuid

from .type import Agent, Message
from .secret import DEEP_SEEK_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY
import google.generativeai as genai
from google.generativeai.types import GenerationConfig


class OpenAI(Agent):
    def __init__(self, model, system_prompt, reasoning_effort=None):
        self.model = model
        self.system_prompt = system_prompt
        self._messages = [{"role": "system", "content": system_prompt}]
        # OpenAI 用に仮想的に用意された "async" 版インターフェースを想定
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.reasoning_effort = reasoning_effort

    async def chat(self, message) -> str:
        self._messages.append({"role": "user", "content": message})
        if self.reasoning_effort is None:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self._messages,
            )
        else:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self._messages,
                reasoning_effort=self.reasoning_effort
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

class OpenAIToolUse(OpenAI):
    async def tool(self, message: str, tools: List[Dict[str, Any]])->Tuple[str,Dict[str,str]]:
        self._messages.append({"role": "user", "content": message})
        if self.reasoning_effort is None:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self._messages,
                tools=tools
            )
        else:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self._messages,
                reasoning_effort=self.reasoning_effort,
                tools=tools
            )
        self._messages.append(response.choices[0].message.model_dump())
        message = response.choices[0].message.content
        tool_calls = response.choices[0].message.tool_calls
        return message, tool_calls

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
    async def tool(self, message: str, tools: List[Dict[str, Any]])->Tuple[str,Dict[str,str]]:
        self._messages.append({"role": "user", "content": message})
        # 非同期版
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self._messages,
            tools=tools
        )
        self._messages.append(response.choices[0].message.model_dump())
        message = response.choices[0].message.content
        tool_calls = response.choices[0].message.tool_calls
        return message, tool_calls

class Gemini(Agent):
    def __init__(self, model, system_prompt):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=model,system_instruction=system_prompt
        )
        self._messages = []

    async def chat(self, message: str) -> str:
        self.append_message({"role": "user", "content": message})
        
        response = await self.model.generate_content_async(message)
        response_text = response.text
        
        self.append_message({"role": "assistant", "content": response_text})
        return response_text

    @property
    def messages(self) -> List[Message]:
        return [Message(role=m["role"], content=m["content"]) for m in self._messages]

    async def count_tokens(self, text: str) -> int:
        response = await self.model.count_tokens_async(text)
        return response.total_tokens

    async def generate_content_with_config(self, prompt: str, config: GenerationConfig = None) -> tuple:
        if config is None:
            config = GenerationConfig()
        response = await self.model.generate_content_async(prompt, generation_config=config)
        return response.text, response.usage_metadata


class GeminiToolUse(Gemini):
    async def tool(self, message: str, tools: List[Dict[str, Any]]) ->Tuple[str,Dict[str,str]]:
        # ツール情報をプロンプトに組み込む
        tool_descriptions = "\n".join([
            f"- {tool['function']['name']}: {tool['function']['description']}"
            for tool in tools
        ])
        
        prompt = f"""
        ユーザーメッセージ: {message}

        利用可能なツール:
        {tool_descriptions}

        指示: 上記のメッセージに対して適切なツールを選択し、使用してください。ツールを使用する場合は、以下の形式で応答してください：

        ツール使用:
        """ + """
        ```
[{
    "name": "ツール名",
    "arguments": {{
        "arg1": "値1",
        "arg2": "値2"
    }}
},...]
```
""" + """

        ツールを使用しない場合は、通常の応答を行ってください。複数のツールを使用する場合は、それぞれのツール使用を別々に記述してください。
        """

        response = await self.model.generate_content_async(prompt)
        response_text = response.text

        # ツール使用の応答をパースする
        tool_uses = []
        tool_use_texts = response_text.split("ツール使用:")
        for tool_use_text in tool_use_texts[1:]:
            json_text = tool_use_text[tool_use_text.index("```")+1:tool_use_text.index("```")].strip()
            print(json_text)
            tool_use = json.loads(json_text)
            tool_uses += tool_use
        self.append_message({"role": "user", "content": message})
        self.append_message({"role": "assistant", "content": response_text})
        return response_text, tool_uses

    async def generate_content_with_tools(self, prompt: str, tools: List[Dict[str, Any]], config: GenerationConfig = None) -> tuple:
        if config is None:
            config = GenerationConfig()
        response = await self.tool(prompt, tools)
        # Note: Gemini APIは現在、ツール使用に関する詳細な使用量メタデータを提供していないため、
        # ここでは簡易的な情報を返します。
        usage_metadata = {
            "prompt_token_count": await self.count_tokens(prompt),
            "response_token_count": await self.count_tokens(response)
        }
        return response, usage_metadata

class Function(BaseModel):
  name: str
  arguments: str

class FunctionTool(BaseModel):
    id: str
    function: Function
class GeminiToolUse(Gemini):
    async def tool(self, message: str, tools: List[Dict[str, Any]]) ->Tuple[str,Dict[str,str]]:
        # ツール情報をプロンプトに組み込む
        tool_descriptions = "\n".join([
            f"- {tool['function']['name']}: {tool['function']['description']}"
            for tool in tools
        ])
        
        prompt = f"""
        ユーザーメッセージ: {message}

        利用可能なツール:
        {tool_descriptions}

        指示: 上記のメッセージに対して適切なツールを選択し、1つだけ使用してください。ツールを使用する場合は、以下の形式で応答してください.直接Pythonのjson.loadsでパースできるように余計な文字は入れないでPythonのdict形式で出力してください.変数を埋め込まないで直接値を入れて。いきなりすべてを行わずに細かく実行して。：
        """ + """
        ```{
    "name": "ツール名",
    "arguments": {{
        "arg1": "値1",
        "arg2": "値2"
    }}
}```""" + """

        ツールを使用しない場合は、通常の応答を行ってください。複数のツールを使用する場合は、それぞれのツール使用を別々に記述してください。
        """

        response = await self.model.generate_content_async(prompt)
        response_text = response.text
        # ツール使用の応答をパースする
        tool_uses = []
        tool_use_text = response_text[response_text.index("{"):].strip()
        json_text = tool_use_text[:tool_use_text.rindex("}")+1]
        print(json_text)
        tool_use = json.loads(json_text)
        tool_use["arguments"] = json.dumps(tool_use["arguments"])
        tool_uses.append(tool_use)
        self.append_message({"role": "user", "content": message})
        self.append_message({"role": "assistant", "content": response_text})
        return response_text, [FunctionTool(id=str(uuid.uuid4()), function=Function(**f)) for f in tool_uses]

    async def generate_content_with_tools(self, prompt: str, tools: List[Dict[str, Any]], config: GenerationConfig = None) -> tuple:
        if config is None:
            config = GenerationConfig()
        response = await self.tool(prompt, tools)
        # Note: Gemini APIは現在、ツール使用に関する詳細な使用量メタデータを提供していないため、
        # ここでは簡易的な情報を返します。
        usage_metadata = {
            "prompt_token_count": await self.count_tokens(prompt),
            "response_token_count": await self.count_tokens(response)
        }
        return response, usage_metadata