from typing import Any

class SettingsConfiguratorMixin:
    def add_settings(
        self,
        settings: dict[str, Any] | None = ...,
        **kw: str
    ) -> None: ...
    def get_settings(self) -> dict[str, Any]: ...
