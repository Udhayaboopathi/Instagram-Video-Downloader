from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from igbyte import download_reel
import instaloader
import re
import json
import os
from pathlib import Path

app = FastAPI(title="Instagram Video Downloader")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")


def validate_instagram_url(url: str) -> bool:
    """Validate if the URL is a valid Instagram URL"""
    pattern = r'^https?://(www\.)?instagram\.com/(p|reel|tv|reels)/[a-zA-Z0-9_-]+/?.*$'
    return bool(re.match(pattern, url))


def extract_shortcode(url: str) -> str:
    """Extract shortcode from Instagram URL"""
    match = re.search(r'/(p|reel|tv|reels)/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(2)
    return None


def download_instagram_content(url: str):
    """Download any Instagram content (posts, reels, videos, images, music)"""
    try:
        # First try igbyte for reels (faster and more reliable)
        if '/reel/' in url or '/reels/' in url:
            try:
                print("Trying igbyte for reel...")
                reel_data_raw = download_reel(url)
                if isinstance(reel_data_raw, str):
                    reel_data = json.loads(reel_data_raw)
                else:
                    reel_data = reel_data_raw
                
                if reel_data and reel_data.get('reel_download_link'):
                    print("Successfully got reel from igbyte")
                    return {
                        'video_url': reel_data.get('reel_download_link'),
                        'thumbnail_url': None,
                        'type': 'video',
                        'caption': reel_data.get('caption', ''),
                        'images': []
                    }
            except Exception as e:
                print(f"igbyte failed: {e}")
        
        # Use instaloader for all content types
        print("Trying instaloader...")
        loader = instaloader.Instaloader(
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            max_connection_attempts=3,
            request_timeout=10,
            video_format='mp4'  # Ensure MP4 format
        )
        
        # Disable rate limiting warnings
        loader.context.quiet = True
        
        shortcode = extract_shortcode(url)
        if not shortcode:
            raise ValueError("Could not extract shortcode from URL")
        
        print(f"Fetching post with shortcode: {shortcode}")
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        
        result = {
            'video_url': None,
            'thumbnail_url': None,
            'type': 'video' if post.is_video else 'image',
            'caption': post.caption if post.caption else '',
            'images': [],
            'quality': 'HD'
        }
        
        # Handle video content - get highest quality
        if post.is_video:
            # Get the highest quality video URL
            result['video_url'] = post.video_url  # This returns the highest quality available
            result['thumbnail_url'] = post.url  # Highest quality thumbnail
            print(f"Found video content - URL: {post.video_url}")
        
        # Handle sidecar (multiple images/videos)
        elif post.typename == 'GraphSidecar':
            result['type'] = 'carousel'
            print("Found carousel content")
            for node in post.get_sidecar_nodes():
                if node.is_video:
                    # Get highest quality video from carousel
                    result['images'].append({
                        'type': 'video',
                        'url': node.video_url,  # Highest quality
                        'thumbnail': node.display_url
                    })
                else:
                    # Get highest quality image from carousel
                    result['images'].append({
                        'type': 'image',
                        'url': node.display_url,  # This is already the highest quality
                        'thumbnail': node.display_url
                    })
        
        # Handle single image - get highest quality
        else:
            print("Found single image content")
            # post.url gives the highest quality image available
            result['images'].append({
                'type': 'image',
                'url': post.url,  # Highest quality
                'thumbnail': post.url
            })
            result['thumbnail_url'] = post.url
        
        return result
        
    except instaloader.exceptions.InstaloaderException as e:
        if "403" in str(e) or "Forbidden" in str(e):
            raise Exception("Instagram is blocking requests. This content might be private or Instagram is rate limiting. Please try again later.")
        elif "404" in str(e) or "not found" in str(e).lower():
            raise Exception("Post not found. The post may have been deleted or the URL is incorrect.")
        else:
            raise Exception(f"Instagram error: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to download: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page"""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "content": None,
            "error": None
        }
    )


@app.post("/download", response_class=HTMLResponse)
async def download_video(request: Request, instagram_url: str = Form(...)):
    """Download Instagram video"""
    
    # Validate input
    if not instagram_url or instagram_url.strip() == "":
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "content": None,
                "error": "Please enter a valid Instagram URL"
            }
        )
    
    # Validate URL format
    if not validate_instagram_url(instagram_url):
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "content": None,
                "error": "Invalid Instagram URL format. Please use a valid Reel, Post, or IGTV link."
            }
        )
    
    try:
        # Download Instagram content using combined approach
        print(f"Attempting to download from: {instagram_url}")
        content_data = download_instagram_content(instagram_url)
        print(f"Downloaded content: {content_data}")
        
        # Render success page with content
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "content": content_data,
                "error": None
            }
        )
        
    except Exception as e:
        print(f"Exception occurred: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        error_message = f"An error occurred while fetching the video: {str(e)}"
        
        # Provide more specific error messages
        if "private" in str(e).lower():
            error_message = "This account is private and cannot be accessed."
        elif "not found" in str(e).lower() or "404" in str(e):
            error_message = "The post was not found or has been deleted."
        elif "403" in str(e) or "blocked" in str(e).lower() or "Forbidden" in str(e):
            error_message = "Instagram is currently blocking this request.\n\n💡 Tip: Reels work better! If this is a regular post, Instagram may be rate limiting.\n\nTry:\n• Using a Reel URL instead\n• Waiting a few minutes\n• Ensuring the post is public"
        elif "401" in str(e) or "Unauthorized" in str(e) or "wait a few minutes" in str(e).lower():
            error_message = "Instagram is rate limiting requests. Please wait a few minutes and try again.\n\n✅ Note: Reels usually work better than regular posts!"
        else:
            error_message = f"Unable to fetch content: {str(e)}\n\n💡 Reels work best with this tool!"
        
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "content": None,
                "error": error_message
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
