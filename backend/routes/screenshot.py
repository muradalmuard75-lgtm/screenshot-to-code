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


async def capture_with_playwright(target_url: str, device: str = "desktop") -> bytes:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 832} if device == "desktop" else {"width": 375, "height": 812},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        try:
            await page.goto(target_url, wait_until="networkidle", timeout=25000)
        except Exception:
            pass
        await page.wait_for_timeout(1000)
        image_bytes = await page.screenshot(full_page=True, type="png")
        await browser.close()
        return image_bytes


async def capture_screenshot(
    target_url: str, api_key: str | None = None, device: str = "desktop"
) -> bytes:
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
            print(f"[SCREENSHOT] ScreenshotOne error: {exc}, using free Playwright capture")

    try:
        return await capture_with_playwright(target_url, device=device)
    except Exception as exc:
        print(f"[SCREENSHOT] Playwright error: {exc}, trying free Microlink API fallback")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                m_resp = await client.get(
                    f"https://api.microlink.io?url={target_url}&screenshot=true&meta=false"
                )
                data = m_resp.json()
                img_url = data.get("data", {}).get("screenshot", {}).get("url")
                if img_url:
                    img_resp = await client.get(img_url)
                    if img_resp.status_code == 200 and img_resp.content:
                        return img_resp.content
        except Exception as e2:
            print(f"[SCREENSHOT] Microlink fallback also failed: {e2}")
        raise exc


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
