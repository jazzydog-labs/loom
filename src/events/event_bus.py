class EventBus:
    """Simple in-process event bus."""

    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_name: str, handler):
        self.subscribers.setdefault(event_name, []).append(handler)

    def publish(self, event_name: str, payload=None) -> str:
        # Just log for now
        for handler in self.subscribers.get(event_name, []):
            handler(payload)
        return f"TODO: publish {event_name}"
