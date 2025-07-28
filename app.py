import streamlit as st
import requests
import re # For parsing diff output

# --- Streamlit UI Setup ---
st.set_page_config(layout="wide", page_title="GitHub Repo Code Validator & Viewer")

st.title("Code-Validator-and-Deployer-Agent")
# st.markdown("""
# This app fetches and displays the commit history and **core code differences** (additions in green, deletions in red) for a given GitHub repository.
# The code differences are now shown directly for each commit, without needing to expand.
# It uses a GitHub Personal Access Token (PAT) for higher API rate limits, securely loaded via `st.secrets`.

# **Note on Jupyter Notebooks (.ipynb):**
# Due to their JSON structure, Git diffs for notebooks can be verbose. This app attempts to filter out some of the JSON noise to show only the relevant code changes, and now ensures colors are applied to all detected additions/deletions. For a truly rich and accurate notebook diff, consider using tools like `nbdime` locally.
# """)

# Input fields
github_repo_url = st.text_input(
    "Enter GitHub Repo URL",
    "" # Empty input field for user to type/paste
)

# --- Access GitHub Token from Streamlit secrets ---
# This is the correct and secure way to load your PAT.
# Ensure you have a .streamlit/secrets.toml file with GITHUB_TOKEN = "your_pat_here"
github_token = st.secrets.get("GITHUB_TOKEN")

if not github_token:
    st.error("GitHub Token not found in Streamlit secrets. "
             "API rate limits will be very low, and access to private repositories will fail. "
             "Please add `GITHUB_TOKEN = \"your_pat_here\"` to your `.streamlit/secrets.toml` file.")
    st.stop() # Stop the app if no token is provided, as it won't function reliably


submit_button = st.button("Fetch Repo Details")

# --- Function to fetch GitHub data ---

def get_repo_info(url):
    """
    Parses GitHub URL to extract owner and repo name.
    Returns (owner, repo_name) or None if invalid URL.
    """
    match = re.match(r"https://github.com/([^/]+)/([^/]+)(?:\.git)?", url)
    if match:
        owner, repo_name_candidate = match.groups()
        # Explicitly strip .git suffix if present in the candidate name
        if repo_name_candidate.endswith('.git'):
            repo_name = repo_name_candidate[:-4]
        else:
            repo_name = repo_name_candidate
        return owner, repo_name
    return None

def fetch_commits(owner, repo_name, token):
    """Fetches commit history for a given repository using a token."""
    headers = {"Authorization": f"token {token}"}
    
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status() # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching commits: {e}. Check URL or GitHub Token permissions.")
        return None

def fetch_commit_diff(owner, repo_name, sha, token):
    """Fetches the diff for a specific commit SHA using a token."""
    headers = {
        "Accept": "application/vnd.github.v3.diff", # Request diff format
        "Authorization": f"token {token}"
    }

    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits/{sha}"
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.text # Diff comes as plain text
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching diff for commit {sha}: {e}. Check GitHub Token permissions.")
        return None

def format_diff_for_streamlit(diff_text):
    """
    Formats raw Git diff text with HTML-based coloring (red for deletions, green for additions),
    showing only added/deleted lines, with improved filtering for .ipynb JSON.
    """
    formatted_lines = []
    in_hunk = False 
    is_ipynb = False

    for line in diff_text.splitlines():
        if line.startswith('diff --git'):
            # New file diff header - use monospace for consistency with code
            formatted_lines.append(f"<pre style='color: white; background-color: #333; padding: 5px; border-radius: 5px; font-weight: bold;'>{line}</pre>")
            in_hunk = False 
            is_ipynb = '.ipynb' in line 
        elif line.startswith('--- a/') or line.startswith('+++ b/'):
            continue
        elif line.startswith('@@'):
            in_hunk = True
            continue 
        elif in_hunk:
            # Check if the line is an addition or deletion
            if line.startswith('+'):
                html_color = "#008000" # Darker Green
                # For ipynb, try to extract content from JSON string
                if is_ipynb:
                    match = re.match(r'^\+\s*"((?:[^"\\]|\\.)*)\\n",?$', line)
                    if match:
                        content = match.group(1).replace('\\n', '\n').replace('\\"', '"')
                        formatted_lines.append(f"<span style='color:{html_color};'>+{content}</span>")
                    else:
                        formatted_lines.append(f"<span style='color:{html_color};'>{line}</span>")
                else:
                    formatted_lines.append(f"<span style='color:{html_color};'>{line}</span>")
            elif line.startswith('-'):
                html_color = "#FF0000" # Red
                # For ipynb, try to extract content from JSON string
                if is_ipynb:
                    match = re.match(r'^\-\s*"((?:[^"\\]|\\.)*)\\n",?$', line)
                    if match:
                        content = match.group(1).replace('\\n', '\n').replace('\\"', '"')
                        formatted_lines.append(f"<span style='color:{html_color};'>-{content}</span>")
                    else:
                        formatted_lines.append(f"<span style='color:{html_color};'>{line}</span>")
                else:
                    formatted_lines.append(f"<span style='color:{html_color};'>{line}</span>")
            # Context lines (starting with space) are still filtered out
        else:
            # Lines before the first '@@' or other non-code diff lines are skipped
            continue

    if not formatted_lines:
        return "No significant code changes detected (only metadata or context lines filtered out)."
        
    # Join lines and wrap in a <pre> tag for monospace font and consistent spacing
    # Use a dark background for the entire diff block for better contrast
    return f"<pre style='background-color: #262626; padding: 10px; border-radius: 8px; overflow-x: auto;'>{'<br>'.join(formatted_lines)}</pre>"


# --- Main Logic ---
if submit_button:
    # Ensure the URL is provided before proceeding
    if not github_repo_url:
        st.warning("Please enter a GitHub repository URL.")
        st.stop()

    repo_info = get_repo_info(github_repo_url)

    if not repo_info:
        st.error("Invalid GitHub repository URL. Please enter a URL like `https://github.com/owner/repo_name`.")
    else:
        owner, repo_name = repo_info
        st.subheader(f"Repository: {owner}/{repo_name}")
        # st.write(f"Project Name: {project_name}") # Project name is commented out in your provided code

        st.markdown("---")
        st.subheader("Commit History")

        commits = fetch_commits(owner, repo_name, github_token) 
        
        if commits:
            for commit in commits:
                sha = commit['sha']
                author = commit['commit']['author']['name']
                date = commit['commit']['author']['date']
                message = commit['commit']['message']

                st.markdown(f"**Commit:** `{sha[:7]}`")
                st.markdown(f"**Author:** {author}")
                st.markdown(f"**Date:** {date}")
                st.markdown(f"**Message:** {message}")
                
                # --- Display Code Difference Directly (No Expander) ---
                st.markdown(f"**Code Difference for Commit `{sha[:7]}`:**")
                diff_text = fetch_commit_diff(owner, repo_name, sha, github_token)
                if diff_text:
                    # Use st.markdown with unsafe_allow_html=True for HTML rendering
                    st.markdown(format_diff_for_streamlit(diff_text), unsafe_allow_html=True) 
                else:
                    st.warning("Could not retrieve diff for this commit. Check token permissions or API rate limits.")
                st.markdown("---") # Separator between commits
        else:
            st.warning("No commits found or unable to fetch commit history. Check URL or GitHub API rate limits.")

