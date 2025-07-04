# quick_reddit_test.py - Schneller Test für Reddit API
import asyncio
import aiohttp
import json

async def test_reddit_directly():
    """Test Reddit API direkt ohne deinen Service"""
    
    print("🧪 Testing Reddit API directly...")
    
    # Reddit's public JSON API (no auth needed)
    url = "https://www.reddit.com/r/travel/search.json?q=Barcelona&limit=10"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                print(f"📡 Response Status: {response.status}")
                print(f"📡 Response Headers: {dict(response.headers)}")
                
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"✅ Reddit API working!")
                    print(f"📊 Raw data structure:")
                    print(f"   - data: {type(data.get('data', 'Missing'))}")
                    
                    children = data.get('data', {}).get('children', [])
                    print(f"   - children: {len(children)} posts found")
                    
                    if children:
                        first_post = children[0].get('data', {})
                        print(f"   - First post title: {first_post.get('title', 'No title')[:60]}...")
                        print(f"   - First post ups: {first_post.get('ups', 0)}")
                        print(f"   - First post selftext: {len(first_post.get('selftext', ''))}")
                    
                    # Filter for Barcelona-specific content
                    relevant_posts = []
                    for post in children:
                        post_data = post.get('data', {})
                        title = post_data.get('title', '').lower()
                        text = post_data.get('selftext', '').lower()
                        
                        if 'barcelona' in title or 'barcelona' in text:
                            relevant_posts.append({
                                'title': post_data.get('title', '')[:80],
                                'ups': post_data.get('ups', 0),
                                'text_length': len(post_data.get('selftext', ''))
                            })
                    
                    print(f"🎯 Barcelona-relevant posts: {len(relevant_posts)}")
                    for i, post in enumerate(relevant_posts[:3]):
                        print(f"   {i+1}. {post['title']} (👍{post['ups']}, {post['text_length']} chars)")
                    
                else:
                    print(f"❌ Reddit API failed with status {response.status}")
                    error_text = await response.text()
                    print(f"Error: {error_text[:200]}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

async def test_different_subreddits():
    """Test different subreddits for Barcelona"""
    
    subreddits = [
        'travel',
        'solotravel', 
        'barcelona',
        'spain',
        'europe'
    ]
    
    print(f"\n🔍 Testing different subreddits...")
    
    for subreddit in subreddits:
        try:
            url = f"https://www.reddit.com/r/{subreddit}/search.json?q=Barcelona&limit=5"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        children = data.get('data', {}).get('children', [])
                        print(f"   r/{subreddit}: {len(children)} posts")
                    else:
                        print(f"   r/{subreddit}: Failed ({response.status})")
        except Exception as e:
            print(f"   r/{subreddit}: Error - {e}")

async def main():
    print("🚀 Reddit API Debug Test")
    print("=" * 50)
    
    # Test 1: Basic API call
    success = await test_reddit_directly()
    
    if success:
        # Test 2: Different subreddits
        await test_different_subreddits()
        
        print("\n✅ Reddit API is working!")
        print("🔧 If your service shows only mock data, check:")
        print("   1. Network connectivity")
        print("   2. Timeout settings (maybe too short)")
        print("   3. Error handling in your service")
    else:
        print("\n❌ Reddit API not accessible")
        print("💡 Possible reasons:")
        print("   1. Network/firewall blocking Reddit")
        print("   2. Reddit API temporarily down")
        print("   3. Rate limiting")

if __name__ == "__main__":
    asyncio.run(main())