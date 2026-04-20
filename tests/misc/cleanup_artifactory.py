# File to delete all repositories on the server
# that start with `unittest-`.
#
# NOTE: it is important to only call this script
# when no test pipeline is running

import requests

import audbackend


host = "https://audeering.jfrog.io/artifactory"

authentication = audbackend.Artifactory.get_authentication(host)
r = requests.get(f"{host}/api/repositories", auth=authentication)

if r.status_code == 200:
    # Collect names of leftover unittest repositories
    repos = [entry["key"] for entry in r.json()]
    repos = [repo for repo in repos if repo.startswith("unittest-")]
    length = len(repos)
    # Delete leftover repositories
    for n, repo in enumerate(repos):
        try:
            response = requests.delete(
                f"{host}/api/repositories/{repo}",
                auth=authentication,
            )
            response.raise_for_status()
            print(f"{n + 1:4.0f} / {length:4.0f} Deleted {repo}")
        except Exception:
            raise RuntimeError(
                f"Cleaning up of repo {repo} failed. "
                f"Please try to run this script later again."
            )
