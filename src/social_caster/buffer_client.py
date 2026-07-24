"""Small standard-library GraphQL client for the current Buffer API."""

import json
from typing import Any, cast
from urllib.request import Request, urlopen


class BufferApiError(RuntimeError):
    """Raised for transport, GraphQL, or typed Buffer mutation errors."""


class BufferClient:
    endpoint = "https://api.buffer.com"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
        request = Request(
            self.endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                result = json.load(response)
        except OSError as exc:
            raise BufferApiError(f"Buffer APIへの接続に失敗しました: {exc}") from exc

        if result.get("errors"):
            messages = "; ".join(str(error.get("message", error)) for error in result["errors"])
            raise BufferApiError(messages)
        return cast(dict[str, Any], result.get("data", {}))

    def create_post(
        self,
        *,
        channel_id: str,
        text: str,
        image_url: str,
        due_at: str | None = None,
    ) -> str:
        mode = "customScheduled" if due_at else "addToQueue"
        due_at_input = f', dueAt: "{due_at}"' if due_at else ""
        query = f"""
        mutation CreatePost {{
          createPost(input: {{
            text: {json.dumps(text)}
            channelId: {json.dumps(channel_id)}
            schedulingType: automatic
            mode: {mode}{due_at_input}
            assets: [{{ image: {{ url: {json.dumps(image_url)} }} }}]
          }}) {{
            ... on PostActionSuccess {{ post {{ id }} }}
            ... on MutationError {{ message }}
          }}
        }}
        """
        payload = self.execute(query)
        result = payload.get("createPost", {})
        if "message" in result:
            raise BufferApiError(str(result["message"]))
        post_id = result.get("post", {}).get("id")
        if not post_id:
            raise BufferApiError("Buffer APIから投稿IDが返されませんでした")
        return str(post_id)

    def get_account(self) -> dict[str, Any]:
        return self.execute("""
        query GetAccount {
          account { id name organizations { id name } }
        }
        """)

    def get_channels(self, organization_id: str) -> list[dict[str, str]]:
        data = self.execute(
            """
            query GetChannels($organizationId: OrganizationId!) {
              channels(input: { organizationId: $organizationId }) {
                id name service
              }
            }
            """,
            {"organizationId": organization_id},
        )
        channels = data.get("channels", [])
        return [
            {
                "id": str(channel["id"]),
                "name": str(channel["name"]),
                "service": str(channel["service"]),
            }
            for channel in channels
        ]
