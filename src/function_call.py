import json
from typing import Callable, Optional, List, Dict, Any, Union, get_origin, get_args, get_type_hints

def doc(doc_dict: Dict[str, Any]):
    """
    関数に構造化されたドキュメントを追加するデコレーター。型情報は型ヒントから取得します。

    Args:
        doc_dict (Dict[str, Any]): ドキュメントの情報を含む辞書。
            - "description": 関数の説明
            - "args": 引数の説明（キーは引数名、値は説明文）
            - "returns": 戻り値の説明（文字列）
            - "raises": 例外の説明（キーは例外タイプ、値は説明文）

    Returns:
        Callable: デコレートされた関数
    """
    def decorator(func: Callable):
        # 型ヒントを取得
        type_hints = get_type_hints(func)

        # ドキュメントを構築
        docstring = f"{doc_dict.get('description', '')}\n\n"
        
        # 引数の説明
        if "args" in doc_dict:
            docstring += "Args:\n"
            for arg, desc in doc_dict["args"].items():
                arg_type = type_hints.get(arg, "Unknown")
                # arg_type が str などの場合もあるので安全に __name__ を取り出す
                arg_type_name = arg_type.__name__ if hasattr(arg_type, "__name__") else str(arg_type)
                docstring += f"    {arg} ({arg_type_name}): {desc}\n"
        
        # 戻り値の説明
        if "returns" in doc_dict:
            return_type = type_hints.get("return", "Unknown")
            return_type_name = return_type.__name__ if hasattr(return_type, "__name__") else str(return_type)
            docstring += "\nReturns:\n"
            docstring += f"    {return_type_name}: {doc_dict['returns']}\n"
        
        # 例外の説明
        if "raises" in doc_dict:
            docstring += "\nRaises:\n"
            for exc, desc in doc_dict["raises"].items():
                docstring += f"    {exc}: {desc}\n"
        
        # 関数の__doc__属性に設定
        func.__doc__ = docstring
        return func
    return decorator


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

        # 名前を設定（省略時は関数の__qualname__を使用）
        if name is None:
            name = func.__qualname__

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
            LLMToolParser.validate_parameters(parameters, type_hints, func.__qualname__)

        # 必須引数のバリデーション
        if required is not None:
            all_params = [p for p in type_hints.keys() if p != "return"]
            LLMToolParser.validate_required(required, all_params, func.__qualname__)

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
            raise TypeError(f"関数に型ヒントがありません: {func.__qualname__}")
        if "return" not in type_hints:
            raise TypeError(f"関数に戻り値の型ヒントがありません: {func.__qualname__}")
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
    def generate_parameters(
        func: Callable,
        type_hints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
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

            # Optional[T] (Union[T, NoneType]) を含む場合
            param_type = LLMToolParser.extract_non_none_type_if_optional(param_type)

            # JSON Schemaの型に変換
            json_schema_type = LLMToolParser.convert_python_type_to_json_schema_type(param_type)

            # 引数の説明を初期化(型ヒントのみ)
            param_description = f"{param}: {LLMToolParser.get_type_name(param_type)}"

            # docstring から引数の説明を取得
            if func.__doc__:
                doc_lines = func.__doc__.splitlines()
                for line in doc_lines:
                    # 例: "param_name (int):" のような記述を探す場合
                    if f"{param} (" in line:
                        param_description = line.strip()
                        break

            # 文字列の場合は "type": "string" のように入れる
            # 辞書の場合 (例: {"type": "array", "items": ...}) はそれを丸ごと使う
            param_schema: Dict[str, Any] = {"description": param_description}
            if isinstance(json_schema_type, str):
                # プリミティブ型の場合 ("string" / "number" / "boolean" / etc.)
                param_schema["type"] = json_schema_type
            elif isinstance(json_schema_type, dict):
                # 配列やオブジェクトの場合
                # {"type": "array", "items": ...} などをマージする
                param_schema.update(json_schema_type)

            parameters[param] = param_schema

        return parameters

    @staticmethod
    def extract_non_none_type_if_optional(typ: Any) -> Any:
        """
        与えられた型が Optional[T] (Union[T, NoneType]) であれば、
        NoneType 以外の型を取り出して返す。
        それ以外の場合はそのまま返す。
        """
        type_origin = get_origin(typ)
        type_args = get_args(typ)

        # Optional[T] は Union[T, NoneType] なので、Union かつ NoneType を含むかで判定
        if type_origin is Union and type(None) in type_args:
            not_none_args = [arg for arg in type_args if arg is not type(None)]
            if len(not_none_args) == 1:
                return not_none_args[0]
            else:
                # Union[int, str, NoneType] のように複数が含まれる場合は追加対応が必要
                raise ValueError(f"サポートされていない複数Union+NoneTypeです: {typ}")
        return typ

    @staticmethod
    def convert_python_type_to_json_schema_type(python_type: Any) -> Any:
        """
        Pythonの型をJSON Schemaの型または構造に変換する。
        Returnsには dict もしくは str を返す想定。
        """
        type_origin = get_origin(python_type)
        type_args = get_args(python_type)

        # 組み込みのプリミティブ型
        if python_type is str:
            return "string"
        elif python_type is int:
            return "integer"
        elif python_type is bool:
            return "boolean"
        elif python_type is float:
            return "number"

        # list, dict のようなコンテナ型
        if type_origin is list:
            # 例: list[int], list[dict[str, Any]] など
            if type_args:
                item_type = LLMToolParser.convert_python_type_to_json_schema_type(type_args[0])
            else:
                # 型引数が指定されていない場合は「items: {}」として「なんでもOK」
                return {
                    "type": "array",
                    "items": {}
                }

            if isinstance(item_type, str):
                # 要素型がプリミティブのとき → e.g. {"type": "array", "items": {"type": "string"}}
                return {
                    "type": "array",
                    "items": {"type": item_type}
                }
            elif isinstance(item_type, dict):
                # 要素型がさらに配列やオブジェクトなど複合型のとき
                return {
                    "type": "array",
                    "items": item_type
                }
            # 他パターン(Unionなど)は既に別途エラーにしているので省略

        elif type_origin is dict:
            # 例: dict[str, int]
            if len(type_args) == 2:
                key_type, value_type = type_args
                # key を string と断定するなど簡略化
                return {
                    "type": "object",
                    "additionalProperties": LLMToolParser.convert_python_type_to_json_schema_type(value_type),
                }
            else:
                # dict[...] だが型引数が足りないなど
                return {"type": "object"}

        # それ以外の Union 型 (Optional 以外)
        if type_origin is Union:
            # Optional[T] 以外の Union はサポート外
            raise ValueError(f"サポートされていない複数Unionです: {python_type}")

        # クラス型など、それ以外はサポート外
        raise ValueError(f"サポートされていない型です: {python_type}")

    @staticmethod
    def get_description(func: Callable, name: str) -> str:
        """
        関数の説明を取得する。
        docstring がなければエラーを発生させ、docstring 追加例を出力する。
        """
        if func.__doc__:
            return func.__doc__.strip()
        else:
            # docstringがない場合、エラーを発生させる
            type_hints = get_type_hints(func)
            # 引数の表示用
            arg_text = ", ".join([
                f"{p}: {t.__name__}" for p, t in type_hints.items() if p != 'return'
            ])
            return_type_name = type_hints['return'].__name__ if 'return' in type_hints else 'None'

            raise ValueError(
                f"関数 '{name}' にdocstringがありません。以下のようにdocstringを追加してください:\n\n"
                "現在の関数定義:\n"
                f"def {name}({arg_text}) -> {return_type_name}:\n"
                "    # ここにdocstringを追加してください\n"
                "    ...\n\n"
                "例:\n"
                f"def {name}({arg_text}) -> {return_type_name}:\n"
                '    """\n'
                f"    {name} の説明をここに記述します。\n\n"
                "    Args:\n"
                f"        {', '.join([f'{p} ({t.__name__}): {p}の説明' for p, t in type_hints.items() if p != 'return'])}\n\n"
                "    Returns:\n"
                f"        {return_type_name}: 戻り値の説明\n"
                '    """\n'
                "    ..."
            )

    @staticmethod
    def get_type_name(typ: Any) -> str:
        """
        Python の型オブジェクトや Union などから文字列表現を取り出す簡易ヘルパー。
        """
        type_origin = get_origin(typ)
        type_args = get_args(typ)

        if type_origin is Union:
            # 例: Union[int, str] → "int | str"
            return " | ".join(LLMToolParser.get_type_name(arg) for arg in type_args)
        if isinstance(typ, type):
            return typ.__name__
        return str(typ)


class LLMToolManager:
    def __init__(self):
        self.tools = []  # 登録されたツールのJSON Schemaを保持
        self.functions = dict()  # 登録された関数を保持

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
        func_name = name if name is not None else func.__qualname__
        self.functions[func_name] = func

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
        if func_name not in self.functions:
            raise ValueError(f"関数 '{func_name}' は登録されていません。")

        # 関数を取得
        func = self.functions[func_name]

        # 引数を関数に渡して実行
        return func(**arguments)
