#!/usr/bin/env python3
"""
Daily Sports Tracker - GitHub Actions Version
Reads configuration from environment variables (GitHub Secrets)
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import requests
import time

# Configuration from GitHub Secrets (Environment Variables)

SPREADSHEET_ID = "11Ky2AEWx6uMysgK-dI_UgmUZMQAV-TDjaMAwdg3FOs8"
EMAIL_TO = os.environ.get('EMAIL_TO', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Optional API Keys from GitHub Secrets

NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY', '')
SERPAPI_KEY = os.environ.get('SERPAPI_KEY', '')

def get_spreadsheet_data():
    """Fetch data from Google Sheets"""
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/{{SPREADSHEET_ID}}/export?format=csv"
        response = requests.get(csv_url, timeout=10)

        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            players = []
            
            for line in lines[1:]:
                parts = [p.strip().strip('"') for p in line.split(',')]
                if len(parts) >= 3 and parts[0] and parts[1] and parts[2]:
                    players.append({
                        'sport': parts[0],
                        'player': parts[1],
                        'team': parts[2]
                    })
            
            return players
        else:
            print(f"Error fetching spreadsheet: {{response.status_code}}")
            return []
    except Exception as e:
        print(f"Error reading spreadsheet: {{e}}")
        return []

def search_with_newsapi(player_name, team_name):
    """Search using NewsAPI (if API key provided)"""
    if not NEWSAPI_KEY:
        return []

    try:
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': f'"{{team_name}}" baseball OR "{{player_name}}"',
            'from': from_date,
            'sortBy': 'publishedAt',
            'language': 'en',
            'apiKey': NEWSAPI_KEY,
            'pageSize': 5
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            articles = []
            
            for article in data.get('articles', []):
                articles.append({
                    'title': article.get('title', 'No title'),
                    'snippet': article.get('description', 'No description'),
                    'url': article.get('url', ''),
                    'date': article.get('publishedAt', ''),
                    'source': article.get('source', {}).get('name', 'Unknown')
                })
            
            return articles
        
    except Exception as e:
        print(f"NewsAPI error: {{e}}")

    return []

def search_with_serpapi(player_name, team_name):
    """Search using SerpAPI for Google results (if API key provided)"""
    if not SERPAPI_KEY:
        return []

    try:
        url = "https://serpapi.com/search"
        params = {
            'q': f'{{team_name}} baseball {{player_name}} game stats',
            'api_key': SERPAPI_KEY,
            'num': 5
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            for result in data.get('organic_results', []):
                results.append({
                    'title': result.get('title', 'No title'),
                    'snippet': result.get('snippet', 'No description'),
                    'url': result.get('link', ''),
                    'source': 'Google Search'
                })
            
            return results
        
    except Exception as e:
        print(f"SerpAPI error: {{e}}")

    return []

def search_basic(player_name, team_name):
    """Basic search without API keys - uses Bing"""
    news_items = []

    try:
        query = f"{{team_name}} baseball {{player_name}} news game"
        search_url = f"https://www.bing.com/search?q={{query.replace(' ', '+')}}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            text = response.text.lower()
            if team_name.lower() in text or player_name.lower() in text:
                news_items.append({
                    'title': f"Recent mentions found for {{player_name}} and {{team_name}}",
                    'snippet': f"Search results indicate recent activity. Visit Bing to see full results.",
                    'url': search_url,
                    'source': 'Bing Search'
                })

    except Exception as e:
        print(f"Basic search error: {{e}}")

    return news_items

def search_player_news(player_name, team_name):
    """Master search function - tries multiple methods"""
    all_news = []

    # Try NewsAPI first
    if NEWSAPI_KEY:
        print(f"  Searching NewsAPI...")
        news = search_with_newsapi(player_name, team_name)
        all_news.extend(news)
        time.sleep(0.5)

    # Try SerpAPI
    if SERPAPI_KEY and len(all_news) < 3:
        print(f"  Searching with SerpAPI...")
        results = search_with_serpapi(player_name, team_name)
        all_news.extend(results)
        time.sleep(0.5)

    # Fall back to basic search
    if len(all_news) < 2:
        print(f"  Using basic search...")
        basic_results = search_basic(player_name, team_name)
        all_news.extend(basic_results)

    # Remove duplicates
    seen_urls = set()
    unique_news = []
    for item in all_news:
        if item['url'] not in seen_urls:
            seen_urls.add(item['url'])
            unique_news.append(item)

    return unique_news[:5]

def create_report(players_data):
    """Create HTML email report"""
    total_updates = sum(len(p['news']) for p in players_data)

    html = f"""
