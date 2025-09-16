# OpenAI Code Review Setup Guide

## Overview
This repository uses OpenAI GPT-4 for automated code reviews on pull requests. The AI reviewer will analyze code changes and provide suggestions for improvements, potential bugs, and best practices.

## Setup Instructions

### 1. Required GitHub Secrets

You need to configure the following secrets in your GitHub repository settings:

#### A. OPENAI_API_KEY
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign in or create an account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (you won't be able to see it again)

#### B. GITHUB_TOKEN (Optional)
The default `GITHUB_TOKEN` provided by GitHub Actions should work. However, if you need more permissions, you can create a personal access token:
1. Go to GitHub Settings > Developer settings > Personal access tokens
2. Click "Generate new token (classic)"
3. Give it a descriptive name like "Code Review Bot"
4. Select the following scopes:
   - `repo` (full control of private repositories)
   - `write:discussion` (optional, for PR comments)
5. Generate and copy the token

### 2. Adding Secrets to Repository

1. Go to your repository: https://github.com/ProduitsGilbert/lpg-core-platform-api
2. Navigate to Settings > Secrets and variables > Actions
3. Click "New repository secret"
4. Add the required secret:
   - Name: `OPENAI_API_KEY`
   - Value: [Your OpenAI API key]
   
   Note: The `GITHUB_TOKEN` is automatically provided by GitHub Actions

### 3. Workflow Files

Two workflow files have been created:

#### Basic Workflow (`openai-code-review.yml`)
- Simple implementation using the OpenAI Code Review Action
- Triggers on pull request open/sync
- Reviews all code changes

#### Enhanced Workflow (`ai-code-review.yml`)
- Advanced configuration with Python-specific settings
- Filters to only review Python files
- Excludes common non-code files
- Adds summary comments to PRs
- More granular path filtering

### 4. Usage

Once configured, the code review will automatically run when:
- A new pull request is opened
- An existing pull request is updated with new commits
- A pull request is reopened

The AI will:
- Analyze the code diff
- Add inline comments with suggestions
- Provide feedback on:
  - Code quality
  - Potential bugs
  - Performance improvements
  - Security issues
  - Best practices

### 5. Customization

You can customize the review behavior by editing the workflow files:

#### Change AI Model
```yaml
OPENAI_API_MODEL: "gpt-4o"  # or "gpt-4o-turbo", "gpt-4o-mini"
```

#### Exclude Additional Files
```yaml
exclude: |
  **/*.json
  **/*.md
  **/tests/**  # Add more patterns here
```

#### Modify Trigger Events
```yaml
on:
  pull_request:
    types:
      - opened
      - synchronize
      - ready_for_review  # Add more events
```

### 6. Cost Considerations

- OpenAI API usage is billed based on tokens processed
- Each PR review consumes tokens based on:
  - Size of the code diff
  - Number of files changed
  - Complexity of analysis
- Monitor your OpenAI usage dashboard regularly
- Consider setting spending limits in OpenAI dashboard

### 7. Troubleshooting

#### Code review not running:
- Check Actions tab for workflow runs
- Verify secrets are properly configured
- Check workflow syntax is valid

#### No comments appearing:
- Ensure OCTOKIT_TOKEN has proper permissions
- Check OpenAI API key is valid and has credits
- Review Actions logs for errors

#### Too many/few comments:
- Adjust excluded file patterns
- Consider using path filters to limit scope

### 8. Best Practices

1. **Review AI Feedback Critically**: AI suggestions are not always correct
2. **Combine with Human Review**: Use as a supplement, not replacement
3. **Monitor Costs**: Track OpenAI API usage regularly
4. **Update Excludes**: Add patterns for generated/vendored code
5. **Test on Small PRs First**: Validate setup with minor changes

## Support

For issues with:
- GitHub Actions: Check [GitHub Actions documentation](https://docs.github.com/en/actions)
- OpenAI API: Visit [OpenAI Help Center](https://help.openai.com/)
- This setup: Create an issue in the repository