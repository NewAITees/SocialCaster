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
        service: str | None = None,
        board_service_id: str | None = None,
        title: str | None = None,
        destination_url: str | None = None,
    ) -> str:
        mode = "customScheduled" if due_at else "addToQueue"
        due_at_input = f', dueAt: "{due_at}"' if due_at else ""
        if service == "instagram":
            metadata = "metadata: { instagram: { type: post, shouldShareToFeed: true } }"
        elif service == "pinterest":
            if not board_service_id or not title or not destination_url:
                raise ValueError("Pinterest投稿にはボードID・タイトル・リンク先が必要です")
            metadata = (
                "metadata: { pinterest: { "
                f"boardServiceId: {json.dumps(board_service_id)}, "
                f"title: {json.dumps(title, ensure_ascii=False)}, "
                f"url: {json.dumps(destination_url)}"
                " } }"
            )
        else:
            metadata = ""
        query = f"""
        mutation CreatePost {{
          createPost(input: {{
            text: {json.dumps(text)}
            channelId: {json.dumps(channel_id)}
            schedulingType: automatic
            mode: {mode}{due_at_input}
            assets: [{{ image: {{ url: {json.dumps(image_url)} }} }}]
            {metadata}
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

    def scheduled_posts(self, *, organization_id: str, channel_id: str) -> list[dict[str, Any]]:
        """チャンネルの予約済み投稿をBufferから全件取得する。

        `posts` は totalCount を返さないため、Relayのカーソルを辿ってedgesを集める。
        在庫の判断はローカルDBの記録ではなくこの実数を基準にする。
        """
        query = """
        query ScheduledPosts($input: PostsInput!, $after: String) {
          posts(input: $input, first: 100, after: $after) {
            edges { node { id dueAt status } }
            pageInfo { hasNextPage endCursor }
          }
        }
        """
        nodes: list[dict[str, Any]] = []
        after: str | None = None
        while True:
            # 送信済みの変数を書き換えないため、ページごとに組み立てる。
            page = (
                self.execute(
                    query,
                    {
                        "input": {
                            "organizationId": organization_id,
                            "filter": {
                                "channelIds": [channel_id],
                                "status": ["scheduled"],
                            },
                        },
                        "after": after,
                    },
                ).get("posts")
                or {}
            )
            for edge in page.get("edges") or []:
                node = edge.get("node")
                if node:
                    nodes.append(cast(dict[str, Any], node))
            page_info = page.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                return nodes
            after = page_info.get("endCursor")

    def scheduled_post_limit(self, *, organization_id: str) -> int:
        """組織の予約枠上限を返す。

        スキーマの説明は組織単位だが、実際の適用はチャンネル単位である
        （Instagram 6件とPinterest 9件が同時に成立し、合計15件が上限10を超えている）。
        呼び出し側はサービスごとの上限として扱う。
        """
        data = self.execute("""
        query ScheduledPostLimit {
          account { organizations { id limits { scheduledPosts } } }
        }
        """)
        organizations = (data.get("account") or {}).get("organizations") or []
        for organization in organizations:
            if str(organization.get("id")) != organization_id:
                continue
            limit = (organization.get("limits") or {}).get("scheduledPosts")
            if limit is None:
                raise BufferApiError(f"Bufferが予約枠上限を返しませんでした: {organization_id}")
            return int(limit)
        raise BufferApiError(f"Buffer APIに組織が見つかりません: {organization_id}")
