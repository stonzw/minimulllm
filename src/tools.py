import os
import fnmatch
from typing import List, Dict, Any

from minimulllm.src.type import Agent
from .function_call import doc


@doc({
    "description": "指定されたファイルの内容を読み取ります。",
    "args": {
        "file_path": "読み取るファイルのパス。",
    },
    "returns": "ファイルの内容。",
    "raises": {
        "FileNotFoundError": "ファイルが存在しない場合。",
        "IOError": "ファイルの読み取りに失敗した場合。",
    },
})
def file_read(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"ファイル '{file_path}' が見つかりません。")
    except IOError as e:
        raise IOError(f"ファイル '{file_path}' の読み取りに失敗しました: {e}")

@doc({
    "description": "指定されたファイルに書き込みます",
    "args": {
        "file_path": "書き込むファイルのパス",
        "content": "書き込むファイルの内容",
    },
    "returns": "ファイルの内容。",
    "raises": {
        "FileNotFoundError": "ファイルが存在しない場合。",
        "IOError": "ファイルの読み取りに失敗した場合。",
    },
})
def file_write(file_path: str, content: str) -> str:
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            return file.write(content)
    except FileNotFoundError:
        raise FileNotFoundError(f"ファイル '{file_path}' が見つかりません。")
    except IOError as e:
        raise IOError(f"ファイル '{file_path}' の書き込みに失敗しました: {e}")

@doc({
    "description": "指定されたディレクトリ内のファイルを検索します。",
    "args": {
        "directory_path": "検索するディレクトリのパス。",
        "search_string": "検索する文字列。",
        "depth": "検索する深さ（デフォルト: 1）。1は指定されたディレクトリのみ、2はそのサブディレクトリまで、など。",
    },
    "returns": "検索結果のファイルパスのリスト。",
    "raises": {},
})
def search_filename(directory_path: str, search_string: str, depth: int = 1) -> List[str]:
    results = []

    def _search(current_path: str, current_depth: int) -> None:
        if current_depth > depth:
            return
        for entry in os.scandir(current_path):
            if entry.is_file() and search_string in entry.name:
                results.append(entry.path)
            elif entry.is_dir():
                _search(entry.path, current_depth + 1)

    _search(directory_path, 1)
    return results

@doc({
    "description": "指定されたディレクトリ内のファイルとサブディレクトリを探索します。",
    "args": {
        "directory_path": "探索するディレクトリのパス。",
        "depth": "探索する深さ（デフォルト: 1）。1は指定されたディレクトリのみ、2はそのサブディレクトリまで、など。",
        "include_files": "結果にファイルを含めるかどうか（デフォルト: True）。",
        "include_directories": "結果にディレクトリを含めるかどうか（デフォルト: False）。",
    },
    "returns": "探索結果のリスト。各要素は以下のキーを持つ辞書です。\n"
               "    - 'name': ファイルまたはディレクトリの名前\n"
               "    - 'type': 'file' または 'directory'\n"
               "    - 'path': ファイルまたはディレクトリのフルパス",
    "raises": {},
})
def explore_directory(
    directory_path: str,
    depth: int = 1,
    include_files: bool = True,
    include_directories: bool = False,
) -> List[Dict[str, Any]]:
    results = []

    def _explore(current_path: str, current_depth: int) -> None:
        if current_depth > depth:
            return
        for entry in os.scandir(current_path):
            entry_info = {
                "name": entry.name,
                "path": entry.path,
            }
            if entry.is_file() and include_files:
                entry_info["type"] = "file"
                results.append(entry_info)
            elif entry.is_dir():
                if include_directories:
                    entry_info["type"] = "directory"
                    results.append(entry_info)
                _explore(entry.path, current_depth + 1)

    _explore(directory_path, 1)
    return results
