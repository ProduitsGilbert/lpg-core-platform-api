{
  "openapi": "3.1.0",
  "info": {
    "title": "Predictive Analytics API",
    "version": "1.0.0"
  },
  "paths": {
    "/api/v1/achat/models": {
      "get": {
        "tags": [
          "Achats"
        ],
        "summary": "List Models",
        "description": "List available models for this department.\n\nReturns:\n    Dict[str, Any]: Available models and department information",
        "operationId": "list_models_api_v1_achat_models_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response List Models Api V1 Achat Models Get"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/achat/forecast/late-delivery": {
      "post": {
        "tags": [
          "Achats"
        ],
        "summary": "Predict Late Delivery",
        "description": "Predict late delivery risk using live data from SQL database and MRP API.\n\nThis endpoint fetches current purchase order data from the Business Central\nSQL database and enriches it with MRP API data, then applies the XGBoost\nclassifier to predict late delivery risk.\n\nFeatures analyzed include:\n- Live purchase order data from Business Central\n- MRP scheduling data (earliest required dates, expected receipt dates)\n- Vendor performance history from reference data\n- Product categories and lead times\n- Real-time order characteristics\n\nArgs:\n    request: Live data prediction request with configuration options\n\nReturns:\n    LateDeliveryResponse: Predictions with risk assessment for current orders\n\nRaises:\n    HTTPException: If prediction fails or data sources are unavailable",
        "operationId": "predict_late_delivery_api_v1_achat_forecast_late_delivery_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/LiveDataRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/LateDeliveryResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/achat/predict/purchase-order-anomaly": {
      "post": {
        "tags": [
          "Achats"
        ],
        "summary": "Predict Purchase Order Anomaly",
        "description": "Detect anomalies in purchase order lines.\n\nThis endpoint analyzes purchase order characteristics to identify suspicious\nor unusual orders that may require additional review. It uses machine learning\nto detect patterns that deviate from normal purchasing behavior.\n\nFeatures analyzed include:\n- Order quantity and unit cost relationships\n- Vendor-specific patterns\n- Product category patterns\n- Job number patterns\n- Historical ordering patterns\n\nArgs:\n    request: Purchase order anomaly detection request with order details\n\nReturns:\n    PurchaseOrderAnomalyResponse: Anomaly detection results with recommendation\n\nRaises:\n    HTTPException: If anomaly detection fails",
        "operationId": "predict_purchase_order_anomaly_api_v1_achat_predict_purchase_order_anomaly_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PurchaseOrderAnomalyRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PurchaseOrderAnomalyResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/planif/models": {
      "get": {
        "tags": [
          "Planification"
        ],
        "summary": "List Models",
        "description": "List available models for this department.\n\nReturns:\n    Dict[str, Any]: Available models and department information",
        "operationId": "list_models_api_v1_planif_models_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response List Models Api V1 Planif Models Get"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/usinage/models": {
      "get": {
        "tags": [
          "Usinage"
        ],
        "summary": "List Models",
        "description": "List available models for this department.\n\nReturns:\n    Dict[str, Any]: Available models and department information",
        "operationId": "list_models_api_v1_usinage_models_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response List Models Api V1 Usinage Models Get"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/soudure/models": {
      "get": {
        "tags": [
          "Soudure"
        ],
        "summary": "List Models",
        "description": "List available models for this department.\n\nReturns:\n    Dict[str, Any]: Available models and department information",
        "operationId": "list_models_api_v1_soudure_models_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response List Models Api V1 Soudure Models Get"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/finance/models": {
      "get": {
        "tags": [
          "Finance"
        ],
        "summary": "List Models",
        "description": "List available models for this department.\n\nReturns:\n    Dict[str, Any]: Available models and department information",
        "operationId": "list_models_api_v1_finance_models_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response List Models Api V1 Finance Models Get"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/rh/models": {
      "get": {
        "tags": [
          "Ressources Humaines"
        ],
        "summary": "List Models",
        "description": "List available models for this department.\n\nReturns:\n    Dict[str, Any]: Available models and department information",
        "operationId": "list_models_api_v1_rh_models_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response List Models Api V1 Rh Models Get"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/ventes/models": {
      "get": {
        "tags": [
          "Ventes"
        ],
        "summary": "List Models",
        "description": "List available models for this department.\n\nReturns:\n    Dict[str, Any]: Available models and department information",
        "operationId": "list_models_api_v1_ventes_models_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response List Models Api V1 Ventes Models Get"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/achat/forecast/late-delivery": {
      "post": {
        "tags": [
          "API v1.1",
          "Achat v1.1 - Purchase Department"
        ],
        "summary": "Predict Late Delivery V11",
        "description": "Enhanced late delivery prediction for v1.1 with additional analytics.\n\nNew features in v1.1:\n- Vendor performance metrics integration\n- Category-based risk analysis\n- Delivery delay estimation in days\n- Result limiting for performance\n- Enhanced model confidence scoring\n\nArgs:\n    request: Enhanced live data request with v1.1 options\n\nReturns:\n    LateDeliveryResponseV11: Enhanced predictions with vendor and category analytics\n\nRaises:\n    HTTPException: If prediction fails",
        "operationId": "predict_late_delivery_v11_api_v1_1_achat_forecast_late_delivery_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/LiveDataRequestV11"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/LateDeliveryResponseV11"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/achat/predict/purchase-order-delays": {
      "post": {
        "tags": [
          "API v1.1",
          "Achat v1.1 - Purchase Department",
          "Purchase Order Analysis"
        ],
        "summary": "Purchase Order Late Delivery Prediction",
        "description": "**Predict late delivery risk for specific purchase orders**\n\n    This endpoint analyzes individual purchase orders to predict the likelihood of late delivery\n    based on supplier performance, part history, order characteristics, and market conditions.\n\n    **Input Requirements:**\n    - Purchase order document number\n    - Part number and supplier information\n    - Quantity, price, and delivery dates\n    - Optional priority and category information\n\n    **Prediction Features:**\n    - ML-based late delivery probability (0-1)\n    - Risk level classification (low/medium/high/critical)\n    - Estimated delivery delay in days\n    - Vendor performance scoring\n    - Actionable recommendations\n\n    **Use Cases:**\n    - Pre-delivery risk assessment\n    - Supplier performance monitoring\n    - Proactive order management\n    - Supply chain optimization",
        "operationId": "predict_purchase_order_delays_api_v1_1_achat_predict_purchase_order_delays_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PurchaseOrderRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful prediction with risk analysis",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PurchaseOrderResponse"
                },
                "example": {
                  "predictions": [
                    {
                      "document_no": "PO-2025-001234",
                      "item_no": "8406067",
                      "vendor": "SUP001",
                      "predicted_is_late": true,
                      "predicted_probability": 0.73,
                      "risk_level": "high",
                      "delivery_delay_days": 5,
                      "quantity": 100,
                      "cost": 12550
                    }
                  ],
                  "total_orders_analyzed": 1,
                  "late_delivery_predictions": 1,
                  "recommendations": [
                    "Contact supplier SUP001 for delivery confirmation",
                    "Consider expedited shipping for high-risk orders"
                  ]
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/achat/predict/vendor": {
      "post": {
        "tags": [
          "API v1.1",
          "Achat v1.1 - Purchase Department",
          "Vendor Prediction"
        ],
        "summary": "Vendor Prediction for Items",
        "description": "**Predict the most suitable vendor for an item using enhanced hierarchical rules**\n\n    This endpoint uses a sophisticated vendor prediction system with 90% accuracy that combines:\n    - **4-digit patterns** (highest priority): Patterns with ≥80% confidence and ≥5 items\n    - **Vendor specialty keywords**: Domain-specific keyword matching\n    - **3-digit specialty patterns**: Enhanced with vendor specialization scores\n    - **2-digit broad patterns**: Fallback for general classification\n\n    **Vendor Specializations:**\n    - **LAFOU01**: Cutting tools, handles (poignee, vis, outil)\n    - **ALMHY01**: Hydraulic components (raccord, joint, hydraulique)\n    - **BOSRE01**: Linear motion (rail, chariot, série)\n    - **WAJIN01**: Bearings, general (roulement, bearing, bille)\n\n    **Input Requirements:**\n    - Item number (minimum 2 characters)\n    - Item description (minimum 3 characters for keyword matching)\n\n    **Use Cases:**\n    - New item vendor selection\n    - Purchasing optimization\n    - Supplier recommendation\n    - Vendor performance analysis",
        "operationId": "predict_vendor_api_v1_1_achat_predict_vendor_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/VendorPredictionRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful vendor prediction",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/VendorPredictionResponse"
                },
                "example": {
                  "item_no": "0322023",
                  "description": "POIGNEE PLASTIQUE EN T",
                  "predicted_vendor": "LAFOU01",
                  "confidence": 0.678,
                  "rule_type": "keyword_specialty",
                  "details": "Keywords: poignee",
                  "priority": 8,
                  "supporting_items": 193,
                  "success": true
                }
              }
            }
          },
          "404": {
            "description": "No prediction rule found for the item",
            "content": {
              "application/json": {
                "example": {
                  "item_no": "UNKNOWN123",
                  "description": "Unknown item",
                  "confidence": 0,
                  "rule_type": "no_match",
                  "details": "No prediction rule found for this item",
                  "priority": 0,
                  "supporting_items": 0,
                  "success": false
                }
              }
            }
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/achat/predict/vendor/stats": {
      "get": {
        "tags": [
          "API v1.1",
          "Achat v1.1 - Purchase Department",
          "Vendor Prediction"
        ],
        "summary": "Vendor Prediction System Statistics",
        "description": "**Get statistics and capabilities of the vendor prediction system**\n\n    Returns information about:\n    - Total items in training dataset\n    - Number of unique vendors\n    - Rule coverage and types\n    - Supported specialty vendors\n\n    **Use Cases:**\n    - System health monitoring\n    - Understanding prediction coverage\n    - Vendor analysis capabilities",
        "operationId": "get_vendor_prediction_stats_api_v1_1_achat_predict_vendor_stats_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/VendorStatsResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          }
        }
      }
    },
    "/api/v1.1/achat/predict/vendor/vendors": {
      "get": {
        "tags": [
          "API v1.1",
          "Achat v1.1 - Purchase Department",
          "Vendor Prediction"
        ],
        "summary": "Supported Vendors Information",
        "description": "**Get information about vendors with specialized prediction rules**\n\n    Returns detailed information about vendors that have specialized\n    keyword-based prediction rules, including their categories and coverage.",
        "operationId": "get_supported_vendors_api_v1_1_achat_predict_vendor_vendors_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          }
        }
      }
    },
    "/api/v1.1/achat/predict": {
      "post": {
        "tags": [
          "API v1.1",
          "Achat v1.1 - Purchase Department",
          "Standard ML Models"
        ],
        "summary": "General Purchase Predictions",
        "description": "**Standard ML prediction endpoint for the Purchase department**\n\n    Provides general purchasing predictions including:\n    - Cost optimization predictions\n    - Supplier performance forecasts\n    - Purchase volume recommendations\n    - Contract analysis",
        "operationId": "predict_api_v1_1_achat_predict_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PredictionRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PredictionResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/achat/forecast": {
      "post": {
        "tags": [
          "API v1.1",
          "Achat v1.1 - Purchase Department",
          "Standard ML Models"
        ],
        "summary": "Purchase Forecasting",
        "description": "**Purchase volume and cost forecasting**\n\n    Provides forecasting for:\n    - Purchase volume trends\n    - Cost projections\n    - Supplier capacity planning\n    - Budget forecasting",
        "operationId": "forecast_api_v1_1_achat_forecast_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ForecastRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ForecastResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/achat/classify": {
      "post": {
        "tags": [
          "API v1.1",
          "Achat v1.1 - Purchase Department",
          "Standard ML Models"
        ],
        "summary": "Purchase Classification",
        "description": "**Purchase data classification and categorization**\n\n    Provides classification for:\n    - Supplier category classification\n    - Purchase priority assessment\n    - Contract type identification\n    - Risk level categorization",
        "operationId": "classify_api_v1_1_achat_classify_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ClassificationRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ClassificationResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/achat/predict/lead-time": {
      "post": {
        "tags": [
          "API v1.1",
          "Achat v1.1 - Purchase Department",
          "Item Predictions"
        ],
        "summary": "Predict Item Lead Time",
        "description": "**Predict lead time for purchased items**\n\n    Provides lead time predictions based on:\n    - Item number patterns\n    - Vendor relationships\n    - Category mappings\n    - Historical data patterns\n    \n    Uses hybrid approach combining rules-based and ML models for optimal accuracy.",
        "operationId": "predict_lead_time_api_v1_1_achat_predict_lead_time_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ItemPredictionRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ItemPredictionResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/achat/predict/item-category": {
      "post": {
        "tags": [
          "API v1.1",
          "Achat v1.1 - Purchase Department",
          "Item Predictions"
        ],
        "summary": "Predict Item Category",
        "description": "**Predict item category code for purchased items**\n\n    Provides category predictions based on:\n    - Item number patterns\n    - Vendor specializations\n    - Keyword matching\n    - Description analysis\n    \n    Uses hybrid approach with rules and ML models for high accuracy predictions.",
        "operationId": "predict_item_category_api_v1_1_achat_predict_item_category_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ItemPredictionRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ItemPredictionResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/achat/predict/item-both": {
      "post": {
        "tags": [
          "API v1.1",
          "Achat v1.1 - Purchase Department",
          "Item Predictions"
        ],
        "summary": "Predict Both Lead Time and Category",
        "description": "**Predict both lead time and category for purchased items**\n\n    Provides both predictions in a single call:\n    - Lead time prediction\n    - Item category prediction\n    \n    More efficient than calling both endpoints separately.",
        "operationId": "predict_both_api_v1_1_achat_predict_item_both_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ItemPredictionRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/BothPredictionsResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/achat/health": {
      "get": {
        "tags": [
          "API v1.1",
          "Achat v1.1 - Purchase Department"
        ],
        "summary": "Achat API Health Check",
        "description": "Check health status of the Achat v1.1 API",
        "operationId": "health_check_api_v1_1_achat_health_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Health Check Api V1 1 Achat Health Get"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          }
        }
      }
    },
    "/api/v1.1/usinage/predict/tool-risks": {
      "post": {
        "tags": [
          "API v1.1",
          "Usinage v1.1 - Machining Department"
        ],
        "summary": "Predict Tool Shortage and Breakage Risks",
        "description": "**Advanced tool risk prediction using machine learning models (87.8% accuracy)**\n\n    Analyzes a part number and predicts which tools might suffer from shortage or breakage\n    during the planned production period using trained RandomForest models.\n\n    **Key Features:**\n    - 🔍 **Pattern Matching**: Automatically finds all part variants (e.g., 8406067 → 8406067-1OP, 8406067-2OP)\n    - 🤖 **ML Prediction**: RandomForest model with 87.8% accuracy and F1-score of 92.9%\n    - 📊 **Risk Classification**: Categorizes tools as low/medium/high/critical risk\n    - ⚡ **Real-time Integration**: Connects to Fastems 1 & 2 systems for live tool data\n    - 📈 **Production Planning**: Integrates production schedules and quantities\n    - 💡 **Actionable Insights**: Provides specific recommendations for risk mitigation\n\n    **Use Cases:**\n    - Production planning and scheduling\n    - Preventive maintenance scheduling\n    - Inventory management optimization\n    - Risk assessment for critical parts",
        "operationId": "predict_tool_risks_api_v1_1_usinage_predict_tool_risks_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PartToolRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful prediction with tool risk analysis",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PartToolResponse"
                },
                "example": {
                  "part_number": "8406067",
                  "total_tools_analyzed": 1979,
                  "high_risk_tools": 15,
                  "critical_risk_tools": 3,
                  "tool_predictions": [
                    {
                      "tool_id": "1666",
                      "tool_name": "006-001 DMC-100",
                      "shortage_probability": 0.73,
                      "risk_level": "high",
                      "risk_factors": [
                        "High shortage risk: 73.0%",
                        "Stock below recommended level"
                      ]
                    }
                  ],
                  "recommendations": [
                    "URGENT: 3 tools require immediate attention",
                    "Schedule procurement for 15 high-risk tools"
                  ]
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Part number or tools not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid input parameters"
          },
          "503": {
            "description": "Service Unavailable - Fastems API unavailable"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/usinage/predict/tool-risks-enhanced": {
      "post": {
        "tags": [
          "API v1.1",
          "Usinage v1.1 - Machining Department"
        ],
        "summary": "Enhanced Tool Risk Prediction with Inventory Integration",
        "description": "**🚀 ENHANCED tool risk prediction with real-time inventory integration (v2.0)**\n\n    Advanced tool shortage prediction that integrates with Gilbert Tech inventory API\n    for real-time tool instance tracking and backup availability analysis.\n\n    **Enhanced Features:**\n    - 📦 **Real-time Inventory**: Integrates with Gilbert Tech API for live tool instance data\n    - 🔄 **Multi-instance Tracking**: Tracks all instances of same tool across machines\n    - 📊 **Backup Availability**: Considers backup tools in inventory vs. in-use\n    - 🎯 **Inventory-aware Risk**: Adjusts predictions based on backup availability\n    - 📍 **Location Tracking**: Distinguishes between tools on machines vs. in storage\n    - 💡 **Smart Recommendations**: Provides inventory-aware recommendations\n\n    **Key Improvements over Basic Prediction:**\n    - More accurate predictions by considering tool backup availability\n    - Earlier warnings for tools with no backup inventory\n    - Reduced false positives when backup tools are available\n    - Proactive inventory management recommendations\n\n    **Use Cases:**\n    - Advanced production planning with inventory awareness\n    - Smart tool procurement decisions\n    - Risk-based inventory optimization\n    - Preventive tool management",
        "operationId": "predict_tool_risks_enhanced_api_v1_1_usinage_predict_tool_risks_enhanced_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PartToolRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful enhanced prediction with inventory analysis",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PartToolResponse"
                },
                "example": {
                  "part_number": "8406067",
                  "total_tools_analyzed": 1979,
                  "high_risk_tools": 12,
                  "critical_risk_tools": 2,
                  "tool_predictions": [
                    {
                      "tool_id": "1009",
                      "tool_name": "006-001 DMC-100",
                      "shortage_probability": 0.35,
                      "risk_level": "medium",
                      "current_stock": 1,
                      "recommended_action": "⚡ MEDIUM RISK: Plan replacement soon",
                      "confidence_score": 0.65
                    }
                  ],
                  "metadata": {
                    "model_version": "enhanced_v2.0",
                    "features_used": "inventory_integrated",
                    "api_sources": [
                      "fastems",
                      "gilbert_tech_inventory"
                    ]
                  }
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Part number or tools not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid input parameters"
          },
          "503": {
            "description": "Service Unavailable - Fastems API unavailable"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/usinage/tools/list": {
      "post": {
        "tags": [
          "API v1.1",
          "Usinage v1.1 - Machining Department"
        ],
        "summary": "Get Required Tools for Part Number",
        "description": "**Retrieve comprehensive tool lists with pattern matching**\n\n    Fetches all tools required for a specific part number with enhanced pattern matching\n    that automatically discovers all related programs and operations.\n\n    **Features:**\n    - 🔍 **Smart Pattern Matching**: Finds all part variants automatically\n    - 🔗 **Dual System Integration**: Searches both Fastems 1 & 2 systems\n    - 📋 **Complete Tool Specs**: Includes specifications, stock levels, and costs\n    - 📊 **Tool Categorization**: Groups tools by type and operation\n    - ⚡ **Real-time Data**: Live integration with production systems\n\n    **Perfect for:**\n    - Production setup planning\n    - Tool inventory verification\n    - Cost estimation and budgeting\n    - Process documentation",
        "operationId": "get_tool_list_api_v1_1_usinage_tools_list_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ToolListRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Tool list retrieved successfully",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ToolListResponse"
                },
                "example": {
                  "part_number": "8406067",
                  "total_tools": 1979,
                  "tool_categories": {
                    "cutting_tool": 1200,
                    "drill": 450,
                    "mill": 329
                  },
                  "required_tools": [
                    {
                      "tool_id": "1666",
                      "tool_name": "006-001 DMC-100",
                      "tool_type": "cutting_tool",
                      "current_stock": 10,
                      "recommended_stock": 15
                    }
                  ]
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Part number or tools not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid input parameters"
          },
          "503": {
            "description": "Service Unavailable - Fastems API unavailable"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/usinage/test": {
      "get": {
        "tags": [
          "API v1.1",
          "Usinage v1.1 - Machining Department"
        ],
        "summary": "Test Endpoint",
        "description": "Simple test endpoint.",
        "operationId": "test_endpoint_api_v1_1_usinage_test_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "additionalProperties": {
                    "type": "string"
                  },
                  "type": "object",
                  "title": "Response Test Endpoint Api V1 1 Usinage Test Get"
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Part number or tools not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid input parameters"
          },
          "503": {
            "description": "Service Unavailable - Fastems API unavailable"
          }
        }
      }
    },
    "/api/v1.1/usinage/predict": {
      "post": {
        "tags": [
          "API v1.1",
          "Usinage v1.1 - Machining Department",
          "Standard ML Models"
        ],
        "summary": "General Machine Learning Predictions",
        "description": "**Standard ML prediction endpoint for the Usinage department**\n\n    Provides general machine learning predictions for machining operations including:\n    - Quality predictions\n    - Performance forecasts\n    - Process optimization\n    - Equipment reliability\n\n    **Enhanced v1.1 Features:**\n    - Confidence scores included\n    - Multiple model support\n    - Batch processing up to 1000 items\n    - Enhanced validation and error handling",
        "operationId": "predict_api_v1_1_usinage_predict_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PredictionRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PredictionResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Part number or tools not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid input parameters"
          },
          "503": {
            "description": "Service Unavailable - Fastems API unavailable"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/usinage/forecast": {
      "post": {
        "tags": [
          "API v1.1",
          "Usinage v1.1 - Machining Department",
          "Standard ML Models"
        ],
        "summary": "Time Series Forecasting",
        "description": "**Advanced time series forecasting for machining operations**\n\n    Provides forecasting capabilities for:\n    - Production volume predictions\n    - Machine utilization forecasts\n    - Maintenance scheduling\n    - Resource planning\n\n    **Enhanced v1.1 Features:**\n    - Confidence intervals\n    - Seasonal pattern detection\n    - Multiple forecasting models\n    - Accuracy metrics included",
        "operationId": "forecast_api_v1_1_usinage_forecast_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ForecastRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ForecastResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Part number or tools not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid input parameters"
          },
          "503": {
            "description": "Service Unavailable - Fastems API unavailable"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/usinage/classify": {
      "post": {
        "tags": [
          "API v1.1",
          "Usinage v1.1 - Machining Department",
          "Standard ML Models"
        ],
        "summary": "Classification and Categorization",
        "description": "**Advanced classification for machining operations**\n\n    Provides classification capabilities for:\n    - Quality grade classification\n    - Problem category identification\n    - Process type classification\n    - Material categorization\n\n    **Enhanced v1.1 Features:**\n    - Multi-class probabilities\n    - Top-K class predictions\n    - Confidence scoring\n    - Enhanced class information",
        "operationId": "classify_api_v1_1_usinage_classify_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ClassificationRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ClassificationResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Part number or tools not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid input parameters"
          },
          "503": {
            "description": "Service Unavailable - Fastems API unavailable"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/usinage/benchmark": {
      "get": {
        "tags": [
          "API v1.1",
          "Usinage v1.1 - Machining Department",
          "Performance Testing"
        ],
        "summary": "Performance Benchmark",
        "description": "**🚀 Performance benchmark for vectorized batch processing**\n\n    Test the performance improvements of the optimized tool prediction system.\n    This endpoint generates synthetic tools and measures processing performance\n    to demonstrate the 10-100x speed improvement from vectorized batch processing.\n\n    **Performance Expectations:**\n    - 10 tools: ~10x faster than individual processing\n    - 100 tools: ~50x faster than individual processing\n    - 500 tools: ~125x faster than individual processing\n\n    **Query Parameters:**\n    - `n_tools`: Number of tools to simulate (default: 100, max: 500)",
        "operationId": "benchmark_performance_api_v1_1_usinage_benchmark_get",
        "parameters": [
          {
            "name": "n_tools",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "default": 100,
              "title": "N Tools"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Benchmark results with performance metrics",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Benchmark Performance Api V1 1 Usinage Benchmark Get"
                },
                "example": {
                  "benchmark_results": {
                    "n_tools": 100,
                    "processing_time_seconds": 0.15,
                    "optimization_used": "VECTORIZED_BATCH_PROCESSING",
                    "estimated_individual_time": 7.5,
                    "performance_improvement": "50x faster"
                  }
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Part number or tools not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid input parameters"
          },
          "503": {
            "description": "Service Unavailable - Fastems API unavailable"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/usinage/health": {
      "get": {
        "tags": [
          "API v1.1",
          "Usinage v1.1 - Machining Department"
        ],
        "summary": "Health Check",
        "description": "Check the health status of the Usinage v1.1 API with optimization info",
        "operationId": "health_check_api_v1_1_usinage_health_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Health Check Api V1 1 Usinage Health Get"
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Part number or tools not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid input parameters"
          },
          "503": {
            "description": "Service Unavailable - Fastems API unavailable"
          }
        }
      }
    },
    "/api/v1.1/finance/predict": {
      "post": {
        "tags": [
          "API v1.1",
          "Finance v1.1 - Financial Analytics",
          "Finance ML Models"
        ],
        "summary": "Financial Predictions",
        "description": "**Advanced financial predictions and analytics**\n\n    Provides ML-based predictions for:\n    - Revenue and sales predictions\n    - Cost analysis and optimization\n    - Profitability forecasts\n    - Investment returns\n\n    **Enhanced v1.1 Features:**\n    - Financial confidence scoring\n    - Risk-adjusted predictions\n    - Multi-scenario analysis\n    - Enhanced financial validation",
        "operationId": "predict_api_v1_1_finance_predict_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PredictionRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PredictionResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Financial data not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid financial parameters"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/finance/forecast": {
      "post": {
        "tags": [
          "API v1.1",
          "Finance v1.1 - Financial Analytics",
          "Finance ML Models"
        ],
        "summary": "Financial Forecasting",
        "description": "**Advanced financial time series forecasting**\n\n    Provides forecasting for:\n    - Revenue and cash flow forecasts\n    - Budget planning and variance analysis\n    - Seasonal financial patterns\n    - Financial trend analysis\n\n    **Features:**\n    - Confidence intervals for financial planning\n    - Seasonal pattern detection\n    - Risk-adjusted forecasting\n    - Multiple financial scenarios",
        "operationId": "forecast_api_v1_1_finance_forecast_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ForecastRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ForecastResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Financial data not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid financial parameters"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/finance/classify": {
      "post": {
        "tags": [
          "API v1.1",
          "Finance v1.1 - Financial Analytics",
          "Finance ML Models"
        ],
        "summary": "Financial Classification",
        "description": "**Financial data classification and categorization**\n\n    Provides classification for:\n    - Expense category classification\n    - Risk level assessment\n    - Transaction type identification\n    - Financial priority scoring\n\n    **Features:**\n    - Multi-class financial categories\n    - Risk-based classification\n    - Compliance categorization\n    - Financial priority ranking",
        "operationId": "classify_api_v1_1_finance_classify_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ClassificationRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ClassificationResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Financial data not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid financial parameters"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/finance/health": {
      "get": {
        "tags": [
          "API v1.1",
          "Finance v1.1 - Financial Analytics"
        ],
        "summary": "Finance API Health Check",
        "description": "Check health status of the Finance v1.1 API",
        "operationId": "health_check_api_v1_1_finance_health_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Health Check Api V1 1 Finance Health Get"
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Financial data not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid financial parameters"
          }
        }
      }
    },
    "/api/v1.1/planif/predict": {
      "post": {
        "tags": [
          "API v1.1",
          "Planif v1.1 - Production Planning",
          "Planning ML Models"
        ],
        "summary": "Production Planning Predictions",
        "description": "**Advanced production planning predictions**\n\n    Provides ML-based predictions for:\n    - Production capacity requirements\n    - Resource allocation optimization\n    - Bottleneck identification\n    - Delivery timeline predictions\n\n    **Enhanced v1.1 Features:**\n    - Multi-resource planning\n    - Constraint optimization\n    - Real-time scheduling\n    - Capacity utilization analysis",
        "operationId": "predict_api_v1_1_planif_predict_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PredictionRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PredictionResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Planning data not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid planning parameters"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/planif/forecast": {
      "post": {
        "tags": [
          "API v1.1",
          "Planif v1.1 - Production Planning",
          "Planning ML Models"
        ],
        "summary": "Production Planning Forecasting",
        "description": "**Production planning and capacity forecasting**\n\n    Provides forecasting for:\n    - Production capacity planning\n    - Workload distribution\n    - Resource demand forecasting\n    - Schedule optimization",
        "operationId": "forecast_api_v1_1_planif_forecast_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ForecastRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ForecastResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Planning data not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid planning parameters"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/planif/classify": {
      "post": {
        "tags": [
          "API v1.1",
          "Planif v1.1 - Production Planning",
          "Planning ML Models"
        ],
        "summary": "Planning Classification",
        "description": "**Production planning classification and prioritization**\n\n    Provides classification for:\n    - Priority level classification\n    - Resource type identification\n    - Schedule complexity assessment\n    - Bottleneck categorization",
        "operationId": "classify_api_v1_1_planif_classify_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ClassificationRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ClassificationResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Planning data not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid planning parameters"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/planif/health": {
      "get": {
        "tags": [
          "API v1.1",
          "Planif v1.1 - Production Planning"
        ],
        "summary": "Planning API Health Check",
        "description": "Check health status of the Planning v1.1 API",
        "operationId": "health_check_api_v1_1_planif_health_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Health Check Api V1 1 Planif Health Get"
                }
              }
            }
          },
          "404": {
            "description": "Not Found - Planning data not found"
          },
          "500": {
            "description": "Internal Server Error - Processing failed"
          },
          "400": {
            "description": "Bad Request - Invalid planning parameters"
          }
        }
      }
    },
    "/api/v1.1/soudure/predict": {
      "post": {
        "tags": [
          "API v1.1",
          "Soudure v1.1 - Welding Operations",
          "Welding ML Models"
        ],
        "summary": "Welding Quality Predictions",
        "description": "Predict welding quality and defects.",
        "operationId": "predict_api_v1_1_soudure_predict_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PredictionRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PredictionResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/soudure/forecast": {
      "post": {
        "tags": [
          "API v1.1",
          "Soudure v1.1 - Welding Operations",
          "Welding ML Models"
        ],
        "summary": "Welding Operations Forecasting",
        "description": "Forecast welding operations and maintenance.",
        "operationId": "forecast_api_v1_1_soudure_forecast_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ForecastRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ForecastResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/soudure/classify": {
      "post": {
        "tags": [
          "API v1.1",
          "Soudure v1.1 - Welding Operations",
          "Welding ML Models"
        ],
        "summary": "Welding Classification",
        "description": "Classify welding types and quality grades.",
        "operationId": "classify_api_v1_1_soudure_classify_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ClassificationRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ClassificationResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/soudure/health": {
      "get": {
        "tags": [
          "API v1.1",
          "Soudure v1.1 - Welding Operations"
        ],
        "summary": "Health Check",
        "operationId": "health_check_api_v1_1_soudure_health_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Health Check Api V1 1 Soudure Health Get"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          }
        }
      }
    },
    "/api/v1.1/rh/predict": {
      "post": {
        "tags": [
          "API v1.1",
          "RH v1.1 - Human Resources",
          "HR ML Models"
        ],
        "summary": "HR Analytics Predictions",
        "description": "Predict HR metrics and workforce analytics.",
        "operationId": "predict_api_v1_1_rh_predict_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PredictionRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PredictionResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/rh/forecast": {
      "post": {
        "tags": [
          "API v1.1",
          "RH v1.1 - Human Resources",
          "HR ML Models"
        ],
        "summary": "Workforce Forecasting",
        "description": "Forecast workforce needs and HR metrics.",
        "operationId": "forecast_api_v1_1_rh_forecast_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ForecastRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ForecastResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/rh/classify": {
      "post": {
        "tags": [
          "API v1.1",
          "RH v1.1 - Human Resources",
          "HR ML Models"
        ],
        "summary": "HR Classification",
        "description": "Classify HR data and employee categories.",
        "operationId": "classify_api_v1_1_rh_classify_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ClassificationRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ClassificationResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/rh/health": {
      "get": {
        "tags": [
          "API v1.1",
          "RH v1.1 - Human Resources"
        ],
        "summary": "Health Check",
        "operationId": "health_check_api_v1_1_rh_health_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Health Check Api V1 1 Rh Health Get"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          }
        }
      }
    },
    "/api/v1.1/ventes/predict": {
      "post": {
        "tags": [
          "API v1.1",
          "Ventes v1.1 - Sales Analytics",
          "Sales ML Models"
        ],
        "summary": "Sales Predictions",
        "description": "Predict sales performance and opportunities.",
        "operationId": "predict_api_v1_1_ventes_predict_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PredictionRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PredictionResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/ventes/forecast": {
      "post": {
        "tags": [
          "API v1.1",
          "Ventes v1.1 - Sales Analytics",
          "Sales ML Models"
        ],
        "summary": "Sales Forecasting",
        "description": "Forecast sales revenue and trends.",
        "operationId": "forecast_api_v1_1_ventes_forecast_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ForecastRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ForecastResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/ventes/classify": {
      "post": {
        "tags": [
          "API v1.1",
          "Ventes v1.1 - Sales Analytics",
          "Sales ML Models"
        ],
        "summary": "Sales Classification",
        "description": "Classify sales leads and opportunities.",
        "operationId": "classify_api_v1_1_ventes_classify_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ClassificationRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ClassificationResponse"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1.1/ventes/health": {
      "get": {
        "tags": [
          "API v1.1",
          "Ventes v1.1 - Sales Analytics"
        ],
        "summary": "Health Check",
        "operationId": "health_check_api_v1_1_ventes_health_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Health Check Api V1 1 Ventes Health Get"
                }
              }
            }
          },
          "404": {
            "description": "Not found"
          },
          "500": {
            "description": "Internal server error"
          }
        }
      }
    },
    "/": {
      "get": {
        "summary": "Root",
        "description": "Root endpoint providing API information.\n\nReturns:\n    Dict[str, Any]: API information",
        "operationId": "root__get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Root  Get"
                }
              }
            }
          }
        }
      }
    },
    "/health": {
      "get": {
        "summary": "Health Check",
        "description": "Health check endpoint for monitoring.\n\nReturns:\n    Dict[str, str]: Health status",
        "operationId": "health_check_health_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "additionalProperties": {
                    "type": "string"
                  },
                  "type": "object",
                  "title": "Response Health Check Health Get"
                }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "BothPredictionsResponse": {
        "properties": {
          "lead_time": {
            "$ref": "#/components/schemas/ItemPredictionResponse",
            "description": "Lead time prediction"
          },
          "category": {
            "$ref": "#/components/schemas/ItemPredictionResponse",
            "description": "Category prediction"
          }
        },
        "type": "object",
        "required": [
          "lead_time",
          "category"
        ],
        "title": "BothPredictionsResponse",
        "description": "Response model for both lead time and category predictions.",
        "examples": [
          {
            "category": {
              "confidence": 0.92,
              "details": {
                "description_length": 24,
                "item_no": "T14000123",
                "vendor": "ALMHY01"
              },
              "method": "4-digit pattern",
              "prediction": "EQMOU",
              "timestamp": "2025-01-15T10:30:00"
            },
            "lead_time": {
              "confidence": 0.85,
              "details": {
                "category": "EQMOU",
                "item_no": "T14000123",
                "vendor": "ALMHY01"
              },
              "method": "vendor pattern",
              "prediction": "2W",
              "timestamp": "2025-01-15T10:30:00"
            }
          }
        ]
      },
      "ClassificationRequest": {
        "properties": {
          "data": {
            "items": {
              "type": "object"
            },
            "type": "array",
            "maxItems": 1000,
            "minItems": 1,
            "title": "Data",
            "description": "Input data for classification"
          },
          "model_name": {
            "type": "string",
            "title": "Model Name",
            "description": "Name of the classification model to use",
            "default": "default",
            "examples": [
              "default",
              "multi_class",
              "binary"
            ]
          },
          "parameters": {
            "type": "object",
            "title": "Parameters",
            "description": "Additional parameters for classification"
          },
          "return_probabilities": {
            "type": "boolean",
            "title": "Return Probabilities",
            "description": "Return class probabilities in addition to predictions",
            "default": true
          },
          "top_k_classes": {
            "type": "integer",
            "maximum": 10,
            "minimum": 1,
            "title": "Top K Classes",
            "description": "Number of top predicted classes to return",
            "default": 1
          }
        },
        "type": "object",
        "required": [
          "data"
        ],
        "title": "ClassificationRequest",
        "description": "Enhanced classification request model for v1.1.\n\nIncludes multi-class support and probability outputs.",
        "examples": [
          {
            "data": [
              {
                "feature1": 42,
                "text": "sample input"
              }
            ],
            "model_name": "multi_class",
            "return_probabilities": true,
            "top_k_classes": 3
          }
        ]
      },
      "ClassificationResponse": {
        "properties": {
          "classifications": {
            "items": {
              "type": "object"
            },
            "type": "array",
            "title": "Classifications",
            "description": "List of classification results with probabilities"
          },
          "model_name": {
            "type": "string",
            "title": "Model Name",
            "description": "Name of the model used for classification"
          },
          "department": {
            "type": "string",
            "title": "Department",
            "description": "Department that processed the request"
          },
          "class_probabilities": {
            "items": {
              "additionalProperties": {
                "type": "number"
              },
              "type": "object"
            },
            "type": "array",
            "title": "Class Probabilities",
            "description": "Probability scores for each class"
          },
          "confidence_scores": {
            "items": {
              "type": "number"
            },
            "type": "array",
            "title": "Confidence Scores",
            "description": "Overall confidence for each classification (0-1)"
          },
          "model_version": {
            "type": "string",
            "title": "Model Version",
            "description": "Version of the classification model",
            "default": "1.1"
          },
          "class_names": {
            "items": {
              "type": "string"
            },
            "type": "array",
            "title": "Class Names",
            "description": "Names of all possible classes"
          },
          "processing_time": {
            "type": "number",
            "title": "Processing Time",
            "description": "Processing time in seconds",
            "default": 0
          },
          "metadata": {
            "type": "object",
            "title": "Metadata",
            "description": "Enhanced metadata about the classification"
          }
        },
        "type": "object",
        "required": [
          "classifications",
          "model_name",
          "department"
        ],
        "title": "ClassificationResponse",
        "description": "Enhanced classification response model for v1.1.\n\nIncludes class probabilities and confidence information."
      },
      "ForecastRequest": {
        "properties": {
          "historical_data": {
            "items": {
              "type": "object"
            },
            "type": "array",
            "maxItems": 10000,
            "minItems": 2,
            "title": "Historical Data",
            "description": "Historical data for forecasting (enhanced format)"
          },
          "horizon": {
            "type": "integer",
            "maximum": 365,
            "minimum": 1,
            "title": "Horizon",
            "description": "Number of periods to forecast"
          },
          "model_name": {
            "type": "string",
            "title": "Model Name",
            "description": "Name of the forecasting model to use",
            "default": "default",
            "examples": [
              "default",
              "seasonal",
              "ml_forecast"
            ]
          },
          "parameters": {
            "type": "object",
            "title": "Parameters",
            "description": "Additional parameters for the forecast"
          },
          "include_intervals": {
            "type": "boolean",
            "title": "Include Intervals",
            "description": "Include confidence intervals in forecast",
            "default": true
          },
          "seasonal_pattern": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Seasonal Pattern",
            "description": "Seasonal pattern detection (auto, weekly, monthly, yearly)",
            "examples": [
              "auto",
              "weekly",
              "monthly",
              "yearly"
            ]
          }
        },
        "type": "object",
        "required": [
          "historical_data",
          "horizon"
        ],
        "title": "ForecastRequest",
        "description": "Enhanced forecasting request model for v1.1.\n\nIncludes improved validation and seasonal handling.",
        "examples": [
          {
            "historical_data": [
              {
                "date": "2024-01-01",
                "value": 100
              },
              {
                "date": "2024-01-02",
                "value": 105
              }
            ],
            "horizon": 30,
            "include_intervals": true,
            "model_name": "seasonal",
            "seasonal_pattern": "auto"
          }
        ]
      },
      "ForecastResponse": {
        "properties": {
          "forecasts": {
            "items": {
              "type": "object"
            },
            "type": "array",
            "title": "Forecasts",
            "description": "List of forecasted values with enhanced information"
          },
          "model_name": {
            "type": "string",
            "title": "Model Name",
            "description": "Name of the model used for forecasting"
          },
          "department": {
            "type": "string",
            "title": "Department",
            "description": "Department that processed the request"
          },
          "confidence_intervals": {
            "items": {
              "additionalProperties": {
                "type": "number"
              },
              "type": "object"
            },
            "type": "array",
            "title": "Confidence Intervals",
            "description": "Confidence intervals for each forecast period"
          },
          "seasonal_info": {
            "type": "object",
            "title": "Seasonal Info",
            "description": "Information about detected seasonal patterns"
          },
          "model_version": {
            "type": "string",
            "title": "Model Version",
            "description": "Version of the forecasting model",
            "default": "1.1"
          },
          "accuracy_metrics": {
            "additionalProperties": {
              "type": "number"
            },
            "type": "object",
            "title": "Accuracy Metrics",
            "description": "Model accuracy metrics on validation data"
          },
          "processing_time": {
            "type": "number",
            "title": "Processing Time",
            "description": "Processing time in seconds",
            "default": 0
          },
          "metadata": {
            "type": "object",
            "title": "Metadata",
            "description": "Enhanced metadata about the forecast"
          }
        },
        "type": "object",
        "required": [
          "forecasts",
          "model_name",
          "department"
        ],
        "title": "ForecastResponse",
        "description": "Enhanced forecasting response model for v1.1.\n\nIncludes confidence intervals and improved metadata."
      },
      "HTTPValidationError": {
        "properties": {
          "detail": {
            "items": {
              "$ref": "#/components/schemas/ValidationError"
            },
            "type": "array",
            "title": "Detail"
          }
        },
        "type": "object",
        "title": "HTTPValidationError"
      },
      "ItemPredictionRequest": {
        "properties": {
          "item_no": {
            "type": "string",
            "title": "Item No",
            "description": "Item number",
            "examples": [
              "T14000123",
              "8406067"
            ]
          },
          "description": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Description",
            "description": "Item description",
            "examples": [
              "STEEL PLATE 100X200X10MM",
              "BEARING BALL"
            ]
          },
          "vendor_no": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Vendor No",
            "description": "Vendor number",
            "examples": [
              "ALMHY01",
              "SUP001"
            ]
          },
          "inventory_group": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Inventory Group",
            "description": "Inventory posting group",
            "examples": [
              "MAT",
              "TOOLS"
            ]
          },
          "last_direct_cost": {
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "null"
              }
            ],
            "title": "Last Direct Cost",
            "description": "Last direct cost",
            "examples": [125.5, 45]
          },
          "item_category_code": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Item Category Code",
            "description": "Item category code (for lead time prediction)",
            "examples": [
              "EQMOU",
              "DIVERS"
            ]
          }
        },
        "type": "object",
        "required": [
          "item_no"
        ],
        "title": "ItemPredictionRequest",
        "description": "Request model for item predictions (lead time and category).",
        "examples": [
          {
            "description": "STEEL PLATE 100X200X10MM",
            "inventory_group": "MAT",
            "item_category_code": "EQMOU",
            "item_no": "T14000123",
            "last_direct_cost": 125.5,
            "vendor_no": "ALMHY01"
          }
        ]
      },
      "ItemPredictionResponse": {
        "properties": {
          "prediction": {
            "type": "string",
            "title": "Prediction",
            "description": "Predicted value (lead time or category)"
          },
          "confidence": {
            "type": "number",
            "maximum": 1,
            "minimum": 0,
            "title": "Confidence",
            "description": "Prediction confidence (0-1)"
          },
          "method": {
            "type": "string",
            "title": "Method",
            "description": "Method used for prediction"
          },
          "timestamp": {
            "type": "string",
            "title": "Timestamp",
            "description": "Timestamp of prediction"
          },
          "details": {
            "anyOf": [
              {
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "title": "Details",
            "description": "Additional details about the prediction"
          }
        },
        "type": "object",
        "required": [
          "prediction",
          "confidence",
          "method",
          "timestamp"
        ],
        "title": "ItemPredictionResponse",
        "description": "Response model for item predictions.",
        "examples": [
          {
            "confidence": 0.85,
            "details": {
              "category": "EQMOU",
              "item_no": "T14000123",
              "vendor": "ALMHY01"
            },
            "method": "4-digit pattern",
            "prediction": "2W",
            "timestamp": "2025-01-15T10:30:00"
          }
        ]
      },
      "LateDeliveryPrediction": {
        "properties": {
          "document_no": {
            "type": "string",
            "title": "Document No",
            "description": "Purchase order document number"
          },
          "item_no": {
            "type": "string",
            "title": "Item No",
            "description": "Item number"
          },
          "description": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Description",
            "description": "Item description"
          },
          "vendor": {
            "type": "string",
            "title": "Vendor",
            "description": "Vendor name"
          },
          "predicted_is_late": {
            "type": "boolean",
            "title": "Predicted Is Late",
            "description": "Whether delivery is predicted to be late"
          },
          "predicted_probability": {
            "type": "number",
            "maximum": 1,
            "minimum": 0,
            "title": "Predicted Probability",
            "description": "Probability of late delivery"
          },
          "order_date": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Order Date",
            "description": "Order date"
          },
          "required_delivery": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Required Delivery",
            "description": "Required delivery date"
          },
          "cost": {
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "null"
              }
            ],
            "title": "Cost",
            "description": "Order cost"
          },
          "quantity": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Quantity",
            "description": "Order quantity"
          },
          "risk_level": {
            "type": "string",
            "pattern": "^(low|medium|high|critical)$",
            "title": "Risk Level",
            "description": "Risk level based on probability"
          }
        },
        "type": "object",
        "required": [
          "document_no",
          "item_no",
          "vendor",
          "predicted_is_late",
          "predicted_probability",
          "risk_level"
        ],
        "title": "LateDeliveryPrediction",
        "description": "Individual late delivery prediction result."
      },
      "LateDeliveryPredictionV11": {
        "properties": {
          "document_no": {
            "type": "string",
            "title": "Document No"
          },
          "item_no": {
            "type": "string",
            "title": "Item No"
          },
          "description": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "vendor": {
            "type": "string",
            "title": "Vendor"
          },
          "predicted_is_late": {
            "type": "boolean",
            "title": "Predicted Is Late"
          },
          "predicted_probability": {
            "type": "number",
            "maximum": 1,
            "minimum": 0,
            "title": "Predicted Probability"
          },
          "order_date": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Order Date"
          },
          "required_delivery": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Required Delivery"
          },
          "expected_receipt_date": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Expected Receipt Date"
          },
          "cost": {
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "null"
              }
            ],
            "title": "Cost"
          },
          "quantity": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Quantity"
          },
          "risk_level": {
            "type": "string",
            "pattern": "^(low|medium|high|critical)$",
            "title": "Risk Level"
          },
          "delivery_delay_days": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Delivery Delay Days"
          },
          "vendor_performance_score": {
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "null"
              }
            ],
            "title": "Vendor Performance Score"
          },
          "category_risk_score": {
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "null"
              }
            ],
            "title": "Category Risk Score"
          }
        },
        "type": "object",
        "required": [
          "document_no",
          "item_no",
          "vendor",
          "predicted_is_late",
          "predicted_probability",
          "risk_level"
        ],
        "title": "LateDeliveryPredictionV11",
        "description": "Late delivery prediction result for v1.1."
      },
      "LateDeliveryResponse": {
        "properties": {
          "predictions": {
            "items": {
              "$ref": "#/components/schemas/LateDeliveryPrediction"
            },
            "type": "array",
            "title": "Predictions",
            "description": "List of late delivery predictions"
          },
          "total_orders_analyzed": {
            "type": "integer",
            "title": "Total Orders Analyzed",
            "description": "Total number of orders analyzed"
          },
          "high_risk_orders": {
            "type": "integer",
            "title": "High Risk Orders",
            "description": "Number of orders flagged as high risk"
          },
          "probability_threshold": {
            "type": "number",
            "title": "Probability Threshold",
            "description": "Probability threshold used for filtering"
          },
          "model_info": {
            "type": "object",
            "title": "Model Info",
            "description": "Information about the model used"
          },
          "processing_metadata": {
            "type": "object",
            "title": "Processing Metadata",
            "description": "Additional processing metadata"
          }
        },
        "type": "object",
        "required": [
          "predictions",
          "total_orders_analyzed",
          "high_risk_orders",
          "probability_threshold",
          "model_info"
        ],
        "title": "LateDeliveryResponse",
        "description": "Response model for late delivery prediction."
      },
      "LateDeliveryResponseV11": {
        "properties": {
          "predictions": {
            "items": {
              "$ref": "#/components/schemas/LateDeliveryPredictionV11"
            },
            "type": "array",
            "title": "Predictions"
          },
          "total_orders_analyzed": {
            "type": "integer",
            "title": "Total Orders Analyzed"
          },
          "orders_above_threshold": {
            "type": "integer",
            "title": "Orders Above Threshold",
            "description": "Number of orders with probability above threshold"
          },
          "high_risk_orders": {
            "type": "integer",
            "title": "High Risk Orders"
          },
          "critical_risk_orders": {
            "type": "integer",
            "title": "Critical Risk Orders"
          },
          "probability_threshold": {
            "type": "number",
            "title": "Probability Threshold"
          },
          "model_info": {
            "type": "object",
            "title": "Model Info"
          },
          "processing_metadata": {
            "type": "object",
            "title": "Processing Metadata"
          },
          "vendor_analysis": {
            "anyOf": [
              {
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "title": "Vendor Analysis"
          },
          "category_analysis": {
            "anyOf": [
              {
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "title": "Category Analysis"
          }
        },
        "type": "object",
        "required": [
          "predictions",
          "total_orders_analyzed",
          "orders_above_threshold",
          "high_risk_orders",
          "critical_risk_orders",
          "probability_threshold",
          "model_info",
          "processing_metadata"
        ],
        "title": "LateDeliveryResponseV11",
        "description": "Response model for live data late delivery predictions in v1.1."
      },
      "LiveDataRequest": {
        "properties": {
          "use_sql": {
            "type": "boolean",
            "title": "Use Sql",
            "description": "Whether to fetch data from SQL database",
            "default": true
          },
          "use_mrp": {
            "type": "boolean",
            "title": "Use Mrp",
            "description": "Whether to enrich with MRP API data",
            "default": true
          },
          "probability_threshold": {
            "type": "number",
            "maximum": 1,
            "minimum": 0,
            "title": "Probability Threshold",
            "description": "Minimum probability threshold for flagging late deliveries",
            "default": 0.75
          }
        },
        "type": "object",
        "title": "LiveDataRequest",
        "description": "Request model for live data late delivery prediction.\n\nThis model is used when fetching live data from SQL database and MRP API."
      },
      "LiveDataRequestV11": {
        "properties": {
          "use_sql": {
            "type": "boolean",
            "title": "Use Sql",
            "default": true
          },
          "use_mrp": {
            "type": "boolean",
            "title": "Use Mrp",
            "default": true
          },
          "probability_threshold": {
            "type": "number",
            "maximum": 1,
            "minimum": 0,
            "title": "Probability Threshold",
            "description": "Minimum probability to classify as late delivery",
            "default": 0.5
          },
          "include_vendor_metrics": {
            "type": "boolean",
            "title": "Include Vendor Metrics",
            "default": true
          },
          "include_category_analysis": {
            "type": "boolean",
            "title": "Include Category Analysis",
            "default": true
          },
          "max_results": {
            "anyOf": [
              {
                "type": "integer",
                "maximum": 10000,
                "minimum": 1
              },
              {
                "type": "null"
              }
            ],
            "title": "Max Results",
            "description": "Maximum number of results to return"
          }
        },
        "type": "object",
        "title": "LiveDataRequestV11",
        "description": "Request model for live data predictions in v1.1."
      },
      "PartToolRequest": {
        "properties": {
          "part_number": {
            "type": "string",
            "title": "Part Number",
            "description": "Part number to analyze (supports pattern matching for variants)",
            "examples": [
              "8406067",
              "8317069",
              "8406067-1OP"
            ]
          },
          "production_quantity": {
            "type": "integer",
            "minimum": 1,
            "title": "Production Quantity",
            "description": "Planned production quantity",
            "examples": [100, 500, 1000]
          },
          "production_start_date": {
            "type": "string",
            "title": "Production Start Date",
            "description": "ISO date when production starts",
            "examples": [
              "2025-01-15T08:00:00Z",
              "2025-02-01T06:00:00Z"
            ]
          },
          "production_end_date": {
            "type": "string",
            "title": "Production End Date",
            "description": "ISO date when production ends",
            "examples": [
              "2025-01-25T17:00:00Z",
              "2025-02-28T18:00:00Z"
            ]
          },
          "include_maintenance_schedule": {
            "type": "boolean",
            "title": "Include Maintenance Schedule",
            "description": "Include maintenance schedule in prediction",
            "default": true
          },
          "include_historical_data": {
            "type": "boolean",
            "title": "Include Historical Data",
            "description": "Include historical usage data",
            "default": true
          },
          "risk_threshold": {
            "type": "number",
            "maximum": 1,
            "minimum": 0,
            "title": "Risk Threshold",
            "description": "Minimum risk score to include in results (0.0-1.0)",
            "default": 0.5,
            "examples": [0.3, 0.5, 0.7]
          },
          "max_results": {
            "anyOf": [
              {
                "type": "integer",
                "maximum": 1000,
                "minimum": 1
              },
              {
                "type": "null"
              }
            ],
            "title": "Max Results",
            "description": "Maximum number of tools to return (up to 1000)",
            "examples": [10, 50, 100]
          }
        },
        "type": "object",
        "required": [
          "part_number",
          "production_quantity",
          "production_start_date",
          "production_end_date"
        ],
        "title": "PartToolRequest",
        "description": "Request model for tool prediction based on part number.",
        "examples": [
          {
            "max_results": 50,
            "part_number": "8406067",
            "production_end_date": "2025-01-25T17:00:00Z",
            "production_quantity": 100,
            "production_start_date": "2025-01-15T08:00:00Z",
            "risk_threshold": 0.6
          }
        ]
      },
      "PartToolResponse": {
        "properties": {
          "part_number": {
            "type": "string",
            "title": "Part Number",
            "description": "Part number analyzed"
          },
          "part_description": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Part Description",
            "description": "Part description"
          },
          "production_info": {
            "type": "object",
            "title": "Production Info",
            "description": "Production information and parameters"
          },
          "tool_predictions": {
            "items": {
              "$ref": "#/components/schemas/ToolPrediction"
            },
            "type": "array",
            "title": "Tool Predictions",
            "description": "List of tool predictions"
          },
          "total_tools_analyzed": {
            "type": "integer",
            "title": "Total Tools Analyzed",
            "description": "Total number of tools analyzed"
          },
          "high_risk_tools": {
            "type": "integer",
            "title": "High Risk Tools",
            "description": "Number of high/critical risk tools"
          },
          "critical_risk_tools": {
            "type": "integer",
            "title": "Critical Risk Tools",
            "description": "Number of critical risk tools"
          },
          "model_info": {
            "type": "object",
            "title": "Model Info",
            "description": "Model information"
          },
          "processing_metadata": {
            "type": "object",
            "title": "Processing Metadata",
            "description": "Processing metadata and timestamps"
          },
          "tool_list_summary": {
            "type": "object",
            "title": "Tool List Summary",
            "description": "Summary of tools required for this part"
          },
          "recommendations": {
            "items": {
              "type": "string"
            },
            "type": "array",
            "title": "Recommendations",
            "description": "Recommendations for risk mitigation"
          }
        },
        "type": "object",
        "required": [
          "part_number",
          "production_info",
          "tool_predictions",
          "total_tools_analyzed",
          "high_risk_tools",
          "critical_risk_tools",
          "model_info",
          "processing_metadata",
          "tool_list_summary"
        ],
        "title": "PartToolResponse",
        "description": "Response model for tool prediction."
      },
      "PredictionRequest": {
        "properties": {
          "data": {
            "items": {
              "type": "object"
            },
            "type": "array",
            "maxItems": 1000,
            "minItems": 1,
            "title": "Data",
            "description": "Input data for prediction (enhanced validation)"
          },
          "model_name": {
            "type": "string",
            "title": "Model Name",
            "description": "Name of the model to use for prediction",
            "default": "default",
            "examples": [
              "default",
              "enhanced",
              "ml_v2"
            ]
          },
          "parameters": {
            "type": "object",
            "title": "Parameters",
            "description": "Additional parameters for the prediction"
          },
          "include_confidence": {
            "type": "boolean",
            "title": "Include Confidence",
            "description": "Include confidence scores in response",
            "default": true
          }
        },
        "type": "object",
        "required": [
          "data"
        ],
        "title": "PredictionRequest",
        "description": "Enhanced prediction request model for v1.1.\n\nIncludes improved validation and documentation.",
        "examples": [
          {
            "data": [
              {
                "feature1": 100,
                "feature2": "value"
              }
            ],
            "include_confidence": true,
            "model_name": "default"
          }
        ]
      },
      "PredictionResponse": {
        "properties": {
          "predictions": {
            "items": {

            },
            "type": "array",
            "title": "Predictions",
            "description": "List of predictions with enhanced information"
          },
          "model_name": {
            "type": "string",
            "title": "Model Name",
            "description": "Name of the model used"
          },
          "department": {
            "type": "string",
            "title": "Department",
            "description": "Department that processed the request"
          },
          "confidence_scores": {
            "items": {
              "type": "number"
            },
            "type": "array",
            "title": "Confidence Scores",
            "description": "Confidence scores for each prediction (0-1)"
          },
          "model_version": {
            "type": "string",
            "title": "Model Version",
            "description": "Version of the model used",
            "default": "1.1"
          },
          "processing_time": {
            "type": "number",
            "title": "Processing Time",
            "description": "Processing time in seconds",
            "default": 0
          },
          "metadata": {
            "type": "object",
            "title": "Metadata",
            "description": "Enhanced metadata about the prediction"
          }
        },
        "type": "object",
        "required": [
          "predictions",
          "model_name",
          "department"
        ],
        "title": "PredictionResponse",
        "description": "Enhanced prediction response model for v1.1.\n\nIncludes additional metadata and confidence information."
      },
      "PurchaseOrderAnomalyRequest": {
        "properties": {
          "quantity": {
            "type": "number",
            "exclusiveMinimum": 0,
            "title": "Quantity",
            "description": "Order quantity"
          },
          "unit_cost": {
            "type": "number",
            "exclusiveMinimum": 0,
            "title": "Unit Cost",
            "description": "Unit cost per item"
          },
          "line_amount": {
            "type": "number",
            "exclusiveMinimum": 0,
            "title": "Line Amount",
            "description": "Total line amount (quantity × unit_cost)"
          },
          "vendor_no": {
            "type": "string",
            "maxLength": 20,
            "minLength": 1,
            "title": "Vendor No",
            "description": "Vendor number/code"
          },
          "job_no": {
            "type": "string",
            "maxLength": 20,
            "minLength": 1,
            "title": "Job No",
            "description": "Job number"
          },
          "item_no": {
            "type": "string",
            "maxLength": 20,
            "minLength": 1,
            "title": "Item No",
            "description": "Item number"
          }
        },
        "type": "object",
        "required": [
          "quantity",
          "unit_cost",
          "line_amount",
          "vendor_no",
          "job_no",
          "item_no"
        ],
        "title": "PurchaseOrderAnomalyRequest",
        "description": "Request model for purchase order anomaly detection.\n\nThis model validates purchase order line data for suspicious patterns."
      },
      "PurchaseOrderAnomalyResponse": {
        "properties": {
          "valid": {
            "type": "boolean",
            "title": "Valid",
            "description": "Whether the order is valid (not anomalous)"
          },
          "recommendation": {
            "type": "string",
            "pattern": "^(ACCEPT|REJECT)$",
            "title": "Recommendation",
            "description": "Recommendation: ACCEPT or REJECT"
          },
          "confidence": {
            "type": "number",
            "maximum": 1,
            "minimum": 0,
            "title": "Confidence",
            "description": "Confidence level of the prediction"
          },
          "product_category": {
            "type": "string",
            "maxLength": 4,
            "title": "Product Category",
            "description": "Product category (first 4 characters of item_no)"
          },
          "reasons": {
            "items": {
              "type": "string"
            },
            "type": "array",
            "title": "Reasons",
            "description": "List of reasons for the recommendation"
          },
          "score": {
            "type": "number",
            "minimum": 0,
            "title": "Score",
            "description": "Anomaly score (lower = more normal)"
          }
        },
        "type": "object",
        "required": [
          "valid",
          "recommendation",
          "confidence",
          "product_category",
          "reasons",
          "score"
        ],
        "title": "PurchaseOrderAnomalyResponse",
        "description": "Response model for purchase order anomaly detection."
      },
      "PurchaseOrderData": {
        "properties": {
          "document_no": {
            "type": "string",
            "title": "Document No",
            "description": "Purchase order document number",
            "examples": [
              "PO-2025-001",
              "DOC123456"
            ]
          },
          "part_number": {
            "type": "string",
            "title": "Part Number",
            "description": "Part number being ordered",
            "examples": [
              "8406067",
              "PART-ABC-123"
            ]
          },
          "supplier_number": {
            "type": "string",
            "title": "Supplier Number",
            "description": "Supplier/vendor number",
            "examples": [
              "SUP001",
              "VENDOR-456"
            ]
          },
          "quantity": {
            "type": "integer",
            "exclusiveMinimum": 0,
            "title": "Quantity",
            "description": "Quantity ordered",
            "examples": [100, 500, 1000]
          },
          "unit_price": {
            "type": "number",
            "exclusiveMinimum": 0,
            "title": "Unit Price",
            "description": "Unit price in CAD",
            "examples": [25.5, 100, 1250.75]
          },
          "order_date": {
            "type": "string",
            "title": "Order Date",
            "description": "Order placement date (ISO format)",
            "examples": [
              "2025-01-15",
              "2025-02-01"
            ]
          },
          "requested_delivery_date": {
            "type": "string",
            "title": "Requested Delivery Date",
            "description": "Requested delivery date (ISO format)",
            "examples": [
              "2025-02-15",
              "2025-03-01"
            ]
          },
          "total_value": {
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "null"
              }
            ],
            "title": "Total Value",
            "description": "Total order value (auto-calculated if not provided)"
          },
          "priority_level": {
            "type": "string",
            "title": "Priority Level",
            "description": "Order priority",
            "default": "standard",
            "examples": [
              "urgent",
              "standard",
              "low"
            ]
          },
          "category": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Category",
            "description": "Part category",
            "examples": [
              "machining",
              "electronics",
              "raw_material"
            ]
          }
        },
        "type": "object",
        "required": [
          "document_no",
          "part_number",
          "supplier_number",
          "quantity",
          "unit_price",
          "order_date",
          "requested_delivery_date"
        ],
        "title": "PurchaseOrderData",
        "description": "Individual purchase order data for late delivery prediction.",
        "examples": [
          {
            "category": "machining",
            "document_no": "PO-2025-001234",
            "order_date": "2025-01-15",
            "part_number": "8406067",
            "priority_level": "standard",
            "quantity": 100,
            "requested_delivery_date": "2025-02-15",
            "supplier_number": "SUP001",
            "unit_price": 125.5
          }
        ]
      },
      "PurchaseOrderRequest": {
        "properties": {
          "purchase_orders": {
            "items": {
              "$ref": "#/components/schemas/PurchaseOrderData"
            },
            "type": "array",
            "maxItems": 100,
            "minItems": 1,
            "title": "Purchase Orders",
            "description": "List of purchase orders to analyze (up to 100)"
          },
          "include_vendor_history": {
            "type": "boolean",
            "title": "Include Vendor History",
            "description": "Include vendor performance history in prediction",
            "default": true
          },
          "include_part_history": {
            "type": "boolean",
            "title": "Include Part History",
            "description": "Include part delivery history in prediction",
            "default": true
          },
          "probability_threshold": {
            "type": "number",
            "maximum": 1,
            "minimum": 0,
            "title": "Probability Threshold",
            "description": "Minimum probability to classify as late delivery risk",
            "default": 0.5
          }
        },
        "type": "object",
        "required": [
          "purchase_orders"
        ],
        "title": "PurchaseOrderRequest",
        "description": "Request model for purchase order late delivery prediction.",
        "examples": [
          {
            "include_part_history": true,
            "include_vendor_history": true,
            "probability_threshold": 0.6,
            "purchase_orders": [
              {
                "document_no": "PO-2025-001234",
                "order_date": "2025-01-15",
                "part_number": "8406067",
                "priority_level": "standard",
                "quantity": 100,
                "requested_delivery_date": "2025-02-15",
                "supplier_number": "SUP001",
                "unit_price": 125.5
              }
            ]
          }
        ]
      },
      "PurchaseOrderResponse": {
        "properties": {
          "predictions": {
            "items": {
              "$ref": "#/components/schemas/LateDeliveryPredictionV11"
            },
            "type": "array",
            "title": "Predictions",
            "description": "List of predictions for each purchase order"
          },
          "total_orders_analyzed": {
            "type": "integer",
            "title": "Total Orders Analyzed",
            "description": "Total number of orders analyzed"
          },
          "late_delivery_predictions": {
            "type": "integer",
            "title": "Late Delivery Predictions",
            "description": "Number of orders predicted to be late"
          },
          "high_risk_orders": {
            "type": "integer",
            "title": "High Risk Orders",
            "description": "Number of high risk orders"
          },
          "critical_risk_orders": {
            "type": "integer",
            "title": "Critical Risk Orders",
            "description": "Number of critical risk orders"
          },
          "probability_threshold": {
            "type": "number",
            "title": "Probability Threshold",
            "description": "Threshold used for classification"
          },
          "model_info": {
            "type": "object",
            "title": "Model Info",
            "description": "Model information and performance metrics"
          },
          "processing_metadata": {
            "type": "object",
            "title": "Processing Metadata",
            "description": "Processing metadata and timestamps"
          },
          "vendor_analysis": {
            "anyOf": [
              {
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "title": "Vendor Analysis",
            "description": "Vendor performance analysis"
          },
          "category_analysis": {
            "anyOf": [
              {
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "title": "Category Analysis",
            "description": "Part category risk analysis"
          },
          "recommendations": {
            "items": {
              "type": "string"
            },
            "type": "array",
            "title": "Recommendations",
            "description": "Actionable recommendations"
          }
        },
        "type": "object",
        "required": [
          "predictions",
          "total_orders_analyzed",
          "late_delivery_predictions",
          "high_risk_orders",
          "critical_risk_orders",
          "probability_threshold",
          "model_info",
          "processing_metadata"
        ],
        "title": "PurchaseOrderResponse",
        "description": "Response model for purchase order late delivery predictions.",
        "examples": [
          {
            "critical_risk_orders": 0,
            "high_risk_orders": 1,
            "late_delivery_predictions": 1,
            "predictions": [
              {
                "cost": 12550,
                "delivery_delay_days": 5,
                "document_no": "PO-2025-001234",
                "item_no": "8406067",
                "predicted_is_late": true,
                "predicted_probability": 0.73,
                "quantity": 100,
                "risk_level": "high",
                "vendor": "SUP001"
              }
            ],
            "probability_threshold": 0.6,
            "recommendations": [
              "Contact supplier SUP001 for delivery confirmation",
              "Consider expedited shipping for PO-2025-001234"
            ],
            "total_orders_analyzed": 1
          }
        ]
      },
      "ToolListRequest": {
        "properties": {
          "part_number": {
            "type": "string",
            "title": "Part Number",
            "description": "Part number to get tools for (supports pattern matching)",
            "examples": [
              "8406067",
              "8317069",
              "8406067-1OP"
            ]
          },
          "include_alternatives": {
            "type": "boolean",
            "title": "Include Alternatives",
            "description": "Include alternative tools (future feature)",
            "default": false
          },
          "include_specifications": {
            "type": "boolean",
            "title": "Include Specifications",
            "description": "Include detailed tool specifications and stock info",
            "default": true
          }
        },
        "type": "object",
        "required": [
          "part_number"
        ],
        "title": "ToolListRequest",
        "description": "Request model for fetching tool list for a part.",
        "examples": [
          {
            "include_alternatives": false,
            "include_specifications": true,
            "part_number": "8406067"
          }
        ]
      },
      "ToolListResponse": {
        "properties": {
          "part_number": {
            "type": "string",
            "title": "Part Number",
            "description": "Part number"
          },
          "part_description": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Part Description",
            "description": "Part description"
          },
          "required_tools": {
            "items": {
              "type": "object"
            },
            "type": "array",
            "title": "Required Tools",
            "description": "List of required tools with specifications"
          },
          "alternative_tools": {
            "items": {
              "type": "object"
            },
            "type": "array",
            "title": "Alternative Tools",
            "description": "List of alternative tools"
          },
          "total_tools": {
            "type": "integer",
            "title": "Total Tools",
            "description": "Total number of tools"
          },
          "tool_categories": {
            "additionalProperties": {
              "type": "integer"
            },
            "type": "object",
            "title": "Tool Categories",
            "description": "Count of tools by category"
          },
          "metadata": {
            "type": "object",
            "title": "Metadata",
            "description": "Additional metadata"
          }
        },
        "type": "object",
        "required": [
          "part_number",
          "required_tools",
          "total_tools",
          "tool_categories",
          "metadata"
        ],
        "title": "ToolListResponse",
        "description": "Response model for tool list."
      },
      "ToolPrediction": {
        "properties": {
          "tool_id": {
            "type": "string",
            "title": "Tool Id",
            "description": "Unique identifier for the tool"
          },
          "tool_name": {
            "type": "string",
            "title": "Tool Name",
            "description": "Name/description of the tool"
          },
          "tool_type": {
            "type": "string",
            "title": "Tool Type",
            "description": "Type of tool (e.g., drill, mill, lathe)"
          },
          "shortage_probability": {
            "type": "number",
            "maximum": 1,
            "minimum": 0,
            "title": "Shortage Probability",
            "description": "Probability of shortage (0-1)"
          },
          "breakage_probability": {
            "type": "number",
            "maximum": 1,
            "minimum": 0,
            "title": "Breakage Probability",
            "description": "Probability of breakage (0-1)"
          },
          "combined_risk_score": {
            "type": "number",
            "maximum": 1,
            "minimum": 0,
            "title": "Combined Risk Score",
            "description": "Combined risk score (0-1)"
          },
          "risk_level": {
            "type": "string",
            "pattern": "^(low|medium|high|critical)$",
            "title": "Risk Level",
            "description": "Risk level classification"
          },
          "predicted_shortage_date": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Predicted Shortage Date",
            "description": "ISO date when shortage is predicted"
          },
          "predicted_breakage_date": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Predicted Breakage Date",
            "description": "ISO date when breakage is predicted"
          },
          "current_stock": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Current Stock",
            "description": "Current stock level"
          },
          "recommended_stock": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Recommended Stock",
            "description": "Recommended stock level"
          },
          "usage_rate": {
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "null"
              }
            ],
            "title": "Usage Rate",
            "description": "Daily usage rate"
          },
          "wear_rate": {
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "null"
              }
            ],
            "title": "Wear Rate",
            "description": "Daily wear rate"
          },
          "risk_factors": {
            "items": {
              "type": "string"
            },
            "type": "array",
            "title": "Risk Factors",
            "description": "List of risk factors identified"
          }
        },
        "type": "object",
        "required": [
          "tool_id",
          "tool_name",
          "tool_type",
          "shortage_probability",
          "breakage_probability",
          "combined_risk_score",
          "risk_level"
        ],
        "title": "ToolPrediction",
        "description": "Tool shortage/breakage prediction result."
      },
      "ValidationError": {
        "properties": {
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "type": "array",
            "title": "Location"
          },
          "msg": {
            "type": "string",
            "title": "Message"
          },
          "type": {
            "type": "string",
            "title": "Error Type"
          }
        },
        "type": "object",
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError"
      },
      "VendorPredictionRequest": {
        "properties": {
          "item_no": {
            "type": "string",
            "minLength": 2,
            "title": "Item No",
            "description": "Item number for vendor prediction",
            "examples": [
              "0322023",
              "1483116",
              "8406067"
            ]
          },
          "description": {
            "type": "string",
            "minLength": 3,
            "title": "Description",
            "description": "Item description for enhanced prediction accuracy",
            "examples": [
              "POIGNEE PLASTIQUE EN T",
              "RAIL LINÉAIRE SÉRIE 20",
              "BEARING BALL"
            ]
          }
        },
        "type": "object",
        "required": [
          "item_no",
          "description"
        ],
        "title": "VendorPredictionRequest",
        "description": "Request model for vendor prediction.",
        "examples": [
          {
            "description": "POIGNEE PLASTIQUE EN T",
            "item_no": "0322023"
          },
          {
            "description": "RAIL LINÉAIRE SÉRIE 20",
            "item_no": "1483116"
          }
        ]
      },
      "VendorPredictionResponse": {
        "properties": {
          "item_no": {
            "type": "string",
            "title": "Item No",
            "description": "Original item number"
          },
          "description": {
            "type": "string",
            "title": "Description",
            "description": "Original item description"
          },
          "predicted_vendor": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Predicted Vendor",
            "description": "Predicted vendor code"
          },
          "confidence": {
            "type": "number",
            "maximum": 1,
            "minimum": 0,
            "title": "Confidence",
            "description": "Prediction confidence (0-1)"
          },
          "rule_type": {
            "type": "string",
            "title": "Rule Type",
            "description": "Type of rule used for prediction"
          },
          "details": {
            "type": "string",
            "title": "Details",
            "description": "Details about the prediction logic"
          },
          "priority": {
            "type": "integer",
            "title": "Priority",
            "description": "Rule priority level (higher = more reliable)"
          },
          "supporting_items": {
            "type": "integer",
            "title": "Supporting Items",
            "description": "Number of items supporting this rule"
          },
          "success": {
            "type": "boolean",
            "title": "Success",
            "description": "Whether prediction was successful"
          }
        },
        "type": "object",
        "required": [
          "item_no",
          "description",
          "predicted_vendor",
          "confidence",
          "rule_type",
          "details",
          "priority",
          "supporting_items",
          "success"
        ],
        "title": "VendorPredictionResponse",
        "description": "Response model for vendor prediction.",
        "examples": [
          {
            "confidence": 0.678,
            "description": "POIGNEE PLASTIQUE EN T",
            "details": "Keywords: poignee",
            "item_no": "0322023",
            "predicted_vendor": "LAFOU01",
            "priority": 8,
            "rule_type": "keyword_specialty",
            "success": true,
            "supporting_items": 193
          }
        ]
      },
      "VendorStatsResponse": {
        "properties": {
          "total_items": {
            "type": "integer",
            "title": "Total Items",
            "description": "Total items in training data"
          },
          "unique_vendors": {
            "type": "integer",
            "title": "Unique Vendors",
            "description": "Number of unique vendors"
          },
          "pattern_rules": {
            "type": "integer",
            "title": "Pattern Rules",
            "description": "Number of 4-digit pattern rules"
          },
          "keyword_rules": {
            "type": "integer",
            "title": "Keyword Rules",
            "description": "Number of keyword specialty rules"
          },
          "specialty_rules": {
            "type": "integer",
            "title": "Specialty Rules",
            "description": "Number of vendor specialty rules"
          },
          "supported_vendors": {
            "items": {
              "type": "string"
            },
            "type": "array",
            "title": "Supported Vendors",
            "description": "List of specialty vendors"
          }
        },
        "type": "object",
        "required": [
          "total_items",
          "unique_vendors",
          "pattern_rules",
          "keyword_rules",
          "specialty_rules",
          "supported_vendors"
        ],
        "title": "VendorStatsResponse",
        "description": "Response model for vendor prediction statistics.",
        "examples": [
          {
            "keyword_rules": 4,
            "pattern_rules": 23,
            "specialty_rules": 4,
            "supported_vendors": [
              "LAFOU01",
              "ALMHY01",
              "BOSRE01",
              "WAJIN01"
            ],
            "total_items": 14562,
            "unique_vendors": 45
          }
        ]
      }
    }
  }
}