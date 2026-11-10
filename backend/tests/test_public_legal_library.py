"""Public legal library accepts all footer slugs; operator publication is required."""
import pytest
from app.extra_api import LEGAL_SLUGS

@pytest.mark.parametrize("slug", [
    "privacy", "terms", "cookies", "refund", "data-protection",
    "acceptable-use", "disclaimer", "accessibility",
])
def test_all_footer_legal_slugs_are_supported_but_not_autopublished(client, slug):
    assert slug in LEGAL_SLUGS
    response = client.get("/api/v1/public/legal/" + slug)
    assert response.status_code == 404
