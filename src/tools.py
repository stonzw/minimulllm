import os
import fnmatch
from typing import List, Dict, Any
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
        "search_string": "検索する文字列。",
        "depth": "検索する深さ（デフォルト: 1）。1は指定されたディレクトリのみ、2はそのサブディレクトリまで、など。",
        "case_sensitive": "大文字と小文字を区別するかどうか（デフォルト: False）。",
        "use_gitignore": ".gitignore を参照して無視するファイルやディレクトリをスキップするかどうか（デフォルト: True）。",
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

    def _search_in_file(file_path: str) -> None:
        if use_gitignore and _is_ignored(file_path, ignore_patterns):
            return
        with open(file_path, "r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not case_sensitive:
                    line_lower = line.lower()
                    search_string_lower = search_string.lower()
                    if search_string_lower in line_lower:
                        results.append({
                            "file_path": file_path,
                            "line_number": line_number,
                            "line_content": line.strip(),
                        })
                else:
                    if search_string in line:
                        results.append({
                            "file_path": file_path,
                            "line_number": line_number,
                            "line_content": line.strip(),
                        })

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

    _explore(directory_path, 1)
    return results

