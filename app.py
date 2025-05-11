import streamlit as st
import pandas as pd
import requests
import html
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai
from fake_useragent import UserAgent, FakeUserAgentError
import time

# Streamlit Configuration
st.set_page_config(page_title="WhatsApp Content Generator", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for Improved UI
st.markdown("""
<style>
body { font-family: 'Segoe UI', sans-serif; background-color: #f0f2f6; }
.main-title { font-size: 2.5em; color: #25D366; text-align: center; margin-bottom: 0; font-weight: 700; }
.subtitle { font-size: 1.2em; color: #555; text-align: center; margin-top: 5px; margin-bottom: 20px; }
.stButton>button { background-color: #25D366; color: white; border-radius: 8px; font-weight: bold; padding: 10px 20px; transition: all 0.3s ease; border: none; }
.stButton>button:hover { background-color: #1EBE5A; transform: scale(1.05); }
.stButton>button:focus { outline: 2px solid #1DA1F2; box-shadow: 0 0 0 3px rgba(29, 161, 242, 0.4); }
.stTextInput > div > div > input { border-radius: 6px; padding: 10px; border: 1px solid #ccc; }
.stTextInput > div > div > input:focus { border-color: #25D366; outline: 2px solid #1DA1F2; box-shadow: 0 0 0 3px rgba(37, 211, 102, 0.3); }
.stSlider > div { color: #25D366; }
.whatsapp-groups-table { width: 100%; border-collapse: collapse; margin: 20px 0; box-shadow: 0 4px 8px rgba(0,0,0,0.1); background: white; border-radius: 8px; overflow: hidden; }
.whatsapp-groups-table th { background-color: #343A40; color: white; padding: 12px; font-size: 0.9em; text-transform: uppercase; text-align: left; }
.whatsapp-groups-table td { padding: 10px; vertical-align: middle; font-size: 0.95em; text-align: left; }
.whatsapp-groups-table tr { height: 50px; border-bottom: 1px solid #eee; }
.whatsapp-groups-table tr:nth-child(even) { background-color: #f9fafb; }
.whatsapp-groups-table tr:hover { background-color: #e8f4f8; }
.group-logo-img { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 2px solid #eee; vertical-align: middle; }
.join-button { background-color: #25D366; color: white !important; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 0.85em; display: inline-block; }
.join-button:hover { background-color: #1DB954; }
.section { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
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
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


# Initialize Fake User Agent
try:
    ua = UserAgent()
except FakeUserAgentError: # More specific error
    st.warning("Failed to initialize fake-useragent due to network issues or outdated cache. Using default User-Agent.")
    ua = None
except Exception as e:
    st.warning(f"Failed to initialize fake-useragent: {e}. Using default User-Agent.")
    ua = None

def get_headers():
    user_agent_value = DEFAULT_USER_AGENT
    if ua:
        try:
            user_agent_value = ua.random
        except Exception as e:
            # In case ua.random fails for some reason even if ua object exists
            st.warning(f"Failed to get random User-Agent from fake_useragent: {e}. Using default.")
            pass # Stick to default
    return {
        "User-Agent": user_agent_value,
        "Accept-Language": "en-US,en;q=0.9"
    }

# System Prompt - Improved
SYSTEM_PROMPT = """
🔹 **Content Objective:**
Craft a 500+ word, highly engaging, SEO-optimized article. The primary goal is to promote active and verified WhatsApp group links for a specific niche. The article must read as if written by a human, be conversational, structured for readability, and designed to bypass AI detection tools while achieving strong search engine rankings.

🔍 **SEO & Keyword Integration:**
-   **Primary Keyword:** {target_keyword}
-   **LSI Keywords:** {lsi_keywords} (Integrate these naturally throughout the content, not just as a list)
-   **Local SEO Keywords (if applicable):** {local_keywords} (Weave these in if provided, focusing on geographic relevance)

🌟 **Meta Tags (Guideline):**
-   **Meta Title Suggestion:** Top {target_keyword} WhatsApp Groups | Active & Verified Links [Current Year]
-   **Meta Description Suggestion:** Discover the ultimate list of active {target_keyword} WhatsApp groups. Join verified links, updated for [Current Year]. Instant access, free to join, and community-focused!

✍️ **Core Writing Guidelines:**
-   **Tone & Voice:** Adopt a first-person perspective ("I," "we," "you"). Be friendly, approachable, and relatable. Imagine you're sharing valuable finds with a friend.
-   **Human-Like Flow & Rhythm:** Vary sentence length and structure significantly. Use contractions (e.g., "it's," "you're") and casual, everyday expressions.
-   **Keyword Usage:** Integrate keywords naturally and contextually. Avoid keyword stuffing at all costs. Focus on providing value to the reader.
-   **Originality & Depth:** Don't just state facts; provide insights, brief personal anecdotes (can be hypothetical like "I remember when I was searching for..."), or unique perspectives.
-   **Structure for Readability:** Use headings (H1, H2, H3), bullet points, and short paragraphs.

📅 **Suggested Article Structure & Headings (Adapt as needed for uniqueness):**

 H1: Your Main Article Title (incorporating {target_keyword} and [Current Year])

 H2: 👋 Introduction: Why You Need These {target_keyword} WhatsApp Groups
    - Hook the reader with a relatable problem or question.
    - Briefly introduce the value of the article (curated, verified groups).
    - Naturally include the primary keyword early on.
    Example: "Tired of searching for active {target_keyword} WhatsApp groups, only to find expired links? I've been there! That's why I've put together this handpicked list of the best groups for [Current Year]..."

 H2: 🚀 Top {target_keyword} WhatsApp Groups of [Current Year] (Verified & Active)
    - This is where the table of groups will be inserted.
    - Introduce the table briefly, emphasizing that these are checked and active.
    - The table format should be: Group Name | Short AI-Generated Description | Join Link

 H2: 🤔 What Exactly is {target_keyword}? A Quick, Friendly Explainer
    - Briefly explain the {target_keyword} niche for newcomers. Keep it simple and engaging.

 H2: ✨ Key Benefits of Joining Quality {target_keyword} WhatsApp Groups
    - Bullet points are great here:
        - Real-time updates and news.
        - Networking with peers and experts.
        - Access to shared resources or tips.
        - Quick answers and community support.

 H2: ✅ Tips for Joining and Making the Most of These Groups
    - Simple, actionable advice.
    - Example: "To get started, just click 'Join Group'. I recommend introducing yourself and checking any pinned messages for group rules."

 H2: 🚫 Common Pitfalls to Avoid in WhatsApp Groups
    - Briefly touch on etiquette and common mistakes:
        - Over-sharing or spamming.
        - Ignoring group rules or topic.
        - Not contributing to discussions.

 H2: 💡 Frequently Asked Questions (FAQs)
    - (H3 for each question)
    - How do I find more {target_keyword} groups? (A: Mention forums, other communities, but highlight your list's value)
    - Are these links regularly updated? (A: Yes, we strive to keep this list fresh.)
    - Is it free to join? (A: Generally yes, these are public invite links.)

 H2: 🏁 Conclusion: Your Next Step
    - Briefly summarize the article's value.
    - Include a call to action (e.g., "Bookmark this page for future updates!" or "Share this list with others who might find it useful!").

📝 **Writing Style Nuances for AI Detection Evasion:**
-   **Perplexity & Burstiness:** Mix complex sentences with shorter ones. Vary sentence beginnings. Avoid overly uniform sentence structures.
-   **Personal Touch:** Even if creating content broadly, infuse a sense of personal curation. Use phrases like "I've found that...", "In my experience...", "What I love about these communities is...".
-   **Avoid AI Clichés:** Steer clear of common AI phrases like "In conclusion," (use something more natural like "So, there you have it!"), "It's important to note," "Furthermore," etc. Be more direct and less formulaic.
-   **Natural Transitions:** Ensure smooth transitions between paragraphs and sections. Use transition words and phrases that feel organic.
-   **Show, Don't Just Tell:** Instead of saying "This group is very informative," you could say, "In the [Group Name] group, I often find members sharing insightful articles and tips on [topic]..." (if you have such info, otherwise generalize).

🌐 **Post Metadata (For Your Reference - Not for AI to write):**
-   Slug: /{target_keyword}-whatsapp-groups
-   (Categories and Tags will be handled manually in WordPress)

Remember to replace placeholders like `[Current Year]` with the actual current year.
The provided groups table will be inserted into the content. Ensure the article flows naturally around it.
"""

# --- Helper Functions ---

def validate_link(link):
    """Validates a WhatsApp group link and extracts metadata."""
    result = {"Group Name": "Unnamed Group", "Group Link": link, "Logo URL": "", "Status": "Error", "Description": ""}
    try:
        response = requests.get(link, headers=get_headers(), timeout=20, allow_redirects=True)
        response.raise_for_status() # Raise an exception for HTTP errors

        if WHATSAPP_DOMAIN in response.url:
            soup = BeautifulSoup(response.text, 'html.parser')
            title_tag = soup.find('meta', property='og:title')
            image_tag = soup.find('meta', property='og:image')

            group_name_raw = title_tag['content'] if title_tag and title_tag.get('content') else None
            if group_name_raw:
                group_name = html.unescape(str(group_name_raw)).strip()
                result["Group Name"] = group_name if group_name else "Unnamed Group"
            else:
                result["Group Name"] = "Unnamed Group"


            logo_url_raw = image_tag['content'] if image_tag and image_tag.get('content') else ""
            if logo_url_raw:
                result["Logo URL"] = html.unescape(str(logo_url_raw))
            
            result["Status"] = "Active"
            # Description will be AI-generated later, so initialize as empty
            result["Description"] = ""
        else:
            result["Status"] = "Expired or Invalid Link"
    except requests.exceptions.Timeout:
        result["Status"] = "Network Error: Timeout"
    except requests.exceptions.RequestException as e:
        result["Status"] = f"Network Error: {str(e)[:50]}"
    except Exception as e:
        result["Status"] = f"Parsing Error: {str(e)[:50]}"
    return result

def scrape_google(query, top_n, progress_bar, status_text):
    """Scrapes Google for WhatsApp links."""
    try:
        from googlesearch import search
    except ImportError:
        st.error("The 'googlesearch-python' library is not installed. Please install it by running: pip install googlesearch-python")
        return []

    status_text.text(f"Fetching Google search results for: '{query}'...")
    links = set()
    try:
        # Limit num_results to avoid issues, googlesearch can be unreliable with large numbers
        search_results = list(search(query, num_results=top_n, lang="en", sleep_interval=2))
    except Exception as e:
        st.error(f"Google search failed: {e}. Try reducing 'Google Results to Scrape' or check your connection.")
        return []
    
    if not search_results:
        status_text.warning("No search results returned from Google.")
        return []

    progress_bar.progress(0.1)

    with requests.Session() as session:
        for i, url in enumerate(search_results):
            status_text.text(f"Scraping page {i+1}/{len(search_results)}: {url[:70]}...")
            try:
                response = session.get(url, headers=get_headers(), timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    if href and WHATSAPP_DOMAIN in href:
                        parsed_url = urlparse(href)
                        # Normalize: ensure scheme, netloc, and path only
                        clean_link = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                        links.add(clean_link)
                progress_bar.progress(0.1 + (i + 1) / len(search_results) * 0.4)
            except requests.exceptions.RequestException as e:
                st.warning(f"Error scraping {url[:50]}: {type(e).__name__}. Skipping.")
            except Exception as e:
                st.warning(f"Unexpected error scraping {url[:50]}: {e}. Skipping.")
            time.sleep(0.5) # Be respectful to servers
    return list(links)

def generate_html_table_for_display(groups_list):
    """Generates an HTML table for displaying groups in Streamlit."""
    if not groups_list:
        return "<p style='text-align:center;color:#777;'>No active groups found or selected.</p>"

    html_output = '<table class="whatsapp-groups-table" aria-label="WhatsApp Groups">'
    html_output += '<thead><tr><th>Logo</th><th>Group Name</th><th>Description</th><th>Link</th></tr></thead><tbody>'
    for group in groups_list:
        group_name = html.escape(str(group.get("Group Name", "N/A")))
        logo_url = html.escape(str(group.get("Logo URL", "")))
        # Use AI-generated description if available, otherwise a placeholder
        desc = html.escape(str(group.get("Description", "Description pending...")))
        link = html.escape(str(group.get("Group Link", "#")))
        
        html_output += '<tr>'
        html_output += f'<td><img src="{logo_url}" class="group-logo-img" alt="{group_name} Logo" onerror="this.style.display=\'none\'"></td>'
        html_output += f'<td>{group_name}</td>'
        html_output += f'<td>{desc}</td>'
        html_output += f'<td><a href="{link}" class="join-button" target="_blank" rel="nofollow noopener noreferrer">Join</a></td>'
        html_output += '</tr>'
    html_output += '</tbody></table>'
    return html_output

def generate_html_table_for_ai(groups_list):
    """Generates a simple HTML table for the AI prompt."""
    if not groups_list:
        return "<p>No groups selected for the article.</p>"
    
    html_output = '<table border="1" style="border-collapse: collapse; width: 100%;">\n'
    html_output += '<tr><th style="padding: 5px; text-align: left;">Group Name</th><th style="padding: 5px; text-align: left;">Description</th><th style="padding: 5px; text-align: left;">Link</th></tr>\n'
    for group in groups_list:
        group_name = html.escape(str(group.get("Group Name", "N/A")))
        # Ensure description is present for AI; use a generic one if somehow still missing
        desc = html.escape(str(group.get("Description") or f"A community for {group_name}."))
        link = html.escape(str(group.get("Group Link", "#")))
        html_output += f'<tr><td style="padding: 5px;">{group_name}</td><td style="padding: 5px;">{desc}</td><td style="padding: 5px;"><a href="{link}" target="_blank" rel="nofollow noopener noreferrer">Join Group</a></td></tr>\n'
    html_output += '</table>'
    return html_output

def get_ai_description_for_group(group_name, api_key, genai_model):
    """Generates a short description for a WhatsApp group using Gemini."""
    if not group_name or group_name == "Unnamed Group":
        return "A general community group."
    try:
        prompt = f"Write a concise, engaging WhatsApp group description (strictly 30-60 characters) for a group named '{group_name}'. Focus on its main topic or benefit. Output only the description text, nothing else."
        response = genai_model.generate_content(prompt)
        # Clean up the response, ensure it's within length, handle potential API errors
        desc_text = response.text.strip().replace("\n", " ")
        if len(desc_text) > 70: # Allow a bit of leeway over 60
            desc_text = desc_text[:67] + "..."
        return desc_text if desc_text else f"Explore the {group_name} community."
    except Exception as e:
        st.warning(f"AI description generation failed for '{group_name}': {e}")
        return f"A community for {group_name} fans." # Fallback

# --- Main App ---
def main():
    st.markdown('<h1 class="main-title">WhatsApp Content Generator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Search, Scrape, Generate AI Content, and Post to WordPress</p>', unsafe_allow_html=True)

    # Initialize Session State
    if 'all_scraped_groups' not in st.session_state: # All valid groups after scraping
        st.session_state.all_scraped_groups = []
    if 'selected_group_names' not in st.session_state: # Names of groups selected by user
        st.session_state.selected_group_names = []
    if 'generated_article_content' not in st.session_state:
        st.session_state.generated_article_content = None
    if 'gemini_model' not in st.session_state:
        st.session_state.gemini_model = None


    # Sidebar for Inputs
    with st.sidebar:
        st.header("⚙️ Configuration")
        gemini_api_key = st.text_input("Gemini API Key", type="password", help="Enter your Gemini API key from Google AI Studio.")
        
        st.header("🔍 Search Settings")
        search_query = st.text_input("Google Search Query", "active study WhatsApp group links", help="e.g., 'best crypto news whatsapp groups'")
        top_n = st.slider("Google Results to Scrape", 1, 15, 5, help="Number of Google search results to analyze. Higher numbers take longer and risk rate limits.")

        st.header("📝 Content Settings")
        target_keyword = st.text_input("Target Keyword", "Study Groups", help="Primary keyword for SEO content.")
        lsi_keywords = st.text_input("LSI Keywords (comma-separated)", "student community, exam preparation, online learning", help="Related keywords.")
        local_keywords = st.text_input("Local SEO Keywords (optional)", "", help="e.g., 'New York study groups'")
        post_title_template = st.text_input("Post Title Template", "Top {target_keyword} WhatsApp Groups [Current Year]", help="Use placeholders like {target_keyword} and [Current Year].")

        if st.button("Clear All Data & Selections", use_container_width=True, type="secondary"):
            st.session_state.all_scraped_groups = []
            st.session_state.selected_group_names = []
            st.session_state.generated_article_content = None
            st.session_state.gemini_model = None
            st.success("All data cleared!")
            # No rerun needed here if UI elements below depend on these states correctly

    # Configure Gemini Model once API key is available
    if gemini_api_key and not st.session_state.gemini_model:
        try:
            genai.configure(api_key=gemini_api_key)
            # Note: 'gemini-2.0-flash' might be an internal or future name.
            # 'gemini-1.5-flash-latest' is a common, efficient model.
            # Using the one from your original code. Change if it causes errors.
            st.session_state.gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest') # Changed to 1.5 flash, more common
            st.sidebar.success("Gemini API configured.")
        except Exception as e:
            st.sidebar.error(f"Gemini configuration failed: {e}")
            st.session_state.gemini_model = None


    # WordPress Secrets Check (Moved up for early feedback)
    wp_configured = False
    try:
        if "wordpress" in st.secrets and all(
            key in st.secrets["wordpress"] for key in ["username", "app_password", "site_url"]
        ):
            wp_configured = True
        else:
            st.warning(
                "WordPress credentials incomplete in Streamlit Secrets. Please configure them to enable posting. "
                "Required: `wordpress.username`, `wordpress.app_password`, `wordpress.site_url`."
            )
    except Exception: # Catches FileNotFoundError if secrets file doesn't exist locally
        st.info("Running locally or WordPress secrets not found. Posting to WordPress will be disabled.")


    # --- Section 1: Search & Scrape ---
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.subheader("1. Search & Scrape WhatsApp Groups")
    if st.button("Start Search & Scrape", use_container_width=True, disabled=not search_query):
        if not search_query: # Should be disabled, but as a safeguard
            st.error("Please enter a search query.")
        else:
            st.session_state.all_scraped_groups = [] # Clear previous results
            st.session_state.selected_group_names = [] # Clear selections
            st.session_state.generated_article_content = None # Clear old content

            progress_bar = st.progress(0, text="Initializing scrape...")
            status_text = st.empty()
            
            scraped_links = scrape_google(search_query, top_n, progress_bar, status_text)
            
            valid_groups_found = []
            if scraped_links:
                status_text.text(f"Validating {len(scraped_links)} unique links found...")
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    future_to_link = {executor.submit(validate_link, link): link for link in scraped_links}
                    for i, future in enumerate(as_completed(future_to_link)):
                        try:
                            result = future.result()
                            # Filter out unnamed or error groups here
                            if result["Status"] == "Active" and result["Group Name"] != "Unnamed Group":
                                valid_groups_found.append(result)
                        except Exception as exc:
                            status_text.warning(f"Error processing link validation: {exc}")
                        progress_bar.progress(0.5 + (i + 1) / len(scraped_links) * 0.5, 
                                              text=f"Validating link {i+1}/{len(scraped_links)}")
                
                st.session_state.all_scraped_groups = valid_groups_found
                status_text.success(f"Scraping complete! Found {len(valid_groups_found)} active and named groups.")
            else:
                status_text.error("No WhatsApp group links found from Google search.")
            progress_bar.empty() # Remove progress bar after completion
    st.markdown('</div>', unsafe_allow_html=True)


    # --- Section 2: Select Groups & Generate Descriptions ---
    if st.session_state.all_scraped_groups:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.subheader("2. Review & Select Groups for Article")

        # Ensure selected_group_names are valid if all_scraped_groups changes
        current_group_names_available = [g["Group Name"] for g in st.session_state.all_scraped_groups]
        st.session_state.selected_group_names = [
            name for name in st.session_state.selected_group_names if name in current_group_names_available
        ]
        if not st.session_state.selected_group_names and current_group_names_available: # If empty, default to all
             st.session_state.selected_group_names = current_group_names_available


        selected_names_from_ui = st.multiselect(
            "Select groups to include in the article:",
            options=current_group_names_available,
            default=st.session_state.selected_group_names,
            help="Choose which scraped groups will be featured."
        )
        st.session_state.selected_group_names = selected_names_from_ui

        # Create a list of full group dicts for selected groups
        selected_group_dicts = [
            g for g in st.session_state.all_scraped_groups if g["Group Name"] in st.session_state.selected_group_names
        ]

        if selected_group_dicts:
            if st.button("🤖 Generate AI Descriptions for Selected Groups", use_container_width=True, disabled=not st.session_state.gemini_model):
                if not st.session_state.gemini_model:
                    st.error("Gemini API key not configured. Please set it in the sidebar.")
                else:
                    desc_progress = st.progress(0, text="Generating AI descriptions...")
                    with st.spinner("AI is crafting short descriptions for selected groups..."):
                        for i, group_dict in enumerate(selected_group_dicts):
                            # Only generate if description is missing or is the default empty string
                            if not group_dict.get("Description", "").strip():
                                ai_desc = get_ai_description_for_group(group_dict["Group Name"], gemini_api_key, st.session_state.gemini_model)
                                group_dict["Description"] = ai_desc
                                # Update in the master list (all_scraped_groups) as well
                                for master_g in st.session_state.all_scraped_groups:
                                    if master_g["Group Name"] == group_dict["Group Name"]:
                                        master_g["Description"] = ai_desc
                                        break
                            desc_progress.progress((i + 1) / len(selected_group_dicts), text=f"Describing: {group_dict['Group Name'][:30]}...")
                    desc_progress.empty()
                    st.success("AI descriptions generated for selected groups!")
                    # Force a rerun to update the table display with new descriptions
                    st.rerun()

        # Display the table of all (potentially updated) selected groups
        st.markdown(generate_html_table_for_display(selected_group_dicts), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


        # --- Section 3: Generate Article Content ---
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.subheader("3. Generate SEO Article")
        if st.button("📝 Generate Full Article Content", use_container_width=True, disabled=not selected_group_dicts or not st.session_state.gemini_model):
            if not st.session_state.gemini_model:
                st.error("Gemini API key not configured.")
            elif not selected_group_dicts:
                st.error("No groups selected to include in the article.")
            else:
                # Check if all selected groups have descriptions
                missing_descriptions = [g["Group Name"] for g in selected_group_dicts if not g.get("Description", "").strip()]
                if missing_descriptions:
                    st.warning(f"Some selected groups are missing descriptions: {', '.join(missing_descriptions)}. Please generate descriptions first or they will use fallbacks.")

                with st.spinner("Gemini AI is crafting your SEO-optimized article... This may take a moment."):
                    try:
                        # Prepare the groups table HTML for the AI prompt
                        groups_html_for_ai = generate_html_table_for_ai(selected_group_dicts)
                        
                        current_year = time.strftime("%Y")
                        final_post_title = post_title_template.replace("{target_keyword}", target_keyword).replace("[Current Year]", current_year)

                        prompt_payload = SYSTEM_PROMPT.format(
                            target_keyword=target_keyword,
                            lsi_keywords=lsi_keywords,
                            local_keywords=local_keywords if local_keywords else "Not specified",
                        )
                        # Add table and title information to prompt for AI
                        prompt_payload += f"\n\n**Article Title to Generate:** {final_post_title}\n"
                        prompt_payload += f"\n**Use the following table of WhatsApp groups in the 'Top {target_keyword} WhatsApp Groups of {current_year}' section:**\n{groups_html_for_ai}\n"
                        prompt_payload += f"\nRemember to replace `[Current Year]` in the content with `{current_year}`."

                        response = st.session_state.gemini_model.generate_content(prompt_payload)
                        st.session_state.generated_article_content = response.text
                        st.success("Article content generated successfully!")
                    except Exception as e:
                        st.error(f"Error generating content with Gemini: {e}")
                        st.session_state.generated_article_content = None
        st.markdown('</div>', unsafe_allow_html=True)


    # --- Section 4: Review & Post to WordPress ---
    if st.session_state.generated_article_content:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.subheader("4. Review & Post to WordPress")
        
        current_year = time.strftime("%Y")
        final_post_title_for_wp = post_title_template.replace("{target_keyword}", target_keyword).replace("[Current Year]", current_year)
        st.text_area("Generated Article Content:", st.session_state.generated_article_content, height=400, key="article_review_area")
        
        if st.button("🚀 Post to WordPress as Draft", use_container_width=True, disabled=not wp_configured):
            if not wp_configured:
                st.error("WordPress is not configured. Please check Streamlit secrets.")
            else:
                with st.spinner("Posting to WordPress as a draft..."):
                    try:
                        wp_user = st.secrets["wordpress"]["username"]
                        wp_pass = st.secrets["wordpress"]["app_password"]
                        wp_url = st.secrets["wordpress"]["site_url"]
                        
                        auth = (wp_user, wp_pass)
                        
                        # Removed categories and tags as requested
                        post_data = {
                            'title': final_post_title_for_wp,
                            'content': st.session_state.generated_article_content, # Use content from state
                            'status': 'draft',
                            'slug': f"{target_keyword.lower().replace(' ', '-')}-whatsapp-groups-{current_year.lower()}" # Added year to slug for uniqueness
                        }
                        
                        api_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts"
                        
                        response = requests.post(api_url, auth=auth, json=post_data, timeout=30)
                        
                        if response.status_code == 201: # Created
                            post_link = response.json().get('link', '#')
                            st.success(f"Article posted as a draft to WordPress! Edit here: {post_link}")
                        else:
                            try:
                                error_details = response.json()
                                code = error_details.get("code", "N/A")
                                message = error_details.get("message", "No message.")
                                st.error(f"Failed to post to WordPress: {response.status_code} - {code}. Message: {message}")
                                st.json(error_details) # Show full error for debugging
                            except requests.exceptions.JSONDecodeError:
                                st.error(f"Failed to post to WordPress: {response.status_code} - {response.text[:200]}")
                    except KeyError as e:
                        st.error(f"WordPress secret key error: '{e}' not found. Please check your secrets.toml.")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Network error posting to WordPress: {e}")
                    except Exception as e:
                        st.error(f"An unexpected error occurred while posting to WordPress: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    # This check for `html` module being a string is a diagnostic.
    # If the AttributeError persists, this might give a clue.
    # Normally, this should not trigger if imports are correct and no reassignment happens.
    if isinstance(html, str):
        st.error("CRITICAL ERROR: The 'html' module has been overwritten by a string variable. This will cause `html.escape` to fail. Check your code for `html = ...` assignments.")
    else:
        main()
