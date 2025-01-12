from typing import Callable, Dict, Any, List, get_type_hints, Optional, get_origin, get_args

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
        required: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Dict[str, Any]]] = None,
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
            required (Optional[List[str]]): 必須の引数のリスト（省略時は全ての引数を必須とする）
            parameters (Optional[Dict[str, Dict[str, Any]]]): 引数の詳細情報（省略時は型ヒントとdocstringから生成）

        Raises:
            TypeError: 関数がCallableでない場合、または型ヒントがない場合
            ValueError: 無効な型ヒントが指定された場合、またはdocstringがない場合
        """

        # 関数のバリデーション
        self._validate_function(func)

        # 型ヒントの取得とバリデーション
        type_hints = self._validate_type_hints(func)

        # 名前を設定（省略時は関数の__name__を使用）
        if name is None:
            name = func.__name__

        # 説明を設定（省略時はdocstringを使用）
        if description is None:
            description = self._get_description(func, name)

        # 引数の詳細情報を取得
        if parameters is None:
            parameters = self._generate_parameters(func, type_hints)
        self._validate_parameters(parameters, type_hints, name)

        # 必須引数のバリデーション
        all_params = [p for p in type_hints.keys() if p != "return"]
        if required is None:
            required = all_params
        self._validate_required(required, all_params, name)

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

    def _validate_function(self, func: Callable) -> None:
        """関数がCallableかどうかを確認する。"""
        if not callable(func):
            raise TypeError(f"登録対象が関数ではありません: {func}")

    def _validate_type_hints(self, func: Callable) -> Dict[str, Any]:
        """型ヒントが存在するか確認する。"""
        type_hints = get_type_hints(func)
        if not type_hints:
            raise TypeError(f"関数に型ヒントがありません: {func.__name__}")
        if "return" not in type_hints:
            raise TypeError(f"関数に戻り値の型ヒントがありません: {func.__name__}")
        return type_hints

    def _get_description(self, func: Callable, name: str) -> str:
        """関数の説明を取得する。"""
        if func.__doc__:
            return func.__doc__.strip()
        else:
            # docstringがない場合、エラーを発生させる
            raise ValueError(
                f"関数 '{name}' にdocstringがありません。以下のようにdocstringを追加してください:\n\n"
                "現在の関数定義:\n"
                f"def {name}({', '.join([f'{p}: {t.__name__}' for p, t in get_type_hints(func).items() if p != 'return'])}) -> {get_type_hints(func)['return'].__name__}:\n"
                "    # ここにdocstringを追加してください\n"
                "    ...\n\n"
                "例:\n"
                f"def {name}({', '.join([f'{p}: {t.__name__}' for p, t in get_type_hints(func).items() if p != 'return'])}) -> {get_type_hints(func)['return'].__name__}:\n"
                '    """\n'
                f"    {name} の説明をここに記述します。\n\n"
                "    Args:\n"
                f"        {' '.join([f'{p} ({t.__name__}): {p}の説明' for p, t in get_type_hints(func).items() if p != 'return'])}\n\n"
                "    Returns:\n"
                f"        {get_type_hints(func)['return'].__name__}: 戻り値の説明\n"
                '    """\n'
                "    ..."
            )

    def _generate_parameters(self, func: Callable, type_hints: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """型ヒントとdocstringから引数の詳細情報を生成する。"""
        parameters = {}
        for param, param_type in type_hints.items():
            if param == "return":
                continue

            # Optional型を解析
            if get_origin(param_type) is Optional:
                param_type = get_args(param_type)[0]  # Optionalの中身を取得

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
        return parameters

    def _validate_parameters(self, parameters: Dict[str, Dict[str, Any]], type_hints: Dict[str, Any], name: str) -> None:
        """parametersに指定された引数が関数に存在するか確認する。"""
        all_params = [p for p in type_hints.keys() if p != "return"]
        for param in parameters.keys():
            if param not in all_params:
                raise ValueError(f"引数 '{param}' は関数 '{name}' に存在しません。")

    def _validate_required(self, required: List[str], all_params: List[str], name: str) -> None:
        """requiredに指定された引数が関数に存在するか確認する。"""
        for param in required:
            if param not in all_params:
                raise ValueError(f"引数 '{param}' は関数 '{name}' に存在しません。")