@doc({
    "description": "指定されたディレクトリ内のファイルを再帰的に検索し、指定された文字列を含む行を返します。.gitignore を参照して無視するファイルやディレクトリをスキップできます。",
    "args": {
        "directory_path": "検索するディレクトリのパス。",
        "search_string": "検索する文字列。スペース区切りでアンド検索",
        "depth": "検索する深さ（デフォルト: 1）。1は指定されたディレクトリのみ、2はそのサブディレクトリまで、など。",
        "case_sensitive": "大文字と小文字を区別するかどうか（デフォルト: False）。",
        "use_gitignore": ".gitignore を参照して無視するファイルやディレクトリをスキップするかどうか（デフォルト: True）。",
        "max_result_count": "検索結果の最大数（デフォルト: 5）。",
        "chunk_size": "検索文字列の周辺に含める行数（デフォルト: 10）。",
    },
    "returns": "検索結果のリスト。各要素は以下のキーを持つ辞書です。\n"
               "    - 'file_path': ファイルのパス\n"
               "    - 'line_number': 行番号\n"
               "    - 'line_content': 行の内容",
    "raises": {},
})
def search_in_files(
    directory_path: str,
    search_string: str,
    depth: int = 1,
    case_sensitive: bool = False,
    use_gitignore: bool = True,
    max_result_count: int = 5,
    chunk_size: int = 10,
) -> List[Dict[str, Any]]:
    def _parse_gitignore(directory_path: str) -> List[str]:
        """
        .gitignore ファイルをパースし、無視するパターンのリストを返す。

        Args:
            directory_path (str): .gitignore ファイルがあるディレクトリのパス

        Returns:
            List[str]: 無視するパターンのリスト
        """
        gitignore_path = os.path.join(directory_path, ".gitignore")
        if not os.path.exists(gitignore_path):
            return []

        with open(gitignore_path, "r", encoding="utf-8") as file:
            patterns = [line.strip() for line in file if line.strip() and not line.startswith("#")]
        return patterns

    def _is_ignored(path: str, patterns: List[str]) -> bool:
        """
        指定されたパスが .gitignore のパターンにマッチするか確認する。

        Args:
            path (str): 確認するパス
            patterns (List[str]): .gitignore のパターンリスト

        Returns:
            bool: 無視する場合は True、そうでない場合は False
        """
        relative_path = os.path.relpath(path, start=os.path.dirname(path))
        for pattern in patterns:
            if fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
        return False

    results = []
    ignore_patterns = _parse_gitignore(directory_path) if use_gitignore else []
    search_terms = search_string.split()

    def _search_in_file(file_path: str) -> None:
        if use_gitignore and _is_ignored(file_path, ignore_patterns):
            return
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                lines = file.readlines()
                for start_line in range(0, len(lines), chunk_size):
                    chunk = lines[start_line:start_line + chunk_size]
                    chunk_text = ''.join(chunk).lower() if not case_sensitive else ''.join(chunk)
                    if all(term.lower() in chunk_text for term in search_terms):
                        results.append({
                            "file_path": file_path,
                            "line_number": start_line + 1,
                            "line_content": ''.join(chunk).strip(),
                            "context": [line.strip() for line in chunk],
                        })
                    if len(results) >= max_result_count:
                        return
        except Exception as e:
            print(f"ファイル '{file_path}' の読み取り中にエラーが発生しました: {e}")
            return

    def _explore(current_path: str, current_depth: int) -> None:
        if current_depth > depth:
            return
        for entry in os.scandir(current_path):
            if use_gitignore and _is_ignored(entry.path, ignore_patterns):
                continue
            if entry.is_file():
                _search_in_file(entry.path)
            elif entry.is_dir():
                _explore(entry.path, current_depth + 1)
            if len(results) >= max_result_count:
                return

    _explore(directory_path, 1)
    return results

@doc({
    "description": "作業が完了したら呼んでください。",
    "args": {},
    "returns": "COMPLETE",
    "raises": {},
})
def complete() -> str:
    return "COMPLETE"


@doc({
    "description": "ユーザーからの入力を受け取ります。",
    "args": {
        "message": "ユーザーへ表示するメッセージinputの引数",
    },
    "returns": "COMPLETE",
    "raises": {},
})
def user_input(
    message: str,
) -> str:
    return input(message)


class Reviewer:
  def __init__(self, llm: Agent):
    self.llm = llm

  @doc({
      "description": "コードレビューをAIエージェントに依頼します。",
      "args": {
          "files": "レビューしてもらうファイルのパスを,区切りで指定",
          "additional_info": "レビューする際に必要な追加情報1000文字程度(プロジェクト構成、目的、期待する結果、ファイルの中身など)",
      },
      "returns": "レビューの結果を文字列でかえします",
      "raises": {},
  }) 
  def review_code(self, files: List[str], additional_info: str) -> str:
    code = ""
    code_markdown_template = "{filepath}\n```python\n{code}\n```"
    for filepath in files:
      with open(filepath, "r") as f:
        code += code_markdown_template.format(filepath=filepath, code=f.read())
    res = self.llm.chat(f"Please find this code bug. \n code: ```\n{code}\n``` \n additional info: {additional_info}")
    return res
