from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.adapters.dynamics_crm_client import DynamicsCRMClient
from app.domain.crm.models import (
    CRMAccountSummary,
    CRMAccountsResponse,
    CRMContactSummary,
    CRMContactsResponse,
    CRMForecastBucket,
    CRMPipelineOpportunity,
    CRMSalesForecastResponse,
    CRMSalesPipelineResponse,
    CRMSalesStatsResponse,
)


def _to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _to_float(value: Any) -> float:
    return float(_to_decimal(value))


def _to_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            return None
    return None


def _month_key(value: Optional[date]) -> Optional[str]:
    if value is None:
        return None
    return f"{value.year:04d}-{value.month:02d}"


def _first_present(row: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


class CRMService:
    def __init__(self, client: Optional[DynamicsCRMClient] = None) -> None:
        self._client = client or DynamicsCRMClient()

    async def get_accounts(self, *, top: int = 100, search: Optional[str] = None) -> CRMAccountsResponse:
        filter_expr = None
        if search:
            escaped = search.replace("'", "''")
            filter_expr = f"contains(name,'{escaped}')"

        rows = await self._client.get_collection(
            "accounts",
            select=[
                "accountid",
                "name",
                "accountnumber",
                "telephone1",
                "emailaddress1",
                "address1_city",
                "address1_country",
                "revenue",
                "modifiedon",
            ],
            filter_expr=filter_expr,
            order_by="modifiedon desc",
            top=top,
        )

        items = [
            CRMAccountSummary(
                account_id=str(row.get("accountid", "")),
                name=str(row.get("name") or ""),
                account_number=row.get("accountnumber"),
                telephone=row.get("telephone1"),
                email=row.get("emailaddress1"),
                city=row.get("address1_city"),
                country=row.get("address1_country"),
                annual_revenue=_to_float(row.get("revenue")) if row.get("revenue") is not None else None,
                modified_on=row.get("modifiedon"),
            )
            for row in rows
        ]
        return CRMAccountsResponse(items=items, count=len(items))

    async def get_contacts(self, *, top: int = 100, search: Optional[str] = None) -> CRMContactsResponse:
        filter_expr = None
        if search:
            escaped = search.replace("'", "''")
            filter_expr = (
                f"contains(fullname,'{escaped}') or contains(emailaddress1,'{escaped}')"
            )

        rows = await self._client.get_collection(
            "contacts",
            select=[
                "contactid",
                "fullname",
                "firstname",
                "lastname",
                "emailaddress1",
                "mobilephone",
                "telephone1",
                "_parentcustomerid_value",
                "modifiedon",
            ],
            filter_expr=filter_expr,
            order_by="modifiedon desc",
            top=top,
        )

        items = [
            CRMContactSummary(
                contact_id=str(row.get("contactid", "")),
                full_name=str(row.get("fullname") or ""),
                first_name=row.get("firstname"),
                last_name=row.get("lastname"),
                email=row.get("emailaddress1"),
                mobile_phone=row.get("mobilephone"),
                business_phone=row.get("telephone1"),
                parent_customer_id=row.get("_parentcustomerid_value"),
                parent_customer_name=row.get("_parentcustomerid_value@OData.Community.Display.V1.FormattedValue"),
                modified_on=row.get("modifiedon"),
            )
            for row in rows
        ]
        return CRMContactsResponse(items=items, count=len(items))

    async def get_sales_pipeline(self, *, top: int = 200) -> CRMSalesPipelineResponse:
        rows = await self._client.get_collection(
            "opportunities",
            select=[
                "opportunityid",
                "name",
                "estimatedvalue",
                "closeprobability",
                "estimatedclosedate",
                "stepname",
                "statecode",
                "statuscode",
                "_ownerid_value",
                "_customerid_value",
            ],
            filter_expr="statecode eq 0",
            order_by="estimatedclosedate asc",
            top=top,
        )

        items: List[CRMPipelineOpportunity] = []
        pipeline_total = Decimal("0")
        weighted_total = Decimal("0")

        for row in rows:
            estimated_value = _to_decimal(row.get("estimatedvalue"))
            probability = _to_decimal(row.get("closeprobability"))
            weighted = estimated_value * (probability / Decimal("100"))
            pipeline_total += estimated_value
            weighted_total += weighted

            items.append(
                CRMPipelineOpportunity(
                    opportunity_id=str(row.get("opportunityid", "")),
                    name=str(row.get("name") or ""),
                    customer_name=row.get("_customerid_value@OData.Community.Display.V1.FormattedValue"),
                    estimated_close_date=_to_date(row.get("estimatedclosedate")),
                    estimated_value=round(float(estimated_value), 2),
                    probability_percent=round(float(probability), 2) if row.get("closeprobability") is not None else None,
                    weighted_estimated_value=round(float(weighted), 2),
                    stage=row.get("stepname"),
                    status=row.get("statuscode@OData.Community.Display.V1.FormattedValue"),
                    owner_name=row.get("_ownerid_value@OData.Community.Display.V1.FormattedValue"),
                )
            )

        return CRMSalesPipelineResponse(
            as_of=date.today(),
            total_open_opportunities=len(items),
            total_pipeline_amount=round(float(pipeline_total), 2),
            total_weighted_pipeline_amount=round(float(weighted_total), 2),
            items=items,
        )

    async def get_sales_stats(self) -> CRMSalesStatsResponse:
        pipeline = await self.get_sales_pipeline(top=5000)
        today = date.today()
        month_start = today.replace(day=1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)

        rows = await self._client.get_collection(
            "opportunities",
            select=[
                "opportunityid",
                "actualvalue",
                "actualclosedate",
                "statecode",
            ],
            filter_expr=(
                "statecode ne 0 and actualclosedate ge "
                f"{month_start.isoformat()}T00:00:00Z and actualclosedate lt {next_month.isoformat()}T00:00:00Z"
            ),
            top=5000,
        )

        won_count = 0
        won_amount = Decimal("0")
        lost_count = 0

        for row in rows:
            state = int(row.get("statecode", -1)) if row.get("statecode") is not None else -1
            if state == 1:
                won_count += 1
                won_amount += _to_decimal(row.get("actualvalue"))
            elif state == 2:
                lost_count += 1

        return CRMSalesStatsResponse(
            as_of=today,
            open_opportunities_count=pipeline.total_open_opportunities,
            open_pipeline_amount=pipeline.total_pipeline_amount,
            weighted_pipeline_amount=pipeline.total_weighted_pipeline_amount,
            won_this_month_count=won_count,
            won_this_month_amount=round(float(won_amount), 2),
            lost_this_month_count=lost_count,
        )

    async def get_sales_forecast(self, *, months: int = 6) -> CRMSalesForecastResponse:
        pipeline = await self.get_sales_pipeline(top=5000)

        today = date.today().replace(day=1)
        month_keys: List[str] = []
        cursor = today
        for _ in range(months):
            month_keys.append(_month_key(cursor) or "")
            if cursor.month == 12:
                cursor = date(cursor.year + 1, 1, 1)
            else:
                cursor = date(cursor.year, cursor.month + 1, 1)

        aggregations: Dict[str, Dict[str, float | int]] = defaultdict(
            lambda: {
                "count": 0,
                "weighted": 0.0,
                "unweighted": 0.0,
            }
        )

        for item in pipeline.items:
            key = _month_key(item.estimated_close_date)
            if not key or key not in month_keys:
                continue
            bucket = aggregations[key]
            bucket["count"] = int(bucket["count"]) + 1
            bucket["weighted"] = float(bucket["weighted"]) + item.weighted_estimated_value
            bucket["unweighted"] = float(bucket["unweighted"]) + item.estimated_value

        buckets = [
            CRMForecastBucket(
                month=key,
                open_opportunities_count=int(aggregations[key]["count"]),
                weighted_amount=round(float(aggregations[key]["weighted"]), 2),
                unweighted_amount=round(float(aggregations[key]["unweighted"]), 2),
            )
            for key in month_keys
        ]

        return CRMSalesForecastResponse(as_of=date.today(), months=months, buckets=buckets)
