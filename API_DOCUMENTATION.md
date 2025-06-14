# Link Analysis API Documentation

## Overview

The Link Analysis API provides functionality to extract and analyze content from various platforms including YouTube, Bilibili, and general web pages. It automatically detects the platform type and uses appropriate extraction methods.

## Endpoint

### POST `/analyze_link`

Analyzes content from a provided link using platform-specific extractors.

#### Request Body

```json
{
  "link": "https://example.com",
  "platform": "youtube|bilibili|web", // Optional - auto-detected if not provided
  "options": {
    "languages": ["en", "zh"] // Optional - for YouTube/Bilibili transcript languages
  }
}
```

#### Parameters

| Parameter           | Type   | Required | Description                                                                          |
| ------------------- | ------ | -------- | ------------------------------------------------------------------------------------ |
| `link`              | string | Yes      | The URL to analyze                                                                   |
| `platform`          | string | No       | Platform type (`youtube`, `bilibili`, `web`). If not provided, will be auto-detected |
| `options`           | object | No       | Additional options for content extraction                                            |
| `options.languages` | array  | No       | Preferred languages for transcripts (YouTube/Bilibili only)                          |

#### Response Format

**Success Response (200):**

```json
{
  "success": true,
  "platform": "youtube|bilibili|web",
  "data": {
    "title": "Content Title",
    "content": "Extracted content text",
    "url": "https://original-url.com",
    "language": "en", // For transcripts
    "metadata": {
      // Platform-specific metadata
    }
  }
}
```

**Error Response (400/500):**

```json
{
  "success": false,
  "error": "Error type",
  "details": "Detailed error message",
  "platform": "detected_platform", // If applicable
  "suggestions": ["Suggestion 1", "Suggestion 2"]
}
```

## Platform Support

### YouTube

- **Supported URLs:**

  - `https://youtube.com/watch?v=VIDEO_ID`
  - `https://youtu.be/VIDEO_ID`
  - `https://m.youtube.com/watch?v=VIDEO_ID`

- **Features:**

  - Automatic transcript extraction
  - Multiple language support
  - Auto-generated and manual transcripts

- **Options:**
  - `languages`: Array of language codes (e.g., `["en", "zh", "es"]`)

### Bilibili

- **Supported URLs:**

  - `https://bilibili.com/video/BV...`
  - `https://b23.tv/...`
  - `https://m.bilibili.com/video/BV...`

- **Features:**

  - Subtitle extraction when available
  - Chinese and English subtitle support

- **Limitations:**
  - Many videos don't have auto-generated subtitles
  - Manual subtitles may not be available for all content

### Web (General)

- **Supported:** Any valid HTTP/HTTPS URL
- **Features:**

  - Full page content extraction
  - Smart content filtering
  - Metadata extraction

- **Requirements:**
  - Valid SPIDER_API_KEY in environment variables

## Examples

### YouTube Video Analysis

```bash
curl -X POST http://localhost:5001/analyze_link \
  -H "Content-Type: application/json" \
  -d '{
    "link": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "options": {
      "languages": ["en"]
    }
  }'
```

### Bilibili Video Analysis

```bash
curl -X POST http://localhost:5001/analyze_link \
  -H "Content-Type: application/json" \
  -d '{
    "link": "https://bilibili.com/video/BV1234567890",
    "platform": "bilibili"
  }'
```

### Web Page Analysis

```bash
curl -X POST http://localhost:5001/analyze_link \
  -H "Content-Type: application/json" \
  -d '{
    "link": "https://example.com/article",
    "platform": "web"
  }'
```

### Auto-Detection

```bash
curl -X POST http://localhost:5001/analyze_link \
  -H "Content-Type: application/json" \
  -d '{
    "link": "https://youtu.be/dQw4w9WgXcQ"
  }'
```

## Error Handling

### Common Error Types

| Error Type             | Description                    | HTTP Status |
| ---------------------- | ------------------------------ | ----------- |
| `missing_field`        | Required field not provided    | 400         |
| `invalid_url`          | URL format is invalid          | 400         |
| `unsupported_platform` | Platform not supported         | 400         |
| `extraction_failed`    | Content extraction failed      | 500         |
| `missing_dependency`   | Required library not installed | 500         |
| `api_error`            | Third-party API error          | 500         |

### Error Response Examples

**Missing Required Field:**

```json
{
  "success": false,
  "error": "missing_field",
  "details": "Missing required field: link",
  "suggestions": ["Please provide a valid URL in the 'link' field"]
}
```

**YouTube Video Not Found:**

```json
{
  "success": false,
  "error": "extraction_failed",
  "details": "Could not retrieve transcript: No transcript found for video ID: invalid_id",
  "platform": "youtube",
  "suggestions": [
    "Check if the video ID is correct",
    "Verify the video has captions/transcripts available",
    "Try a different language option"
  ]
}
```

**Bilibili Subtitle Not Available:**

```json
{
  "success": false,
  "error": "extraction_failed",
  "details": "No subtitles available for this Bilibili video",
  "platform": "bilibili",
  "suggestions": [
    "This video may not have auto-generated subtitles",
    "Check if manual subtitles are available",
    "Try a different Bilibili video"
  ]
}
```

**Missing Spider API Key:**

```json
{
  "success": false,
  "error": "missing_dependency",
  "details": "Spider API key not configured",
  "platform": "web",
  "suggestions": [
    "Set SPIDER_API_KEY in your environment variables",
    "Get an API key from spider.cloud"
  ]
}
```

## Setup Requirements

### Environment Variables

Add to your `.env` file:

```env
# Spider API for web scraping
SPIDER_API_KEY=your_spider_api_key_here
```

### Dependencies

Install required packages:

```bash
pip install llama-index-readers-youtube-transcript==0.3.0
pip install llama-index-readers-bilibili==0.3.0
pip install llama-index-readers-web==0.4.1
pip install youtube-transcript-api spider-client pycryptodomex PyJWT brotli qrcode
```

### Getting API Keys

**Spider API Key:**

1. Visit [spider.cloud](https://spider.cloud)
2. Sign up for an account
3. Get your API key from the dashboard
4. Add it to your `.env` file

## Troubleshooting

### Common Issues

1. **"No transcript found" for YouTube videos:**

   - Not all YouTube videos have transcripts/captions
   - Try videos with auto-generated captions
   - Check if the video is publicly accessible

2. **"No subtitles available" for Bilibili videos:**

   - Many Bilibili videos don't have auto-generated subtitles
   - Look for videos with manual subtitles
   - This is a limitation of the platform

3. **Spider API errors for web scraping:**

   - Verify your API key is correct
   - Check your Spider API quota/limits
   - Ensure the target website is accessible

4. **Import errors:**
   - Install all required dependencies
   - Check Python environment compatibility
   - Verify LlamaIndex reader versions

### Testing the API

You can test the API functionality with these known working examples:

```bash
# Test YouTube (Rick Roll - has transcripts)
curl -X POST http://localhost:5001/analyze_link \
  -H "Content-Type: application/json" \
  -d '{"link": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'

# Test web scraping (Wikipedia - always accessible)
curl -X POST http://localhost:5001/analyze_link \
  -H "Content-Type: application/json" \
  -d '{"link": "https://en.wikipedia.org/wiki/Artificial_intelligence"}'
```

## Rate Limits

- **YouTube:** No specific rate limits from the API
- **Bilibili:** No specific rate limits from the API
- **Spider API:** Depends on your plan (check spider.cloud for details)

## Security Considerations

- API keys are stored in environment variables
- No user input is directly executed
- URLs are validated before processing
- Error messages don't expose sensitive information
