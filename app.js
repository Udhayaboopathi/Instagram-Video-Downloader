const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');
const cheerio = require('cheerio');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, 'public')));

// Set EJS as template engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// GET Route - Render the index page
app.get('/', (req, res) => {
  res.render('index', { 
    videoUrl: null, 
    error: null,
    thumbnailUrl: null 
  });
});

// Custom Instagram downloader function using multiple fallback methods
async function instagramCustom(instaUrl) {
  try {
    if (!instaUrl || typeof instaUrl !== 'string') throw new Error('Invalid URL');

    // Method 1: Try using snapinsta.app API
    try {
      const snapinstaResponse = await axios.post(
        'https://snapinsta.app/api/ajaxSearch',
        new URLSearchParams({
          q: instaUrl,
          t: 'media',
          lang: 'en'
        }),
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Origin': 'https://snapinsta.app',
            'Referer': 'https://snapinsta.app/'
          },
          timeout: 15000
        }
      );

      if (snapinstaResponse.data && snapinstaResponse.data.data) {
        const $ = cheerio.load(snapinstaResponse.data.data);
        
        // Look for download link
        let downloadUrl = null;
        
        // Try to find the HD download button
        $('a.abutton').each((i, elem) => {
          const href = $(elem).attr('href');
          if (href && href.includes('.mp4')) {
            downloadUrl = href;
            return false; // break
          }
        });

        if (downloadUrl) {
          return downloadUrl;
        }
      }
    } catch (snapError) {
      console.log('Snapinsta failed, trying next method...');
    }

    // Method 2: Try using downloadgram API
    try {
      const downloadgramResponse = await axios.post(
        'https://downloadgram.org/wp-json/aio-dl/video-data/',
        { url: instaUrl },
        {
          headers: {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Origin': 'https://downloadgram.org',
            'Referer': 'https://downloadgram.org/'
          },
          timeout: 15000
        }
      );

      if (downloadgramResponse.data && downloadgramResponse.data.medias) {
        const videoMedia = downloadgramResponse.data.medias.find(m => m.videoAvailable);
        if (videoMedia && videoMedia.url) {
          return videoMedia.url;
        }
      }
    } catch (downloadgramError) {
      console.log('Downloadgram failed, trying next method...');
    }

    // Method 3: Try using saveinsta API
    try {
      const saveinstaResponse = await axios.get(
        `https://saveinsta.io/core/ajax.php?url=${encodeURIComponent(instaUrl)}`,
        {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://saveinsta.io/'
          },
          timeout: 15000
        }
      );

      if (saveinstaResponse.data) {
        const $ = cheerio.load(saveinstaResponse.data);
        const downloadLink = $('.download-items__btn a').first().attr('href');
        if (downloadLink && downloadLink.includes('.mp4')) {
          return downloadLink;
        }
      }
    } catch (saveinstaError) {
      console.log('Saveinsta failed...');
    }

    throw new Error('All download methods failed. Instagram may be blocking requests or the post is private/deleted.');
  } catch (err) {
    throw new Error(`Failed to download: ${err.message}`);
  }
}

// POST Route - Download Instagram Video
app.post('/download', async (req, res) => {
  const { instagramUrl } = req.body;

  // Validate input
  if (!instagramUrl || instagramUrl.trim() === '') {
    return res.render('index', {
      videoUrl: null,
      error: 'Please enter a valid Instagram URL',
      thumbnailUrl: null
    });
  }

  // Validate Instagram URL format
  const instagramUrlPattern = /^https?:\/\/(www\.)?instagram\.com\/(p|reel|tv)\/[a-zA-Z0-9_-]+/;
  if (!instagramUrlPattern.test(instagramUrl)) {
    return res.render('index', {
      videoUrl: null,
      error: 'Invalid Instagram URL format. Please use a valid Reel, Post, or IGTV link.',
      thumbnailUrl: null
    });
  }

  try {
    // Fetch video using custom Instagram downloader
    const videoUrl = await instagramCustom(instagramUrl);

    if (!videoUrl) {
      return res.render('index', {
        videoUrl: null,
        error: 'Unable to fetch video. This could be due to:\n• Private account\n• Content not available\n• No downloadable video found\n• Invalid or expired link',
        thumbnailUrl: null
      });
    }

    // Render the page with video player and download button
    res.render('index', {
      videoUrl: videoUrl,
      error: null,
      thumbnailUrl: null
    });

  } catch (error) {
    console.error('Error fetching Instagram video:', error);

    // Determine error type and provide specific message
    let errorMessage = 'An error occurred while fetching the video. ';

    if (error.message && error.message.includes('private')) {
      errorMessage += 'This account is private and cannot be accessed.';
    } else if (error.message && error.message.includes('not found')) {
      errorMessage += 'The post was not found or has been deleted.';
    } else if (error.message && (error.message.includes('403') || error.message.includes('blocked'))) {
      errorMessage += 'Instagram is blocking this request. Please try:\n• Using a different URL\n• Waiting a few moments and trying again\n• Ensuring the post is public';
    } else if (error.message && error.message.includes('network')) {
      errorMessage += 'Network error. Please check your connection and try again.';
    } else if (error.code === 'ENOTFOUND' || error.code === 'ETIMEDOUT') {
      errorMessage += 'Unable to connect to Instagram. Please try again later.';
    } else {
      errorMessage += 'Please ensure:\n• The URL is correct\n• The account is public\n• The post contains a video\n• The post is still available';
    }

    res.render('index', {
      videoUrl: null,
      error: errorMessage,
      thumbnailUrl: null
    });
  }
});

// Start the server
app.listen(PORT, () => {
  console.log(`🚀 Instagram Video Downloader is running on http://localhost:${PORT}`);
  console.log(`📱 Open your browser and navigate to the URL above`);
});
