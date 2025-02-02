import os
import openai
import anthropic
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from .prompt import JSON_PARSER_PROMPT
from .type import Command, Agent, Message, CodeGenerator
from .secret import OPENAI_API_KEY, DEEP_SEEK_API_KEY, GEMINI_API_KEY


def call_openai_structured_api(model: str, messages: List[dict], response_format: BaseModel):
    response = openai.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=response_format,
    )
    return response
class OpenAI(Agent):
    def __init__(self, model, system_prompt):
        self.model = model
        self.system_prompt = system_prompt
        self._messages = [{"role": "system", "content": system_prompt}]
        # OpenAI 用に仮想的に用意された "async" 版インターフェースを想定
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)

    def chat(self, message) -> str:
        self._messages.append({"role": "user", "content": message})
        # 非同期版
        response = self.client.chat.completions.create(
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

class CodeGeneratorOpenAI(CodeGenerator):
    OPEN_AI_MODELS = ["gpt-4o", "gpt-4o-mini", "o1-mini", "o1"]
    def __init__(self, model, system_prompt):
        self.model = model
        self.system_prompt = system_prompt
        self._messages = [{"role": "system", "content": system_prompt}]

    def chat(self, message) -> str:
        openai.api_key = OPENAI_API_KEY
        self._messages.append({"role": "user", "content": message})
        response = openai.chat.completions.create(
            model=self.model,
            messages=self._messages
        )
        self._messages.append({"role": "assistant", "content": response.choices[0].message.content})
        return response.choices[0].message.content

    def code(self, message) -> Optional[Command]:
        openai.api_key = OPENAI_API_KEY
        self._messages.append({"role": "user", "content": message})
        response = call_openai_structured_api(self.model, self._messages, Command)
        self._messages.append({"role": "assistant", "content": response.choices[0].message.content})
        return response.choices[0].message.parsed

    @property
    def messages(self) -> List[Message]:
        return [
            Message(
                role=m["role"],
                content=m["content"]
            ) for m in self._messages
        ]

class DeepSeek(Agent):

    def __init__(self, model, system_prompt):
        self.model = model
        self.system_prompt = system_prompt
        self._messages = [{"role": "system", "content": system_prompt}]
        self.client = openai.OpenAI(api_key=DEEP_SEEK_API_KEY, base_url="https://api.deepseek.com")

    def chat(self, message) -> str:
        self._messages.append({"role": "user", "content": message})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._messages,
        )
        self._messages.append({"role": "assistant", "content": response.choices[0].message.content})
        return response.choices[0].message.content

    @property
    def messages(self) -> List[Message]:
        return [
            Message(
                role=m["role"],
                content=m["content"]
            ) for m in self._messages
        ]
class CodeGeneratorDeepSeek(DeepSeek):
    def code(self, message) -> Optional[Command]:
        self.chat(message)
        openai.api_key = OPENAI_API_KEY
        raw_message = self.messages[-1].content
        messages = [
            {"role": "system", "content": "You are JSON parser, don't rewrite content just parse it."},
            {"role": "user", "content": "parse following.: \n" + raw_message},
        ]
        response = call_openai_structured_api("gpt-4o-mini", messages, Command)
        return response.choices[0].message.parsed

class DeepSeekToolUse(DeepSeek):
    def tool(self, message: str, tools: List[Dict[str, Any]])->str:
        self._messages.append({"role": "user", "content": message})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._messages,
            tools=tools
        )
        self._messages.append(response.choices[0].message.model_dump())
        return response

class Anthropic(Agent):

    def __init__(self, model, system_prompt):
        self.client = anthropic.Anthropic()
        self.model = model
        self.system_prompt = system_prompt
        self._messages = []
        if self.model == "claude-3-5-sonnet-20241022":
            self.max_tokens = 4000
        else:
            self.max_tokens = 2000

    def chat(self, message) -> str:
        self._messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": message
                }
            ]
        })
        
        response = self.client.messages.create(
            model=self.model,
            system=self.system_prompt,
            messages=self._messages,
            max_tokens=self.max_tokens
        )
        
        self._messages.append({
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": response.content[0].text
                }
            ]
        })
        
        return response.content[0].text

    @property
    def messages(self) -> List[Message]:
        return [
            Message(
                role=m["role"],
                content=m["content"][0]["text"] if isinstance(m["content"], list) else m["content"]
            ) for m in self._messages
        ]


class CodeGeneratorAnthropic(Anthropic):
    def code(self, message) -> Optional[Command]:
        self.chat(message)
        openai.api_key = OPENAI_API_KEY
        raw_message = self.messages[-1].content
        messages = [
            {"role": "system", "content": "You are JSON parser, don't rewrite content just parse it."},
            {"role": "user", "content": "parse following.: \n" + raw_message},
        ]
        response = call_openai_structured_api("gpt-4o-mini", messages, Command)
        return response.choices[0].message.parsed

class Gemini(Agent):
    def __init__(self, model, system_prompt):
        self.model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt,
            api_key=os.environ.get("GEMINI_API_KEY")
        )
        self.system_prompt = system_prompt
        self._messages = []

    def chat(self, message) -> str:
        self._messages.append({"role": "user", "content": message})
        response = self.model.generate_content(message)
        response_text = response.text
        self._messages.append({"role": "assistant", "content": response_text})
        return response_text

    @property
    def messages(self) -> List[Message]:
        return [
            Message(
                role=m["role"],
                content=m["content"]
            ) for m in self._messages
        ]

class CodeGeneratorGemini(Gemini):
    def code(self, message) -> Optional[Command]:
        self.chat(message)
        
        openai.api_key = GEMINI_API_KEY
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
            
        raw_message = self.messages[-1].content
        messages = [
            {"role": "system", "content": JSON_PARSER_PROMPT},
            {"role": "user", "content": "parse following.: \n" + raw_message},
        ]
        response = call_openai_structured_api("gpt-4o-mini", messages, Command)
        return response.choices[0].message.parsed


