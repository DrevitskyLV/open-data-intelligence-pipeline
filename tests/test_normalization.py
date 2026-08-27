from open_data_intelligence.services.normalization import (
    normalize_organization_name,
    normalize_registration_code,
)


def test_registration_code_removes_separators() -> None:
    assert normalize_registration_code("ua-50 0001") == "UA500001"


def test_registration_code_is_case_insensitive() -> None:
    assert normalize_registration_code("ua500001") == "UA500001"


def test_company_suffixes_are_removed() -> None:
    assert normalize_organization_name("Nova Data Solutions, LLC") == "nova data solutions"


def test_unicode_name_is_normalized() -> None:
    assert normalize_organization_name("ТОВ «Альфа Системи»") == "альфа системи"
