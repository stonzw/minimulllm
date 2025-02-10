from .browser_tool import BrowserTool
from .function_call import doc
import urllib.parse

class WebSearchTool(BrowserTool):
    @doc({
        "description": "DuckDuckGoで指定されたクエリを含むURLを使用して検索を行い、結果ページのHTMLをマークダウンとして返します。",
        "args": {"query": "検索クエリ。"},
        "returns": "DuckDuckGo検索結果のページのマークダウン形式。",
    })
    def search_duckduckgo(self, query: str) -> str:
        try:
            base_url = 'https://duckduckgo.com/?q='
            encoded_query = urllib.parse.quote(query)
            full_url = base_url + encoded_query
            return self.fetch_markdown(full_url)
        except Exception as e:
            raise Exception(f"DuckDuckGo検索中にエラーが発生しました: {e}")

    @doc({
        "description": "Yahooで指定されたクエリを含むURLを使用して検索を行い、結果ページのHTMLをマークダウンとして返します。",
        "args": {"query": "検索クエリ。"},
        "returns": "Yahoo検索結果のページのマークダウン形式。",
    })
    def search_yahoo(self, query: str) -> str:
        try:
            base_url = 'https://search.yahoo.com/search?p='
            encoded_query = urllib.parse.quote(query)
            full_url = base_url + encoded_query
            return self.fetch_markdown(full_url)
        except Exception as e:
            raise Exception(f"Yahoo検索中にエラーが発生しました: {e}")

# Example usage
if __name__ == "__main__":
    tool = WebSearchTool()
    duckduckgo_results = tool.search_duckduckgo("OpenAI")
    print("DuckDuckGo検索結果:")
    print(duckduckgo_results)
    
    yahoo_results = tool.search_yahoo("OpenAI")
    print("Yahoo検索結果:")
    print(yahoo_results)
