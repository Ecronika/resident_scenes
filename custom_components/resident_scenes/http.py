"""Image delivery and upload; only signed or authenticated requests reach them."""

from __future__ import annotations

from http import HTTPStatus

from aiohttp import web

from homeassistant.components.http import KEY_HASS, KEY_HASS_USER, HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import CONF_IMAGE_KB, DOMAIN, IMAGE_URL, PHOTO_URL, UPLOAD_URL
from .model import ValidationError, can_edit, opt
from .store import SceneStore, image_dir, upload_dir, valid_image_name, valid_upload_id

MAX_REQUEST = 4 * 1024 * 1024  # the card shrinks images before upload; this is just a stop


def _store(hass: HomeAssistant) -> SceneStore:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry.runtime_data
    raise web.HTTPNotFound


async def _file(hass: HomeAssistant, path) -> web.FileResponse:
    if not await hass.async_add_executor_job(path.is_file):
        raise web.HTTPNotFound
    # URLs change when they are signed again, so the browser may keep an image for a day
    return web.FileResponse(path, headers={"Cache-Control": "private, max-age=86400"})


class ImageView(HomeAssistantView):
    """Serve images of the library."""

    url = IMAGE_URL + "/{name}"
    name = f"api:{DOMAIN}:image"
    requires_auth = True

    async def get(self, request: web.Request, name: str) -> web.StreamResponse:
        """Return one library image."""
        hass = request.app[KEY_HASS]
        store = _store(hass)
        if not valid_image_name(name):
            raise web.HTTPNotFound
        return await _file(hass, image_dir(hass, store.entry) / name)


class PhotoView(HomeAssistantView):
    """Serve images uploaded by residents."""

    url = PHOTO_URL + "/{upload_id}"
    name = f"api:{DOMAIN}:photo"
    requires_auth = True

    async def get(self, request: web.Request, upload_id: str) -> web.StreamResponse:
        """Return one uploaded image."""
        hass = request.app[KEY_HASS]
        _store(hass)
        if not valid_upload_id(upload_id):
            raise web.HTTPNotFound
        return await _file(hass, upload_dir(hass) / upload_id)


class UploadView(HomeAssistantView):
    """Accept a scene image from an account with edit right."""

    url = UPLOAD_URL
    name = f"api:{DOMAIN}:upload"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Store an uploaded image (field 'file') and return its image name and URL."""
        hass = request.app[KEY_HASS]
        store = _store(hass)
        if not can_edit(store.entry, request[KEY_HASS_USER]):
            return self.json_message("No permission to edit scenes", HTTPStatus.FORBIDDEN, "unauthorized")
        if (request.content_length or 0) > MAX_REQUEST:
            return self.json_message("Too large", HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "image_too_large")
        try:
            data = await request.post()
            field = data.get("file")
            if not isinstance(field, web.FileField):
                raise ValidationError("invalid_image_file")
            content = await hass.async_add_executor_job(field.file.read, MAX_REQUEST)
            image = await store.async_add_upload(content)
        except ValidationError as err:
            message = f"{err.code}: {opt(store.entry, CONF_IMAGE_KB)} kB" if err.code == "image_too_large" else err.code
            return self.json_message(message, HTTPStatus.BAD_REQUEST, err.code)
        return self.json({"image": image, "url": store.sign(image)})
