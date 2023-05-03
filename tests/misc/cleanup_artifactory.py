# File to delete all repositories on the server
# that start with `unittest-`.
#
# NOTE: it is important to only call this script
# when no test pipeline is running

import requests

import audbackend


name = 'artifactory'
host = 'https://audeering.jfrog.io/artifactory'

username, api_key = audbackend.core.artifactory._authentication(host)
r = requests.get(f'{host}/api/repositories', auth=(username, api_key))

if r.status_code == 200:
    repos = [entry['key'] for entry in r.json()]
    repos = [
        repo for repo in repos
        if repo.startswith('unittest-')
    ]
    length = len(repos)
    for n, repo in enumerate(repos):
        try:
            audbackend.delete(name, host, repo)
            print(f'{n + 1:4.0f} / {length:4.0f} Deleted {repo}')
        except audbackend.BackendError:
            raise RuntimeError(
                f'Cleaning up of repo {repo} failed. '
                f'Please try to run this script later again.'
            )
