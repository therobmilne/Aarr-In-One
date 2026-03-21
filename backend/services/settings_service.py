import json
from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.setting import AppSetting


async def get_setting(db: AsyncSession, key: str, default: Any = None) -> Any:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        return default
    try:
        return json.loads(setting.value)
    except (json.JSONDecodeError, TypeError):
        return setting.value


async def set_setting(
    db: AsyncSession, key: str, value: Any, category: str = "general"
) -> AppSetting:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()

    value_str = json.dumps(value) if not isinstance(value, str) else value

    if setting is None:
        setting = AppSetting(key=key, value=value_str, category=category)
        db.add(setting)
    else:
        setting.value = value_str
        setting.category = category

    await db.flush()
    return setting


async def get_all_settings(db: AsyncSession, category: str | None = None) -> dict[str, Any]:
    query = select(AppSetting)
    if category:
        query = query.where(AppSetting.category == category)

    result = await db.execute(query)
    settings_dict = {}
    for setting in result.scalars().all():
        try:
            settings_dict[setting.key] = json.loads(setting.value)
        except (json.JSONDecodeError, TypeError):
            settings_dict[setting.key] = setting.value
    return settings_dict


async def delete_setting(db: AsyncSession, key: str) -> bool:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        await db.delete(setting)
        return True
    return False
