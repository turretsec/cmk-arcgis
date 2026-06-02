class CollectionStatus:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def add(self, component: str, target: str, status: str, message: str = "") -> None:
        safe_message = message.replace("\n", " ").strip()
        if safe_message:
            self.lines.append(f"{component} {target} {status} {safe_message}")
        else:
            self.lines.append(f"{component} {target} {status}")

    def ok(self, component: str, target: str) -> None:
        self.add(component, target, "OK")

    def warn(self, component: str, target: str, message: str = "") -> None:
        self.add(component, target, "WARN", message)

    def error(self, component: str, target: str, exc: Exception | str) -> None:
        self.add(component, target, "ERROR", str(exc))

    def skip(self, component: str, target: str, message: str = "") -> None:
        self.add(component, target, "SKIP", message)