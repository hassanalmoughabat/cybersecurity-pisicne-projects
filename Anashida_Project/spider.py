import argparse
import os
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time

def is_valid_url(url, base_url):
    if not url:
        return False
    
    if not url.startswith(('http://', 'https://')):
        return True
    
    base_domain = urlparse(base_url).netloc
    url_domain = urlparse(url).netloc
    return base_domain == url_domain

def is_image_url(url):
    extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in extensions)

def download_image(img_url, base_url, save_path):
    try:
        full_url = urljoin(base_url, img_url)
        
        filename = os.path.basename(urlparse(full_url).path)
        if not filename:
            filename = f"image_{int(time.time())}.jpg"
        
        filepath = os.path.join(save_path, filename)
        
        if os.path.exists(filepath):
            print(f"Image already exists: {filepath}")
            return
        
        response = requests.get(full_url, stream=True)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Downloaded: {filename}")
        else:
            print(f"Failed to download {full_url}")
            
    except Exception as e:
        print(f"Error downloading {img_url}: {e}")

def crawl(url, depth, max_depth, save_path, visited_urls):
    """Search the URL for images and links."""
    if depth > max_depth or url in visited_urls:
        return
    
    visited_urls.add(url)
    print(f"Searching: {url} (Depth: {depth}/{max_depth})")
    
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to access {url}")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for img in soup.find_all('img'):
            img_url = img.get('src')
            if img_url and is_image_url(img_url):
                download_image(img_url, url, save_path)
        
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and is_image_url(href):
                download_image(href, url, save_path)
        
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and is_valid_url(href, url):
                next_url = urljoin(url, href)
                if next_url not in visited_urls:
                    time.sleep(0.5)
                    crawl(next_url, depth + 1, max_depth, save_path, visited_urls)
                    
    except Exception as e:
        print(f"Error crawling {url}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Download images from websites.')
    parser.add_argument('url', help='URL to start downloading from')
    parser.add_argument('-r', action='store_true', help='recursively download images')
    parser.add_argument('-l', type=int, default=5, help='maximum recursion depth (default: 5)')
    parser.add_argument('-p', default='./data/', help='path to save images (default: ./data/)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.p):
        os.makedirs(args.p)
    
    visited_urls = set()
    
    if args.r:
        print(f"Starting recursive download from {args.url} with max depth {args.l}")
        crawl(args.url, 1, args.l, args.p, visited_urls)
    else:
        print(f"Downloading images from {args.url}")
        crawl(args.url, 1, 1, args.p, visited_urls)
    
    print(f"Spider completed. Visited {len(visited_urls)} pages.")

if __name__ == "__main__":
    main()