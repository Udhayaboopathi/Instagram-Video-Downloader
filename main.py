from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from igbyte import download_reel
import instaloader
import re
import json
import os
import requests
import time
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
        # First try igbyte for all content types (most reliable)
        try:
            print("Trying igbyte...")
            reel_data_raw = download_reel(url)
            if isinstance(reel_data_raw, str):
                reel_data = json.loads(reel_data_raw)
            else:
                reel_data = reel_data_raw
            
            if reel_data and reel_data.get('reel_download_link'):
                print("Successfully got content from igbyte")
                return {
                    'video_url': reel_data.get('reel_download_link'),
                    'thumbnail_url': None,
                    'type': 'video',
                    'caption': reel_data.get('caption', ''),
                    'images': []
                }
        except Exception as e:
            print(f"igbyte failed: {e}")
        
        # Fallback: Try web scraping method
        print("Trying web scraping fallback...")
        try:
            shortcode = extract_shortcode(url)
            if shortcode:
                embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.instagram.com/',
                }
                
                response = requests.get(embed_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    content = response.text
                    
                    # Try to extract video URL
                    video_match = re.search(r'"video_url":"([^"]+)"', content)
                    if video_match:
                        video_url = video_match.group(1).replace('\\u0026', '&')
                        print(f"Found video via web scraping: {video_url}")
                        return {
                            'video_url': video_url,
                            'thumbnail_url': None,
                            'type': 'video',
                            'caption': '',
                            'images': []
                        }
                    
                    # Try to extract image URL
                    image_match = re.search(r'"display_url":"([^"]+)"', content)
                    if image_match:
                        image_url = image_match.group(1).replace('\\u0026', '&')
                        print(f"Found image via web scraping: {image_url}")
                        return {
                            'video_url': None,
                            'thumbnail_url': image_url,
                            'type': 'image',
                            'caption': '',
                            'images': [{'type': 'image', 'url': image_url, 'thumbnail': image_url}]
                        }
        except Exception as e:
            print(f"Web scraping failed: {e}")
        
        # Last resort: Use instaloader with better session handling
        print("Trying instaloader with session...")
        loader = instaloader.Instaloader(
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            max_connection_attempts=1,
            request_timeout=15
        )
        
        # Disable rate limiting warnings
        loader.context.quiet = True
        
        # Add delay to avoid rate limiting
        time.sleep(1)
        
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
        error_msg = str(e)
        if "403" in error_msg or "Forbidden" in error_msg:
            raise Exception("⚠️ Instagram is blocking requests.\n\n💡 Solutions:\n• Wait 5-10 minutes and try again\n• Try using a Reel URL (works better!)\n• Make sure the account is public\n• Clear your browser cache")
        elif "401" in error_msg or "Unauthorized" in error_msg or "wait a few minutes" in error_msg.lower():
            raise Exception("⏳ Instagram rate limit detected.\n\n✅ What to do:\n• Wait 5-10 minutes before trying again\n• Use Reel URLs - they work much better!\n• Try the same URL later\n\n💡 Tip: Reels download successfully even during rate limits!")
        elif "404" in error_msg or "not found" in error_msg.lower():
            raise Exception("❌ Post not found.\n\nPossible reasons:\n• Post was deleted\n• Account is private\n• URL is incorrect\n• Post is not accessible")
        else:
            raise Exception(f"⚠️ Instagram error.\n\n💡 Try these:\n• Wait a few minutes and retry\n• Use a Reel URL instead\n• Make sure content is public\n\nError: {error_msg[:100]}")
    except Exception as e:
        error_msg = str(e)
        if "⚠️" in error_msg or "❌" in error_msg or "⏳" in error_msg:
            raise  # Re-raise our custom formatted errors
        raise Exception(f"⚠️ Failed to download.\n\n💡 Suggestions:\n• Try a Reel URL (works best!)\n• Wait a few minutes\n• Ensure content is public\n\nDetails: {error_msg[:150]}")


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


@app.post("/download")
async def download_video(request: Request, instagram_url: str = Form(...)):
    """Download Instagram content - supports both HTML and JSON responses"""
    
    # Check if it's an AJAX request
    is_ajax = request.headers.get('sec-fetch-mode') == 'cors' or \
              request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    # Validate input
    if not instagram_url or instagram_url.strip() == "":
        error_msg = "Please enter a valid Instagram URL"
        if is_ajax:
            return JSONResponse(
                status_code=400,
                content={"error": error_msg, "success": False}
            )
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "content": None,
                "error": error_msg
            }
        )
    
    # Validate URL format
    if not validate_instagram_url(instagram_url):
        error_msg = "Invalid Instagram URL format. Please use a valid Reel, Post, or IGTV link."
        if is_ajax:
            return JSONResponse(
                status_code=400,
                content={"error": error_msg, "success": False}
            )
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "content": None,
                "error": error_msg
            }
        )
    
    try:
        # Download Instagram content using combined approach
        print(f"Attempting to download from: {instagram_url}")
        content_data = download_instagram_content(instagram_url)
        print(f"Downloaded content: {content_data}")
        
        # Return JSON for AJAX requests
        if is_ajax:
            return JSONResponse(
                content={
                    "success": True,
                    "content": content_data
                }
            )
        
        # Render success page with content for regular requests
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
        
        # Return JSON for AJAX requests
        if is_ajax:
            return JSONResponse(
                status_code=400,
                content={"error": error_message, "success": False}
            )
        
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
