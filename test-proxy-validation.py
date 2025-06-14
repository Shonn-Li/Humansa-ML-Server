#!/usr/bin/env python3
"""
Proxy validation test for YouTube Transcript API
This script validates that the Webshare proxy is properly configured and working
"""

import os
import sys
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_proxy_direct():
    """Test proxy configuration directly with YouTube Transcript API"""
    
    # Check for Webshare credentials
    proxy_username = os.getenv('WEBSHARE_PROXY_USERNAME')
    proxy_password = os.getenv('WEBSHARE_PROXY_PASSWORD')
    
    if not proxy_username or not proxy_password:
        logger.error("❌ WEBSHARE_PROXY_USERNAME or WEBSHARE_PROXY_PASSWORD not found in .env file!")
        logger.error("These are NOT the API key!")
        logger.error("Go to your Webshare dashboard -> Proxy Settings to find these values")
        return False
    
    logger.info(f"✅ Webshare proxy username found: {proxy_username[:5]}...")
    logger.info("✅ Webshare proxy password found")
    
    # Configure proxy using WebshareProxyConfig
    logger.info("🌐 Configuring WebshareProxyConfig for rotating residential proxies")
    
    # Test video ID (your 2-hour podcast)
    video_id = "9V6tWC4CdFQ"
    logger.info(f"\n📹 Testing with video ID: {video_id}")
    
    try:
        logger.info("🔄 Initializing YouTubeTranscriptApi with WebshareProxyConfig...")
        
        # Initialize API with WebshareProxyConfig
        ytt_api = YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=proxy_username,
                proxy_password=proxy_password,
            )
        )
        
        logger.info("🔄 Attempting to fetch transcript WITH WEBSHARE PROXY...")
        
        # Try to fetch transcript with proxy
        transcript = ytt_api.get_transcript(video_id)
        
        logger.info(f"✅ SUCCESS! Webshare proxy is working!")
        logger.info(f"   Retrieved {len(transcript)} transcript segments")
        logger.info(f"   First segment: {transcript[0]['text'][:50]}...")
        logger.info(f"   Total duration: {sum(s['duration'] for s in transcript):.2f} seconds")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ PROXY TEST FAILED: {type(e).__name__}: {str(e)}")
        
        if "404" in str(e) or "Unable to connect to proxy" in str(e):
            logger.error("🔴 Proxy connection failed - Invalid credentials or configuration")
            logger.error("Please verify:")
            logger.error("1. You have an active Webshare 'Residential' proxy package (not free tier)")
            logger.error("2. Your proxy username and password are correct")
            logger.error("3. Your Webshare account is active and has available bandwidth")
        
        # Try without proxy to see if it's a proxy issue
        logger.info("\n🔄 Attempting WITHOUT proxy for comparison...")
        try:
            transcript_direct = YouTubeTranscriptApi.get_transcript(video_id)
            logger.warning("⚠️ Direct access works but proxy failed - check proxy configuration")
            logger.warning("This confirms the issue is with the Webshare proxy setup")
        except Exception as direct_e:
            logger.error(f"❌ Direct access also failed: {str(direct_e)}")
            logger.info("Both proxy and direct access failed - might be rate limited")
        
        return False

def main():
    """Run proxy validation test"""
    print("="*80)
    print("WEBSHARE PROXY VALIDATION TEST")
    print("="*80)
    
    # Check if running on cloud/server
    if os.path.exists('/var/lib/cloud'):
        logger.info("☁️ Running on cloud server - proxy is REQUIRED")
    else:
        logger.info("💻 Running locally - proxy recommended for testing")
    
    # Run the test
    success = test_proxy_direct()
    
    print("\n" + "="*80)
    if success:
        print("✅ PROXY VALIDATION SUCCESSFUL")
        print("The Webshare proxy is properly configured and working!")
    else:
        print("❌ PROXY VALIDATION FAILED")
        print("\nTroubleshooting steps:")
        print("1. Log in to webshare.io")
        print("2. Go to 'Proxy Settings' (not API settings)")
        print("3. Copy your 'Proxy Username' and 'Proxy Password'")
        print("4. Update WEBSHARE_PROXY_USERNAME and WEBSHARE_PROXY_PASSWORD in .env")
        print("5. Ensure you have a 'Residential' proxy package (not 'Proxy Server' or 'Static')")
        print("6. Check your proxy bandwidth usage hasn't exceeded limits")
    print("="*80)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
