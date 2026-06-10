from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    CollectionStatusEntry,
    SectionCollectionStatus,
)

class CollectionStatus:
    def __init__(self) -> None:
        self.entries: list[CollectionStatusEntry] = []

    def add(self, component: str, target: str, status: str, message: str = "") -> None:
        self.entries.append(
            CollectionStatusEntry(
                component=component,
                target=target,
                status=status,
                message=message.replace("\n", " ").strip(),
            )
        )

    def ok(self, component: str, target: str, message: str = "") -> None:
        self.add(component, target, "OK", message)

    def warn(self, component: str, target: str, message: str = "") -> None:
        self.add(component, target, "WARN", message)

    def error(self, component: str, target: str, exc: Exception | str) -> None:
        self.add(component, target, "ERROR", str(exc))

    def skip(self, component: str, target: str, message: str = "") -> None:
        self.add(component, target, "SKIP", message)

    def section(self) -> SectionCollectionStatus:
        return SectionCollectionStatus(entries=self.entries)