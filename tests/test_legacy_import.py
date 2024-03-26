import audbackend


def test_legacy_import(hosts):
    audbackend.Backend("host", "repo")
    audbackend.Artifactory(hosts[audbackend.backend.Artifactory], "repo")
    audbackend.FileSystem(hosts[audbackend.backend.FileSystem], "repo")