<html>
<head>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            line-height: 1.6; 
            color: #333; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .header {{
            background: linear-gradient(135deg, #0066cc, #0099cc);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        h1 {{ 
            margin: 0;
            font-size: 28px;
        }}
        .summary {{ 
            background-color: white; 
            padding: 15px; 
            border-radius: 5px; 
            margin-top: 15px;
            border-left: 4px solid #ffcc00;
        }}
        .player-section {{ 
            margin-bottom: 30px; 
            padding: 20px; 
            background-color: white; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h2 {{ 
            color: #0066cc; 
            margin-top: 0;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 10px;
        }}
        .player-info {{
            color: #666;
            font-size: 14px;
            margin-bottom: 15px;
        }}
        .news-item {{ 
            margin: 15px 0; 
            padding: 15px; 
            background-color: #f8f9fa; 
            border-left: 4px solid #0066cc;
            border-radius: 4px;
        }}
        .news-title {{ 
            font-weight: bold; 
            color: #0066cc; 
            font-size: 16px;
            margin-bottom: 8px;
        }}
        .news-snippet {{ 
            color: #666; 
            margin-bottom: 10px;
            line-height: 1.5;
        }}
        .news-meta {{
            font-size: 12px;
            color: #999;
            margin-bottom: 8px;
        }}
        .news-link {{ 
            color: #0099cc; 
            text-decoration: none; 
            font-size: 14px;
            font-weight: 500;
        }}
        .news-link:hover {{
            text-decoration: underline;
        }}
        .no-news {{ 
            color: #999; 
            font-style: italic; 
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 4px;
        }}
        .footer {{ 
            margin-top: 40px;
            padding: 20px;
            background-color: #f0f0f0;
            border-radius: 8px;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            background-color: #0066cc;
            color: white;
            margin-left: 10px;
        }}
        .github-badge {{
            background-color: #28a745;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 11px;
            color: white;
            display: inline-block;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>⚾ Daily Sports Tracker Report</h1>
        <div class="summary">
            <strong>Date:</strong> {{datetime.now().strftime('%A, %B %d, %Y')}}<br>
            <strong>Total Updates:</strong> {{total_updates}} item(s) found<br>
            <strong>Players Monitored:</strong> {{len(players_data)}}<br>
            <span class="github-badge">🤖 Automated via GitHub Actions</span>
        </div>
    </div>
"""

    for player_data in players_data:
        player = player_data['player_info']
        news_items = player_data['news']
        
        html += f"""
    <div class="player-section">
        <h2>
            {{player['player']}}
            <span class="badge">{{len(news_items)}} update(s)</span>
        </h2>
        <div class="player-info">
            📍 <strong>{{player['team']}}</strong> • {{player['sport']}}
        </div>
    """
        
        if news_items:
            for item in news_items:
                date_str = ""
                if 'date' in item and item['date']:
                    try:
                        date_obj = datetime.fromisoformat(item['date'].replace('Z', '+00:00'))
                        date_str = f"<div class='news-meta'>📅 {{date_obj.strftime('%B %d, %Y')}} • Source: {{item.get('source', 'Unknown')}}</div>"
                    except:
                        if 'source' in item:
                            date_str = f"<div class='news-meta'>Source: {{item['source']}}</div>"
                
                html += f"""
            <div class="news-item">
                <div class="news-title">{{item['title']}}</div>
                {{date_str}}
                <div class="news-snippet">{{item['snippet']}}</div>
                <a href="{{item['url']}}" class="news-link" target="_blank">Read full article →</a>
            </div>
            """
        else:
            html += '<div class="no-news">📭 No recent news or updates found for this player.</div>'
        
        html += "</div>"

    html += f"""
    <div class="footer">
        <p><strong>Daily Sports Tracker</strong></p>
        <p>Automatically generated on {{datetime.now().strftime('%B %d, %Y at %I:%M %p UTC')}}</p>
        <p style="font-size: 12px; margin-top: 15px;">
            🤖 Running on GitHub Actions - Fully automated!<br>
            📊 Monitoring your Google Spreadsheet for player updates.
        </p>
    </div>
</body>
</html>
"""

    return html

def send_email(subject, html_content):
    """Send email report"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO

        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Email sent successfully to {{EMAIL_TO}}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {{e}}")
        return False

def main():
    """Main execution"""
    print("=" * 60)
    print("DAILY SPORTS TRACKER - GitHub Actions")
    print("=" * 60)
    print(f"Started: {{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}}")
    print()

    # Verify environment variables
    if not EMAIL_TO or not EMAIL_FROM or not EMAIL_PASSWORD:
        print("❌ ERROR: Email configuration missing!")
        print("Please set EMAIL_TO, EMAIL_FROM, and EMAIL_PASSWORD in GitHub Secrets")
        return

    # Check API keys status
    print("API Keys Status:")
    print(f"  NewsAPI: {'✅ Configured' if NEWSAPI_KEY else '❌ Not configured (using basic search)'}")
    print(f"  SerpAPI: {'✅ Configured' if SERPAPI_KEY else '❌ Not configured (using basic search)'}")
    print()

    # Get players
    players = get_spreadsheet_data()

    if not players:
        print("❌ No players found in spreadsheet")
        return

    print(f"📋 Found {{len(players)}} player(s) to track:\n")
    for p in players:
        print(f"  • {{p['player']}} ({{p['team']}})")
    print()

    # Collect news
    players_data = []
    for i, player in enumerate(players, 1):
        print(f"[{{i}}/{{len(players)}}] Searching: {{player['player']}} ({{player['team']}})")
        news = search_player_news(player['player'], player['team'])
        print(f"  ✅ Found {{len(news)}} item(s)\n")
        
        players_data.append({
            'player_info': player,
            'news': news
        })
        
        time.sleep(1)

    # Create and send report
    print("📧 Creating email report...")
    report_html = create_report(players_data)
    subject = f"Daily Sports Update - {{datetime.now().strftime('%b %d, %Y')}}"

    # Send email
    if send_email(subject, report_html):
        print("\n" + "=" * 60)
        print("✅ COMPLETE! Report sent successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Email failed - check GitHub Secrets configuration")
        print("=" * 60)

if __name__ == "__main__":
    main()