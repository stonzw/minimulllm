## 概要

Minimulllm は、LLM（Large Language Model）とのやり取りを簡単に行うための 小さく (Mini) かつ 複数の LLM をまとめられる (Multiple) ライブラリです。
現在、多様な LLM 向けのクライアントライブラリはそれぞれ独自のインターフェースを提供しており、一貫した利用が難しくなっています。Minimulllm では、こうしたさまざまな LLM 向けライブラリをシンプルかつ標準的なインターフェースでまとめつつ、カスタマイズ性の高いラッパを提供します。

## 特徴

- シンプルかつ軽量: コードベースを最小限に抑え、理解・拡張が容易
- 柔軟なカスタマイズ: コア部分を自由に拡張可能。LLM クライアントの差し替えも容易
- 統一的なインターフェース: 複数の LLM をまとめて同じように扱うことが可能
- コードの再利用性: 必要最低限のコンポーネントのみを提供し、既存プロジェクトでも流用しやすい設計

## APIキーは環境変数でセットするか.envに定義

```
export OPENAI_API_KEY="sk-***"
export ANTHROPIC_API_KEY="sk-***"
export GEMINI_API_KEY="sk-***"
export DEEP_SEEK_API_KEY="sk-***"
```


## コードを書かせてみる


```
from minimulllm.tools import (
    CodeGeneratorOpenAI, CodeGeneratorDeepSeek, CodeGeneratorAnthropic, CodeGeneratorGemini,
    DeepSeek, Anthropic, Gemini
)
from minimulllm.const import QA_ENGINEER_SYSTEM_PROMPT, OPEN_INTERPRETER_SYSTEM_PROMPT

# ==============
# コード生成用
# ==============
# 1) OpenAI GPT を使用したコード生成器
cg_oa = CodeGeneratorOpenAI(
    model_name="gpt-4o-mini",
    system_prompt=OPEN_INTERPRETER_SYSTEM_PROMPT
)

# 2) DeepSeek を使用したコード生成器
cg_ds = CodeGeneratorDeepSeek(
    model_name="deepseek-chat",
    system_prompt=OPEN_INTERPRETER_SYSTEM_PROMPT
)

# 3) Gemini を使用したコード生成器
cg_gm = CodeGeneratorGemini(
    model_name="gemini-1.5-flash",
    system_prompt=OPEN_INTERPRETER_SYSTEM_PROMPT
)

# 4) Anthropic Claude を使用したコード生成器
cg_ap = CodeGeneratorAnthropic(
    model_name="claude-3-5-sonnet-20241022",
    system_prompt=OPEN_INTERPRETER_SYSTEM_PROMPT
)

# ==============
# QA（質問応答）用
# ==============
# 1) OpenAI GPT を使用した QA
qa_oa = CodeGeneratorOpenAI(
    model_name="gpt-4o-mini",
    system_prompt=QA_ENGINEER_SYSTEM_PROMPT
)

# 2) DeepSeek を使用した QA
qa_ds = DeepSeek(
    model_name="deepseek-chat",
    system_prompt=QA_ENGINEER_SYSTEM_PROMPT
)

# 3) Gemini を使用した QA
qa_gm = Gemini(
    model_name="gemini-1.5-flash",
    system_prompt=QA_ENGINEER_SYSTEM_PROMPT
)

# 4) Anthropic Claude を使用した QA
qa_ap = Anthropic(
    model_name="claude-3-5-sonnet-20241022",
    system_prompt=QA_ENGINEER_SYSTEM_PROMPT
)

```


```
# 例: OpenAI GPT-4 (mini) を利用して Python のコードを書かせたい
code_prompt = "Pythonでリスト内の重複要素を削除する関数を作成して下さい。"
generated_code = cg_oa.generate_code(code_prompt)

print("Generated Code by GPT-4 (mini):")
print(generated_code)


# 例: DeepSeek を利用してバグを修正する
qa_prompt = "先ほどのコードのバグを修正してください"
answer = qa_ds.ask_question(qa_prompt)

print("Answer from DeepSeek:")
print(answer)

```