import asyncio
from typing import (  # noqa: F401
    List,
)

import pytest

from conftest import (
    generate_unique_name,
)
from lahja import (
    BaseEvent,
    BroadcastConfig,
    ConnectionConfig,
    Endpoint,
)


@pytest.mark.asyncio
async def test_subscribed_events(event_loop: asyncio.AbstractEventLoop) -> None:
    class TestSubscriptionEvent(BaseEvent):
        pass

    with Endpoint() as endpoint:
        endpoint.subscribe(TestSubscriptionEvent, lambda event: None)

        assert endpoint.subscribed_events == {TestSubscriptionEvent}

        class TestStreamEvent(BaseEvent):
            pass

        async def stream() -> None:
            async for _ in endpoint.stream(TestStreamEvent):  # noqa: F841
                pass

        future = asyncio.ensure_future(stream())
        await asyncio.sleep(0)  # give stream a chance to be scheduled

        assert endpoint.subscribed_events == {TestSubscriptionEvent, TestStreamEvent}

        future.cancel()


class TestEvent(BaseEvent):
    # This must be importable in order for it to be pickleable
    pass


@pytest.mark.asyncio
async def test_remote_subscribed_events(event_loop: asyncio.AbstractEventLoop) -> None:
    with Endpoint() as local, Endpoint() as remote:
        local.subscribe(TestEvent, lambda event: None)

        assert local.subscribed_events == {TestEvent}

        local_config = ConnectionConfig.from_name(generate_unique_name())
        await local.start_serving(local_config, event_loop)

        remote._loop = event_loop  # Endpoint assumes you'll serve before connecting
        await remote.connect_to_endpoints(local_config)

        proxy = remote._connected_endpoints[local_config.name]
        assert proxy.proxy.subscribed_events() == {TestEvent}


@pytest.mark.asyncio
async def test_can_wait_for_changes(event_loop: asyncio.AbstractEventLoop) -> None:
    with Endpoint() as local, Endpoint() as remote:
        assert local.subscribed_events == set()

        local_config = ConnectionConfig.from_name(generate_unique_name())
        await local.start_serving(local_config, event_loop)

        remote._loop = event_loop  # Endpoint assumes you'll serve before connecting
        await remote.connect_to_endpoints(local_config)

        proxy = remote._connected_endpoints[local_config.name]
        assert proxy.proxy.subscribed_events() == set()

        await asyncio.sleep(0.1)  # give the thread time to start

        local.subscribe(TestEvent, lambda event: None)

        await asyncio.sleep(0.1)  # give the thread time to update

        assert proxy.proxy.subscribed_events() == {TestEvent}


@pytest.mark.asyncio
async def test_filtered_messages_not_sent(event_loop: asyncio.AbstractEventLoop) -> None:
    "Test that messages we're not listening for are truly not sent"
    class MockEndpoint(Endpoint):
        def __init__(self) -> None:
            super().__init__()
            self.received_messages: List[BaseEvent] = []

        def _process_item(self, item: BaseEvent, config: BroadcastConfig) -> None:
            self.received_messages.append(item)

    with MockEndpoint() as local, Endpoint() as remote:
        local_config = ConnectionConfig.from_name(generate_unique_name())
        await local.start_serving(local_config, event_loop)

        remote_config = ConnectionConfig.from_name(generate_unique_name())
        await remote.start_serving(remote_config, event_loop)
        await remote.connect_to_endpoints(local_config)

        assert len(local.received_messages) == 0

        # We're not subscribed to the message so it better not be sent

        remote.broadcast(TestEvent())

        await asyncio.sleep(0.1)  # give the message time to propogate

        assert len(local.received_messages) == 0

        # Now, try subscribing to the message and see that it's sent

        local.subscribe(TestEvent, lambda event: None)

        await asyncio.sleep(0.1)  # give the thread time to update

        remote.broadcast(TestEvent())

        await asyncio.sleep(0.1)  # give the message time to propogate

        assert len(local.received_messages) == 1
