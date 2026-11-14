"""Image library delivery; only signed or authenticated requests reach it."""

from __future__ import annotations

from aiohttp import web

from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.config_entries import ConfigEntryState

from .const import DOMAIN, IMAGE_URL
from .store import image_dir, valid_image_name


class ImageView(HomeAssistantView):
    """Serve images of the library."""

    url = IMAGE_URL + "/{name}"
    name = f"api:{DOMAIN}:image"
    requires_auth = True

    async def get(self, request: web.Request, name: str) -> web.StreamResponse:
        """Return one image."""
        hass = request.app[KEY_HASS]
        entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]
        if not entries or not valid_image_name(name):
            raise web.HTTPNotFound
        path = image_dir(hass, entries[0]) / name
        if not await hass.async_add_executor_job(path.is_file):
            raise web.HTTPNotFound
        return web.FileResponse(path)
