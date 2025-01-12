from typing import Callable, Dict, Any, List, get_type_hints, Optional

class FunctionRegistry:
    """
    LLMの関数呼び出しのために関数を登録・管理するクラス。
    """
    def __init__(self):
        self._functions: List[Dict[str, Any]] = []

    def register(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        関数を登録する。
        型ヒントとdocstringを使用して関数を書くだけでregisterを通して登録できます。引数で指定することも可能です。
        funcの引数の型は、str, int, float, bool, List, Dict, Optionalのみサポートしています。
        funcの引数の説明は、docstringから取得します。説明がない場合は型ヒントのみになります。

        Args:
            func (Callable): 登録する関数
            name (Optional[str]): 関数の名前（省略時は関数の__name__を使用）
            description (Optional[str]): 関数の説明（省略時はdocstringを使用）

        Raises:
            TypeError: 関数がCallableでない場合、または型ヒントがない場合
            ValueError: 無効な型ヒントが指定された場合、またはdocstringがない場合
        """
        # 関数がCallableかどうかを確認
        if not callable(func):
            raise TypeError(f"登録対象が関数ではありません: {func}")

        # 型ヒントを取得
        type_hints = get_type_hints(func)
        if not type_hints:
            raise TypeError(f"関数に型ヒントがありません: {func.__name__}")

        # 戻り値の型ヒントを確認
        if "return" not in type_hints:
            raise TypeError(f"関数に戻り値の型ヒントがありません: {func.__name__}")

        # 名前を設定（省略時は関数の__name__を使用）
        if name is None:
            name = func.__name__

        # 説明を設定（省略時はdocstringを使用）
        if description is None:
            if func.__doc__:
                description = func.__doc__.strip()
            else:
                # docstringがない場合、エラーを発生させる
                raise ValueError(
                    f"関数 '{name}' にdocstringがありません。以下のようにdocstringを追加してください:\n\n"
                    "現在の関数定義:\n"
                    f"def {name}({', '.join([f'{p}: {t.__name__}' for p, t in type_hints.items() if p != 'return'])}) -> {type_hints['return'].__name__}:\n"
                    "    # ここにdocstringを追加してください\n"
                    "    ...\n\n"
                    "例:\n"
                    f"def {name}({', '.join([f'{p}: {t.__name__}' for p, t in type_hints.items() if p != 'return'])}) -> {type_hints['return'].__name__}:\n"
                    '    """\n'
                    f"    {name} の説明をここに記述します。\n\n"
                    "    Args:\n"
                    f"        {' '.join([f'{p} ({t.__name__}): {p}の説明' for p, t in type_hints.items() if p != 'return'])}\n\n"
                    "    Returns:\n"
                    f"        {type_hints['return'].__name__}: 戻り値の説明\n"
                    '    """\n'
                    "    ..."
                )

        # 引数の型ヒントと説明を取得
        parameters = {}
        required = []
        for param, param_type in type_hints.items():
            if param == "return":
                continue

            # 型ヒントが無効な場合
            if not isinstance(param_type, type):
                raise ValueError(f"無効な型ヒントです: {param}: {param_type}")

            # 引数の説明を初期化(型ヒントのみ)
            param_description = f"{param}: {param_type.__name__}"

            # 引数の説明を取得（docstringから）
            if func.__doc__:
                doc_lines = func.__doc__.splitlines()
                for line in doc_lines:
                    if f"{param} (" in line:
                        param_description = line.strip()
                        break

            parameters[param] = {
                "type": param_type.__name__,
                "description": param_description,
            }
            required.append(param)

        # JSON Schemaを構築
        schema = {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
        }
        self._functions.append(schema)

    @property
    def functions(self) -> List[Dict[str, Any]]:
        """
        登録されたすべての関数のJSON Schemaを取得する。

        Returns:
            List[Dict[str, Any]]: 関数のJSON Schemaリスト
        """
        return self._functions
