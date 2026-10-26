import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from urllib.parse import urlparse

router = APIRouter()


def normalize_url(url: str) -> str:
    """
    Normalize URL to ensure it has a proper protocol.
    If no protocol is specified, default to https://
    """
    url = url.strip()
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Check if we have a scheme
    if not parsed.scheme:
        # No scheme, add https://
        url = f"https://{url}"
    elif parsed.scheme in ['http', 'https']:
        # Valid scheme, keep as is
        pass
    else:
        # Check if this might be a domain with port (like example.com:8080)
        # urlparse treats this as scheme:netloc, but we want to handle it as domain:port
        if ':' in url and not url.startswith(('http://', 'https://', 'ftp://', 'file://')):
            # Likely a domain:port without protocol
            url = f"https://{url}"
        else:
            # Invalid protocol
            raise ValueError(f"Unsupported protocol: {parsed.scheme}")
    
    return url


def bytes_to_data_url(image_bytes: bytes, mime_type: str) -> str:
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{base64_image}"


async def capture_screenshot(
    target_url: str, api_key: str | None = None, device: str = "desktop"
) -> bytes:
    # 1. Custom ScreenshotOne API key if provided
    if api_key and api_key.strip():
        try:
            api_base_url = "https://api.screenshotone.com/take"
            params = {
                "access_key": api_key.strip(),
                "url": target_url,
                "full_page": "true",
                "device_scale_factor": "1",
                "format": "png",
                "block_ads": "true",
                "block_cookie_banners": "true",
                "block_trackers": "true",
                "cache": "false",
                "viewport_width": "1280" if device == "desktop" else "375",
                "viewport_height": "832" if device == "desktop" else "812",
            }
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.get(api_base_url, params=params)
                if response.status_code == 200 and response.content:
                    return response.content
        except Exception as exc:
            print(f"[SCREENSHOT] ScreenshotOne error: {exc}")

    # 2. Microlink cloud screenshot (instant, free, 0 MB server memory)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            m_resp = await client.get(
                f"https://api.microlink.io?url={target_url}&screenshot=true&meta=false"
            )
            data = m_resp.json()
            img_url = data.get("data", {}).get("screenshot", {}).get("url")
            if img_url:
                img_resp = await client.get(img_url, timeout=30)
                if img_resp.status_code == 200 and img_resp.content:
                    return img_resp.content
    except Exception as exc:
        print(f"[SCREENSHOT] Microlink error: {exc}")

    # 3. thum.io cloud screenshot fallback (instant, free, 0 MB server memory)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            thum_resp = await client.get(
                f"https://image.thum.io/get/width/1280/{target_url}",
                timeout=30,
                follow_redirects=True,
            )
            if thum_resp.status_code == 200 and thum_resp.content:
                return thum_resp.content
    except Exception as exc:
        print(f"[SCREENSHOT] thum.io error: {exc}")

    raise Exception("Failed to capture website screenshot from URL")


class ScreenshotRequest(BaseModel):
    url: str
    apiKey: str | None = None


class ScreenshotResponse(BaseModel):
    url: str


@router.post("/api/screenshot")
async def app_screenshot(request: ScreenshotRequest):
    # Extract the URL from the request body
    url = request.url
    api_key = request.apiKey

    try:
        # Normalize the URL
        normalized_url = normalize_url(url)
        
        # Capture screenshot with normalized URL
        image_bytes = await capture_screenshot(normalized_url, api_key=api_key)

        # Convert the image bytes to a data url
        data_url = bytes_to_data_url(image_bytes, "image/png")

        return ScreenshotResponse(url=data_url)
    except ValueError as e:
        # Handle URL normalization errors
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Handle other errors
        raise HTTPException(status_code=500, detail=f"Error capturing screenshot: {str(e)}")
