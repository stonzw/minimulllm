from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from .function_call import doc
import html2text

class BrowserTool:
    def __init__(self):
        options = Options()
        options.add_argument('--headless')  # Run in headless mode.
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    @doc({
        "description": "現在のページのHTMLを返します。",
        "args": {},
        "returns": "現在のページのHTMLコンテンツ。",
    })
    def get(self) -> str:
        try:
            return self.driver.page_source
        except Exception as e:
            raise Exception(f"ページの取得に失敗しました: {e}")

    @doc({
        "description": "現在のページのHTMLをマークダウンとして返します。",
        "args": {},
        "returns": "現在のページ情報のマークダウン形式。",
    })
    def get_markdown(self) -> str:
        try:
            html_content = self.driver.page_source
            markdown_content = html2text.html2text(html_content)
            return markdown_content
        except Exception as e:
            raise Exception(f"ページの取得に失敗しました: {e}")

    @doc({
        "description": "指定されたURLにナビゲートしてページのHTMLをマークダウンとして取得します。",
        "args": {"url": "マークダウン形式で情報を取得するウェブページのURL。"},
        "returns": "ページ情報のマークダウン形式。",
    })
    def fetch_markdown(self, url: str) -> str:
        try:
            self.driver.get(url)
            html_content = self.driver.page_source
            markdown_content = html2text.html2text(html_content)
            return markdown_content
        except Exception as e:
            raise Exception(f"ページ '{url}' の取得に失敗しました: {e}")

    @doc({
        "description": "指定されたURLにナビゲートします。",
        "args": {"url": "目的のウェブページのURL。"},
        "returns": "ページのHTMLコンテンツ。",
    })
    def fetch(self, url: str) -> str:
        try:
            self.driver.get(url)
            return self.driver.page_source
        except Exception as e:
            raise Exception(f"ページ '{url}' の取得に失敗しました: {e}")

    @doc({
        "description": "指定された要素をクリックします。",
        "args": {
            "by": "検索メソッド。選択肢は 'CLASS_NAME', 'CSS_SELECTOR', 'ID', 'LINK_TEXT', 'NAME', 'PARTIAL_LINK_TEXT', 'TAG_NAME', 'XPATH' など。",
            "value": "要素を見つけるための値。"
        },
        "returns": "成功したかどうか。",
    })
    def click(self, by: str, value: str) -> bool:
        try:
            element = self.driver.find_element(by=By(by), value=value)
            element.click()
            return True
        except Exception as e:
            raise Exception(f"要素 '{value}' のクリックに失敗しました: {e}")

    @doc({
        "description": "指定された要素のテキストを取得します。",
        "args": {
            "by": "検索メソッド。選択肢は 'CLASS_NAME', 'CSS_SELECTOR', 'ID', 'LINK_TEXT', 'NAME', 'PARTIAL_LINK_TEXT', 'TAG_NAME', 'XPATH' など。",
            "value": "要素を見つけるための値。"
        },
        "returns": "要素のテキスト。",
    })
    def get_element_text(self, by: str, value: str) -> str:
        try:
            element = self.driver.find_element(by=By(by), value=value)
            return element.text
        except Exception as e:
            raise Exception(f"要素 '{value}' のテキスト取得に失敗しました: {e}")

    @doc({
        "description": "ブラウザを閉じます。",
        "args": {},
        "returns": "ブラウザが正常に閉じたかどうか。",
    })
    def close(self) -> bool:
        try:
            self.driver.quit()
            return True
        except Exception as e:
            raise Exception(f"ブラウザの終了に失敗しました: {e}")
