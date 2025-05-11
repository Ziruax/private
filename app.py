import streamlit as st
import pandas as pd
import requests
import html as html_parser # Aliased to avoid potential shadowing
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai
from fake_useragent import UserAgent
import time
import re # For cleaning up AI generated content

# Streamlit Configuration
st.set_page_config(page_title="WhatsApp Content Generator", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for Improved UI (from your initial code)
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
.section { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 1200px; margin-left: auto; margin-right: auto;}
.status-message { font-size: 1em; color: #333; margin: 10px 0; }
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
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124" # From your original

# Initialize Fake User Agent
try:
    ua = UserAgent()
except Exception as e:
    st.warning(f"Failed to initialize fake-useragent: {e}. Using default User-Agent.")
    ua = None

def get_headers(): # From your original
    return {
        "User-Agent": ua.random if ua else DEFAULT_USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9"
    }

# System Prompt (Enhanced version, as this was a positive change)
SYSTEM_PROMPT = """
(((((You are an expert SEO content writer. Your goal is to write a highly engaging, human-like, and SEO-optimized article that will pass AI detection tools and rank well. Use a conversational, first-person narrative (I, we, you).))))

🔹 **Content Objective:**
Craft a 500+ word article promoting active and verified WhatsApp group links for the niche: **{target_keyword}**.
The article must be exceptionally human-like, avoiding robotic phrasing or predictable AI patterns. It should feel like a genuine recommendation from an experienced individual.

🔍 **SEO Details (for content guidance, not for WP tags/cats by script):**
- **Primary Keyword:** {target_keyword}
- **LSI Keywords:** {lsi_keywords}
- **Local SEO Keywords (if applicable):** {local_keywords}

🌟 **Meta Tags (Suggest these at the end of the article in a separate block for manual use):**
- **Meta Title (60-70 chars):** Example: Top {target_keyword} WhatsApp Groups 2025: Active & Verified Links
- **Meta Description (150-160 chars):** Example: Join the best {target_keyword} WhatsApp groups! Discover active, verified 2025 links for instant access to community, news, and resources.

✍️ **Writing Guidelines for AI Detection Bypass & Human Touch:**
1.  **Tone & Voice:** Strictly first-person ("I found...", "We recommend...", "You'll discover..."). Be friendly, relatable, enthusiastic, and slightly opinionated.
2.  **Human-Like Flow:**
    *   Vary sentence length and structure significantly. Mix short, punchy sentences with longer, more descriptive ones.
    *   Use contractions (e.g., "it's", "you'll", "we've") and casual, conversational expressions.
    *   Incorporate rhetorical questions to engage the reader.
    *   Use natural transitions between paragraphs and ideas.
3.  **Avoid Overuse:** Keywords should appear naturally. Don't stuff them. Prioritize readability and value over keyword density.
4.  **Unique Value & Anecdotes:**
    *   Insert at least one brief, relatable (even if fictionalized for demonstration) anecdote or personal observation about using such groups or finding information in the niche.
    *   Provide unique insights or tips that go beyond a simple list of links.
5.  **Critical Self-Correction:** Before finalizing, review your writing. If any sentence sounds like it was written by an AI, rewrite it. Does it sound like something a real person would say or write on their blog?
6.  **Formatting:** Use Markdown for headings, bolding, italics, and lists to improve readability.

📅 **Suggested Article Structure (Adapt as needed for flow and niche):**

**<h1>Catchy, Keyword-Rich Title for the Article (Not the Meta Title)</h1>**

**<h2>👋 Introduction: Hook 'Em In!</h2>**
   - Start with a relatable hook. Why are people searching for these groups?
   - Briefly introduce what the article offers (curated, active groups for {target_keyword}).
   - Naturally include the primary keyword early on.
   *Example: "Hey everyone! If you're like me, you're always on the lookout for the best places to connect and get the latest scoop on {target_keyword}. I've dived deep to find the most active {target_keyword} WhatsApp groups for 2025, so you don't have to!*"

**<h2>🚀 Verified {target_keyword} WhatsApp Groups – Updated 2025 (Our Top Picks!)</h2>**
   - Present the groups. The actual HTML table of groups will be inserted here. Your text should lead into it.
   - Emphasize that these are verified and active.
   *Example: "Alright, let's get to the good stuff! Below is a table of WhatsApp groups I've personally checked out. They're packed with {target_keyword} enthusiasts and buzzing with activity:"*
   
   {{{{GROUP_TABLE_PLACEHOLDER}}}} (You will write the text around this placeholder; the actual table will be injected by the script)

**<h2>🤔 What Exactly IS {target_keyword}? (A Quick, Friendly Explainer)</h2>** (Optional, if the keyword isn't universally understood)
   - Briefly explain the {target_keyword} in simple, layperson terms. Keep it friendly and engaging.

**<h2>🌟 Why Join {target_keyword} WhatsApp Groups? (The Real Perks)</h2>**
   - Bullet points or short paragraphs on benefits:
     - Real-time updates & news
     - Networking with like-minded people / experts
     - Access to exclusive tips, resources, or deals
     - Quick answers to niche questions
     - Community support and discussion

**<h2>💡 How to Make the Most of These Groups (Our Pro Tips)</h2>**
   - Offer actionable advice:
     - Introduce yourself (if appropriate for group culture).
     - Be respectful and follow group rules.
     - Participate actively but avoid spamming.
     - Share value and help others.
     - *Personal touch example: "I always make it a point to check a new group's rules first – saves a lot of hassle later!"*

**<h2>⚠️ A Word of Caution: Staying Safe in Online Groups</h2>**
   - Briefly mention common sense safety:
     - Don't share overly personal information.
     - Be wary of unsolicited DMs or suspicious links.
     - Verify information before acting on it.

**<h2>🙋‍♀️ Frequently Asked Questions (FAQs)</h2>**
   - **Q1: How often is this list updated?**
     *A: We strive to check these links regularly to ensure they're active for 2025!*
   - **Q2: Are these groups free to join?**
     *A: Yes, all listed groups have direct join links and are free.*
   - **Q3: Can I suggest a group?**
     *A: Absolutely! Feel free to drop a comment (if comments are enabled on the site) or contact us.*

**<h2>🎬 Conclusion: Your Turn to Connect!</h2>**
   - Summarize the value offered.
   - Reinforce the benefits of joining.
   - End with a friendly call to action (e.g., "Go ahead, pick a group, and dive in! Let me know which ones you love.").
   - *Example: "So there you have it – your go-to list for {target_keyword} WhatsApp groups in 2025. I'm confident you'll find some amazing communities here. Happy connecting!"*

---
**Post Metadata Suggestions (for your manual use in WordPress):**
Slug: {target_keyword}-whatsapp-groups-2025 (The script will try to set this slug)
Category: WhatsApp Groups (Primary), {target_keyword} (Sub-category if possible)
Tags: {target_keyword}, {lsi_keywords_comma_separated_for_tags}, WhatsApp Groups, Active Links 2025, {local_keywords_comma_separated_for_tags}
Meta Title: (Generated based on above guidelines)
Meta Description: (Generated based on above guidelines)
---
"""

# --- Helper Functions ---

# YOUR ORIGINAL validate_link function
def validate_link(link):
    result = {"Group Name": "Unnamed Group", "Group Link": link, "Logo URL": "", "Status": "Error", "Description": "A community for enthusiasts."}
    try:
        response = requests.get(link, headers=get_headers(), timeout=20, allow_redirects=True)
        if response.status_code == 200 and WHATSAPP_DOMAIN in response.url:
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.find('meta', property='og:title')
            image = soup.find('meta', property='og:image')
            # Use html_parser.unescape for consistency with other parts of the code
            group_name = html_parser.unescape(title['content']).strip() if title and title.get('content') else None # Changed to None if no name
            
            if group_name: # Only proceed if a group name was found
                result["Group Name"] = group_name
                result["Logo URL"] = html_parser.unescape(image['content']) if image and image.get('content') else ""
                result["Status"] = "Active"
                # AI description will be handled later if needed, remove default here
                result["Description"] = "" # Start with empty, AI can fill if needed
            else:
                result["Group Name"] = None # Explicitly set to None if not found
                result["Status"] = "No Group Name Found" # More specific status
        else:
            result["Status"] = "Expired"
    except requests.RequestException as e:
        result["Status"] = f"Network Error: {str(e)[:50]}"
    return result

# YOUR ORIGINAL scrape_google function
def scrape_google(query, top_n, progress_bar, status_text):
    try:
        from googlesearch import search
    except ImportError:
        st.error("Please install googlesearch-python: `pip install googlesearch-python`")
        return []

    status_text.text("Fetching Google search results...")
    links = set()
    try:
        # Your original search call didn't specify user_agent, but it's good practice
        search_results = list(search(query, num_results=top_n, user_agent=get_headers()["User-Agent"]))
    except Exception as e:
        st.error(f"Google search failed: {str(e)[:100]}") # Show more of the error
        return []
    
    if not search_results:
        status_text.warning("No search results found on Google for this query.")
        return []
        
    progress_bar.progress(0.1)

    with requests.Session() as session:
        session.headers.update(get_headers()) # Ensure session uses consistent headers
        for i, url in enumerate(search_results):
            status_text.text(f"Scraping page {i+1}/{len(search_results)}: {url[:50]}...")
            try:
                response = session.get(url, timeout=15) # Removed headers=get_headers() as session has them
                response.raise_for_status() # Good practice to check for HTTP errors
                soup = BeautifulSoup(response.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if href.startswith(WHATSAPP_DOMAIN): # Your original check
                        parsed = urlparse(href)
                        # Your original link construction
                        links.add(f"{parsed.scheme}://{parsed.netloc}{parsed.path}")
                progress_bar.progress(0.1 + (i + 1) / len(search_results) * 0.4)
            except requests.exceptions.RequestException as e: # Catch specific request errors
                st.warning(f"Error scraping {url[:50]}: {str(e)[:50]}")
            except Exception as e: # Catch other potential errors during parsing
                st.warning(f"Unexpected error scraping {url[:50]}: {str(e)[:50]}")
            time.sleep(0.5)  # Avoid rate limiting
    return list(links)


# HTML table generation (from your original, with html_parser.escape)
def generate_display_html_table(groups_to_display):
    if not groups_to_display:
        return "<p style='text-align:center;color:#777;'>No active groups found or selected.</p>"

    html_output = '<table class="whatsapp-groups-table" aria-label="WhatsApp Groups">'
    html_output += '<thead><tr><th>Logo</th><th>Group Name</th><th>Description</th><th>Link</th></tr></thead><tbody>'
    for group in groups_to_display:
        # Group Name is now guaranteed by earlier filtering
        group_name = html_parser.escape(group["Group Name"])
        logo_url = html_parser.escape(group.get("Logo URL", ""))
        link = html_parser.escape(group.get("Group Link", "#"))
        # Use AI Description if available, otherwise scraped (which is now empty initially), or a generic fallback
        desc_to_use = group.get("AI_Description") or group.get("Description") or "Details in group."
        desc = html_parser.escape(desc_to_use)
        
        html_output += '<tr>'
        html_output += f'<td><img src="{logo_url}" class="group-logo-img" alt="{group_name} Logo" onerror="this.style.display=\'none\'"></td>'
        html_output += f'<td>{group_name}</td>'
        html_output += f'<td>{desc}</td>'
        html_output += f'<td><a href="{link}" class="join-button" target="_blank" rel="nofollow noopener noreferrer">Join</a></td>'
        html_output += '</tr>'
    html_output += '</tbody></table>'
    return html_output

# Content table for AI (from your original, with html_parser.escape)
def generate_content_table_for_ai(groups_for_ai):
    if not groups_for_ai:
        return "<p><em>(No specific group details to list here)</em></p>"
    
    html_output = '<table border="1" style="width:100%; border-collapse: collapse;">\n' # Added style for AI
    html_output += '<tr><th style="padding: 5px; background-color: #f0f0f0;">Group Name</th><th style="padding: 5px; background-color: #f0f0f0;">Short Description</th><th style="padding: 5px; background-color: #f0f0f0;">Join Link</th></tr>\n'
    for group in groups_for_ai:
        group_name = html_parser.escape(group["Group Name"]) # Assured to exist
        desc = html_parser.escape(group.get("AI_Description") or group.get("Description") or f"Community for {group_name}.")
        link = html_parser.escape(group.get("Group Link", "#"))
        html_output += f'<tr><td style="padding: 5px;">{group_name}</td><td style="padding: 5px;">{desc}</td><td style="padding: 5px;"><a href="{link}" target="_blank" rel="nofollow noopener noreferrer">Join Group</a></td></tr>\n'
    html_output += '</table>'
    return html_output


def generate_short_description_with_ai(group_name, niche_topic, gemini_api_key_desc):
    if not gemini_api_key_desc:
        st.toast(f"Gemini API key missing for AI description of {group_name}.", icon="⚠️")
        return f"Join {group_name} to discuss {niche_topic}." # Basic fallback
    if not group_name: # Should not happen if filtering is correct
        return "General group for this topic."

    try:
        genai.configure(api_key=gemini_api_key_desc)
        model = genai.GenerativeModel('gemini-2.0-flash') # As per your request
        prompt = f"Create a very short, engaging WhatsApp group description (strictly 30-60 characters, ideally 45-50) for a group named '{group_name}' about '{niche_topic}'. Make it appealing, clear what it offers. Avoid quotes."
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        response = model.generate_content(prompt, safety_settings=safety_settings)
        
        ai_desc = response.text.strip().replace('"', '').replace("'", "")
        
        if len(ai_desc) > 60: ai_desc = ai_desc[:57] + "..."
        elif len(ai_desc) < 20: ai_desc = f"Your hub for {group_name} and {niche_topic}!"

        return ai_desc if ai_desc else f"Explore {group_name} for {niche_topic} news."

    except Exception as e:
        st.warning(f"AI description generation failed for '{group_name}': {str(e)[:100]}.")
        return f"A group for {group_name} ({niche_topic})."

# Main App
def main():
    st.markdown('<h1 class="main-title">WhatsApp Content Generator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Search, Scrape, and Create SEO-Optimized Content for Your WordPress Site</p>', unsafe_allow_html=True)

    if 'groups' not in st.session_state:
        st.session_state.groups = [] # Will ONLY store active, named groups
    if 'content' not in st.session_state:
        st.session_state.content = None
    if 'selected_group_names' not in st.session_state: # Store names of selected groups
        st.session_state.selected_group_names = []

    with st.sidebar:
        st.header("⚙️ Configuration")
        gemini_api_key = st.text_input("Gemini API Key", type="password", help="Enter your Gemini API key. Ensure 'gemini-2.0-flash' is available for this key.")
        
        st.subheader("🔍 Search Settings")
        search_query_default = "crypto WhatsApp groups" # From your original
        search_query = st.text_input("Google Search Query", st.session_state.get("search_query", search_query_default))
        st.session_state.search_query = search_query

        top_n_default = 5 # From your original
        top_n = st.slider("Google Results to Scrape", 1, 20, st.session_state.get("top_n", top_n_default))
        st.session_state.top_n = top_n

        st.subheader("📝 Content Details")
        target_keyword_default = "Crypto" # From your original
        target_keyword = st.text_input("Target Keyword", st.session_state.get("target_keyword",target_keyword_default))
        st.session_state.target_keyword = target_keyword

        lsi_keywords_default = "cryptocurrency, bitcoin, blockchain" # From your original
        lsi_keywords = st.text_input("LSI Keywords (comma-separated)", st.session_state.get("lsi_keywords",lsi_keywords_default))
        st.session_state.lsi_keywords = lsi_keywords

        local_keywords_default = "" # From your original
        local_keywords = st.text_input("Local SEO Keywords (optional)", st.session_state.get("local_keywords",local_keywords_default))
        st.session_state.local_keywords = local_keywords
        
        post_title_default = f"Top {target_keyword or 'Niche'} WhatsApp Groups 2025" # Adjusted from your original
        post_title = st.text_input("WordPress Post Title", st.session_state.get("post_title", post_title_default))
        st.session_state.post_title = post_title

        if st.button("Clear All Session Data", use_container_width=True, type="secondary"): # Changed button text slightly
            keys_to_clear = ['groups', 'content', 'selected_group_names', 
                             'search_query', 'top_n', 'target_keyword', 'lsi_keywords', 'local_keywords', 'post_title']
            for key in keys_to_clear:
                if key in st.session_state: del st.session_state[key]
            st.success("All session data cleared!")
            st.rerun()

    wp_secrets_ok = False
    try:
        if "wordpress" in st.secrets and all(key in st.secrets["wordpress"] for key in ["username", "app_password", "site_url"]):
            wp_secrets_ok = True
        else:
            st.error(
                "WordPress credentials incomplete in Streamlit Secrets. Please add:\n"
                "```toml\n[wordpress]\nusername = \"your_wp_username\"\napp_password = \"your_wp_application_password\"\nsite_url = \"https://yourwordpresssite.com\"\n```"
            )
    except Exception as e:
        st.error(f"Error accessing WordPress secrets: {str(e)}. Check secrets.toml.")

    col1, col2 = st.columns([0.6, 0.4]) # Using columns for layout

    with col1:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.subheader("1. Find WhatsApp Groups")
        scrape_button_text = "Search & Scrape Groups"
        if st.session_state.groups: scrape_button_text = "Re-Scrape / Find More Groups"
        
        if st.button(scrape_button_text, use_container_width=True, type="primary"):
            if not search_query:
                st.error("Please enter a search query in the sidebar.")
            else:
                st.session_state.groups = [] 
                st.session_state.selected_group_names = []
                st.session_state.content = None

                scrape_progress_bar = st.progress(0, text="Initializing search...")
                scrape_status_text = st.empty()
                
                # Using your original scrape_google function
                potential_links = scrape_google(search_query, top_n, scrape_progress_bar, scrape_status_text)
                
                if potential_links:
                    scrape_status_text.text(f"Found {len(potential_links)} potential links. Validating now...")
                    scrape_progress_bar.progress(0.5, text="Validating links...") # Adjusted progress
                    
                    all_validated_results = []
                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        future_to_link = {executor.submit(validate_link, link): link for link in potential_links}
                        for i, future in enumerate(as_completed(future_to_link)):
                            try:
                                result = future.result()
                                all_validated_results.append(result)
                            except Exception as exc:
                                st.warning(f"Error validating link ({future_to_link[future]}): {exc}")
                            # Adjusted progress calculation
                            scrape_progress_bar.progress(0.5 + ((i + 1) / len(potential_links) * 0.5), text=f"Validating link {i+1}/{len(potential_links)}")
                    
                    # Filter for active groups WITH names (as per your original validate_link logic where name can be None)
                    st.session_state.groups = [
                        g for g in all_validated_results if g["Status"] == "Active" and g.get("Group Name") and g["Group Name"] != "Unnamed Group"
                    ]
                    
                    active_found = len(st.session_state.groups)
                    total_processed = len(all_validated_results)
                    scrape_status_text.success(f"Validation complete! Found {active_found} active, named groups out of {total_processed} processed links.")
                else:
                    scrape_status_text.error("No potential WhatsApp group links found from Google scraping.")
                scrape_progress_bar.empty() # Remove progress bar
        st.markdown('</div>', unsafe_allow_html=True)

    selectable_groups = st.session_state.groups 

    if selectable_groups:
        with col1:
            st.markdown('<div class="section">', unsafe_allow_html=True)
            st.subheader(f"2. Select Groups for Article ({len(selectable_groups)} Available)")
            
            group_names_for_selection = [g["Group Name"] for g in selectable_groups]
            
            # Ensure default selection is valid against current selectable_groups
            valid_default_selection = [name for name in st.session_state.selected_group_names if name in group_names_for_selection]
            if not valid_default_selection and group_names_for_selection: # If no valid default, but groups exist, select all by default
                 valid_default_selection = group_names_for_selection


            st.session_state.selected_group_names = st.multiselect(
                "Choose groups to include in the article:",
                options=group_names_for_selection,
                default=valid_default_selection, 
                help="Only active, named groups are shown here."
            )

            final_selected_groups_data = [
                g for g in selectable_groups if g["Group Name"] in st.session_state.selected_group_names
            ]
            
            st.caption(f"{len(final_selected_groups_data)} groups currently selected.")
            
            if final_selected_groups_data:
                if gemini_api_key and st.button("✨ Enrich Selected Groups with AI Descriptions", use_container_width=True):
                    with st.spinner("Generating AI descriptions for selected groups... This may take a moment."):
                        for group_data_selected in final_selected_groups_data: # Iterate over the selection
                            # Find the group in the main st.session_state.groups to update it
                            original_group_to_update = next((g for g in st.session_state.groups if g["Group Name"] == group_data_selected["Group Name"]), None)
                            if original_group_to_update:
                                st.info(f"Processing group: {original_group_to_update['Group Name']}")
                                # Only generate if description is empty (as per your validate_link) or very short
                                if not original_group_to_update.get("Description") or len(original_group_to_update.get("Description","")) < 10 :
                                    ai_desc = generate_short_description_with_ai(original_group_to_update["Group Name"], target_keyword, gemini_api_key)
                                    original_group_to_update["AI_Description"] = ai_desc # Store AI desc
                                    original_group_to_update["Description"] = ai_desc # Also update main description for display

                    st.success("AI descriptions processed for selected groups!")
                    # Re-derive final_selected_groups_data to reflect potential updates
                    final_selected_groups_data = [
                        g for g in st.session_state.groups if g["Group Name"] in st.session_state.selected_group_names
                    ]

            display_list = final_selected_groups_data if final_selected_groups_data else selectable_groups[:5] # Show top 5 if nothing selected
            if display_list:
                st.markdown(generate_display_html_table(display_list), unsafe_allow_html=True)
            elif selectable_groups and not final_selected_groups_data:
                 st.info("Select some groups from the dropdown above to include them in your article.")
            st.markdown('</div>', unsafe_allow_html=True)
    elif st.session_state.get('search_query'): 
        with col1:
            st.markdown('<div class="section">', unsafe_allow_html=True)
            st.info("No active, named WhatsApp groups found with the current search query and filters. Try a different query or adjust scraping settings.")
            st.markdown('</div>', unsafe_allow_html=True)

    current_final_selected_data = [
        g for g in st.session_state.groups if g["Group Name"] in st.session_state.get("selected_group_names", [])
    ]

    with col2:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.subheader("3. Generate AI Content")
        if not current_final_selected_data:
            st.warning("Please select at least one group to generate content.")
        elif not gemini_api_key:
            st.error("Please enter your Gemini API Key in the sidebar to generate content.")
        else:
            if st.button("🚀 Generate Full Article with AI", use_container_width=True, type="primary"):
                with st.spinner("🤖 Gemini is crafting your SEO-optimized article... Please wait."):
                    try:
                        groups_html_for_ai = generate_content_table_for_ai(current_final_selected_data)
                        
                        lsi_kws_str = ", ".join([kw.strip() for kw in lsi_keywords.split(',') if kw.strip()])
                        local_kws_str = ", ".join([kw.strip() for kw in local_keywords.split(',') if kw.strip()]) if local_keywords else "Not specified"

                        current_prompt = SYSTEM_PROMPT.format(
                            target_keyword=target_keyword,
                            lsi_keywords=lsi_kws_str,
                            local_keywords=local_kws_str,
                            lsi_keywords_comma_separated_for_tags = lsi_kws_str, 
                            local_keywords_comma_separated_for_tags = local_kws_str if local_keywords else ""
                        )
                        current_prompt = current_prompt.replace("{{{{GROUP_TABLE_PLACEHOLDER}}}}", groups_html_for_ai)
                        
                        genai.configure(api_key=gemini_api_key)
                        model = genai.GenerativeModel('gemini-2.0-flash') # Your requested model
                        
                        safety_settings=[
                            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        ]

                        response = model.generate_content(current_prompt, safety_settings=safety_settings)
                        
                        if not response.candidates:
                             st.error("Content generation was blocked by safety settings. The prompt or generated content may have violated safety policies. Please try adjusting your keywords or the prompt structure.")
                             st.session_state.content = "Error: Content generation blocked by safety filter."
                        else:
                            st.session_state.content = response.text
                            st.success("AI Article generated successfully!")

                    except Exception as e:
                        st.error(f"Error generating content with Gemini (gemini-2.0-flash): {str(e)}")
                        st.session_state.content = f"Error during content generation: {str(e)}"
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.content:
        st.markdown('<div class="section" style="margin-top: 20px;">', unsafe_allow_html=True)
        st.subheader("4. Review & Post to WordPress")
        
        cleaned_content = re.split(r"---\s*Post Metadata Suggestions.*", st.session_state.content, flags=re.IGNORECASE | re.DOTALL)[0]
        
        st.text_area("Generated Article Content:", cleaned_content, height=400)

        if wp_secrets_ok and st.button("✅ Post to WordPress as Draft", use_container_width=True):
            if not st.secrets["wordpress"]["username"] or \
               not st.secrets["wordpress"]["app_password"] or \
               not st.secrets["wordpress"]["site_url"]:
                 st.error("WordPress credentials are not fully set in secrets.")
            else:
                with st.spinner("🚀 Connecting to WordPress and posting..."):
                    try:
                        wp_auth = (st.secrets["wordpress"]["username"], st.secrets["wordpress"]["app_password"])
                        wp_site_url = st.secrets["wordpress"]["site_url"].rstrip('/')
                        
                        post_data = {
                            'title': post_title,
                            'content': cleaned_content,
                            'status': 'draft',
                            'slug': f"{target_keyword.lower().replace(' ', '-')}-whatsapp-groups" 
                                    if target_keyword else "new-whatsapp-group-post"
                        }
                        
                        post_url = f"{wp_site_url}/wp-json/wp/v2/posts"
                        response = requests.post(post_url, auth=wp_auth, json=post_data, timeout=30)

                        if response.status_code == 201: 
                            post_info = response.json()
                            post_link = post_info.get('link')
                            st.success("Article posted as a draft to WordPress! 🎉")
                            if post_link:
                                st.markdown(f"**[View Draft Post]({post_link})** (You might need to be logged into WordPress)")
                        else:
                            st.error(f"Failed to post to WordPress. Status: {response.status_code}")
                            try:
                                error_details = response.json()
                                st.json(error_details) 
                                if response.status_code == 401:
                                    st.warning("401 Unauthorized: Check WordPress user role (Editor/Admin) and Application Password permissions.")
                                elif response.status_code == 403:
                                     st.warning("403 Forbidden: Security plugin or firewall might be blocking, or user lacks specific permission.")
                            except ValueError: 
                                st.text(response.text[:500]) 
                    except requests.exceptions.RequestException as e:
                        st.error(f"Network error posting to WordPress: {str(e)}")
                    except Exception as e:
                        st.error(f"An unexpected error occurred during WordPress posting: {str(e)}")
                        import traceback
                        st.error(traceback.format_exc())
        st.markdown('</div>', unsafe_allow_html=True)
    elif current_final_selected_data and not st.session_state.content:
         with col2: # If groups are selected but no content generated yet
            st.info("Selected groups are ready. Click 'Generate Full Article with AI' to create the content.")


if __name__ == "__main__":
    main()
