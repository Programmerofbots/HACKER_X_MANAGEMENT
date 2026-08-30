import os
import asyncio
import tempfile
from datetime import datetime

from PIL import Image
import requests
from telegraph import Telegraph

from FallenRobot import LOGGER, telethn as tbot
from FallenRobot.events import register

Anonymous = "Fallen"
TMP_DOWNLOAD_DIRECTORY = "./"
telegraph = Telegraph()


def _telegraph_url(path):
    if not path:
        raise RuntimeError("Telegraph upload returned an empty response")
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return "https://telegra.ph/" + path.lstrip("/")


def _safe_telegraph_upload(file_path):
    try:
        with open(file_path, "rb") as media_file:
            response = requests.post(
                "https://telegra.ph/upload",
                files={
                    "file": (
                        "image.png",
                        media_file,
                        "image/png",
                    )
                },
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=60,
            )
        if not response.ok:
            raise RuntimeError(
                "Telegraph returned HTTP {}: {}".format(
                    response.status_code, response.text[:300]
                )
            )
        result = response.json()
    except Exception as exc:
        LOGGER.warning("Telegraph upload failed: %s", exc)
        raise

    if isinstance(result, dict):
        if "error" in result:
            raise RuntimeError(str(result["error"]))
        if "src" in result:
            return _telegraph_url(result["src"])
        if "url" in result:
            return _telegraph_url(result["url"])

    if isinstance(result, str):
        return _telegraph_url(result)

    if isinstance(result, (list, tuple)):
        if not result:
            raise RuntimeError("Telegraph upload returned an empty response")
        first_result = result[0]
        if isinstance(first_result, dict):
            return _safe_telegraph_upload_result(first_result)
        if isinstance(first_result, str):
            return _telegraph_url(first_result)

    raise RuntimeError("Telegraph upload returned an unexpected response format")


def _safe_telegraph_upload_result(result):
    if "error" in result:
        raise RuntimeError(str(result["error"]))
    if "src" in result:
        return _telegraph_url(result["src"])
    if "url" in result:
        return _telegraph_url(result["url"])
    raise RuntimeError("Telegraph upload returned an unexpected response format")


def _get_telegraph():
    if not telegraph.access_token:
        account = telegraph.create_account(short_name=Anonymous)
        telegraph.access_token = account["access_token"]
    return telegraph


def _prepare_media_for_upload(file_path):
    try:
        with Image.open(file_path) as image:
            image.seek(0)
            if image.mode in ("RGBA", "LA", "P"):
                image = image.convert("RGBA")
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
            max_size = 2000
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            file_handle, upload_path = tempfile.mkstemp(
                suffix=".jpg", prefix="telegraph_upload_"
            )
            os.close(file_handle)
            image.save(upload_path, "JPEG", quality=85, optimize=True)
    except Exception as exc:
        raise RuntimeError("This media format cannot be uploaded to Telegraph") from exc
    return upload_path


@register(pattern="^/tg(m|t) ?(.*)")
async def _(event):
    if event.fwd_from:
        return
    optional_title = event.pattern_match.group(2)
    if event.reply_to_msg_id:
        start = datetime.now()
        r_message = await event.get_reply_message()
        input_str = event.pattern_match.group(1)
        if input_str == "m":
            downloaded_file_name = await tbot.download_media(
                r_message, TMP_DOWNLOAD_DIRECTORY
            )
            end = datetime.now()
            ms = (end - start).seconds
            h = await event.reply(
                "Downloaded to {} in {} seconds.".format(downloaded_file_name, ms)
            )
            try:
                upload_file_name = _prepare_media_for_upload(downloaded_file_name)
                start = datetime.now()
                media_url = await asyncio.to_thread(
                    _safe_telegraph_upload, upload_file_name
                )
            except Exception as exc:
                LOGGER.warning("Telegraph file upload failed: %s", exc)
                await h.edit(
                    "ERROR: This media cannot be uploaded to Telegraph right now."
                )
                if os.path.exists(downloaded_file_name):
                    os.remove(downloaded_file_name)
                if (
                    "upload_file_name" in locals()
                    and upload_file_name != downloaded_file_name
                    and os.path.exists(upload_file_name)
                ):
                    os.remove(upload_file_name)
            else:
                end = datetime.now()
                (end - start).seconds
                if os.path.exists(downloaded_file_name):
                    os.remove(downloaded_file_name)
                if upload_file_name != downloaded_file_name and os.path.exists(upload_file_name):
                    os.remove(upload_file_name)
                await h.edit(
                    "Uploaded to {}".format(media_url),
                    link_preview=True,
                )
        elif input_str == "t":
            user_object = await tbot.get_entity(r_message.sender_id)
            title_of_page = user_object.first_name  # + " " + user_object.last_name
            # apparently, all Users do not have last_name field
            if optional_title:
                title_of_page = optional_title
            page_content = r_message.message
            if r_message.media:
                if page_content != "":
                    title_of_page = page_content
                downloaded_file_name = await tbot.download_media(
                    r_message, TMP_DOWNLOAD_DIRECTORY
                )
                m_list = None
                with open(downloaded_file_name, "rb") as fd:
                    m_list = fd.readlines()
                for m in m_list:
                    page_content += m.decode("UTF-8") + "\n"
                os.remove(downloaded_file_name)
            page_content = page_content.replace("\n", "<br>")
            response = _get_telegraph().create_page(
                title_of_page, html_content=page_content
            )
            end = datetime.now()
            ms = (end - start).seconds
            await event.reply(
                "Pasted to https://telegra.ph/{} in {} seconds.".format(
                    response["path"], ms
                ),
                link_preview=True,
            )
    else:
        await event.reply("Reply to a message to get a permanent telegra.ph link.")


def resize_image(image):
    im = Image.open(image)
    im.save(image, "PNG")


__help__ = """
I can upload files to Telegraph
 ❍ /tgm :Get Telegraph Link Of Replied Media
 ❍ /tgt :Get Telegraph Link of Replied Text
 ❍ /tgt [custom name]: Get telegraph link of replied text with custom name.
"""

__mod_name__ = "T-Gʀᴀᴘʜ"
