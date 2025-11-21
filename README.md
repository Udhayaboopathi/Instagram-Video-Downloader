# 📹 Instagram Video Downloader

A fully functional Instagram content downloader web application built with **FastAPI** and **Python**. Download Instagram Reels, Videos, Images, and Carousels in **Full HD quality** from any public account.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.121.3-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- 📹 **Reel Downloads** - Fast and reliable downloads using igbyte (Works Best!)
- 🎥 **Video Posts** - Download video posts in Full HD quality
- 📸 **Image Posts** - Download images in original quality
- 🎠 **Carousel Posts** - Download all images/videos from carousel posts
- 🎬 **Full HD Quality** - All content downloaded in maximum available quality
- 💬 **Caption Display** - View post captions alongside content
- 🎨 **Modern UI** - Beautiful gradient design with responsive layout
- 🚀 **Fast & Reliable** - Dual download strategy for best results

## 🎯 Supported Content

| Content Type | Quality | Status |
|-------------|---------|--------|
| Reels | Full HD | ✅ Works Best |
| Video Posts | Full HD | ✅ Supported |
| Image Posts | Original | ⚠️ May face rate limits |
| Carousel Posts | Full HD | ✅ Supported |

**Note:** Only public accounts are supported. Instagram may rate-limit non-reel content.

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository:**
```bash
git clone <your-repo-url>
cd new
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run the application:**
```bash
python main.py
```

4. **Open your browser:**
```
http://localhost:8000
```

## 📦 Dependencies

The application uses the following Python packages:

- **FastAPI** (0.121.3) - Modern web framework for building APIs
- **Uvicorn** (0.34.0) - ASGI server for running FastAPI
- **igbyte** (0.1.1) - Instagram reel downloader (primary method)
- **instaloader** (4.15) - Instagram content scraper (fallback method)
- **Jinja2** (3.1.5) - Template engine for HTML rendering
- **python-multipart** (0.0.20) - Form data parsing

## 🎮 How to Use

1. **Copy Instagram URL:**
   - Go to any public Instagram post, reel, or video
   - Copy the URL from your browser

2. **Paste and Fetch:**
   - Paste the URL into the input field
   - Click "Fetch Content" button

3. **Preview and Download:**
   - View the content in the preview player
   - Click "Download" button to save in Full HD quality

### Example URLs:
```
https://www.instagram.com/reel/ABC123xyz/
https://www.instagram.com/p/ABC123xyz/
https://www.instagram.com/tv/ABC123xyz/
```

## 🏗️ Project Structure

```
new/
├── main.py                 # FastAPI application & download logic
├── app.py                  # Test script for igbyte
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── README_FASTAPI.md      # FastAPI documentation
├── static/
│   └── favicon.svg        # Custom favicon
└── templates/
    └── index.html         # Frontend UI
```

## 🔧 Technical Details

### Download Strategy

The application uses a **dual download approach** for maximum reliability:

1. **Primary Method (igbyte):**
   - Used for Instagram Reels
   - Fast and reliable
   - Returns direct download links
   - Recommended for best results

2. **Fallback Method (instaloader):**
   - Used for posts, images, and carousels
   - Configured for Full HD quality
   - May face Instagram rate limiting
   - Includes retry logic and custom user agent

### Backend Configuration

```python
# Instaloader settings for maximum quality
L = instaloader.Instaloader(
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
    max_connection_attempts=3,
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    video_format='mp4'  # Ensures Full HD quality
)
```

### API Endpoints

- `GET /` - Main page with download interface
- `POST /download` - Process download request and return content

## ⚠️ Known Limitations

- **Rate Limiting:** Instagram may temporarily block requests for non-reel content (403/401 errors)
- **Public Only:** Only public accounts are supported
- **CORS Issues:** Some images may not preview due to Instagram's CORS policy, but downloads still work
- **Best Practice:** Use with Instagram Reels for most reliable results

## 🐛 Troubleshooting

### "Please wait a few minutes before you try again"
- This is Instagram's rate limiting
- Try again after a few minutes
- Reels are less likely to be rate-limited

### Images not displaying in preview
- This is due to Instagram's CORS restrictions
- The download button will still work
- Videos and reels preview correctly

### Server won't start on port 8000
```bash
# Kill any process using port 8000
lsof -ti:8000 | xargs kill -9

# Restart the server
python main.py
```

## 🔒 Privacy & Legal

- This tool is for **personal use** only
- Only works with **public** Instagram content
- Respects Instagram's robots.txt and terms of service
- Do not use for commercial purposes
- Always credit original content creators

## 📝 Development

### Running in Development Mode

```bash
# With auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing with Different Content Types

```bash
# Test igbyte directly
python app.py
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **igbyte** - For reliable reel downloads
- **instaloader** - For comprehensive Instagram content support
- **FastAPI** - For the amazing web framework

## 📧 Support

If you encounter any issues or have questions:
1. Check the troubleshooting section above
2. Review known limitations
3. Open an issue on GitHub

---

**Made with ❤️ using FastAPI and Python**

⭐ If you find this useful, please give it a star!
