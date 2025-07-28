import streamlit as st
import requests
import re # For parsing diff output

# --- Streamlit UI Setup ---
st.set_page_config(layout="wide", page_title="GitHub Repo Code Validator & Viewer")

st.title("Code-Validator-and-Deployer-Agent: GitHub Repo Viewer")
st.markdown("""
This app fetches and displays the commit history and **core code differences** (additions in green, deletions in red) for a given **public** GitHub repository.

**Note on Jupyter Notebooks (.ipynb):**
Due to their JSON structure, Git diffs for notebooks can be verbose. This app attempts to filter out some of the JSON noise to show only the relevant code changes. For a truly rich and accurate notebook diff, consider using tools like `nbdime` locally.
""")

# Input fields
project_name = st.text_input("Project Name (Optional)", "My ML Classification Project")
github_repo_url = st.text_input(
    "Enter GitHub Repo URL",
    "https://github.com/ria-pahujani77/Code-Validator-and-Deployer-Agent" # Replace with your actual public repo URL
)

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

def fetch_commits(owner, repo_name):
    """
    Fetches commit history for a given public repository.
    No token needed.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
    
    try:
        response = requests.get(api_url)
        response.raise_for_status() # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching commits: {e}. Check URL or GitHub API rate limits.")
        return None

def fetch_commit_diff(owner, repo_name, sha):
    """
    Fetches the diff for a specific commit SHA for a public repository.
    No token needed.
    """
    headers = {"Accept": "application/vnd.github.v3.diff"} # Request diff format

    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits/{sha}"
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.text # Diff comes as plain text
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching diff for commit {sha}: {e}. Check URL or GitHub API rate limits.")
        return None

def format_diff_for_streamlit(diff_text):
    """
    Formats raw Git diff text with Streamlit-compatible coloring,
    showing only added/deleted lines, with improved filtering for .ipynb JSON.
    """
    formatted_lines = []
    # Flag to indicate if we are inside a code block (after '@@')
    in_hunk = False 
    # Flag to indicate if the current file is a Jupyter Notebook
    is_ipynb = False

    for line in diff_text.splitlines():
        if line.startswith('diff --git'):
            # New file diff header
            formatted_lines.append(f"\n\033[1m{line}\033[0m") # Bold for file header
            in_hunk = False # Reset for new file
            is_ipynb = '.ipynb' in line # Check if it's a notebook
        elif line.startswith('--- a/') or line.startswith('+++ b/'):
            # Ignore these file path headers
            continue
        elif line.startswith('@@'):
            # This marks the start of a hunk (code block)
            in_hunk = True
            continue 
        elif in_hunk:
            # For .ipynb files, try to extract the actual code from the JSON string
            if is_ipynb:
                # Regex to extract content inside quotes, handling escaped quotes
                # This is a heuristic and might not catch all complex JSON scenarios
                match = re.match(r'^[+-]\s*"((?:[^"\\]|\\.)*)\\n",?$', line)
                if match:
                    # Decode escaped characters like \\n to actual newlines
                    content = match.group(1).replace('\\n', '\n').replace('\\"', '"')
                    # Apply color based on original line start
                    if line.startswith('+'):
                        formatted_lines.append(f"\033[92m+{content}\033[0m") # Green for additions
                    elif line.startswith('-'):
                        formatted_lines.append(f"\033[91m-{content}\033[0m") # Red for deletions
                # If it doesn't match the expected JSON line, or is just context, skip it
                continue # Always continue to avoid adding raw JSON lines
            else: # For non-ipynb files, use the previous logic
                if line.startswith('+'):
                    formatted_lines.append(f"\033[92m{line}\033[0m") # Green for additions
                elif line.startswith('-'):
                    formatted_lines.append(f"\033[91m{line}\033[0m") # Red for deletions
                # Context lines (starting with space) are still filtered out by default here
        else:
            # Lines before the first '@@' or other non-code diff lines
            continue

    if not formatted_lines:
        return "No significant code changes detected (only metadata or context lines filtered out)."
        
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

        commits = fetch_commits(owner, repo_name) 
        
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

                with st.expander(f"View Code Difference for Commit `{sha[:7]}`"):
                    diff_text = fetch_commit_diff(owner, repo_name, sha)
                    if diff_text:
                        st.code(format_diff_for_streamlit(diff_text), language='ansi') 
                    else:
                        st.warning("Could not retrieve diff for this commit. May be due to GitHub API rate limits.")
                st.markdown("---")
        else:
            st.warning("No commits found or unable to fetch commit history. Check URL or GitHub API rate limits.")

