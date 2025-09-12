{
  "openapi": "3.0.1",
  "info": {
    "title": "GilbertAPI",
    "version": "1.0"
  },
  "paths": {
    "/api/mrp/AdvancedMRP/RunMRP": {
      "get": {
        "tags": [
          "AdvancedMRP"
        ],
        "summary": "Force Runs the MRP",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/AdvancedMRP/GetUnused_PurchaseOrder": {
      "get": {
        "tags": [
          "AdvancedMRP"
        ],
        "summary": "Returns the current Purchase Order List that have unused remaining Qty .",
        "parameters": [
          {
            "name": "filter",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "hideUnmanagedHardware",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "boolean",
              "default": true
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/AdvancedMRP/GetUnused_ProductionOrder": {
      "get": {
        "tags": [
          "AdvancedMRP"
        ],
        "summary": "Returns the current Production Order List that have unused remaining Qty .",
        "parameters": [
          {
            "name": "filter",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/AdvancedMRP/GetEarly_PurchaseOrder": {
      "get": {
        "tags": [
          "AdvancedMRP"
        ],
        "summary": "Returns the current Purchase Order List that are too early .",
        "parameters": [
          {
            "name": "filter",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "minimumDaysEarlyTrigger",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "integer",
              "format": "int32",
              "default": 90
            }
          },
          {
            "name": "hideUnmanagedHardware",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "boolean",
              "default": true
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/AdvancedMRP/GetEarly_ProductionOrder": {
      "get": {
        "tags": [
          "AdvancedMRP"
        ],
        "summary": "Returns the current Production Order List that are too early .",
        "parameters": [
          {
            "name": "filter",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "minimumDaysEarlyTrigger",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "integer",
              "format": "int32",
              "default": 90
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/AdvancedMRP/GetBO_PurchaseOrder": {
      "get": {
        "tags": [
          "AdvancedMRP"
        ],
        "summary": "Returns the current BO List that requires a Purchase Order.",
        "parameters": [
          {
            "name": "filter",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "shortTerm",
            "in": "query",
            "description": "A boolean parameter that determines whether to return only short term data.",
            "style": "form",
            "schema": {
              "type": "boolean",
              "default": false
            }
          },
          {
            "name": "hideUnmanagedHardware",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "boolean",
              "default": true
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/AdvancedMRP/GetBO_ProductionOrder": {
      "get": {
        "tags": [
          "AdvancedMRP"
        ],
        "summary": "Returns the current BO List that requires a Production Order.",
        "parameters": [
          {
            "name": "removeBoyaux",
            "in": "query",
            "description": "A boolean parameter that determines whether to remove the item with a description starting with BOYAU.",
            "style": "form",
            "schema": {
              "type": "boolean",
              "default": true
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/AdvancedMRP/GetMonitoring_PurchaseOrder": {
      "get": {
        "tags": [
          "AdvancedMRP"
        ],
        "summary": "Returns the current Purchase Order Items (Suivi).",
        "parameters": [
          {
            "name": "filter",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "critical",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "boolean",
              "default": false
            }
          },
          {
            "name": "hideUnmanagedHardware",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "boolean",
              "default": true
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/AdvancedMRP/GetMonitoring_ProductionOrder": {
      "get": {
        "tags": [
          "AdvancedMRP"
        ],
        "summary": "Returns the current Production Order Items (Suivi).",
        "parameters": [
          {
            "name": "filter",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "critical",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "boolean",
              "default": false
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/AdvancedMRP/GetUnique_SuiviStatut": {
      "get": {
        "tags": [
          "AdvancedMRP"
        ],
        "summary": "Returns the unique SuiviStatus Options.",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/AdvancedMRP/GetUnique_SuiviReverseMRP": {
      "get": {
        "tags": [
          "AdvancedMRP"
        ],
        "summary": "Returns the unique SuiviStatus Options.",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/BasicMRP/RunMRP": {
      "get": {
        "tags": [
          "BasicMRP"
        ],
        "summary": "Force Runs the MRP",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/BasicMRP/In": {
      "get": {
        "tags": [
          "BasicMRP"
        ],
        "summary": "Returns the Input side of the MRP dataset.",
        "description": " WARNING: This method can return very large data sets. \r\n Large data sets can consume a lot of memory and potentially crash your application. \r\n Use with caution and consider implementing pagination or filtering to limit the size of the returned data.\r\n <br />\r\nFilter Implementation json object written as a string:<br />\r\n      -valid operator:  eq,neq,lt,lte,gt,gte,contains,startwith<br />\r\n      -valid logic:  and, or<br /><br />\r\n {\r\n\"filters\": [\r\n{\r\n    \"field\": \"FieldName1\",\r\n    \"operator\": \"contains\",  \r\n    \"value\": \"0\"\r\n},\r\n{\r\n    \"field\": \"FieldName2\",\r\n    \"operator\": \"contains\",\r\n    \"value\": \"0\"\r\n}\r\n],\r\n\"logic\": \"and\"\r\n}",
        "parameters": [
          {
            "name": "filter",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/BasicMRP/InCompressed": {
      "get": {
        "tags": [
          "BasicMRP"
        ],
        "summary": "Returns the compressed Input side of the MRP dataset (GZIP compression).",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/BasicMRP/In({item})": {
      "get": {
        "tags": [
          "BasicMRP"
        ],
        "summary": "Returns a filtered view of the Input side of the MRP for a single Item.",
        "parameters": [
          {
            "name": "item",
            "in": "path",
            "description": "A string value for a basic Item filtering functionnality.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/BasicMRP/Out": {
      "get": {
        "tags": [
          "BasicMRP"
        ],
        "summary": "Returns the Output side of the MRP dataset.",
        "description": " WARNING: This method can return very large data sets. \r\n Large data sets can consume a lot of memory and potentially crash your application. \r\n Use with caution and consider implementing pagination or filtering to limit the size of the returned data.\r\n <br />\r\nFilter Implementation json object written as a string:<br />\r\n      -valid operator:  eq,neq,lt,lte,gt,gte,contains,startwith<br />\r\n      -valid logic:  and, or<br /><br />\r\n {\r\n\"filters\": [\r\n{\r\n    \"field\": \"FieldName1\",\r\n    \"operator\": \"contains\",  \r\n    \"value\": \"0\"\r\n},\r\n{\r\n    \"field\": \"FieldName2\",\r\n    \"operator\": \"contains\",\r\n    \"value\": \"0\"\r\n}\r\n],\r\n\"logic\": \"and\"\r\n}",
        "parameters": [
          {
            "name": "filter",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "type",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "integer",
              "format": "int32",
              "default": -1
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/BasicMRP/OutNewFilter": {
      "get": {
        "tags": [
          "BasicMRP"
        ],
        "parameters": [
          {
            "name": "type",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "integer",
              "format": "int32",
              "default": -1
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/BasicMRP/OutCompressed": {
      "get": {
        "tags": [
          "BasicMRP"
        ],
        "summary": "Returns the compressed Output side of the MRP dataset (GZIP compression).",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/BasicMRP/Out({item})": {
      "get": {
        "tags": [
          "BasicMRP"
        ],
        "summary": "Returns a filtered view of the Output side of the MRP for a single Item.",
        "parameters": [
          {
            "name": "item",
            "in": "path",
            "description": "A string value for a basic Item filtering functionnality.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/CommentMRP/GetComments": {
      "get": {
        "tags": [
          "CommentMRP"
        ],
        "summary": "Get The list of all the comments",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/CommentMRP/GetItemComments": {
      "get": {
        "tags": [
          "CommentMRP"
        ],
        "summary": "Get The list of all the comments",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/CommentMRP/CreateComment": {
      "post": {
        "tags": [
          "CommentMRP"
        ],
        "requestBody": {
          "content": {
            "application/json-patch+json": {
              "schema": {
                "$ref": "#/components/schemas/MRP_Comment"
              }
            },
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/MRP_Comment"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/MRP_Comment"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/MRP_Comment"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/CommentMRP/UpdateComment({id})": {
      "post": {
        "tags": [
          "CommentMRP"
        ],
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json-patch+json": {
              "schema": {
                "$ref": "#/components/schemas/MRP_Comment"
              }
            },
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/MRP_Comment"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/MRP_Comment"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/MRP_Comment"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/CommentMRP/DeleteComment({id})": {
      "delete": {
        "tags": [
          "CommentMRP"
        ],
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/EmployeeActivity/Get_ActiveEmployee": {
      "get": {
        "tags": [
          "EmployeeActivity"
        ],
        "summary": "Returns all the active employee",
        "parameters": [
          {
            "name": "employeeId",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/EmployeeActivity/Get_GroupSupervisors": {
      "get": {
        "tags": [
          "EmployeeActivity"
        ],
        "summary": "Returns the group's supervisors list",
        "parameters": [
          {
            "name": "group",
            "in": "query",
            "description": "Returns info for this specific group",
            "style": "form",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/EmployeeActivity/Get_EmployeeAttendingActivities": {
      "get": {
        "tags": [
          "EmployeeActivity"
        ],
        "summary": "Returns an employee attending activities for a selected time period",
        "parameters": [
          {
            "name": "employeeId",
            "in": "query",
            "description": "Employee ID selected to get activities for",
            "style": "form",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "startDate",
            "in": "query",
            "description": "Start of the time period to analyze (format: yyyy-MM-dd)",
            "style": "form",
            "schema": {
              "type": "string",
              "format": "date-time"
            }
          },
          {
            "name": "endDate",
            "in": "query",
            "description": "End of the time period to analyze, can be omitted (format: yyyy-MM-dd)",
            "style": "form",
            "schema": {
              "type": "string",
              "format": "date-time"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/EmployeeActivity/Get_EmployeeWorkingActivities": {
      "get": {
        "tags": [
          "EmployeeActivity"
        ],
        "summary": "Returns an employee attending activities for a selected time period",
        "parameters": [
          {
            "name": "employeeId",
            "in": "query",
            "description": "Employee ID selected to get activities for",
            "style": "form",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "startDate",
            "in": "query",
            "description": "Start of the time period to analyze (format: yyyy-MM-dd)",
            "style": "form",
            "schema": {
              "type": "string",
              "format": "date-time"
            }
          },
          {
            "name": "endDate",
            "in": "query",
            "description": "End of the time period to analyze, can be omitted (format: yyyy-MM-dd)",
            "style": "form",
            "schema": {
              "type": "string",
              "format": "date-time"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/KpiMRP/GetKPI_BO": {
      "get": {
        "tags": [
          "KpiMRP"
        ],
        "summary": "Returns the current BO Total Count and value across all Purchase Order and Production Order Requiremements",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/LifeCycleStatistics": {
      "get": {
        "tags": [
          "LifeCycleStatistics"
        ],
        "summary": "Get some statistics for debugging purposes",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/MTConnectInfo/GetMachine_Name": {
      "get": {
        "tags": [
          "MTConnectInfo"
        ],
        "summary": "Returns the name mapping for the mtconnect machine",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/MTConnectInfo/GetMachine_CurrentInfo": {
      "get": {
        "tags": [
          "MTConnectInfo"
        ],
        "summary": "Returns the current info the selected machine",
        "parameters": [
          {
            "name": "machineName",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/RobotizeStatistics/GetStationAndPalletRelatedStatistics": {
      "get": {
        "tags": [
          "RobotizeStatistics"
        ],
        "summary": "Returns the pallet and station statistics",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/RobotizeStatistics/DailyTaskStatistics": {
      "get": {
        "tags": [
          "RobotizeStatistics"
        ],
        "parameters": [
          {
            "name": "beginDate",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string",
              "format": "date-time"
            }
          },
          {
            "name": "endDate",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string",
              "format": "date-time"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/ToolingScheduling/Get_RoutedProgramOnMachine": {
      "get": {
        "tags": [
          "ToolingScheduling"
        ],
        "summary": "Returns all the currently routed programs",
        "parameters": [
          {
            "name": "loadedOnly",
            "in": "query",
            "description": "A boolean parameter that determines if data should be analyzed for program that are only Loaded (Not yet fully routed), False means Loaded and Routed.",
            "style": "form",
            "schema": {
              "type": "boolean",
              "default": false
            }
          },
          {
            "name": "machineId",
            "in": "query",
            "description": "An Integer representing the Machine ID for more specific results.",
            "style": "form",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/ToolingScheduling/Get_CurrentlyMissingToolOnMachine": {
      "get": {
        "tags": [
          "ToolingScheduling"
        ],
        "summary": "Returns all the currently missing required tool based on routed programs on machine",
        "parameters": [
          {
            "name": "loadedOnly",
            "in": "query",
            "description": "A boolean parameter that determines if data should be analyzed for program that are only Loaded (Not yet fully routed), False means Loaded and Routed.",
            "style": "form",
            "schema": {
              "type": "boolean",
              "default": false
            }
          },
          {
            "name": "machineId",
            "in": "query",
            "description": "An Integer representing the Machine ID for more specific results.",
            "style": "form",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/ToolingScheduling/Get_CurrentlyUnusedToolOnMachine": {
      "get": {
        "tags": [
          "ToolingScheduling"
        ],
        "summary": "Returns all the currently unused tool on machine, available for others to grab",
        "parameters": [
          {
            "name": "loadedOnly",
            "in": "query",
            "description": "A boolean parameter that determines if data should be analyzed for program that are only Loaded (Not yet fully routed), False means Loaded and Routed.",
            "style": "form",
            "schema": {
              "type": "boolean",
              "default": false
            }
          },
          {
            "name": "machineId",
            "in": "query",
            "description": "An Integer representing the Machine ID for more specific results.",
            "style": "form",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          },
          {
            "name": "toolId",
            "in": "query",
            "description": "A string representing a specific tool for limited results.",
            "style": "form",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/ToolingScheduling/Get_ToolingKitInformation": {
      "get": {
        "tags": [
          "ToolingScheduling"
        ],
        "summary": "Returns all the know tool kit information with available component location",
        "parameters": [
          {
            "name": "toolId",
            "in": "query",
            "description": "Optional - Filtering value only for this specific tool.",
            "style": "form",
            "schema": {
              "type": "string",
              "default": ""
            }
          },
          {
            "name": "componentId",
            "in": "query",
            "description": "Optional - Filtering value for all tool using this specific componentId.",
            "style": "form",
            "schema": {
              "type": "string",
              "default": ""
            }
          },
          {
            "name": "noManufacturer",
            "in": "query",
            "description": "Optional - Filtering value for all tool using this specific noManufacturer, sometime componentId is not set.",
            "style": "form",
            "schema": {
              "type": "string",
              "default": ""
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/ToolInstanceLocation/Get_ToolInstances": {
      "get": {
        "tags": [
          "ToolInstanceLocation"
        ],
        "summary": "Returns all the known tool instance location across all devices",
        "parameters": [
          {
            "name": "filter",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/ToolInstanceLocation/Get_ToolInstances({toolId})": {
      "get": {
        "tags": [
          "ToolInstanceLocation"
        ],
        "summary": "Returns all the known tool instance location across all devices for a specific toolId",
        "parameters": [
          {
            "name": "toolId",
            "in": "path",
            "description": "A string value for a basic Item filtering functionnality.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/mrp/ToolInstanceLocation/Get_ToolInstanceGrouped": {
      "get": {
        "tags": [
          "ToolInstanceLocation"
        ],
        "summary": "Returns all the known tool instance location across all devices grouped",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "MRP_Comment": {
        "type": "object",
        "properties": {
          "comment": {
            "type": "string",
            "nullable": true
          },
          "assignedToSystemID": {
            "type": "string",
            "nullable": true
          },
          "assignedToItem": {
            "type": "string",
            "nullable": true
          },
          "userName": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      }
    }
  },
  "tags": [
    {
      "name": "AdvancedMRP",
      "description": "AdvancedMRPLogic Endpoint, pre-filtered lists for more targeted queries"
    },
    {
      "name": "BasicMRP",
      "description": "Basic MRP Endpoint Use at your own risk! for pre-filtered lists use the AdvanceMRP Endpoint"
    },
    {
      "name": "CommentMRP",
      "description": "Comment Endpoint"
    },
    {
      "name": "EmployeeActivity",
      "description": "View of all the known location for Tool and relevent information"
    },
    {
      "name": "KpiMRP",
      "description": "MRP KPI Endpoint, relevent KPI associated with the MRP"
    },
    {
      "name": "LifeCycleStatistics",
      "description": "API Statistics"
    },
    {
      "name": "MTConnectInfo",
      "description": "MRP KPI Endpoint, relevent KPI associated with the MRP"
    },
    {
      "name": "RobotizeStatistics",
      "description": "Robotize Statistics Endpoint"
    },
    {
      "name": "ToolingScheduling",
      "description": "View of all the relevent information for the Tooling Schedule required based on CNC machine requirements"
    },
    {
      "name": "ToolInstanceLocation",
      "description": "View of all the known location for Tool and relevent information"
    }
  ]
}