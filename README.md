# Minimulllm

## 概要

Minimulllmは、LLM（Large Language Model）とのやり取りを簡単に行うための小さく (Mini) かつ複数の LLM をまとめられる (Multiple) ライブラリです。現在、多様な LLM 向けのクライアントライブラリはそれぞれ独自のインターフェースを提供しており、一貫した利用が難しくなっています。Minimulllm では、こうしたさまざまな LLM 向けライブラリをシンプルかつ標準的なインターフェースでまとめつつ、カスタマイズ性の高いラッパを提供します。

## 特徴

- **シンプルかつ軽量**: コードベースを最小限に抑え、理解・拡張が容易
- **柔軟なカスタマイズ**: コア部分を自由に拡張可能。LLM クライアントの差し替えも容易
- **統一的なインターフェース**: 複数の LLM をまとめて同じように扱うことが可能
- **コードの再利用性**: 必要最小限のコンポーネントのみを提供し、既存プロジェクトでも流用しやすい設計

## 環境設定

### 必要なツール
- Python 3.x
- [uv](https://pypi.org/project/uv/): 環境の管理

### 環境セットアップ手順
1. リポジトリをクローンします。

```bash
$ git clone <repository-url>
$ cd minimulllm
```

2. `uv` をインストールして、環境をセットアップします。

```bash
$ pip install uv
$ uv setup
```

3. 必要なAPIキーを `.env` ファイル または環境変数に設定します。

```env
OPENAI_API_KEY="sk-***"
ANTHROPIC_API_KEY="sk-***"
GEMINI_API_KEY="sk-***"
DEEP_SEEK_API_KEY="sk-***"
```

## 使い方

### コードを生成してみる
以下のコード例は、どのようにして Minimulllm ライブラリを使って LLM モデルを操作するかを示しています。

```python
from minimulllm.tools import (
    CodeGeneratorOpenAI, CodeGeneratorDeepSeek, CodeGeneratorAnthropic, CodeGeneratorGemini,
    DeepSeek, Anthropic, Gemini
)
from minimulllm.const import QA_ENGINEER_SYSTEM_PROMPT, OPEN_INTERPRETER_SYSTEM_PROMPT

# OpenAI GPT を使用したコード生成器
cg_oa = CodeGeneratorOpenAI(
    model_name="gpt-4o-mini",
    system_prompt=OPEN_INTERPRETER_SYSTEM_PROMPT
)

code_prompt = "Pythonでリスト内の重複要素を削除する関数を作成してください。"
generated_code = cg_oa.generate_code(code_prompt)

print("Generated Code by GPT-4 (mini):")
print(generated_code)
```

### コマンドライン引数を用いた実行
`example_with_args.py` を用いることで、コマンドラインから `goal` を設定し実行することができます。

```bash
$ python example_with_args.py --goal "ターゲットの設定目標をここに入力"
```

この機能により、動的に目標設定を行うことができ、スクリプトの汎用性が向上します。