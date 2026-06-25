import audbackend


def test_legacy_import(hosts):
    audbackend.Backend("host", "repo")
    audbackend.FileSystem(hosts["file-system"], "repo")
