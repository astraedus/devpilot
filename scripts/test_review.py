#!/usr/bin/env python3
"""
Test script: Exercise PR review agent directly without webhook.
Uses the astraedus/devpilot repo's own first PR or a manually specified one.
"""
import asyncio
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings
from backend.tools.github import GitHubTools
from backend.agents.pr_reviewer import review_pr, format_review_comment


async def main(repo: str = "astraedus/devpilot", pr_number: int = 1):
    print(f"Testing PR review: {repo}#{pr_number}")
    print(f"Azure Foundry configured: {bool(settings.azure_project_connection_string)}")
    print(f"GitHub token: {'set' if settings.github_token else 'NOT SET'}")
    print()

    gh = GitHubTools(token=settings.github_token)

    print("Fetching PR diff...")
    diff = await gh.get_pr_diff(repo, pr_number)
    print(f"Diff length: {len(diff)} chars")

    print("Fetching PR files...")
    files = await gh.get_pr_files(repo, pr_number)
    print(f"Files changed: {len(files)}")

    print("\nRunning review agent...")
    try:
        review = await review_pr(repo, pr_number, diff, files)
        print("\n=== REVIEW RESULT ===")
        print(f"Summary: {review.summary}")
        print(f"Overall: {review.overall}")
        print(f"Issues: {len(review.issues)}")
        for issue in review.issues:
            print(f"  [{issue.severity}] {issue.file}:{issue.line} - {issue.comment}")

        print("\n=== FORMATTED COMMENT ===")
        print(format_review_comment(review))

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    repo = sys.argv[1] if len(sys.argv) > 1 else "astraedus/devpilot"
    pr_number = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    asyncio.run(main(repo, pr_number))
