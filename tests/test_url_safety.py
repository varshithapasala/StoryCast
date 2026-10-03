import pytest
from app.services.url_safety import UnsafeURLError, validate_public_url

@pytest.mark.parametrize("url",["http://127.0.0.1/admin","http://localhost:8000","file:///etc/passwd","http://user:pass@example.com"])
def test_private_and_credentialed_urls_are_blocked(url):
    with pytest.raises(UnsafeURLError): validate_public_url(url)
