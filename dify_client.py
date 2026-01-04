"""
Dify Chat API Client
支援 streaming 和 blocking 模式
"""

import os
import json
import httpx
from typing import Generator, Optional


class DifyClient:
    """Dify Chat API 客戶端"""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
    ):
        self.api_key = api_key or os.environ.get("DIFY_API_KEY")
        self.base_url = (base_url or os.environ.get("DIFY_BASE_URL", "https://api.dify.ai/v1")).rstrip("/")

        if not self.api_key:
            raise ValueError("DIFY_API_KEY is required")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(
        self,
        query: str,
        user: str,
        conversation_id: Optional[str] = None,
        inputs: Optional[dict] = None,
        files: Optional[list] = None,
    ) -> dict:
        """
        Blocking 模式發送聊天訊息

        Args:
            query: 用戶問題
            user: 用戶識別碼
            conversation_id: 對話 ID（用於延續對話）
            inputs: 額外輸入變數
            files: 檔案列表

        Returns:
            完整的回應 dict
        """
        payload = {
            "query": query,
            "user": user,
            "response_mode": "blocking",
            "inputs": inputs or {},
        }

        if conversation_id:
            payload["conversation_id"] = conversation_id

        if files:
            payload["files"] = files

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.base_url}/chat-messages",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def chat_stream(
        self,
        query: str,
        user: str,
        conversation_id: Optional[str] = None,
        inputs: Optional[dict] = None,
        files: Optional[list] = None,
    ) -> Generator[dict, None, None]:
        """
        Streaming 模式發送聊天訊息

        Args:
            query: 用戶問題
            user: 用戶識別碼
            conversation_id: 對話 ID（用於延續對話）
            inputs: 額外輸入變數
            files: 檔案列表

        Yields:
            每個 SSE 事件的 dict
        """
        payload = {
            "query": query,
            "user": user,
            "response_mode": "streaming",
            "inputs": inputs or {},
        }

        if conversation_id:
            payload["conversation_id"] = conversation_id

        if files:
            payload["files"] = files

        with httpx.Client(timeout=120.0) as client:
            with client.stream(
                "POST",
                f"{self.base_url}/chat-messages",
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # 移除 "data: " 前綴
                        if data.strip():
                            try:
                                yield json.loads(data)
                            except json.JSONDecodeError:
                                continue

    def chat_complete(
        self,
        query: str,
        user: str,
        conversation_id: Optional[str] = None,
        inputs: Optional[dict] = None,
        files: Optional[list] = None,
        stream: bool = True,
    ) -> tuple[str, str]:
        """
        便捷方法：發送訊息並返回完整回應

        Args:
            query: 用戶問題
            user: 用戶識別碼
            conversation_id: 對話 ID
            inputs: 額外輸入變數
            files: 檔案列表
            stream: 是否使用 streaming 模式

        Returns:
            (answer, conversation_id) 元組
        """
        if stream:
            answer_parts = []
            final_conversation_id = conversation_id

            for event in self.chat_stream(
                query=query,
                user=user,
                conversation_id=conversation_id,
                inputs=inputs,
                files=files,
            ):
                event_type = event.get("event")

                if event_type == "message":
                    # 累積回應文字
                    answer_parts.append(event.get("answer", ""))
                    # 獲取 conversation_id
                    if not final_conversation_id:
                        final_conversation_id = event.get("conversation_id")

                elif event_type == "message_end":
                    # 獲取最終的 conversation_id
                    final_conversation_id = event.get("conversation_id", final_conversation_id)

                elif event_type == "error":
                    raise Exception(f"Dify error: {event.get('message', 'Unknown error')}")

            return "".join(answer_parts), final_conversation_id

        else:
            result = self.chat(
                query=query,
                user=user,
                conversation_id=conversation_id,
                inputs=inputs,
                files=files,
            )
            return result.get("answer", ""), result.get("conversation_id", "")


# 簡易測試
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    client = DifyClient()

    print("Testing blocking mode...")
    answer, conv_id = client.chat_complete(
        query="你好，請自我介紹",
        user="test-user",
        stream=False,
    )
    print(f"Answer: {answer}")
    print(f"Conversation ID: {conv_id}")

    print("\nTesting streaming mode...")
    answer, conv_id = client.chat_complete(
        query="繼續聊聊",
        user="test-user",
        conversation_id=conv_id,
        stream=True,
    )
    print(f"Answer: {answer}")
    print(f"Conversation ID: {conv_id}")
