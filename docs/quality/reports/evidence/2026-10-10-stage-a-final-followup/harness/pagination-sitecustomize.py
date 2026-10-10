"""QA-only synthetic materials fixture; loaded only for the follow-up Fake run."""
from datetime import datetime

from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.integrations.feishu.provider import Material, MaterialPage

_original_materials = FakeFeishu.materials


def _qa_materials(self, credentials, query, visibility, cursor, limit):
    original = _original_materials(self, credentials, query, visibility, None, 30)
    base = [
        Material(
            material_id=f"qa-minute-{index:02d}",
            title=f"Synthetic pagination item {index:02d}",
            visibility="owner" if index % 2 else "shared",
            updated_at=datetime.fromisoformat("2026-10-09T08:00:00+08:00"),
        )
        for index in range(1, 25)
    ]
    all_rows = list(original.items) + base
    selected = [
        row
        for row in all_rows
        if query.casefold() in row.title.casefold()
        and (visibility is None or visibility == row.visibility)
    ]
    offset = int(cursor.removeprefix("fake-page-")) if cursor else 0
    end = offset + limit
    next_cursor = f"fake-page-{end}" if end < len(selected) else None
    return MaterialPage(items=selected[offset:end], next_cursor=next_cursor)


FakeFeishu.materials = _qa_materials
