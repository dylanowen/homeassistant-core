"""The tests for the image component."""
from http import HTTPStatus
from unittest.mock import patch

from aiohttp import hdrs
import pytest

from homeassistant.components import image
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .conftest import (
    MockImageEntity,
    MockImageNoStateEntity,
    MockImagePlatform,
    MockImageSyncEntity,
)

from tests.common import MockModule, mock_integration, mock_platform
from tests.typing import ClientSessionGenerator


@pytest.mark.freeze_time("2023-04-01 00:00:00+00:00")
async def test_state(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, mock_image_platform
) -> None:
    """Test image state."""
    state = hass.states.get("image.test")
    assert state.state == "2023-04-01T00:00:00+00:00"
    access_token = state.attributes["access_token"]
    assert state.attributes == {
        "access_token": access_token,
        "entity_picture": f"/api/image_proxy/image.test?token={access_token}",
        "friendly_name": "Test",
    }


@pytest.mark.freeze_time("2023-04-01 00:00:00+00:00")
async def test_config_entry(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, mock_image_config_entry
) -> None:
    """Test setting up an image platform from a config entry."""
    state = hass.states.get("image.test")
    assert state.state == "2023-04-01T00:00:00+00:00"
    access_token = state.attributes["access_token"]
    assert state.attributes == {
        "access_token": access_token,
        "entity_picture": f"/api/image_proxy/image.test?token={access_token}",
        "friendly_name": "Test",
    }


@pytest.mark.freeze_time("2023-04-01 00:00:00+00:00")
async def test_state_attr(
    hass: HomeAssistant, hass_client: ClientSessionGenerator
) -> None:
    """Test image state with entity picture from attr."""
    mock_integration(hass, MockModule(domain="test"))
    entity = MockImageEntity()
    entity._attr_entity_picture = "abcd"
    mock_platform(hass, "test.image", MockImagePlatform([entity]))
    assert await async_setup_component(
        hass, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await hass.async_block_till_done()

    state = hass.states.get("image.test")
    assert state.state == "2023-04-01T00:00:00+00:00"
    access_token = state.attributes["access_token"]
    assert state.attributes == {
        "access_token": access_token,
        "entity_picture": "abcd",
        "friendly_name": "Test",
    }


async def test_no_state(
    hass: HomeAssistant, hass_client: ClientSessionGenerator
) -> None:
    """Test image state."""
    mock_integration(hass, MockModule(domain="test"))
    mock_platform(hass, "test.image", MockImagePlatform([MockImageNoStateEntity()]))
    assert await async_setup_component(
        hass, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await hass.async_block_till_done()

    state = hass.states.get("image.test")
    assert state.state == "unknown"
    access_token = state.attributes["access_token"]
    assert state.attributes == {
        "access_token": access_token,
        "entity_picture": f"/api/image_proxy/image.test?token={access_token}",
        "friendly_name": "Test",
    }


async def test_fetch_image_authenticated(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, mock_image_platform
) -> None:
    """Test fetching an image with an authenticated client."""
    client = await hass_client()

    resp = await client.get("/api/image_proxy/image.test")
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body == b"Test"

    resp = await client.get("/api/image_proxy/image.unknown")
    assert resp.status == HTTPStatus.NOT_FOUND


async def test_fetch_image_fail(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, mock_image_platform
) -> None:
    """Test fetching an image with an authenticated client."""
    client = await hass_client()

    with patch.object(MockImageEntity, "async_image", side_effect=TimeoutError):
        resp = await client.get("/api/image_proxy/image.test")
        assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR


async def test_fetch_image_sync(
    hass: HomeAssistant, hass_client: ClientSessionGenerator
) -> None:
    """Test fetching an image with an authenticated client."""
    mock_integration(hass, MockModule(domain="test"))
    mock_platform(hass, "test.image", MockImagePlatform([MockImageSyncEntity()]))
    assert await async_setup_component(
        hass, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await hass.async_block_till_done()

    client = await hass_client()

    resp = await client.get("/api/image_proxy/image.test")
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body == b"Test"


async def test_fetch_image_unauthenticated(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_image_platform,
) -> None:
    """Test fetching an image with an unauthenticated client."""
    client = await hass_client_no_auth()

    resp = await client.get("/api/image_proxy/image.test")
    assert resp.status == HTTPStatus.FORBIDDEN

    resp = await client.get("/api/image_proxy/image.test")
    assert resp.status == HTTPStatus.FORBIDDEN

    resp = await client.get(
        "/api/image_proxy/image.test", headers={hdrs.AUTHORIZATION: "blabla"}
    )
    assert resp.status == HTTPStatus.UNAUTHORIZED

    state = hass.states.get("image.test")
    resp = await client.get(state.attributes["entity_picture"])
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body == b"Test"

    resp = await client.get("/api/image_proxy/image.unknown")
    assert resp.status == HTTPStatus.NOT_FOUND
