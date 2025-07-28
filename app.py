import streamlit as st
import requests
import re # For parsing diff output

# --- Streamlit UI Setup ---
st.set_page_config(layout="wide", page_title="GitHub Repo Code Validator & Viewer")

st.title("Code-Validator-and-Deployer-Agent: GitHub Repo Viewer")
st.markdown("""
This app fetches and displays the commit history and **only the core code differences** (additions in green, deletions in red) for a given GitHub repository.
It supports **private repositories** using a GitHub Personal Access Token (PAT).
""")

# Input fields
project_name = st.text_input("Project Name (Optional)", "My ML Classification Project")
github_repo_url = st.text_input(
    "Enter GitHub Repo URL",
    "https://github.com/ria-pahujani77/Code-Validator-and-Deployer-Agent" # Replace with your actual repo URL
)

# Access GitHub Token from Streamlit secrets
# Ensure you have a .streamlit/secrets.toml file with GITHUB_TOKEN = "your_pat_here"
github_token = st.secrets.get("GITHUB_TOKEN")

if not github_token:
    st.warning("GitHub Token not found in Streamlit secrets. "
               "Access to private repositories will fail. "
               "Please add GITHUB_TOKEN to your `.streamlit/secrets.toml` file.")

submit_button = st.button("Fetch Repo Details")

# --- Function to fetch GitHub data ---

def get_repo_info(url):
    """
    Parses GitHub URL to extract owner and repo name.
    Returns (owner, repo_name) or None if invalid URL.
    """
    match = re.match(r"https://github.com/([^/]+)/([^/]+)(?:\.git)?", url)
    if match:
        return match.groups()
    return None

def fetch_commits(owner, repo_name, token=None):
    """Fetches commit history for a given repository."""
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}" # Use 'token' for PAT
    
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status() # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching commits: {e}. Check URL and GitHub Token/permissions.")
        return None

def fetch_commit_diff(owner, repo_name, sha, token=None):
    """Fetches the diff for a specific commit SHA."""
    headers = {"Accept": "application/vnd.github.v3.diff"} # Request diff format
    if token:
        headers["Authorization"] = f"token {token}"

    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits/{sha}"
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.text # Diff comes as plain text
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching diff for commit {sha}: {e}. Check GitHub Token/permissions.")
        return None

def format_diff_for_streamlit(diff_text):
    """
    Formats raw Git diff text with Streamlit-compatible coloring,
    showing only added/deleted lines.
    """
    formatted_lines = []
    # Use a flag to indicate if we are inside a code block (after '@@')
    in_code_block = False 

    for line in diff_text.splitlines():
        if line.startswith('diff --git'):
            # This is a new file diff header, include it as a separator
            formatted_lines.append(f"\n\033[1m{line}\033[0m") # Bold for file header
            in_code_block = False # Reset for new file
        elif line.startswith('--- a/') or line.startswith('+++ b/'):
            # Ignore these file path headers
            continue
        elif line.startswith('@@'):
            # This marks the start of a hunk (code block)
            in_code_block = True
            # Optionally, you can include the @@ line for context, or skip it
            # formatted_lines.append(f"\033[36m{line}\033[0m") # Cyan for @@ lines
            continue # Skip the @@ line itself for a cleaner output
        elif in_code_block:
            if line.startswith('+'):
                formatted_lines.append(f"\033[92m{line}\033[0m") # Green for additions
            elif line.startswith('-'):
                formatted_lines.append(f"\033[91m{line}\033[0m") # Red for deletions
            # else: # This is a context line, we are explicitly excluding these
            #     formatted_lines.append(line) 
        else:
            # Lines before the first '@@' or other non-code diff lines
            continue

    if not formatted_lines:
        return "No significant code changes (only metadata or context lines)."
        
    return "\n".join(formatted_lines)

# --- Main Logic ---
if submit_button:
    repo_info = get_repo_info(github_repo_url)

    if not repo_info:
        st.error("Invalid GitHub repository URL. Please enter a URL like `https://github.com/owner/repo_name`.")
    else:
        owner, repo_name = repo_info
        st.subheader(f"Repository: {owner}/{repo_name}")
        st.write(f"Project Name: {project_name}")

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

                # Fetch and display diff for each commit
                with st.expander(f"View Code Difference for Commit `{sha[:7]}`"):
                    diff_text = fetch_commit_diff(owner, repo_name, sha, github_token)
                    if diff_text:
                        # Use 'ansi' language for st.code to render colors
                        st.code(format_diff_for_streamlit(diff_text), language='ansi') 
                    else:
                        st.warning("Could not retrieve diff for this commit. Check token permissions or rate limits.")
                st.markdown("---")
        else:
            st.warning("No commits found or unable to fetch commit history. Check URL and token permissions.")

