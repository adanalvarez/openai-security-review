import git
import openai
import os
import json


def check_code_vulnerabilities(code, tokens):
    """
    Analyzes the provided code for vulnerabilities using OpenAI's API.

    Args:
        code (str): The code to analyze.
        tokens (str): The maximum number of tokens to use in the API request.

    Returns:
        str: The result of the vulnerability analysis in Markdown format.
    """
    client = openai.ChatCompletion() 
    prompt = (
        f"**Prompt:**\n\n"
        f"Analyze the following code for security vulnerabilities:\n\n"
        f"```python\n{code}\n```\n\n"
        f"If vulnerabilities exist:\n"
        f"1. Identify the specific line(s) containing the issue.\n"
        f"2. Provide a detailed explanation of the vulnerability.\n"
        f"3. Recommend a solution to resolve the issue, including an example of improved code.\n\n"
        f"Return the response in **Markdown format**, formatted as a GitHub comment."
    )
    try:
        response = client.create(
            model="gpt-4",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_tokens=int(tokens),
            temperature=0.2,
            top_p=1,
            frequency_penalty=1,
            presence_penalty=1,
        )
        result_text = response["choices"][0]["message"]["content"]
        if result_text.strip().startswith("No"):
            return "No vulnerabilities detected"
        else:
            return result_text
    except Exception as e:
        return f"An error occurred: {e}"


def get_modified_files():
    """
    Identifies modified files in the current Git repository based on a pull request event.

    Returns:
        list: A list of modified file paths.

    Raises:
        ValueError: If the current directory is not a Git repository.
    """
    try:
        with open(os.environ['GITHUB_EVENT_PATH']) as f:
            event = json.load(f)
        # Open the repository using the `git` library
        repo = git.Repo('.')

        # Get the base and head commit SHAs from the pull request event
        base_sha = event['pull_request']['base']['sha']
        head_sha = event['pull_request']['head']['sha']
        
        source_commit = repo.commit(base_sha)
        target_commit = repo.commit(head_sha)

        # Use the `git.Diff` class to get a list of modified files
        diff = source_commit.diff(target_commit)

        modified_files = []
        for d in diff:
            if d.change_type in ('A', 'M', 'T'):
                modified_files.append(d.a_path)
        return modified_files
    except git.exc.InvalidGitRepositoryError as e:
        raise ValueError("The current directory is not a Git repository.") from e


def run():
    """
    Main function to analyze modified files for vulnerabilities and generate a comment.
    """
    max_files = os.environ.get("MAX_FILES")
    tokens = os.environ.get("TOKENS")

    comment = "## Suggestions from the AI"

    try:
        files = get_modified_files()
        print(files)
        if len(files) > int(max_files):
            comment = f"{len(files)} files were modified. Limit {max_files} exceeded."
        else:
            for file in files:
                try:
                    with open(file, 'r') as f:
                        code = f.read()
                    iasuggestion = check_code_vulnerabilities(code, tokens)
                except Exception as e:
                    iasuggestion = f"An error occurred while analyzing {file}: {e}"
                comment = f"{comment}\n\n### {file}\n{iasuggestion}\n"
    except Exception as e:
        comment += f"\n\nAn error occurred during execution: {e}"

    # Write the comment to a file
    with open("comment.md", "w") as f:
        f.write(comment)


if __name__ == "__main__":
    run()
