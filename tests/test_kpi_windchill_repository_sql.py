from app.integrations.windchill_repository import (
    SQL_CREATED_DRAWINGS_PER_USER,
    SQL_MODIFIED_DRAWINGS_PER_USER,
)


def _normalized_sql(text_clause) -> str:
    return " ".join(str(text_clause).split()).lower()


def test_created_drawings_query_counts_unique_master_documents() -> None:
    sql = _normalized_sql(SQL_CREATED_DRAWINGS_PER_USER)
    assert "count(distinct epmm.ida2a2) as count" in sql
    assert "group by cast(epmm.createstampa2 as date), cusr.fullname" in sql


def test_modified_drawings_query_counts_unique_master_documents() -> None:
    sql = _normalized_sql(SQL_MODIFIED_DRAWINGS_PER_USER)
    assert "count(distinct epmm.ida2a2) as count" in sql
    assert "cast(epmd.modifystampa2 as date) <> cast(epmm.createstampa2 as date)" in sql
    assert "group by cast(epmd.modifystampa2 as date), musr.fullname" in sql
