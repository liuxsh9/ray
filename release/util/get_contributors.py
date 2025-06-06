from github import Github
from subprocess import check_output
import shlex
from tqdm import tqdm
import click
from collections import defaultdict
import sys


def _find_pr_number(line: str) -> str:
    start = line.find("(#")
    if start < 0:
        return ""
    end = line.find(")", start + 2)
    if end < 0:
        return ""
    return line[start + 2 : end]


@click.command()
@click.option(
    "--access-token",
    required=True,
    help="""
Github Access token that has repo:public_repo and user:read:user permission.

Create them at https://github.com/settings/tokens/new
""",
)
@click.option(
    "--prev-release-commit",
    required=True,
    help="Last commit SHA of the previous release.",
)
@click.option(
    "--curr-release-commit",
    required=True,
    help="Last commit SHA of the current release.",
)
def run(access_token, prev_release_commit, curr_release_commit):
    print("Writing commit descriptions to 'commits.txt'...")
    commits = check_output(
        [
            "git",
            "log",
            f"{prev_release_commit}..{curr_release_commit}",
            "--pretty=format:'%s'",
        ],
        stderr=sys.stderr,
    ).decode()
    with open("commits.txt", "w") as file:
        file.write(commits)

    # Generate command
    cmd = []
    cmd.append(
        (
            f"git log {prev_release_commit}..{curr_release_commit} "
            f'--pretty=format:"%s" '
            rf' | grep -Eo "#(\d+)"'
        )
    )
    joined = " && ".join(cmd)
    cmd = f"bash -c '{joined}'"
    cmd = shlex.split(cmd)
    print("Executing", cmd)

    lines = commits.split("\n")
    pr_numbers = []
    for line in lines:
        pr_number = _find_pr_number(line)
        if pr_number:
            pr_numbers.append(int(pr_number))

    # Sort the PR numbers
    print("PR numbers", pr_numbers)

    # Use Github API to fetch the
    g = Github(access_token)
    ray_repo = g.get_repo("ray-project/ray")
    logins = set()
    for num in tqdm(pr_numbers):
        try:
            logins.add(ray_repo.get_pull(num).user.login)
        except Exception as e:
            print(e)

    print()
    print("Here's the list of contributors")
    print("=" * 10)
    print()
    print("@" + ", @".join(logins))
    print()
    print("=" * 10)

    # Organize commits
    NO_CATEGORY = "[NO_CATEGORY]"

    def get_category(line):
        if line[0] == "[":
            return (line.split("]")[0].strip(" ") + "]").upper()
        else:
            return NO_CATEGORY

    commits = defaultdict(list)

    with open("commits.txt") as file:
        for line in file.readlines():
            commits[get_category(line)].append(line.strip())

    with open("commits.txt", "a") as file:
        for category, commit_msgs in commits.items():
            file.write("\n{}\n".format(category))
            for commit_msg in commit_msgs:
                file.write("{}\n".format(commit_msg))


if __name__ == "__main__":
    run()
