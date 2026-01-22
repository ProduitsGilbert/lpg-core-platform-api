#!/usr/bin/env python3
"""
AI Code Review Script for GitHub Actions
"""

import os
import sys
import json
import requests
from typing import List, Dict, Any
import openai

def get_pr_files(repo: str, pr_number: int, github_token: str) -> List[Dict[str, Any]]:
    """Get list of files changed in the PR"""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    url = f'https://api.github.com/repos/{repo}/pulls/{pr_number}/files'
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error fetching PR files: {response.status_code}")
        return []

    return response.json()

def get_file_content(repo: str, file_path: str, github_token: str) -> str:
    """Get content of a specific file"""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    url = f'https://api.github.com/repos/{repo}/contents/{file_path}'
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return f"Error fetching file content: {response.status_code}"

    content = response.json()
    if 'content' in content:
        import base64
        return base64.b64decode(content['content']).decode('utf-8')
    return ""

def analyze_code_with_ai(file_path: str, content: str) -> str:
    """Analyze code using OpenAI"""
    openai.api_key = os.getenv('OPENAI_API_KEY')

    if not openai.api_key:
        return "❌ OpenAI API key not configured"

    prompt = f"""
    Please review the following code file and provide constructive feedback:

    File: {file_path}

    Code:
    ```python
    {content}
    ```

    Please provide:
    1. Code quality assessment
    2. Potential bugs or issues
    3. Security concerns
    4. Performance suggestions
    5. Best practices recommendations

    Focus on Python best practices, error handling, and maintainability.
    Be concise but thorough.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert Python code reviewer. Provide constructive, actionable feedback."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.3
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Error calling OpenAI API: {str(e)}"

def post_review_comment(repo: str, pr_number: int, comment: str, github_token: str):
    """Post review comment on the PR"""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    url = f'https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews'

    data = {
        'body': comment,
        'event': 'COMMENT'
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code not in [200, 201]:
        print(f"Error posting review: {response.status_code} - {response.text}")
    else:
        print("✅ Review posted successfully")

def main():
    # Get environment variables
    openai_key = os.getenv('OPENAI_API_KEY')
    github_token = os.getenv('GITHUB_TOKEN')
    pr_number = os.getenv('PR_NUMBER')
    repo_name = os.getenv('REPO_NAME')

    if not all([openai_key, github_token, pr_number, repo_name]):
        print("❌ Missing required environment variables")
        sys.exit(1)

    try:
        pr_number = int(pr_number)
    except ValueError:
        print("❌ Invalid PR number")
        sys.exit(1)

    print(f"🤖 Starting AI code review for PR #{pr_number} in {repo_name}")

    # Get changed files
    files = get_pr_files(repo_name, pr_number, github_token)

    if not files:
        print("❌ No files found in PR")
        sys.exit(1)

    # Filter for Python files
    python_files = [f for f in files if f['filename'].endswith('.py')]

    if not python_files:
        print("ℹ️ No Python files changed in this PR")
        sys.exit(0)

    print(f"📁 Found {len(python_files)} Python files to review")

    # Analyze each file
    review_comments = []

    for file_info in python_files[:5]:  # Limit to 5 files to avoid API limits
        file_path = file_info['filename']
        print(f"🔍 Analyzing {file_path}...")

        content = get_file_content(repo_name, file_path, github_token)

        if content.startswith("Error"):
            review_comments.append(f"## {file_path}\n\n{content}")
            continue

        analysis = analyze_code_with_ai(file_path, content)
        review_comments.append(f"## {file_path}\n\n{analysis}")

    # Compile final review
    final_comment = "# 🤖 AI Code Review\n\n"
    final_comment += "This is an automated code review using AI. Please consider the suggestions below:\n\n"
    final_comment += "\n\n---\n\n".join(review_comments)

    # Post the review
    post_review_comment(repo_name, pr_number, final_comment, github_token)

    print("✅ AI code review completed!")

if __name__ == "__main__":
    main()



