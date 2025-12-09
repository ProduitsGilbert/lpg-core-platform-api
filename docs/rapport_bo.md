please create a new endpoint to retrieve all missing parts for a specific sales order. the goal is to take a sales order number and return a fully formed excel file which will be designed to be human readable, ideal would be a even pretty looking excel file, instead of a raw data file that seem to come from a csv export. 

with a sales order number (in this case GI022960) we can fetch the MRP 
you can use this filter syntax on the MRP in and out endpoint : 
{ "filters": [ { "field": "JobNo", "operator": "contains", "value": "GI023758" }]}


Curl

curl -X 'GET' \
  'https://api.gilbert-tech.com:7778/api/mrp/BasicMRP/Out?filter=%7B%20%22filters%22%3A%20%5B%20%7B%20%22field%22%3A%20%22JobNo%22%2C%20%22operator%22%3A%20%22contains%22%2C%20%22value%22%3A%20%22GI023758%22%20%7D%5D%7D&type=-1' \
  -H 'accept: */*'
Request URL
https://api.gilbert-tech.com:7778/api/mrp/BasicMRP/Out?filter=%7B%20%22filters%22%3A%20%5B%20%7B%20%22field%22%3A%20%22JobNo%22%2C%20%22operator%22%3A%20%22contains%22%2C%20%22value%22%3A%20%22GI023758%22%20%7D%5D%7D&type=-1
Server response
Code	Details
200	
Response body
Download
{
  "count": 4,
  "values": [
    {
      "$type": "GilbertAPI.Model.MRP.outSalesOrder, GilbertAPI",
      "noHeader": "GI023758",
      "quantityTotal": 1,
      "orderDate": "2025-10-27T00:00:00",
      "billtoName": "HARRIGAN LUMBER COMPANY INC.",
      "status": "Released",
      "lineType": "2",
      "whsQtyOutstanding": 1,
      "whsQtyPicked": 0,
      "whsQtytoShip": 0,
      "whsQtyShipped": 0,
      "auxiliaryIndex1": "GI023758",
      "auxiliaryIndex2": "Order",
      "binCode": "P405",
      "isUnmanagedHardware": false,
      "lastDirectCost": 1606.35,
      "lineNo": 10000,
      "qtyToFill": 1,
      "qtyFilled": 1,
      "itemNo": "8450080",
      "jobNo": "GI023758",
      "unitofMeasureCode": "UN",
      "qtyperUnitofMeasure": 1,
      "replenishmentSystem": "Prod. Order",
      "vendorNo": "",
      "vendorItemNo": "",
      "description": "CHIP BREAKER, PRIMARY, NEW TUNGSTEN",
      "descriptionItemCard": "S2. (CLAD) PIED PRESSEUR",
      "lotSize": 1,
      "needDate": "2025-10-29T00:00:00",
      "latestApplied": "2026-01-08T15:37:11-05:00",
      "typeOfOut": 0,
      "attributionFromIn": [
        {
          "systemID": "c36e417c-cbc0-f011-adc0-0050568b51e9",
          "name": "M179628",
          "job": "GI023758",
          "qty": 1,
          "type": "mo",
          "dateRequiredOrAvailable": "2026-01-08T15:37:11-05:00"
        }
      ],
      "substitutesExist": false,
      "noofSubstitutes": 0,
      "critical": false,
      "systemId": "b3ed3dff-5db3-f011-adc0-0050568b51e9",
      "name": "GI023758",
      "remainingQuantity": 0,
      "qtyRemainingFIll": 0,
      "safetyStockQuantity": 2,
      "leadTimeCalculation": "30D",
      "mrpTakeFrom": "1xM179628-1; ",
      "willBeTooLate": true,
      "isTooLate": true,
      "plannedDelayDay": -71,
      "actualDelayDay": -22,
      "shippingAgentServiceCode": "",
      "shippingAgentCode": "PURO3",
      "shippingAgentRush": false,
      "mrpComment": [],
      "mrpItemComment": [],
      "bloquerAchatMRP": false
    },
    {
      "$type": "GilbertAPI.Model.MRP.outSalesOrder, GilbertAPI",
      "noHeader": "GI023758",
      "quantityTotal": 1,
      "orderDate": "2025-10-27T00:00:00",
      "billtoName": "HARRIGAN LUMBER COMPANY INC.",
      "status": "Released",
      "lineType": "2",
      "whsQtyOutstanding": 0,
      "whsQtyPicked": 0,
      "whsQtytoShip": 0,
      "whsQtyShipped": 0,
      "auxiliaryIndex1": "GI023758",
      "auxiliaryIndex2": "Order",
      "binCode": "P410",
      "isUnmanagedHardware": false,
      "lastDirectCost": 1756.22,
      "lineNo": 20000,
      "qtyToFill": 0,
      "qtyFilled": 0,
      "itemNo": "8450119",
      "jobNo": "GI023758",
      "unitofMeasureCode": "UN",
      "qtyperUnitofMeasure": 1,
      "replenishmentSystem": "Prod. Order",
      "vendorNo": "",
      "vendorItemNo": "",
      "description": "CHIP BREAKER, SEC, NEW TUNGSTEN",
      "descriptionItemCard": "S2. (CLAD) PIED PRESSEUR",
      "lotSize": 1,
      "needDate": "2025-10-29T00:00:00",
      "latestApplied": "0001-01-01T00:00:00",
      "typeOfOut": 0,
      "attributionFromIn": [],
      "substitutesExist": false,
      "noofSubstitutes": 0,
      "critical": false,
      "systemId": "b4ed3dff-5db3-f011-adc0-0050568b51e9",
      "name": "GI023758",
      "remainingQuantity": 0,
      "qtyRemainingFIll": 0,
      "safetyStockQuantity": 1,
      "leadTimeCalculation": "30D",
      "mrpTakeFrom": "",
      "willBeTooLate": false,
      "isTooLate": false,
      "plannedDelayDay": 739552,
      "actualDelayDay": -22,
      "shippingAgentServiceCode": "",
      "shippingAgentCode": "PURO3",
      "shippingAgentRush": false,
      "mrpComment": [],
      "mrpItemComment": [],
      "bloquerAchatMRP": false
    },
    {
      "$type": "GilbertAPI.Model.MRP.outProdOrd, GilbertAPI",
      "prodOrderLineNo": 10000,
      "prodOrderNo": "M179628",
      "qtyPick": 73,
      "qty": 73,
      "expectedQuantity": 73,
      "status": "Released",
      "planningLevelCode": 0,
      "prepRemainingQuantity": 0,
      "suppliedbyLineNo": 0,
      "prodOrderSystemID": "fca9b575-cbc0-f011-adc0-0050568b51e9",
      "binCode": "PLASMA",
      "isUnmanagedHardware": false,
      "lastDirectCost": 2.625,
      "lineNo": 0,
      "qtyToFill": 0,
      "qtyFilled": 0,
      "itemNo": "0413140",
      "jobNo": "GI023758",
      "unitofMeasureCode": "PO2",
      "qtyperUnitofMeasure": 1,
      "replenishmentSystem": "Purchase",
      "vendorNo": "ACILE01",
      "vendorItemNo": "5'' 44W/A36",
      "description": "PLAQUE 5\" 44W (4' X 8')",
      "descriptionItemCard": "PLAQUE 5\" 44W (4' X 8')",
      "lotSize": 4608,
      "needDate": "2025-11-10T00:00:00",
      "latestApplied": "0001-01-01T00:00:00",
      "typeOfOut": 1,
      "attributionFromIn": [],
      "substitutesExist": false,
      "noofSubstitutes": 0,
      "critical": false,
      "systemId": "e96e417c-cbc0-f011-adc0-0050568b51e9",
      "name": "M179628",
      "remainingQuantity": 0,
      "qtyRemainingFIll": 0,
      "safetyStockQuantity": 858,
      "leadTimeCalculation": "4W",
      "mrpTakeFrom": "",
      "willBeTooLate": false,
      "isTooLate": false,
      "plannedDelayDay": 739564,
      "actualDelayDay": -10,
      "shippingAgentRush": false,
      "mrpComment": [],
      "mrpItemComment": [],
      "bloquerAchatMRP": false
    },
    {
      "$type": "GilbertAPI.Model.MRP.outProdOrd, GilbertAPI",
      "prodOrderLineNo": 10000,
      "prodOrderNo": "M179628",
      "qtyPick": 0,
      "qty": 1.15,
      "expectedQuantity": 1.15,
      "status": "Released",
      "planningLevelCode": 0,
      "prepRemainingQuantity": 0,
      "suppliedbyLineNo": 0,
      "prodOrderSystemID": "fca9b575-cbc0-f011-adc0-0050568b51e9",
      "binCode": "SCIE",
      "isUnmanagedHardware": false,
      "lastDirectCost": 0.27083,
      "lineNo": 0,
      "qtyToFill": 1.15,
      "qtyFilled": 1.15,
      "itemNo": "0423602",
      "jobNo": "GI023758",
      "unitofMeasureCode": "PO",
      "qtyperUnitofMeasure": 1,
      "replenishmentSystem": "Purchase",
      "vendorNo": "ACILE01",
      "vendorItemNo": "1  A36",
      "description": "FER CARRE 1\"  44W",
      "descriptionItemCard": "FER CARRE 1\"  44W",
      "lotSize": 20,
      "needDate": "2025-11-10T00:00:00",
      "latestApplied": "2024-11-20T14:25:26.6734005-05:00",
      "typeOfOut": 1,
      "attributionFromIn": [
        {
          "systemID": "b4736d8e-e066-eb11-ad31-0050568b51e9",
          "name": "Stock",
          "job": "GI023317;GIM0899;GI023758;MINIMUM STOCK;GIM0885;GIM0888;GIM0866",
          "qty": 1.15,
          "type": "stock",
          "dateRequiredOrAvailable": "2024-11-20T14:25:26.6734005-05:00"
        }
      ],
      "substitutesExist": false,
      "noofSubstitutes": 0,
      "critical": false,
      "systemId": "e76e417c-cbc0-f011-adc0-0050568b51e9",
      "name": "M179628",
      "remainingQuantity": 1.15,
      "qtyRemainingFIll": 0,
      "safetyStockQuantity": 0,
      "leadTimeCalculation": "4W",
      "mrpTakeFrom": "1,15xStock; ",
      "willBeTooLate": false,
      "isTooLate": false,
      "plannedDelayDay": 0,
      "actualDelayDay": -10,
      "shippingAgentRush": false,
      "mrpComment": [],
      "mrpItemComment": [],
      "bloquerAchatMRP": false
    }
  ]
}

