{
  "openapi": "3.1.0",
  "info": {
    "title": "lpg-ai-agent-api",
    "description": "AI Agent API service for email processing across departments",
    "version": "1.0.0"
  },
  "paths": {
    "/api/v1/achat/triage": {
      "post": {
        "tags": [
          "achat"
        ],
        "summary": "Process email with triage agent",
        "description": "Analyze email and categorize it for the Achat department",
        "operationId": "process_triage_api_v1_achat_triage_post",
        "requestBody": {
          "content": {
            "multipart/form-data": {
              "schema": {
                "$ref": "#/components/schemas/Body_process_triage_api_v1_achat_triage_post"
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
                  "$ref": "#/components/schemas/AchatTriageResponse"
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
    "/api/v1/achat/sentiment": {
      "post": {
        "tags": [
          "achat"
        ],
        "summary": "Analyze email sentiment",
        "description": "Analyze sentiment and urgency of an email for the Achat department",
        "operationId": "process_sentiment_api_v1_achat_sentiment_post",
        "requestBody": {
          "content": {
            "multipart/form-data": {
              "schema": {
                "$ref": "#/components/schemas/Body_process_sentiment_api_v1_achat_sentiment_post"
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
                  "$ref": "#/components/schemas/SentimentAnalysisResponse"
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
    "/api/v1/achat/analyze": {
      "post": {
        "tags": [
          "achat"
        ],
        "summary": "Complete email analysis",
        "description": "Process email with both triage and sentiment agents",
        "operationId": "analyze_email_api_v1_achat_analyze_post",
        "requestBody": {
          "content": {
            "multipart/form-data": {
              "schema": {
                "$ref": "#/components/schemas/Body_analyze_email_api_v1_achat_analyze_post"
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
                  "additionalProperties": true,
                  "type": "object",
                  "title": "Response Analyze Email Api V1 Achat Analyze Post"
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
    "/api/v1/customer-support/triage": {
      "post": {
        "tags": [
          "customer-support"
        ],
        "summary": "Process email with triage agent",
        "description": "Analyze email and categorize it for the Customer Support department",
        "operationId": "process_triage_api_v1_customer_support_triage_post",
        "requestBody": {
          "content": {
            "multipart/form-data": {
              "schema": {
                "$ref": "#/components/schemas/Body_process_triage_api_v1_customer_support_triage_post"
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
                  "$ref": "#/components/schemas/CustomerSupportTriageResponse"
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
    "/api/v1/customer-support/sentiment": {
      "post": {
        "tags": [
          "customer-support"
        ],
        "summary": "Analyze email sentiment",
        "description": "Analyze sentiment and urgency of an email for the Customer Support department",
        "operationId": "process_sentiment_api_v1_customer_support_sentiment_post",
        "requestBody": {
          "content": {
            "multipart/form-data": {
              "schema": {
                "$ref": "#/components/schemas/Body_process_sentiment_api_v1_customer_support_sentiment_post"
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
                  "$ref": "#/components/schemas/SentimentAnalysisResponse"
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
    "/api/v1/customer-support/analyze": {
      "post": {
        "tags": [
          "customer-support"
        ],
        "summary": "Complete email analysis",
        "description": "Process email with both triage and sentiment agents",
        "operationId": "analyze_email_api_v1_customer_support_analyze_post",
        "requestBody": {
          "content": {
            "multipart/form-data": {
              "schema": {
                "$ref": "#/components/schemas/Body_analyze_email_api_v1_customer_support_analyze_post"
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
                  "additionalProperties": true,
                  "type": "object",
                  "title": "Response Analyze Email Api V1 Customer Support Analyze Post"
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
    "/health": {
      "get": {
        "summary": "Health Check",
        "description": "Health check endpoint",
        "operationId": "health_check_health_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

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
      "AchatEmailCategory": {
        "type": "string",
        "enum": [
          "order_confirmation",
          "order_modification",
          "purchase_order",
          "sales_order",
          "order_revision",
          "quote_request",
          "supplier_quote",
          "rfq_response",
          "delivery_issue",
          "order_tracking",
          "project_followup",
          "delay_notification",
          "confirmation_request",
          "invoice",
          "steel_invoice",
          "payment_request",
          "credit_note",
          "customs_request",
          "technical_request",
          "work_order",
          "approval_request",
          "requisition",
          "internal_request",
          "plan_request",
          "document_request",
          "web_search",
          "follow_up",
          "treatment_request",
          "project_creation",
          "project_revision",
          "chat_message",
          "supplier_communication",
          "contract_negotiation",
          "general_inquiry",
          "unknown"
        ],
        "title": "AchatEmailCategory",
        "description": "Email categories for Achat (Purchasing) department"
      },
      "AchatTriageResponse": {
        "properties": {
          "confidence": {
            "type": "number",
            "maximum": 100,
            "minimum": 0,
            "title": "Confidence",
            "description": "Confidence score as percentage (0-100)"
          },
          "urgency": {
            "type": "number",
            "maximum": 100,
            "minimum": 0,
            "title": "Urgency",
            "description": "Urgency score as percentage (0-100)"
          },
          "sentiment": {
            "$ref": "#/components/schemas/SentimentLevel"
          },
          "category": {
            "$ref": "#/components/schemas/AchatEmailCategory"
          }
        },
        "additionalProperties": false,
        "type": "object",
        "required": [
          "confidence",
          "urgency",
          "sentiment",
          "category"
        ],
        "title": "AchatTriageResponse",
        "description": "Response model for Achat triage agent",
        "example": {
          "category": "invoice",
          "confidence": 95.5,
          "sentiment": "neutral",
          "urgency": 70
        }
      },
      "Body_analyze_email_api_v1_achat_analyze_post": {
        "properties": {
          "subject": {
            "type": "string",
            "title": "Subject"
          },
          "body": {
            "type": "string",
            "title": "Body"
          },
          "attachments": {
            "anyOf": [
              {
                "items": {
                  "type": "string",
                  "format": "binary"
                },
                "type": "array"
              },
              {
                "type": "null"
              }
            ],
            "title": "Attachments"
          }
        },
        "type": "object",
        "required": [
          "subject",
          "body"
        ],
        "title": "Body_analyze_email_api_v1_achat_analyze_post"
      },
      "Body_analyze_email_api_v1_customer_support_analyze_post": {
        "properties": {
          "subject": {
            "type": "string",
            "title": "Subject"
          },
          "body": {
            "type": "string",
            "title": "Body"
          },
          "attachments": {
            "anyOf": [
              {
                "items": {
                  "type": "string",
                  "format": "binary"
                },
                "type": "array"
              },
              {
                "type": "null"
              }
            ],
            "title": "Attachments"
          }
        },
        "type": "object",
        "required": [
          "subject",
          "body"
        ],
        "title": "Body_analyze_email_api_v1_customer_support_analyze_post"
      },
      "Body_process_sentiment_api_v1_achat_sentiment_post": {
        "properties": {
          "subject": {
            "type": "string",
            "title": "Subject"
          },
          "body": {
            "type": "string",
            "title": "Body"
          },
          "attachments": {
            "anyOf": [
              {
                "items": {
                  "type": "string",
                  "format": "binary"
                },
                "type": "array"
              },
              {
                "type": "null"
              }
            ],
            "title": "Attachments"
          }
        },
        "type": "object",
        "required": [
          "subject",
          "body"
        ],
        "title": "Body_process_sentiment_api_v1_achat_sentiment_post"
      },
      "Body_process_sentiment_api_v1_customer_support_sentiment_post": {
        "properties": {
          "subject": {
            "type": "string",
            "title": "Subject"
          },
          "body": {
            "type": "string",
            "title": "Body"
          },
          "attachments": {
            "anyOf": [
              {
                "items": {
                  "type": "string",
                  "format": "binary"
                },
                "type": "array"
              },
              {
                "type": "null"
              }
            ],
            "title": "Attachments"
          }
        },
        "type": "object",
        "required": [
          "subject",
          "body"
        ],
        "title": "Body_process_sentiment_api_v1_customer_support_sentiment_post"
      },
      "Body_process_triage_api_v1_achat_triage_post": {
        "properties": {
          "subject": {
            "type": "string",
            "title": "Subject"
          },
          "body": {
            "type": "string",
            "title": "Body"
          },
          "attachments": {
            "anyOf": [
              {
                "items": {
                  "type": "string",
                  "format": "binary"
                },
                "type": "array"
              },
              {
                "type": "null"
              }
            ],
            "title": "Attachments"
          }
        },
        "type": "object",
        "required": [
          "subject",
          "body"
        ],
        "title": "Body_process_triage_api_v1_achat_triage_post"
      },
      "Body_process_triage_api_v1_customer_support_triage_post": {
        "properties": {
          "subject": {
            "type": "string",
            "title": "Subject"
          },
          "body": {
            "type": "string",
            "title": "Body"
          },
          "attachments": {
            "anyOf": [
              {
                "items": {
                  "type": "string",
                  "format": "binary"
                },
                "type": "array"
              },
              {
                "type": "null"
              }
            ],
            "title": "Attachments"
          }
        },
        "type": "object",
        "required": [
          "subject",
          "body"
        ],
        "title": "Body_process_triage_api_v1_customer_support_triage_post"
      },
      "CustomerSupportEmailCategory": {
        "type": "string",
        "enum": [
          "product_inquiry",
          "technical_support",
          "order_status",
          "complaint",
          "return_request",
          "warranty_claim",
          "feedback",
          "billing_issue",
          "account_help",
          "general_inquiry"
        ],
        "title": "CustomerSupportEmailCategory",
        "description": "Email categories for Customer Support department"
      },
      "CustomerSupportTriageResponse": {
        "properties": {
          "confidence": {
            "type": "number",
            "maximum": 100,
            "minimum": 0,
            "title": "Confidence",
            "description": "Confidence score as percentage (0-100)"
          },
          "urgency": {
            "type": "number",
            "maximum": 100,
            "minimum": 0,
            "title": "Urgency",
            "description": "Urgency score as percentage (0-100)"
          },
          "sentiment": {
            "$ref": "#/components/schemas/SentimentLevel"
          },
          "category": {
            "$ref": "#/components/schemas/CustomerSupportEmailCategory"
          }
        },
        "additionalProperties": false,
        "type": "object",
        "required": [
          "confidence",
          "urgency",
          "sentiment",
          "category"
        ],
        "title": "CustomerSupportTriageResponse",
        "description": "Response model for Customer Support triage agent",
        "example": {
          "category": "technical_support",
          "confidence": 88.2,
          "sentiment": "negative",
          "urgency": 85
        }
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
      "SentimentAnalysisResponse": {
        "properties": {
          "confidence": {
            "type": "number",
            "maximum": 100,
            "minimum": 0,
            "title": "Confidence",
            "description": "Confidence score as percentage (0-100)"
          },
          "urgency": {
            "type": "number",
            "maximum": 100,
            "minimum": 0,
            "title": "Urgency",
            "description": "Urgency score as percentage (0-100)"
          },
          "sentiment": {
            "$ref": "#/components/schemas/SentimentLevel"
          }
        },
        "additionalProperties": false,
        "type": "object",
        "required": [
          "confidence",
          "urgency",
          "sentiment"
        ],
        "title": "SentimentAnalysisResponse",
        "description": "Response model for sentiment analysis agent (used by both departments)",
        "example": {
          "confidence": 92.1,
          "sentiment": "positive",
          "urgency": 60
        }
      },
      "SentimentLevel": {
        "type": "string",
        "enum": [
          "very_negative",
          "negative",
          "neutral",
          "positive",
          "very_positive"
        ],
        "title": "SentimentLevel",
        "description": "Enum for sentiment levels"
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
      }
    }
  }
}