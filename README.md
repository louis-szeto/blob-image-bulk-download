# blob-image-bulk-download
Download all blob images in a dynamic scrolling webpage in bulk

### Prerequisites
- Python packages:
    - selenium, 
    - selenium-wire, 
    - blinker (1.7.0)
    - Pillow, 
    - webdriver-manager
- Chrome
For Linux (Debian/Ubuntu):
```
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt-get update
sudo apt-get install google-chrome-stable
```

### Usage
```
> python3 blob_image_downloader.py`
```

Note: Do not use `sudo`
