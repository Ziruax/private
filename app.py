import streamlit as st
import pandas as pd
import requests
import html
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai

# Streamlit Configuration
st.set_page_config(page_title="WhatsApp Content Generator", layout="wide")

# Custom CSS for Responsive Table
st.markdown("""
<style>
.whatsapp-groups-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
.whatsapp-groups-table th { background-color: #343A40; color: white; padding: 10px; }
.whatsapp-groups-table td { padding: 8px; vertical-align: middle; }
.whatsapp-groups-table tr { height: 50px; }
.whatsapp-groups-table tr:nth-child(even) { background-color: #F9FAFB; }
.group-logo-img { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; }
.join-button { background-color: #25D366; color: white; padding: 6px 12px; border-radius: 6px; text-decoration: none; }
@media (max-width: 768px) {
    .whatsapp-groups-table { display: block; overflow-x: auto; }
    .group-logo-img { width: 30px; height: 30px; }
    .join-button { padding: 5px 10px; font-size: 0.8em; }
}
</style>
""", unsafe_allow_html=True)

# Constants
WHATSAPP_DOMAIN = "https://chat.whatsapp.com/"

# System Prompt
SYSTEM_PROMPT = """
🔹 Content Objective:

Craft a 500+ word SEO-optimized article promoting active and verified WhatsApp group links in a specific niche. The article should be engaging, human-like, conversational, and structured to pass AI detection tools while ranking well in search engines.

🔍 SEO Details

Primary Keyword: {target_keyword}

LSI Keywords (3-5): [Insert Related Keywords]

Local SEO Keywords (if relevant): [City/Country/Interest-based keywords]

🌟 Meta Tags

Meta Title: 50-60 characters | Keyword-rich, click-worthy

Example: Top [Keyword] WhatsApp Groups | Active & Verified 2025

Meta Description: 150-160 characters | Summarizes the benefit

Example: Discover the best [Keyword] WhatsApp groups. Join active, verified links updated for 2025. Fast access & free to join!

✍️ Writing Guidelines

Tone & Voice: First-person, friendly, and relatable. Use "I," "we," "you".

Human-Like Flow: Vary sentence length, use contractions, add casual expressions.

Avoid Overuse: Don’t stuff keywords. Use naturally and sparingly.

Bypass AI Detection: Insert real-life anecdotes, natural transitions, and personal recommendations.

📅 Suggested Structure & Headings

✉️ 1. Introduction (H1)

Hook the reader with a relatable statement.

Mention what they will find in the post.

Include the main keyword early.

Example:
"Looking for the most active [Target Keyword] WhatsApp groups in 2025? I've spent hours researching and collecting the best, so you don't have to."

📆 2. Updated [Target Keyword] WhatsApp Groups for 2025 (H2)

Use a numbered list: Group Name + 1-2 Line Description

Emphasize benefits or what kind of content users can expect.

“Here are the verified and updated WhatsApp groups we’ve personally tested and found active in 2025:”

Note: Insert the groups table here.

🔎 3. What is [Target Keyword]? (H2)

Explain the keyword simply.

Assume the reader has never heard of it before.

Keep it friendly and non-technical.

🎯 4. Key Benefits of Joining [Target Keyword] WhatsApp Groups (H2)

Use bullet points or short paragraphs:

Stay updated with real-time [industry-specific info].

Connect with like-minded individuals.

Access exclusive resources.

Get quick responses to questions.

Network with experts.

✅ 5. How to Join & Use [Target Keyword] WhatsApp Groups Effectively (H2)

Write a step-by-step tutorial.

Keep it casual and helpful.

Example:
"I usually bookmark the invite page or turn on group notifications to never miss updates."

⚠️ 6. Common Mistakes to Avoid When Using These Groups (H2)

Spam posting

Ignoring group rules

Not engaging meaningfully

Sharing outdated links

Falling for scams

Use a helpful and non-judgmental tone.

🤔 7. Frequently Asked Questions (Use H3 for Questions)

How can I find more [target keyword] WhatsApp groups?Explore niche forums, Reddit, and curated lists like ours.

Are these groups really active in 2025?Yes! All groups are verified by our team regularly.

Do I need admin approval to join?Most are open join links, but some may require approval.

Are there groups for [specific location or subgroup]?Absolutely! Check the tags to find location-specific ones.

Is it safe to join random WhatsApp groups?Stick to verified lists like this one, and never share personal info.

📄 8. Conclusion (H2)

Summarize key points.

Reinforce the benefits.

Add a CTA (Subscribe, Share, Comment, Bookmark).

Example:
"So there you have it — the best [Target Keyword] WhatsApp groups for 2025. I’ll keep updating this list regularly, so be sure to check back or bookmark this page!"

📊 SEO Optimization Checklist

🌐 Post Metadata Template (for WordPress or SEO Plugin)

Title: [Auto-generate or write manually]

Meta Title: [Insert Meta Title Here]

Meta Description: [Insert Meta Description Here]

Focus Keyword: [Target Keyword]

Slug: /[target-keyword]-whatsapp-groups

Category: WhatsApp Groups > [Niche/Industry]

Tags: [Target Keyword], [Related Keywords], [Year], Active Groups, WhatsApp Links
"""

