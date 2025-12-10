from pyramid.interfaces import IRendererFactory

class RenderingConfiguratorMixin:
    def add_renderer(
        self,
        name: str,
        factory: IRendererFactory | str
    ) -> None: ...
