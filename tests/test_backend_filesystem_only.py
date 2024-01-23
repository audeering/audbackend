import pytest

import audbackend


# Check optional backends are not available
with pytest.raises(AttributeError):
    audbackend.Artifactory('https://host.com', 'repo')
