#!/usr/bin/env python3
"""
Blob Image Interceptor - Captures blob images from websites with scrolling support

Requires: 
- Python packages:
    - selenium, 
    - selenium-wire, 
    - blinker (1.7.0)
    - Pillow, 
    - webdriver-manager
- Chrome, below is for Linux (Debian/Ubuntu)
    - wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    - sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
    - sudo apt-get update
    - sudo apt-get install google-chrome-stable

Usage:
> python3 blob_image_downloader.py
Note: Do not use `sudo`
"""


###################################################
# Configuration
TARGET_URL = "https://example.com"  # Replace with your target URL, must be no redirection
OUTPUT_DIR = "./cache"
HEADLESS = False                    # Set to True for headless mode
SCROLL_PAUSE = 5                    # Seconds to wait after each scroll
MAX_SCROLLS = 150                   # Maximum number of scrolls
HEIGHT_PER_SCROLL = 1000            # Pixel per scroll
###################################################


import os
import time
import base64
import hashlib
from io import BytesIO

# Selenium imports
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Selenium Wire for network interception
from seleniumwire import webdriver as wire_webdriver

# Image handling
from PIL import Image


class BlobImageInterceptor:
    def __init__(self, output_dir="captured_images", headless=False):
        """
        Initialize the blob image interceptor
        
        Args:
            output_dir: Directory to save captured images
            headless: Run Chrome in headless mode
        """
        self.output_dir = output_dir
        self.headless = headless
        self.captured_blobs = set()
        self.image_counter = 0
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Setup Chrome options
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--window-size=1920,1080")
        
        # Enable logging for debugging
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        
        # Selenium Wire options for intercepting network traffic
        self.seleniumwire_options = {
            'disable_encoding': True,  # Ask the server not to compress the response
            'connection_timeout': None  # Never timeout
        }
        
    def setup_driver(self):
        """Setup Chrome driver with network interception"""
        print("Setting up Chrome driver...")
        self.driver = wire_webdriver.Chrome(
            options=self.chrome_options,
            seleniumwire_options=self.seleniumwire_options
        )
        return self.driver
    
    def inject_blob_interceptor(self):
        """Inject JavaScript to intercept blob URLs"""
        js_code = """
        // Store original fetch and XMLHttpRequest
        window.interceptedBlobs = window.interceptedBlobs || [];
        
        // Override createObjectURL to capture blob URLs
        const originalCreateObjectURL = URL.createObjectURL;
        URL.createObjectURL = function(blob) {
            const url = originalCreateObjectURL.call(this, blob);
            
            // Convert blob to base64
            if (blob instanceof Blob) {
                const reader = new FileReader();
                reader.onloadend = function() {
                    window.interceptedBlobs.push({
                        url: url,
                        data: reader.result,
                        type: blob.type,
                        size: blob.size,
                        timestamp: new Date().toISOString()
                    });
                };
                reader.readAsDataURL(blob);
            }
            
            return url;
        };
        
        // Function to get all img elements with blob URLs
        window.getBlobImages = function() {
            const images = document.querySelectorAll('img[src^="blob:"]');
            const blobUrls = [];
            images.forEach(img => {
                blobUrls.push({
                    src: img.src,
                    alt: img.alt || '',
                    width: img.naturalWidth,
                    height: img.naturalHeight
                });
            });
            return blobUrls;
        };
        
        console.log('Blob interceptor injected successfully');
        """
        self.driver.execute_script(js_code)
    
    def capture_network_images(self):
        """Capture images from network traffic"""
        captured_count = 0
        
        for request in self.driver.requests:
            # Check for image responses
            if request.response and request.response.headers.get('Content-Type', '').startswith('image/'):
                try:
                    # Generate unique hash for the image
                    image_hash = hashlib.md5(request.response.body).hexdigest()
                    
                    if image_hash not in self.captured_blobs:
                        self.captured_blobs.add(image_hash)
                        
                        # Save the image
                        image = Image.open(BytesIO(request.response.body))
                        
                        # Determine file extension
                        ext = 'jpg'
                        content_type = request.response.headers.get('Content-Type', '')
                        if 'png' in content_type:
                            ext = 'png'
                        elif 'gif' in content_type:
                            ext = 'gif'
                        elif 'webp' in content_type:
                            ext = 'webp'
                        
                        filename = f"network_image_{self.image_counter}_{image_hash[:8]}.{ext}"
                        filepath = os.path.join(self.output_dir, filename)
                        
                        image.save(filepath)
                        print(f"  Saved network image: {filename} ({image.width}x{image.height})")
                        
                        self.image_counter += 1
                        captured_count += 1
                        
                except Exception as e:
                    pass  # Skip problematic images
        
        return captured_count
    
    def capture_blob_images(self):
        """Capture blob images from the page"""
        captured_count = 0
        
        try:
            # Get intercepted blobs from JavaScript
            blobs = self.driver.execute_script("return window.interceptedBlobs || [];")
            
            for blob in blobs:
                if blob['data'] and blob['data'].startswith('data:image'):
                    # Extract base64 data
                    data = blob['data'].split(',')[1]
                    image_data = base64.b64decode(data)
                    
                    # Generate unique hash
                    image_hash = hashlib.md5(image_data).hexdigest()
                    
                    if image_hash not in self.captured_blobs:
                        self.captured_blobs.add(image_hash)
                        
                        # Save the image
                        image = Image.open(BytesIO(image_data))
                        
                        # Determine file extension from MIME type
                        mime_type = blob['type']
                        ext = 'jpg'
                        if 'png' in mime_type:
                            ext = 'png'
                        elif 'gif' in mime_type:
                            ext = 'gif'
                        elif 'webp' in mime_type:
                            ext = 'webp'
                        
                        filename = f"blob_image_{self.image_counter}_{image_hash[:8]}.{ext}"
                        filepath = os.path.join(self.output_dir, filename)
                        
                        image.save(filepath)
                        print(f"  Saved blob image: {filename} ({image.width}x{image.height})")
                        
                        self.image_counter += 1
                        captured_count += 1
            
            # Clear the intercepted blobs to avoid duplicates
            self.driver.execute_script("window.interceptedBlobs = [];")
            
        except Exception as e:
            print(f"  Error capturing blob images: {e}")
        
        return captured_count
    
    def scroll_and_capture(self, url, scroll_pause=2, max_scrolls=10):
        """
        Navigate to URL, scroll through the page, and capture images
        
        Args:
            url: Website URL to visit
            scroll_pause: Time to wait after each scroll (seconds)
            max_scrolls: Maximum number of scrolls
        """
        print(f"\nNavigating to: {url}")
        self.driver.get(url)
        
        # Wait for initial page load
        time.sleep(3)
        
        # Inject blob interceptor
        self.inject_blob_interceptor()
        
        # Get initial page height
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        scroll_height = 0
        
        print("\nStarting image capture with scrolling...")
        
        while scroll_count < max_scrolls:
            print(f"\n--- Scroll {scroll_count + 1} ---")
            
            # Capture current images
            network_count = self.capture_network_images()
            blob_count = self.capture_blob_images()
            
            if network_count > 0 or blob_count > 0:
                print(f"  Captured: {network_count} network images, {blob_count} blob images")
            
            # Scroll down
            scroll_height += HEIGHT_PER_SCROLL
            self.driver.execute_script(f"window.scrollTo(0, {scroll_height});")
            
            # Wait for new content to load
            time.sleep(scroll_pause)
            
            # Check if new content was loaded
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if scroll_height >= last_height:
                print("  No more content to load")
                break

            scroll_count += 1
        
        # Final capture
        print("\n--- Final capture ---")
        network_count = self.capture_network_images()
        blob_count = self.capture_blob_images()
        if network_count > 0 or blob_count > 0:
            print(f"  Captured: {network_count} network images, {blob_count} blob images")
        
        print(f"\n✅ Total unique images captured: {len(self.captured_blobs)}")
        print(f"📁 Images saved to: {os.path.abspath(self.output_dir)}")
    
    def close(self):
        """Close the browser"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            print("\nBrowser closed")


def main():
    """Main function with example usage"""
    
    # Create interceptor
    interceptor = BlobImageInterceptor(
        output_dir=OUTPUT_DIR,
        headless=HEADLESS
    )
    
    try:
        # Setup driver
        interceptor.setup_driver()
        
        # Start capturing
        interceptor.scroll_and_capture(
            url=TARGET_URL,
            scroll_pause=SCROLL_PAUSE,
            max_scrolls=MAX_SCROLLS
        )
        
        # Wait before closing (optional)
        input("\nPress Enter to close the browser...")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        interceptor.close()


if __name__ == "__main__":
    main()