"""Buffer側の予約実数から、サービス別の在庫計画を組み立てる。

在庫をローカルDBの記録から推定すると、Bufferが実際に保持している予約と
ずれたまま補充を続け、超過分が FAILED として積み上がる。基準はBufferの
`posts(status: scheduled)` と `limits.scheduledPosts` に置く。

取得に失敗したときは呼び出し側へ例外を通す。推定値へ退避してはならない。
"""

from collections.abc import Mapping
from typing import Any, Protocol

from social_caster.batch import ServiceStock, plan_service_stock
from social_caster.config import Settings


class ReservationReader(Protocol):
    def organization_id(self) -> str: ...

    def scheduled_post_limit(self, *, organization_id: str) -> int: ...

    def scheduled_posts(self, *, organization_id: str, channel_id: str) -> list[dict[str, Any]]: ...


def service_channels(settings: Settings) -> dict[str, str]:
    """予約枠を数える対象サービスとチャンネルID。

    Xは在庫管理の対象に含めない（ENABLE_TWITTER=false の運用で、APIキーからも参照できない）。
    """
    channels = {"instagram": settings.instagram_channel_id}
    if settings.enable_pinterest:
        channels["pinterest"] = settings.pinterest_channel_id
    return channels


def read_service_stock(
    client: ReservationReader, *, channels: Mapping[str, str], target_stock: int
) -> dict[str, ServiceStock]:
    organization_id = client.organization_id()
    limit = client.scheduled_post_limit(organization_id=organization_id)
    scheduled = {
        service: len(client.scheduled_posts(organization_id=organization_id, channel_id=channel_id))
        for service, channel_id in channels.items()
    }
    return plan_service_stock(scheduled=scheduled, limit=limit, target_stock=target_stock)
