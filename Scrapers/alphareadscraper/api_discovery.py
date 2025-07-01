import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import json

# Load environment variables
load_dotenv()

def discover_api_endpoints():
    """Discover API endpoints by monitoring network requests"""
    api_calls = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Monitor all network requests
        def handle_request(request):
            # Filter for API-like requests
            if any(keyword in request.url.lower() for keyword in ['api', 'graphql', 'rest', 'json']):
                api_calls.append({
                    'method': request.method,
                    'url': request.url,
                    'headers': dict(request.headers),
                    'post_data': request.post_data
                })
                print(f"API Call: {request.method} {request.url}")
        
        def handle_response(response):
            # Log responses from API-like URLs
            if any(keyword in response.url.lower() for keyword in ['api', 'graphql', 'rest']) and response.status == 200:
                try:
                    content_type = response.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        print(f"API Response: {response.url} - Status: {response.status}")
                except Exception as e:
                    print(f"Error reading response: {e}")
        
        page.on('request', handle_request)
        page.on('response', handle_response)
        
        try:
            # Navigate and login (same as your scraper)
            page.goto('https://alpharead.alpha.school/guide/students')
            page.wait_for_load_state('networkidle')
            
            # Login flow
            try:
                page.wait_for_selector('button.bg-gradient-to-b.from-reading-primary.to-reading-secondary', state='visible', timeout=5000)
                page.click('button.bg-gradient-to-b.from-reading-primary.to-reading-secondary')
            except Exception:
                page.wait_for_selector('button:has-text("Sign in with")', state='visible', timeout=5000)
                page.click('button:has-text("Sign in with")')
            
            page.wait_for_url("https://accounts.google.com/**", timeout=15000)
            page.wait_for_selector('input#identifierId', state='visible', timeout=15000)
            page.fill('input#identifierId', os.getenv('ALPHAREAD_EMAIL'))
            page.click('button:has-text("Next")')
            
            page.wait_for_selector('input[type="password"]', state='visible', timeout=15000)
            page.fill('input[type="password"]', os.getenv('ALPHAREAD_PASSWORD'))
            page.click('button:has-text("Next")')
            
            # Navigate to student management
            page.click('text=Guide Dashboard')
            page.click('text=Student Management')
            
            # Wait for the page to load and capture API calls
            page.wait_for_load_state('networkidle')
            
            # Try searching for a student to trigger more API calls
            if len(api_calls) == 0:
                print("\nSearching for student to trigger API calls...")
                page.fill('input[placeholder="Search..."]', 'keyen.gupta@2hourlearning.com')
                page.wait_for_load_state('networkidle')
            
            # Save discovered API calls
            with open('discovered_apis.json', 'w') as f:
                json.dump(api_calls, f, indent=2)
            
            print(f"\nDiscovered {len(api_calls)} API calls")
            print("API calls saved to 'discovered_apis.json'")
            
            if api_calls:
                print("\nSample API calls found:")
                for call in api_calls[:3]:
                    print(f"  {call['method']} {call['url']}")
            else:
                print("\nNo obvious API calls found. The site might use:")
                print("1. Server-side rendering without APIs")
                print("2. Internal APIs with different naming")
                print("3. GraphQL endpoints")
                
        except Exception as e:
            print(f"Error during discovery: {e}")
        finally:
            browser.close()
    
    return api_calls

if __name__ == "__main__":
    print("Starting API endpoint discovery...")
    print("This will login and monitor network traffic for API calls.\n")
    discover_api_endpoints() 