______________

Curl

curl -X 'GET' \
  'https://api.gilbert-tech.com:7778/api/mrp/BasicMRP/In?filter=%7B%20%22filters%22%3A%20%5B%20%7B%20%22field%22%3A%20%22JobNo%22%2C%20%22operator%22%3A%20%22contains%22%2C%20%22value%22%3A%20%22GI023758%22%20%7D%5D%7D' \
  -H 'accept: */*'
Request URL
https://api.gilbert-tech.com:7778/api/mrp/BasicMRP/In?filter=%7B%20%22filters%22%3A%20%5B%20%7B%20%22field%22%3A%20%22JobNo%22%2C%20%22operator%22%3A%20%22contains%22%2C%20%22value%22%3A%20%22GI023758%22%20%7D%5D%7D
Server response
Code	Details
200	
Response body
Download
{
  "count": 2,
  "values": [
    {
      "$type": "GilbertAPI.Model.MRP.InStock, GilbertAPI",
      "binCode": "SCIE",
      "isFixed": true,
      "isDefault": true,
      "quantity": 165.33,
      "auxiliaryIndex1": "GIL",
      "vendorNo": "ACILE01",
      "vendorItemNo": "1  A36",
      "lastDirectCost": 0.27083,
      "replenishmentSystem": "Purchase",
      "baseUnitofMeasure": "PO",
      "purchUnitofMeasure": "PI",
      "purchQtyperUnitofMeasure": 1,
      "suiviReverseMRP": " ",
      "jobMaximumAttribution": [
        {
          "jobNo": "GI023317",
          "maxAvailableQty": 1.15,
          "qtyAttributed": 1.15,
          "currentlyAvailable": 0
        },
        {
          "jobNo": "GIM0899",
          "maxAvailableQty": 3.45,
          "qtyAttributed": 3.45,
          "currentlyAvailable": 0
        },
        {
          "jobNo": "GI023758",
          "maxAvailableQty": 1.15,
          "qtyAttributed": 1.15,
          "currentlyAvailable": 0
        },
        {
          "jobNo": "MINIMUM STOCK",
          "maxAvailableQty": 4.6,
          "qtyAttributed": 4.6,
          "currentlyAvailable": 0
        },
        {
          "jobNo": "GIM0885",
          "maxAvailableQty": 2.3,
          "qtyAttributed": 2.3,
          "currentlyAvailable": 0
        },
        {
          "jobNo": "GIM0888",
          "maxAvailableQty": 23,
          "qtyAttributed": 23,
          "currentlyAvailable": 0
        },
        {
          "jobNo": "GIM0866",
          "maxAvailableQty": 2.3,
          "qtyAttributed": 2.3,
          "currentlyAvailable": 0
        }
      ],
      "lineNo": 0,
      "earliestRequired": "2025-09-25T00:00:00",
      "systemID": "b4736d8e-e066-eb11-ad31-0050568b51e9",
      "tooLate": false,
      "leadTimeCalculation": "4W",
      "critical": false,
      "itemCategoryCode": "ACIER",
      "qtyCanApply": 165.33,
      "qtyApplied": 54.049999999999976,
      "itemNo": "0423602",
      "description": "FER CARRE 1\"  44W",
      "descriptionItemCard": "FER CARRE 1\"  44W",
      "jobNo": "GI023317;GIM0899;GI023758;MINIMUM STOCK;GIM0885;GIM0888;GIM0866",
      "unitofMeasureCode": "PO",
      "lotSize": 20,
      "qtyperUnitofMeasure": 1,
      "dateGet": "2024-11-20T14:25:26.6734005-05:00",
      "qtyDisponible": 119.33,
      "qtyUnused": 111.28,
      "name": "Stock",
      "type": "InStock",
      "typeOfIn": 0,
      "attributionToOut": [
        {
          "systemID": "7c90f214-409a-f011-adc0-0050568b51e9",
          "name": "M178078",
          "job": "GI023317",
          "qty": 1.15,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2025-09-25T00:00:00"
        },
        {
          "systemID": "7b482317-1488-f011-adc0-0050568b51e9",
          "name": "M176239",
          "job": "GIM0899",
          "qty": 3.45,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2025-10-29T00:00:00"
        },
        {
          "systemID": "e76e417c-cbc0-f011-adc0-0050568b51e9",
          "name": "M179628",
          "job": "GI023758",
          "qty": 1.15,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2025-11-10T00:00:00"
        },
        {
          "systemID": "42ad52f2-2358-f011-adbe-0050568b51e9",
          "name": "M173653",
          "job": "MINIMUM STOCK",
          "qty": 4.6,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2026-03-01T00:00:00"
        },
        {
          "systemID": "f38fc043-8743-ef11-adab-0050568b51e9",
          "name": "PR217421",
          "job": "GIM0885",
          "qty": 2.3,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2027-02-01T00:00:00"
        },
        {
          "systemID": "6936eca3-6f66-f011-adbf-0050568b51e9",
          "name": "SPR76334",
          "job": "GIM0888",
          "qty": 23,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2027-02-01T00:00:00"
        },
        {
          "systemID": "8d8e1d4c-8743-ef11-adab-0050568b51e9",
          "name": "SPR53863",
          "job": "GIM0866",
          "qty": 2.3,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2027-04-01T00:00:00"
        },
        {
          "systemID": "63171150-4499-f011-adc0-0050568b51e9",
          "name": "M177888",
          "job": "GI023317",
          "qty": 1.15,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2025-09-26T00:00:00"
        },
        {
          "systemID": "ce479e3a-29bf-f011-adc0-0050568b51e9",
          "name": "SPR79047",
          "job": "MINIMUM STOCK",
          "qty": 1.15,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2026-03-02T00:00:00"
        },
        {
          "systemID": "21088493-24bb-f011-adc0-0050568b51e9",
          "name": "SPR79012",
          "job": "MINIMUM STOCK",
          "qty": 1.15,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2026-03-02T00:00:00"
        },
        {
          "systemID": "e0e3898c-24bb-f011-adc0-0050568b51e9",
          "name": "SPR79011",
          "job": "MINIMUM STOCK",
          "qty": 1.15,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2026-03-02T00:00:00"
        },
        {
          "systemID": "d48ac3a2-7f43-ef11-adab-0050568b51e9",
          "name": "PR217422",
          "job": "GIM0885",
          "qty": 1.15,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2027-02-01T00:00:00"
        },
        {
          "systemID": "9360512a-4c40-ef11-adaa-0050568b51e9",
          "name": "PR217420",
          "job": "GIM0885",
          "qty": 1.15,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2027-02-01T00:00:00"
        },
        {
          "systemID": "9b67d4de-1e79-f011-adc0-0050568b51e9",
          "name": "SPR53862",
          "job": "GIM0866",
          "qty": 1.15,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2027-04-01T00:00:00"
        },
        {
          "systemID": "58d7e034-b52c-ef11-adaa-0050568b51e9",
          "name": "SPR56434",
          "job": "GIM0866",
          "qty": 1.15,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2027-04-01T00:00:00"
        },
        {
          "systemID": "ce34549c-b85f-ef11-adad-0050568b51e9",
          "name": "SPR60436",
          "job": "GIM0866",
          "qty": 2.3,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2027-04-01T00:00:00"
        },
        {
          "systemID": "20c858b7-be55-ef11-adab-0050568b51e9",
          "name": "SPR35772",
          "job": "GIM0866",
          "qty": 2.3,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2027-04-01T00:00:00"
        },
        {
          "systemID": "6186a267-4abe-ef11-adb6-0050568b51e9",
          "name": "SPR67852",
          "job": "GIM0866",
          "qty": 2.3,
          "type": "prodOrd",
          "dateRequiredOrAvailable": "2027-04-01T00:00:00"
        }
      ],
      "qty_AttibutedToMinimums": 8.05,
      "substitutesExist": false,
      "noofSubstitutes": 0,
      "safetyStockQuantity": 0,
      "mrpComment": [],
      "mrpItemComment": []
    },
    {
      "$type": "GilbertAPI.Model.MRP.InProd, GilbertAPI",
      "pctDone": 0,
      "prodOrderNo": "M179628",
      "quantity": 1,
      "remainingQuantity": 1,
      "planningLevelCode": 0,
      "startingDate": "2025-11-10T00:00:00",
      "endingDate": "2026-01-08T00:00:00",
      "childProdOrderNo": [],
      "lineNo": 10000,
      "earliestRequired": "2025-10-29T00:00:00",
      "systemID": "c36e417c-cbc0-f011-adc0-0050568b51e9",
      "tooLate": true,
      "safetyLeadTime": "0\u0002",
      "leadTimeCalculation": "30D",
      "critical": false,
      "itemCategoryCode": "EQMOU",
      "routingNo": "8450080-06",
      "qtyCanApply": 1,
      "qtyApplied": 1,
      "itemNo": "8450080",
      "description": "S2. (CLAD) PIED PRESSEUR",
      "descriptionItemCard": "S2. (CLAD) PIED PRESSEUR",
      "jobNo": "GI023758",
      "unitofMeasureCode": "UN",
      "lotSize": 0,
      "qtyperUnitofMeasure": 1,
      "dateGet": "2026-01-08T15:37:11-05:00",
      "qtyDisponible": 0,
      "qtyUnused": 0,
      "name": "M179628",
      "type": "InProd",
      "typeOfIn": 2,
      "attributionToOut": [
        {
          "systemID": "b3ed3dff-5db3-f011-adc0-0050568b51e9",
          "name": "GI023758",
          "job": "GI023758",
          "qty": 1,
          "type": "salesOrd",
          "dateRequiredOrAvailable": "2025-10-29T00:00:00"
        }
      ],
      "qty_AttibutedToMinimums": 0,
      "substitutesExist": false,
      "noofSubstitutes": 0,
      "safetyStockQuantity": 0,
      "mrpComment": [],
      "mrpItemComment": []
    }
  ]
}



















current implementation of the report (which is run manually)

																						
	GI022960    Généré en date de:  2025-10-08 15:53:03																					
																						
	Mo	Item	QtyOnMO	QtyRemaining	Type	Rev	Description	Palette	Note	QtyItemBO	Job	DueDate										
	M176567	8218725	2	2		0	MEC DOUILLE FIXATION ASS.	TO-PROD;		4	GI022960	9/29/25	Item	Description	ReqQty	WipQty	BinNo	Origin_POMO	WC_Date	Qty	Job	LastMove
													622411	BOUL. CYL. SPC 1/4-20UNC X 1/2	16	0	141B1	16x Stock		0		
													1401009	COUSSINET 1/4" X 7/16" 17/32" ACIER	4	0	128G02	4x Stock		0		
													8315107	DOUILLE DE FIXATION	2	0	P349	2x Stock		0		
													8315108	DOUILLE DE FIXATION	2	0		2x M172792	CQ	6	GI022960	8/7/25 11:33
																						
																						