from normalize import canonicalize_url, normalize_doi, normalize_title


def test_doi_normalization() -> None:
    assert normalize_doi("https://doi.org/10.1016/J.TEST.2024.01.001") == "10.1016/j.test.2024.01.001"
    assert normalize_doi("doi:10.1/ABC") == "10.1/abc"


def test_canonical_url_normalization() -> None:
    assert canonicalize_url("HTTPS://Example.COM/path/?utm_source=x&a=1#frag") == "https://example.com/path?a=1"


def test_normalized_title_matching_signal() -> None:
    assert normalize_title("Pavement: Thermal Management!") == "pavement thermal management"
