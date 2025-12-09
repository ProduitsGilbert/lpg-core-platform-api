->list the current number of PO that need to be sent using similar syntax with the Business Central API : 
def fetch_orders():
    base_url = "https://bc.gilbert-tech.com:7063/ProductionBCBasic/ODataV4/Company('Gilbert-Tech')/PurchaseOrderHeaders"
    
    filter_criteria = f"No_Printed eq 0"
    endpoint = f"{base_url}?$filter={filter_criteria}&$orderby=No desc&$select=No,Buy_from_Vendor_No, Buy_from_Vendor_Name, RequisitionNumber"
    response = requests.get(endpoint, headers=headers, auth=(username, password))
    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        logfire.error(f"Failed to fetch orders. Status Code: {response.status_code}")
        return None

the important part is No_Printed eq 0 which list all not sent purchase order

--> then will return the last 3 months worth of data from those KPI table from Retool table 
Jules related KPI : SELECT [ID]
      ,[DATE]
      ,[Type]
      ,[Sous-Type]
      ,[metric]
      ,[vendor]
  FROM [Retool].[dbo].[Achat_KPI_Jules]

--> Days late avg BO and quantity and other metric of back order for purchasing : 
SELECT  [ID]
      ,[Date]
      ,[Description]
      ,[Metric]
  FROM [Retool].[dbo].[Achat_KPI]

--> vendor related KPI for : Average Delivery Delay Days and Average Promise vs. Actual Days :
SELECT  [ID]
      ,[Date]
      ,[Vendor]
      ,[Description]
      ,[Metric]
  FROM [Retool].[dbo].[Achat_KPI_Vendor]