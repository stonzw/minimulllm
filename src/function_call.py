import json
from typing import Callable, Optional, List, Dict, Any, get_origin, get_args, get_type_hints

class LLMToolParser:
    """
    LLMの関数呼び出しのために関数を解析・バリデーションするユーティリティクラス。
    すべてのメソッドはスタティックメソッドとして提供され、ステートレスです。
    """

    @staticmethod
    def parse_func(
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        required: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        関数を解析し、JSON Schemaを生成する。

        Args:
            func (Callable): 解析する関数
            name (Optional[str]): 関数の名前（省略時は関数の__name__を使用）
            description (Optional[str]): 関数の説明（省略時はdocstringを使用）
            required (Optional[List[str]]): 必須の引数のリスト（省略時は全ての引数を必須とする）
            parameters (Optional[Dict[str, Dict[str, Any]]]): 引数の詳細情報（省略時は型ヒントとdocstringから生成）

        Returns:
            Dict[str, Any]: 生成されたJSON Schema

        Raises:
            TypeError: 関数がCallableでない場合、または型ヒントがない場合
            ValueError: 無効な型ヒントが指定された場合、またはdocstringがない場合
        """
        # バリデーションを実行
        LLMToolParser.validate(func, parameters, required)

        # 型ヒントの取得
        type_hints = get_type_hints(func)

        # 名前を設定（省略時は関数の__name__を使用）
        if name is None:
            name = func.__name__

        # 説明を設定（省略時はdocstringを使用）
        if description is None:
            description = LLMToolParser.get_description(func, name)

        # 引数の詳細情報を取得
        if parameters is None:
            parameters = LLMToolParser.generate_parameters(func, type_hints)

        # 必須引数の設定
        all_params = [p for p in type_hints.keys() if p != "return"]
        if required is None:
            required = all_params

        # JSON Schemaを構築
        schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required,
                },
            }
        }
        return schema

    @staticmethod
    def validate(
        func: Callable,
        parameters: Optional[Dict[str, Dict[str, Any]]] = None,
        required: Optional[List[str]] = None,
    ) -> None:
        """
        関数とその引数に関するすべてのバリデーションを実行する。

        Args:
            func (Callable): 対象の関数
            parameters (Optional[Dict[str, Dict[str, Any]]]): 引数の詳細情報
            required (Optional[List[str]]): 必須の引数のリスト

        Raises:
            TypeError: 関数がCallableでない場合、または型ヒントがない場合
            ValueError: 無効な型ヒントが指定された場合、またはdocstringがない場合
        """
        # 関数のバリデーション
        LLMToolParser.validate_function(func)

        # 型ヒントのバリデーション
        type_hints = LLMToolParser.validate_type_hints(func)

        # 引数のバリデーション
        if parameters is not None:
            LLMToolParser.validate_parameters(parameters, type_hints, func.__name__)

        # 必須引数のバリデーション
        if required is not None:
            all_params = [p for p in type_hints.keys() if p != "return"]
            LLMToolParser.validate_required(required, all_params, func.__name__)

    @staticmethod
    def validate_function(func: Callable) -> None:
        """関数がCallableかどうかを確認する。"""
        if not callable(func):
            raise TypeError(f"登録対象が関数ではありません: {func}")

    @staticmethod
    def validate_type_hints(func: Callable) -> Dict[str, Any]:
        """型ヒントが存在するか確認する。"""
        type_hints = get_type_hints(func)
        if not type_hints:
            raise TypeError(f"関数に型ヒントがありません: {func.__name__}")
        if "return" not in type_hints:
            raise TypeError(f"関数に戻り値の型ヒントがありません: {func.__name__}")
        return type_hints

    @staticmethod
    def validate_parameters(parameters: Dict[str, Dict[str, Any]], type_hints: Dict[str, Any], name: str) -> None:
        """parametersに指定された引数が関数に存在するか確認する。"""
        all_params = [p for p in type_hints.keys() if p != "return"]
        for param in parameters.keys():
            if param not in all_params:
                raise ValueError(f"引数 '{param}' は関数 '{name}' に存在しません。")

    @staticmethod
    def validate_required(required: List[str], all_params: List[str], name: str) -> None:
        """requiredに指定された引数が関数に存在するか確認する。"""
        for param in required:
            if param not in all_params:
                raise ValueError(f"引数 '{param}' は関数 '{name}' に存在しません。")

    @staticmethod
    def generate_parameters(func: Callable, type_hints: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """
        型ヒントとdocstringから引数の詳細情報を生成する。

        Args:
            func (Callable): 対象の関数
            type_hints (Optional[Dict[str, Any]]): 型ヒント（省略時は関数から取得）

        Returns:
            Dict[str, Dict[str, Any]]: 引数の詳細情報
        """
        if type_hints is None:
            type_hints = get_type_hints(func)

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

            # Pythonの型をJSON Schemaの型に変換
            json_schema_type = LLMToolParser.convert_python_type_to_json_schema_type(param_type)

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
                "type": json_schema_type,
                "description": param_description,
            }
        return parameters

    @staticmethod
    def convert_python_type_to_json_schema_type(python_type: type) -> str:
        """Pythonの型をJSON Schemaの型に変換する。"""
        if python_type is str:
            return "string"
        elif python_type is int:
            return "integer"
        elif python_type is bool:
            return "boolean"
        elif python_type is float:
            return "number"
        elif python_type is list:
            return "array"
        elif python_type is dict:
            return "object"
        else:
            raise ValueError(f"サポートされていない型です: {python_type}")

    @staticmethod
    def get_description(func: Callable, name: str) -> str:
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

class LLMToolManager:
    def __init__(self):
        self.tools = []  # 登録されたツールのJSON Schemaを保持
        self._func = dict()  # 登録された関数を保持

    def register(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        required: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        関数を登録し、JSON Schemaを生成する。

        Args:
            func (Callable): 登録する関数
            name (Optional[str]): 関数の名前（省略時は関数の__name__を使用）
            description (Optional[str]): 関数の説明（省略時はdocstringを使用）
            required (Optional[List[str]]): 必須の引数のリスト（省略時は全ての引数を必須とする）
            parameters (Optional[Dict[str, Dict[str, Any]]]): 引数の詳細情報（省略時は型ヒントとdocstringから生成）

        Returns:
            Dict[str, Any]: 生成されたJSON Schema
        """
        # JSON Schemaを生成
        schema = LLMToolParser.parse_func(func, name, description, required, parameters)

        # 関数を登録
        func_name = name if name is not None else func.__name__
        self._func[func_name] = func

        # JSON Schemaをツールリストに追加
        self.tools.append(schema)

        return schema

    def exec(self, res: Any) -> Any:
        """
        登録された関数を実行する。

        Args:
            res (Any): LLMの戻り値(res.choices[0].message.tool_calls[i])

        Returns:
            Any: 関数の実行結果

        Raises:
            ValueError: 関数が登録されていない場合、または引数が不正な場合
            Error: 実行時エラー
        """
        # 関数名と引数を取得
        func_name = res.name
        arguments = json.loads(res.arguments)

        # 関数が登録されているか確認
        if func_name not in self._func:
            raise ValueError(f"関数 '{func_name}' は登録されていません。")

        # 関数を取得
        func = self._func[func_name]

        # 引数を関数に渡して実行
        return func(**arguments)

