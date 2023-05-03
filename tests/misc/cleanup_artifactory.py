# File to delete all repositories on the server
# that start with `unittest-`.
#
# NOTE:
# * it is important to only call this script
#   when no test pipeline is running
# * you need to install `audfactory` to execute this script

import audbackend
import audfactory


name = 'artifactory'
host = 'https://audeering.jfrog.io/artifactory'

r = audfactory.rest_api_get(f'{host}/api/repositories')

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
