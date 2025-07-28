import streamlit as st
import requests
import base64
import re # For parsing diff output

# --- Streamlit UI Setup ---
st.set_page_config(layout="wide", page_title="GitHub Repo Code Validator & Viewer")

st.title("Code-Validator-and-Deployer-Agent: GitHub Repo Viewer")
st.markdown("""
This app fetches and displays the commit history and code differences for a given GitHub repository.
""")

# Input fields
project_name = st.text_input("Project Name (Optional)", "My ML Classification Project")
github_repo_url = st.text_input(
    "Enter GitHub Repo URL",
    "https://github.com/ria-pahujani77/Code-Validator-and-Deployer-Agent"
)

# You can add a GitHub Personal Access Token (PAT) for higher rate limits or private repos
# For public repos and basic usage, it might not be strictly necessary, but good practice.
# st.info("For private repositories or higher API rate limits, consider setting a GitHub Personal Access Token as a Streamlit secret or environment variable.")
# github_token = st.secrets.get("GITHUB_TOKEN", "") # Example of getting from Streamlit secrets

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
        headers["Authorization"] = f"token {token}"
    
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status() # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching commits: {e}")
        return None

def fetch_commit_diff(owner, repo_name, sha, token=None):
    """Fetches the diff for a specific commit SHA."""
    headers = {"Accept": "application/vnd.github.v3.diff"}
    if token:
        headers["Authorization"] = f"token {token}"

    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits/{sha}"
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.text # Diff comes as plain text
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching diff for commit {sha}: {e}")
        return None

def format_diff_for_streamlit(diff_text):
    """
    Formats raw Git diff text with Streamlit-compatible coloring.
    Uses ANSI escape codes for red/green, which st.code can render.
    """
    formatted_lines = []
    for line in diff_text.splitlines():
        if line.startswith('+') and not line.startswith('+++'):
            formatted_lines.append(f"\033[92m{line}\033[0m") # Green
        elif line.startswith('-') and not line.startswith('---'):
            formatted_lines.append(f"\033[91m{line}\033[0m") # Red
        elif line.startswith('diff --git'): # Start of a new file diff
            formatted_lines.append(f"\n\033[1m{line}\033[0m") # Bold for file header
        else:
            formatted_lines.append(line)
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

        commits = fetch_commits(owner, repo_name) # Pass github_token if using
        
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
                    diff_text = fetch_commit_diff(owner, repo_name, sha) # Pass github_token if using
                    if diff_text:
                        # Streamlit's st.code supports ANSI escape codes for coloring
                        st.code(format_diff_for_streamlit(diff_text), language='diff')
                    else:
                        st.warning("Could not retrieve diff for this commit.")
                st.markdown("---")
        else:
            st.warning("No commits found or unable to fetch commit history.")

