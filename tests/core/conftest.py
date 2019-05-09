import uuid

import pytest

from lahja import (
    ConnectionConfig,
    Endpoint,
)


def generate_unique_name():
    # We use unique names to avoid clashing of IPC pipes
    return str(uuid.uuid4())


@pytest.fixture(scope='function')
async def endpoint():

    endpoint = Endpoint()
    await endpoint.start_serving(ConnectionConfig.from_name(generate_unique_name()))
    # We need to connect to our own Endpoint if we care about receiving
    # the events we broadcast. Many tests use the same Endpoint for
    # broadcasting and receiving which is a valid use case so we hook it up
    await endpoint.connect_to_endpoints(
        ConnectionConfig.from_name(endpoint.name),
    )
    try:
        yield endpoint
    finally:
        endpoint.stop()


@pytest.fixture(scope='function')
async def pair_of_endpoints():

    endpoint1 = Endpoint()
    endpoint2 = Endpoint()
    await endpoint1.start_serving(ConnectionConfig.from_name(generate_unique_name()))
    await endpoint2.start_serving(ConnectionConfig.from_name(generate_unique_name()))
    await endpoint1.connect_to_endpoints(
        ConnectionConfig.from_name(endpoint2.name),
    )
    await endpoint2.connect_to_endpoints(
        ConnectionConfig.from_name(endpoint1.name),
    )
    try:
        yield endpoint1, endpoint2
    finally:
        endpoint1.stop()
        endpoint2.stop()


@pytest.fixture(scope="function")
async def triplet_of_endpoints():

    endpoint1 = Endpoint()
    endpoint2 = Endpoint()
    endpoint3 = Endpoint()
    await endpoint1.start_serving(ConnectionConfig.from_name(generate_unique_name()))
    await endpoint2.start_serving(ConnectionConfig.from_name(generate_unique_name()))
    await endpoint3.start_serving(ConnectionConfig.from_name(generate_unique_name()))
    await endpoint1.connect_to_endpoints(
        ConnectionConfig.from_name(endpoint2.name),
        ConnectionConfig.from_name(endpoint3.name),
    )

    await endpoint2.connect_to_endpoints(
        ConnectionConfig.from_name(endpoint1.name),
        ConnectionConfig.from_name(endpoint3.name),
    )
    await endpoint3.connect_to_endpoints(
        ConnectionConfig.from_name(endpoint1.name),
        ConnectionConfig.from_name(endpoint2.name),
    )

    try:
        yield endpoint1, endpoint2, endpoint3
    finally:
        endpoint1.stop()
        endpoint2.stop()
        endpoint3.stop()