# Helper Functions
def validate_link(link):
    result = {"Group Name": "Unnamed Group", "Group Link": link, "Logo URL": "", "Status": "Error"}
    try:
        response = requests.get(link, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        if response.status_code == 200 and WHATSAPP_DOMAIN in response.url:
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.find('meta', property='og:title')
            image = soup.find('meta', property='og:image')
            if title and title.get('content'):
                result["Group Name"] = html.unescape(title['content'])
            if image and image.get('content'):
                result["Logo URL"] = html.unescape(image['content'])
            result["Status"] = "Active"
        else:
            result["Status"] = "Expired"
    except requests.RequestException:
        result["Status"] = "Network Error"
    return result

def scrape_google(query, top_n):
    from googlesearch import search
    links = set()
    for url in search(query, num_results=top_n):
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                if a['href'].startswith(WHATSAPP_DOMAIN):
                    links.add(a['href'])
        except:
            continue
    return list(links)

def generate_html_table(groups):
    html = '<table class="whatsapp-groups-table"><tr><th>Logo</th><th>Group Name</th><th>Link</th></tr>'
    for group in groups:
        html += f'<tr><td><img src="{group["Logo URL"]}" class="group-logo-img" onerror="this.style.display=\'none\'"></td>'
        html += f'<td>{html.escape(group["Group Name"])}</td>'
        html += f'<td><a href="{group["Group Link"]}" class="join-button" target="_blank" rel="nofollow noopener">Join</a></td></tr>'
    html += '</table>'
    return html

def generate_content_table(groups):
    html = '<table><tr><th>Group Name</th><th>Link</th></tr>'
    for group in groups:
        html += f'<tr><td>{html.escape(group["Group Name"])}</td><td><a href="{group["Group Link"]}" target="_blank" rel="nofollow noopener">Join</a></td></tr>'
    html += '</table>'
    return html

# Main App
def main():
    st.title("WhatsApp Content Generator")

    # Inputs
    search_query = st.text_input("Search Query", "crypto WhatsApp groups")
    target_keyword = st.text_input("Target Keyword", "crypto")
    post_title = st.text_input("Post Title", "Top Crypto WhatsApp Groups 2025")
    top_n = st.slider("Number of Google Results", 1, 20, 5)

    if 'groups' not in st.session_state:
        st.session_state.groups = []
    if 'content' not in st.session_state:
        st.session_state.content = None

    if st.button("Search & Scrape"):
        links = scrape_google(search_query, top_n)
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(validate_link, links))
        st.session_state.groups = [r for r in results if r["Status"] == "Active"]
        st.success(f"Found {len(st.session_state.groups)} active groups.")

    if st.session_state.groups:
        st.subheader("Active Groups")
        html_table = generate_html_table(st.session_state.groups)
        st.markdown(html_table, unsafe_allow_html=True)

        selected_names = st.multiselect("Select Groups", [g["Group Name"] for g in st.session_state.groups], default=[g["Group Name"] for g in st.session_state.groups])
        selected_groups = [g for g in st.session_state.groups if g["Group Name"] in selected_names]

        if st.button("Generate Content"):
            groups_table = generate_content_table(selected_groups)
            prompt = f"{SYSTEM_PROMPT.format(target_keyword=target_keyword)}\n\nTarget Keyword: {target_keyword}\nPost Title: {post_title}\nGroups Table:\n{groups_table}"
            genai.configure(api_key=st.secrets["gemini"]["api_key"])
            model = genai.GenerativeModel('gemini-2.0-flash')
            with st.spinner("Generating content..."):
                response = model.generate_content(prompt)
                st.session_state.content = response.text
            st.success("Content generated!")

    if st.session_state.content:
        st.subheader("Generated Content")
        st.markdown(st.session_state.content, unsafe_allow_html=True)
        if st.button("Post to WordPress"):
            auth = (st.secrets["wordpress"]["username"], st.secrets["wordpress"]["app_password"])
            post_data = {
                'title': post_title,
                'content': st.session_state.content,
                'status': 'draft'
            }
            response = requests.post(f"{st.secrets['wordpress']['site_url']}/wp-json/wp/v2/posts", auth=auth, json=post_data)
            if response.status_code == 201:
                st.success("Posted as draft!")
            else:
                st.error(f"Error: {response.status_code}")

if __name__ == "__main__":
    main()
