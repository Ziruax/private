import streamlit as st
import pandas as pd
import requests
import html
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai
from fake_useragent import UserAgent
import time
import streamlit.components.v1 as components

# Streamlit Configuration
st.set_page_config(page_title="WhatsApp Content Generator", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for Improved UI
st.markdown("""
<style>
body { font-family: 'Segoe UI', sans-serif; background-color: #f0f2f6; }
.main-title { font-size: 2.5em; color: #25D366; text-align: center; margin-bottom: 0; font-weight: 700; }
.subtitle { font-size: 1.2em; color: #555; text-align: center; margin-top: 5px; margin-bottom: 20px; }
.stButton>button { background-color: #25D366; color: white; border-radius: 8px; font-weight: bold; padding: 10px 20px; transition: all 0.3s ease; }
.stButton>button:hover { background-color: #1EBE5A; transform: scale(1.05); }
.stTextInput > div > div > input { border-radius: 6px; padding: 10px; border: 1px solid #ccc; }
.stSlider > div { color: #25D366; }
.whatsapp-groups-table { width: 100%; border-collapse: collapse; margin: 20px 0; box-shadow: 0 4px 8px rgba(0,0,0,0.1); background: white; border-radius: 8px; overflow: hidden; }
.whatsapp-groups-table th { background-color: #343A40; color: white; padding: 12px; font-size: 0.9em; text-transform: uppercase; }
.whatsapp-groups-table td { padding: 10px; vertical-align: middle; font-size: 0.95em; }
.whatsapp-groups-table tr { height: 50px; border-bottom: 1px solid #eee; }
.whatsapp-groups-table tr:nth-child(even) { background-color: #f9fafb; }
.whatsapp-groups-table tr:hover { background-color: #e8f4f8; }
.group-logo-img { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 2px solid #eee; }
.join-button { background-color: #25D366; color: white !important; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 0.85em; }
.join-button:hover { background-color: #1DB954; }
.section { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.status-message { font-size: 1em; color: #333; margin: 10px 0; }
.warning-box { background-color: #fff3cd; padding: 10px; border-radius: 6px; color: #856404; font-size: 0.9em; margin-bottom: 10px; }
@media (max-width: 768px) {
    .whatsapp-groups-table { display: block; overflow-x: auto; }
    .group-logo-img { width: 30px; height: 30px; }
    .join-button { padding: 5px 10px; font-size: 0.8em; }
}
</style>
""", unsafe_allow_html=True)

# Constants
WHATSAPP_DOMAIN = "https://chat.whatsapp.com/"
MAX_WORKERS = 8

# Initialize Fake User Agent
try:
    ua = UserAgent()
except Exception as e:
    st.warning(f"Failed to initialize fake-useragent: {e}. Using default User-Agent.")
    ua = None

def get_headers():
    return {
        "User-Agent": ua.random if ua else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124",
        "Accept-Language": "en-US,en;q=0.9"
    }

# System Prompt
SYSTEM_PROMPT = """
🔹 Content Objective:
Craft a 500+ word SEO-optimized article promoting active and verified WhatsApp group links in a specific niche. The article should be engaging, human-like, conversational, and structured to pass AI detection tools while ranking well in search engines.

🔍 SEO Details
Primary Keyword: {target_keyword}
LSI Keywords: {lsi_keywords}
Local SEO Keywords: {local_keywords}

🌟 Meta Tags
Meta Title: Top {target_keyword} WhatsApp Groups | Active & Verified 2025
Meta Description: Discover the best {target_keyword} WhatsApp groups. Join active, verified links updated for 2025. Fast access & free to join!

✍️ Writing Guidelines
Tone & Voice: First-person, friendly, relatable. Use "I," "we," "you".
Human-Like Flow: Vary sentence length, use contractions, add casual expressions.
Avoid Overuse: Don’t stuff keywords. Use naturally and sparingly.
Bypass AI Detection: Insert real-life anecdotes, natural transitions, personal recommendations.

📅 Suggested Structure & Headings
✉️ 1. Introduction (H1)
Hook the reader with a relatable statement. Mention what they will find. Include main keyword early.
Example: "Looking for the most active {target_keyword} WhatsApp groups in 2025? I've spent hours researching and collecting the best, so you don't have to."

📆 2. Updated {target_keyword} WhatsApp Groups for 2025 (H2)
Use a table: Group Name + 1-2 Line Description + Link. Emphasize benefits or content users can expect.
“Here are the verified and updated WhatsApp groups we’ve personally tested and found active in 2025:”

🔎 3. What is {target_keyword}? (H2)
Explain the keyword simply. Assume the reader has never heard of it. Keep it friendly and non-technical.

🎯 4. Key Benefits of Joining {target_keyword} WhatsApp Groups (H2)
- Stay updated with real-time info.
- Connect with like-minded individuals.
- Access exclusive resources.
- Get quick responses to questions.
- Network with experts.

✅ 5. How to Join & Use {target_keyword} WhatsApp Groups Effectively (H2)
Step-by-step tutorial. Keep it casual and helpful.
Example: "I usually bookmark the invite page or turn on group notifications to never miss updates."

⚠️ 6. Common Mistakes to Avoid (H2)
- Spam posting
- Ignoring group rules
- Not engaging meaningfully
- Sharing outdated links
- Falling for scams

🤔 7. Frequently Asked Questions (H3)
- How can I find more {target_keyword} WhatsApp groups? Explore niche forums, Reddit, and curated lists like ours.
- Are these groups active in 2025? Yes! All groups are verified regularly.
- Do I need admin approval? Most are open join links, but some may require approval.
- Are there groups for specific locations? Check the tags for location-specific ones.
- Is it safe to join? Stick to verified lists like this one, and never share personal info.

📄 8. Conclusion (H2)
Summarize key points. Reinforce benefits. Add a CTA (Subscribe, Share, Bookmark).
Example: "So there you have it — the best {target_keyword} WhatsApp groups for 2025. I’ll keep updating this list, so bookmark this page!"

🌐 Post Metadata
Slug: /{target_keyword}-whatsapp-groups
Category: WhatsApp Groups > {target_keyword}
Tags: {target_keyword}, {lsi_keywords}, 2025, Active Groups, WhatsApp Links
"""

# JavaScript to Load/Save Credentials in Local Storage
components.html("""
<script>
function saveCredentials() {
    const geminiApiKey = document.getElementById('gemini_api_key').value;
    const wpUsername = document.getElementById('wp_username').value;
    const wpAppPassword = document.getElementById('wp_app_password').value;
    const wpSiteUrl = document.getElementById('wp_site_url').value;
    localStorage.setItem('gemini_api_key', geminiApiKey);
    localStorage.setItem('wp_username', wpUsername);
    localStorage.setItem('wp_app_password', wpAppPassword);
    localStorage.setItem('wp_site_url', wpSiteUrl);
}

function loadCredentials() {
    const geminiApiKey = localStorage.getItem('gemini_api_key') || '';
    const wpUsername = localStorage.getItem('wp_username') || '';
    const wpAppPassword = localStorage.getItem('wp_app_password') || '';
    const wpSiteUrl = localStorage.getItem('wp_site_url') || '';
    const inputs = {
        'gemini_api_key': geminiApiKey,
        'wp_username': wpUsername,
        'wp_app_password': wpAppPassword,
        'wp_site_url': wpSiteUrl
    };
    window.parent.postMessage({type: 'SET_INPUTS', inputs: inputs}, '*');
}
window.onload = loadCredentials;
</script>
""", height=0)

# Helper Functions
def validate_link(link):
    result = {"Group Name": "Unnamed Group", "Group Link": link, "Logo URL": "", "Status": "Error", "Description": "A community for enthusiasts."}
    try:
        response = requests.get(link, headers=get_headers(), timeout=20, allow_redirects=True)
        if response.status_code == 200 and WHATSAPP_DOMAIN in response.url:
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.find('meta', property='og:title')
            image = soup.find('meta', property='og:image')
            group_name = html.unescape(title['content']).strip() if title and title.get('content') else "Unnamed Group"
            result["Group Name"] = group_name
            result["Logo URL"] = html.unescape(image['content']) if image and image.get('content') else ""
            result["Status"] = "Active"
            result["Description"] = f"Join this active {group_name} group for updates and discussions."
        else:
            result["Status"] = "Expired"
    except requests.RequestException as e:
        result["Status"] = f"Network Error: {str(e)[:50]}"
    return result

def scrape_google(query, top_n, progress_bar, status_text):
    try:
        from googlesearch import search
    except ImportError:
        st.error("Please install googlesearch-python: `pip install googlesearch-python`")
        return []

    status_text.text("Fetching Google search results...")
    links = set()
    try:
        search_results = list(search(query, num_results=top_n))
    except Exception as e:
        st.error(f"Google search failed: {str(e)[:50]}")
        return []
    progress_bar.progress(0.1)

    with requests.Session() as session:
        for i, url in enumerate(search_results):
            status_text.text(f"Scraping page {i+1}/{len(search_results)}: {url[:50]}...")
            try:
                response = session.get(url, headers=get_headers(), timeout=15)
                soup = BeautifulSoup(response.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if href.startswith(WHATSAPP_DOMAIN):
                        parsed = urlparse(href)
                        links.add(f"{parsed.scheme}://{parsed.netloc}{parsed.path}")
                progress_bar.progress(0.1 + (i + 1) / len(search_results) * 0.4)
            except Exception as e:
                st.warning(f"Error scraping {url[:50]}: {str(e)[:50]}")
            time.sleep(0.5)  # Avoid rate limiting
    return list(links)

def generate_html_table(groups):
    if not groups:
        return "<p style='text-align:center;color:#777;'>No active groups found.</p>"

    html_output = '<table class="whatsapp-groups-table" aria-label="WhatsApp Groups">'
    html_output += '<tr><th>Logo</th><th>Group Name</th><th>Description</th><th>Link</th></tr>'
    for group in groups:
        group_name = html.escape(group.get("Group Name", "Unnamed Group") or "Unnamed Group")
        logo_url = html.escape(group.get("Logo URL", ""))
        link = html.escape(group.get("Group Link", ""))
        desc = html.escape(group.get("Description", "A community for enthusiasts."))
        html_output += '<tr>'
        html_output += f'<td><img src="{logo_url}" class="group-logo-img" alt="{group_name} Logo" onerror="this.style.display=\'none\'"></td>'
        html_output += f'<td>{group_name}</td>'
        html_output += f'<td>{desc}</td>'
        html_output += f'<td><a href="{link}" class="join-button" target="_blank" rel="nofollow noopener">Join</a></td>'
        html_output += '</tr>'
    html_output += '</table>'
    return html_output

def generate_content_table(groups):
    html_output = '<table border="1"><tr><th>Group Name</th><th>Description</th><th>Link</th></tr>'
    for group in groups:
        group_name = html.escape(group.get("Group Name", "Unnamed Group") or "Unnamed Group")
        desc = html.escape(group.get("Description", "A community for enthusiasts."))
        link = html.escape(group.get("Group Link", ""))
        html_output += f'<tr><td>{group_name}</td><td>{desc}</td><td><a href="{link}" target="_blank" rel="nofollow noopener">Join</a></td></tr>'
    html_output += '</table>'
    return html_output

# Main App
def main():
    st.markdown('<h1 class="main-title">WhatsApp Content Generator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Search, Scrape, and Create SEO-Optimized Content for Your WordPress Site</p>', unsafe_allow_html=True)

    # Security Warning
    st.markdown(
        '<div class="warning-box">⚠️ <strong>Security Warning:</strong> Storing API keys and WordPress credentials in the browser is not secure. '
        'Use this for testing only. For production, use Streamlit Cloud Secrets or environment variables.</div>',
        unsafe_allow_html=True
    )

    # Initialize Session State
    if 'groups' not in st.session_state:
        st.session_state.groups = []
    if 'content' not in st.session_state:
        st.session_state.content = None
    if 'selected_groups' not in st.session_state:
        st.session_state.selected_groups = []
    if 'gemini_api_key' not in st.session_state:
        st.session_state.gemini_api_key = ""
    if 'wp_username' not in st.session_state:
        st.session_state.wp_username = ""
    if 'wp_app_password' not in st.session_state:
        st.session_state.wp_app_password = ""
    if 'wp_site_url' not in st.session_state:
        st.session_state.wp_site_url = ""

    # Sidebar for Inputs
    with st.sidebar:
        st.header("🔍 Configuration")
        gemini_api_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.gemini_api_key,
            type="password",
            help="Enter your Gemini API key from Google AI Studio.",
            key="gemini_api_key"
        )
        wp_username = st.text_input(
            "WordPress Username",
            value=st.session_state.wp_username,
            help="Enter your WordPress username.",
            key="wp_username"
        )
        wp_app_password = st.text_input(
            "WordPress Application Password",
            value=st.session_state.wp_app_password,
            type="password",
            help="Enter your WordPress Application Password (generated in Users > Profile).",
            key="wp_app_password"
        )
        wp_site_url = st.text_input(
            "WordPress Site URL",
            value=st.session_state.wp_site_url,
            help="Enter your WordPress site URL (e.g., https://yourwordpresssite.com).",
            key="wp_site_url"
        )

        # Update Session State
        st.session_state.gemini_api_key = gemini_api_key
        st.session_state.wp_username = wp_username
        st.session_state.wp_app_password = wp_app_password
        st.session_state.wp_site_url = wp_site_url

        # JavaScript to Save Credentials on Input Change
        components.html("""
        <script>
        const inputs = ['gemini_api_key', 'wp_username', 'wp_app_password', 'wp_site_url'];
        inputs.forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.addEventListener('input', () => {
                    localStorage.setItem(id, input.value);
                });
            }
        });
        </script>
        """, height=0)

        st.header("🔍 Search Settings")
        search_query = st.text_input("Search Query", "crypto WhatsApp groups", help="Enter a Google search query to find WhatsApp groups.")
        target_keyword = st.text_input("Target Keyword", "Crypto", help="Primary keyword for SEO content.")
        lsi_keywords = st.text_input("LSI Keywords (comma-separated)", "cryptocurrency, bitcoin, blockchain", help="Related keywords for SEO.")
        local_keywords = st.text_input("Local SEO Keywords", "", help="Optional: e.g., New York Crypto, USA Blockchain")
        post_title = st.text_input("Post Title", "Top Crypto WhatsApp Groups 2025", help="Title for the WordPress post.")
        top_n = st.slider("Google Results to Scrape", 1, 20, 5, help="Number of Google search results to analyze.")

        if st.button("Clear All Data", use_container_width=True):
            st.session_state.groups = []
            st.session_state.content = None
            st.session_state.selected_groups = []
            st.session_state.gemini_api_key = ""
            st.session_state.wp_username = ""
            st.session_state.wp_app_password = ""
            st.session_state.wp_site_url = ""
            components.html("<script>localStorage.clear();</script>", height=0)
            st.success("All data and credentials cleared!")
            st.rerun()

    # Search and Scrape
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.subheader("1. Search & Scrape Groups")
    if st.button("Search & Scrape", use_container_width=True):
        if not search_query:
            st.error("Please enter a search query.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            links = scrape_google(search_query, top_n, progress_bar, status_text)
            if links:
                status_text.text(f"Validating {len(links)} links...")
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = {executor.submit(validate_link, link): link for link in links}
                    results = []
                    for i, future in enumerate(as_completed(futures)):
                        try:
                            result = future.result()
                            if result["Status"] == "Active":
                                results.append(result)
                        except Exception as e:
                            st.warning(f"Error validating link: {str(e)[:50]}")
                        progress_bar.progress(0.5 + (i + 1) / len(links) * 0.4)
                    st.session_state.groups = results
                    status_text.success(f"Found {len(results)} active groups!")
            else:
                status_text.error("No WhatsApp group links found.")
            progress_bar.progress(1.0)
    st.markdown('</div>', unsafe_allow_html=True)

    # Display and Filter Groups
    if st.session_state.groups:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.subheader("2. Select Groups")
        html_table = generate_html_table(st.session_state.groups)
        st.markdown(html_table, unsafe_allow_html=True)

        group_names = [g["Group Name"] for g in st.session_state.groups if g.get("Group Name")]
        selected_names = st.multiselect(
            "Select Groups for Content",
            group_names,
            default=st.session_state.get("selected_groups", group_names),
            help="Choose which groups to include in the article."
        )
        st.session_state.selected_groups = selected_names
        selected_groups = [g for g in st.session_state.groups if g.get("Group Name") in selected_names]
        st.markdown('</div>', unsafe_allow_html=True)

        # Generate Content
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.subheader("3. Generate Content")
        if st.button("Generate Content", use_container_width=True):
            if not selected_groups:
                st.error("Please select at least one group.")
            elif not gemini_api_key:
                st.error("Please enter a Gemini API key in the sidebar.")
            else:
                with st.spinner("Generating SEO-optimized content..."):
                    try:
                        groups_table = generate_content_table(selected_groups)
                        prompt = SYSTEM_PROMPT.format(
                            target_keyword=target_keyword,
                            lsi_keywords=lsi_keywords,
                            local_keywords=local_keywords or "None"
                        ) + f"\n\nPost Title: {post_title}\nGroups Table:\n{groups_table}"
                        genai.configure(api_key=gemini_api_key)
                        model = genai.GenerativeModel('gemini-2.0-flash')
                        response = model.generate_content(prompt)
                        st.session_state.content = response.text
                        st.success("Content generated successfully!")
                    except Exception as e:
                        st.error(f"Error generating content: {str(e)[:100]}. Please verify your Gemini API key.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Display and Post Content
    if st.session_state.content:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.subheader("4. Review & Post Content")
        st.markdown(st.session_state.content, unsafe_allow_html=True)
        if st.button("Post to WordPress", use_container_width=True):
            if not all([wp_username, wp_app_password, wp_site_url]):
                st.error("Please enter all WordPress credentials in the sidebar.")
            else:
                with st.spinner("Posting to WordPress..."):
                    try:
                        auth = (wp_username, wp_app_password)
                        post_data = {
                            'title': post_title,
                            'content': st.session_state.content,
                            'status': 'draft',
                            'slug': f"{target_keyword.lower().replace(' ', '-')}-whatsapp-groups",
                            'categories': [],  # Add category IDs if needed
                            'tags': [target_keyword, *lsi_keywords.split(','), '2025', 'Active Groups', 'WhatsApp Links']
                        }
                        response = requests.post(
                            f"{wp_site_url.rstrip('/')}/wp-json/wp/v2/posts",
                            auth=auth,
                            json=post_data
                        )
                        if response.status_code == 201:
                            st.success("Posted as draft to WordPress!")
                        else:
                            st.error(f"Failed to post: {response.status_code} - {response.text[:100]}")
                    except Exception as e:
                        st.error(f"Error posting to WordPress: {str(e)[:100]}. Please verify your WordPress credentials and site URL.")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
