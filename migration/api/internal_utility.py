{
  "openapi": "3.0.1",
  "info": {
    "title": "My API",
    "version": "1.0"
  },
  "paths": {
    "/api/v1/Ai/motd": {
      "get": {
        "tags": [
          "Ai"
        ],
        "summary": "Generates a personalized Message Of The Day (MOTD) based on the provided prompt.",
        "parameters": [
          {
            "name": "prompt",
            "in": "query",
            "description": "The base text to generate the MOTD.",
            "style": "form",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "language",
            "in": "query",
            "description": "Optional language for the response (default is English).",
            "style": "form",
            "schema": {
              "type": "string",
              "default": "English"
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
    "/api/v1/Ai/changelog": {
      "get": {
        "tags": [
          "Ai"
        ],
        "summary": "Generates a changelog based on the commit messages provided.",
        "parameters": [
          {
            "name": "commitMessages",
            "in": "query",
            "description": "The commit messages since the last published version.",
            "style": "form",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "language",
            "in": "query",
            "description": "Optional language for the response (default is English).",
            "style": "form",
            "schema": {
              "type": "string",
              "default": "English"
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
    "/api/v1/Ai/response": {
      "get": {
        "tags": [
          "Ai"
        ],
        "summary": "A generic endpoint to get an AI response for any prompt.",
        "parameters": [
          {
            "name": "prompt",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "language",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string",
              "default": "English"
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
    "/api/v1/CacheMonitoring/CacheStatistics": {
      "get": {
        "tags": [
          "CacheMonitoring"
        ],
        "summary": "Retrieve the General Cache statistics",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/CacheMonitoring/InvalidateAllCaches": {
      "get": {
        "tags": [
          "CacheMonitoring"
        ],
        "summary": "Invalidate all the caches",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/CertificationCriteria": {
      "get": {
        "tags": [
          "CertificationCriteria"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/CertificationCriteria"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/CertificationCriteria"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/CertificationCriteria"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "CertificationCriteria"
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationCriteriaCreationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationCriteriaCreationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationCriteriaCreationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationCriteria"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationCriteria"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationCriteria"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/CertificationCriteria/{id}": {
      "get": {
        "tags": [
          "CertificationCriteria"
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
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationCriteria"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationCriteria"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationCriteria"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "CertificationCriteria"
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
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationCriteriaUpdateDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationCriteriaUpdateDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationCriteriaUpdateDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationCriteria"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationCriteria"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationCriteria"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "CertificationCriteria"
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
    "/api/v1/Certifications": {
      "get": {
        "tags": [
          "Certifications"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/CertificationDTO"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/CertificationDTO"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/CertificationDTO"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "Certifications"
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationsCreationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationsCreationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationsCreationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationDTO"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationDTO"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationDTO"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/Certifications/{id}": {
      "get": {
        "tags": [
          "Certifications"
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
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationDTO"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationDTO"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationDTO"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "Certifications"
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
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationsUpdateDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationsUpdateDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationsUpdateDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationDTO"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationDTO"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/CertificationDTO"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "Certifications"
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
    "/api/v1/Certifications/{id}/{CriteriaId}": {
      "put": {
        "tags": [
          "Certifications"
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
          },
          {
            "name": "CriteriaId",
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
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationCertificationCriteriaUpdateDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationCertificationCriteriaUpdateDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/CertificationCertificationCriteriaUpdateDTO"
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
    "/api/v1/Department": {
      "get": {
        "tags": [
          "Department"
        ],
        "summary": "Gets all departments.",
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Department"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Department"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Department"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "Department"
        ],
        "summary": "Creates a new department.",
        "requestBody": {
          "description": "The department creation DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/DepartmentCreationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/DepartmentCreationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/DepartmentCreationDTO"
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
    "/api/v1/Department/{id}": {
      "get": {
        "tags": [
          "Department"
        ],
        "summary": "Gets a department by ID.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The department ID.",
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
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Department"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Department"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Department"
                  }
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "Department"
        ],
        "summary": "Updates an existing department.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The department ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          }
        ],
        "requestBody": {
          "description": "The department update DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/DepartmentUpdateDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/DepartmentUpdateDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/DepartmentUpdateDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      },
      "delete": {
        "tags": [
          "Department"
        ],
        "summary": "Deletes a department by ID.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The department ID.",
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
    "/api/v1/FileShare/GetItemPDFFile({itemNo})": {
      "get": {
        "tags": [
          "FileShare"
        ],
        "parameters": [
          {
            "name": "itemNo",
            "in": "path",
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
    "/api/v1/FileShare/CreateDxfArchive": {
      "post": {
        "tags": [
          "FileShare"
        ],
        "requestBody": {
          "content": {
            "multipart/form-data": {
              "schema": {
                "type": "object",
                "properties": {
                  "wolFile": {
                    "type": "string",
                    "format": "binary"
                  }
                }
              },
              "encoding": {
                "wolFile": {
                  "style": "form"
                }
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
    "/api/v1/Fixture": {
      "get": {
        "tags": [
          "Fixture"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/FixtureDTO"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/FixtureDTO"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/FixtureDTO"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "Fixture"
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/FixtureModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/FixtureModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/FixtureModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureDTO"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureDTO"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureDTO"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/Fixture/{fixtureNo}": {
      "get": {
        "tags": [
          "Fixture"
        ],
        "parameters": [
          {
            "name": "fixtureNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureDTO"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureDTO"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureDTO"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "Fixture"
        ],
        "parameters": [
          {
            "name": "fixtureNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/FixtureModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/FixtureModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/FixtureModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureDTO"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureDTO"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureDTO"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "Fixture"
        ],
        "parameters": [
          {
            "name": "fixtureNo",
            "in": "path",
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
    "/api/v1/Fixture/{fixtureNo}/Inventory/Add": {
      "post": {
        "tags": [
          "Fixture"
        ],
        "parameters": [
          {
            "name": "fixtureNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "locationId",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          },
          {
            "name": "quantity",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "number",
              "format": "double"
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
    "/api/v1/Fixture/{fixtureNo}/Inventory/Remove": {
      "post": {
        "tags": [
          "Fixture"
        ],
        "parameters": [
          {
            "name": "fixtureNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "locationId",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          },
          {
            "name": "quantity",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "number",
              "format": "double"
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
    "/api/v1/Fixture/{fixtureNo}/Inventory": {
      "get": {
        "tags": [
          "Fixture"
        ],
        "parameters": [
          {
            "name": "fixtureNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/FixtureLocationDTO"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/FixtureLocationDTO"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/FixtureLocationDTO"
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/FixtureReceiver": {
      "get": {
        "tags": [
          "FixtureReceiver"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/FixtureReceiver"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/FixtureReceiver"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/FixtureReceiver"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "FixtureReceiver"
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/FixtureReceiverModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/FixtureReceiverModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/FixtureReceiverModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureReceiver"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureReceiver"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureReceiver"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/FixtureReceiver/{id}": {
      "get": {
        "tags": [
          "FixtureReceiver"
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
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureReceiver"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureReceiver"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureReceiver"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "FixtureReceiver"
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
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/FixtureReceiverModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/FixtureReceiverModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/FixtureReceiverModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureReceiver"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureReceiver"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/FixtureReceiver"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "FixtureReceiver"
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
    "/api/v1/HealthMonitoring": {
      "get": {
        "tags": [
          "HealthMonitoring"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/HealthMonitoring/query-stats": {
      "get": {
        "tags": [
          "HealthMonitoring"
        ],
        "summary": "Get database statistic information",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/HealthMonitoring/cpu-usage": {
      "get": {
        "tags": [
          "HealthMonitoring"
        ],
        "summary": "Get Current CPU Usage",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/HealthMonitoring/memory-Usage": {
      "get": {
        "tags": [
          "HealthMonitoring"
        ],
        "summary": "Get Current Memory Usage",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/Item": {
      "get": {
        "tags": [
          "Item"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/ItemDTO"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/ItemDTO"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/ItemDTO"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "Item"
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ItemModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/ItemModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/ItemModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/Item"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Item"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/Item"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/Item/{itemNo}": {
      "get": {
        "tags": [
          "Item"
        ],
        "parameters": [
          {
            "name": "itemNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/ItemDTO"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/ItemDTO"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/ItemDTO"
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/Item/{itemNo}/{rev}": {
      "get": {
        "tags": [
          "Item"
        ],
        "parameters": [
          {
            "name": "itemNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "rev",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/Item"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Item"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/Item"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "Item"
        ],
        "parameters": [
          {
            "name": "itemNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "rev",
            "in": "path",
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
    "/api/v1/Item/{itemNo}/{rev}/Program/AddProgramToItem": {
      "post": {
        "tags": [
          "Item"
        ],
        "parameters": [
          {
            "name": "itemNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "rev",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "simulated",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "boolean"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CncProgramToLogDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/CncProgramToLogDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/CncProgramToLogDTO"
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
    "/api/v1/Item/{itemNo}/{rev}/Program": {
      "get": {
        "tags": [
          "Item"
        ],
        "parameters": [
          {
            "name": "itemNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "rev",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/ItemCncProgramDTO"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/ItemCncProgramDTO"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/ItemCncProgramDTO"
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/Item/{itemNo}/{rev}/Program/{programId}": {
      "get": {
        "tags": [
          "Item"
        ],
        "parameters": [
          {
            "name": "itemNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "rev",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "programId",
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
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/CncProgramWithTimesDTO"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/CncProgramWithTimesDTO"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/CncProgramWithTimesDTO"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/Item/{itemNo}/{rev}/Program/{programId}/AddFixtureToProgram": {
      "post": {
        "tags": [
          "Item"
        ],
        "parameters": [
          {
            "name": "itemNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "rev",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "programId",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          },
          {
            "name": "fixtureNo",
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
    "/api/v1/Item/{itemNo}/{rev}/Program/{programId}/RemoveFixtureFromProgram": {
      "post": {
        "tags": [
          "Item"
        ],
        "parameters": [
          {
            "name": "itemNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "rev",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "programId",
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
    "/api/v1/Item/{itemNo}/{rev}/Inventory/Add": {
      "post": {
        "tags": [
          "Item"
        ],
        "parameters": [
          {
            "name": "itemNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "rev",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "locationId",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          },
          {
            "name": "quantity",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "number",
              "format": "double"
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
    "/api/v1/Item/{itemNo}/{rev}/Inventory/Remove": {
      "post": {
        "tags": [
          "Item"
        ],
        "parameters": [
          {
            "name": "itemNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "rev",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "locationId",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          },
          {
            "name": "quantity",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "number",
              "format": "double"
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
    "/api/v1/Item/{itemNo}/{rev}/Inventory": {
      "get": {
        "tags": [
          "Item"
        ],
        "parameters": [
          {
            "name": "itemNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "rev",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/ItemLocationDTO"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/ItemLocationDTO"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/ItemLocationDTO"
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/Location": {
      "get": {
        "tags": [
          "Location"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/LocationDTO"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/LocationDTO"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/LocationDTO"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "Location"
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/LocationModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/LocationModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/LocationModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/Location"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Location"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/Location"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/Location/{id}": {
      "get": {
        "tags": [
          "Location"
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
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/LocationDTO"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/LocationDTO"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/LocationDTO"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "Location"
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
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/LocationModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/LocationModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/LocationModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/Location"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Location"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/Location"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "Location"
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
    "/api/v1/LocationType": {
      "get": {
        "tags": [
          "LocationType"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/LocationType"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/LocationType"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/LocationType"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "LocationType"
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/LocationTypeModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/LocationTypeModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/LocationTypeModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/LocationType"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/LocationType"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/LocationType"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/LocationType/{id}": {
      "get": {
        "tags": [
          "LocationType"
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
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/LocationType"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/LocationType"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/LocationType"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "LocationType"
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
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/LocationTypeModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/LocationTypeModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/LocationTypeModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/LocationType"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/LocationType"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/LocationType"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "LocationType"
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
    "/api/v1/MachineCenter": {
      "get": {
        "tags": [
          "MachineCenter"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/MachineCenterWorkCenter"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/MachineCenterWorkCenter"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/MachineCenterWorkCenter"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "MachineCenter"
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/MachineCenterWorkCenterModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/MachineCenterWorkCenterModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/MachineCenterWorkCenterModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/MachineCenterWorkCenter"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/MachineCenterWorkCenter"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/MachineCenterWorkCenter"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/MachineCenter/{id}": {
      "get": {
        "tags": [
          "MachineCenter"
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
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/MachineCenterWorkCenter"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/MachineCenterWorkCenter"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/MachineCenterWorkCenter"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "MachineCenter"
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
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/MachineCenterWorkCenterModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/MachineCenterWorkCenterModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/MachineCenterWorkCenterModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/MachineCenterWorkCenter"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/MachineCenterWorkCenter"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/MachineCenterWorkCenter"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "MachineCenter"
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
    "/api/v1/MachineCenter/WorkCenter/{workCenterNo}": {
      "get": {
        "tags": [
          "MachineCenter"
        ],
        "parameters": [
          {
            "name": "workCenterNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/MachineCenterWorkCenter"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/MachineCenterWorkCenter"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/MachineCenterWorkCenter"
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/Notification": {
      "post": {
        "tags": [
          "Notification"
        ],
        "summary": "Creates a new notification and sends it to one or more recipients.",
        "requestBody": {
          "description": "The notification creation request containing the notification data and recipient IDs.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationCreationRequest"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationCreationRequest"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationCreationRequest"
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
    "/api/v1/Notification/{userId}": {
      "get": {
        "tags": [
          "Notification"
        ],
        "summary": "Retrieves notifications for a specified user with optional pagination.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user ID whose notifications should be fetched.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "limit",
            "in": "query",
            "description": "The number of notifications to return. \r\nIf set to 0, all notifications starting from the offset will be returned.",
            "style": "form",
            "schema": {
              "type": "integer",
              "format": "int32",
              "default": 0
            }
          },
          {
            "name": "offset",
            "in": "query",
            "description": "The zero-based index of the first notification to return.",
            "style": "form",
            "schema": {
              "type": "integer",
              "format": "int32",
              "default": 0
            }
          },
          {
            "name": "onlyUnread",
            "in": "query",
            "description": "If set to true, only unread notifications are returned.",
            "style": "form",
            "schema": {
              "type": "boolean",
              "default": false
            }
          },
          {
            "name": "singleLevel",
            "in": "query",
            "description": "If set to true, only a single level DTO will be returned.",
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
    "/api/v1/Notification/{userId}/{notificationId}": {
      "get": {
        "tags": [
          "Notification"
        ],
        "summary": "Retrieves notifications for a specified user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user ID whose notifications should be fetched.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "notificationId",
            "in": "path",
            "description": "The notification ID",
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
    "/api/v1/Notification/{userId}/{notificationId}/read": {
      "post": {
        "tags": [
          "Notification"
        ],
        "summary": "Marks a specific notification as read for a given user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "notificationId",
            "in": "path",
            "description": "The notification ID to mark as read.",
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
    "/api/v1/Notification/{userId}/readall": {
      "post": {
        "tags": [
          "Notification"
        ],
        "summary": "Marks all notifications as read for a given user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user ID.",
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
    "/api/v1/NotificationSubscription": {
      "get": {
        "tags": [
          "NotificationSubscription"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/NotificationSubscription"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/NotificationSubscription"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/NotificationSubscription"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "NotificationSubscription"
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationSubscriptionModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationSubscriptionModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationSubscriptionModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/NotificationSubscription"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/NotificationSubscription"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/NotificationSubscription"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/NotificationSubscription/{id}": {
      "get": {
        "tags": [
          "NotificationSubscription"
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
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/NotificationSubscription"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/NotificationSubscription"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/NotificationSubscription"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "NotificationSubscription"
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
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationSubscriptionModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationSubscriptionModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationSubscriptionModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/NotificationSubscription"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/NotificationSubscription"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/NotificationSubscription"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "NotificationSubscription"
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
    "/api/v1/NotificationTypes": {
      "get": {
        "tags": [
          "NotificationTypes"
        ],
        "summary": "Gets all notification types.",
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/NotificationTypes"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/NotificationTypes"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/NotificationTypes"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "NotificationTypes"
        ],
        "summary": "Creates a new notification type.",
        "requestBody": {
          "description": "The notification type creation DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationTypesCreationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationTypesCreationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationTypesCreationDTO"
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
    "/api/v1/NotificationTypes/{id}": {
      "get": {
        "tags": [
          "NotificationTypes"
        ],
        "summary": "Gets a notification type by ID.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The notification type ID.",
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
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/NotificationTypes"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/NotificationTypes"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/NotificationTypes"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "NotificationTypes"
        ],
        "summary": "Updates an existing notification type.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The notification type ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          }
        ],
        "requestBody": {
          "description": "The notification type update DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationTypesUpdateDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationTypesUpdateDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/NotificationTypesUpdateDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      },
      "delete": {
        "tags": [
          "NotificationTypes"
        ],
        "summary": "Deletes a notification type by ID.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The notification type ID.",
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
    "/api/v1/OvertimePeriod": {
      "get": {
        "tags": [
          "OvertimePeriod"
        ],
        "summary": "Retrieves all overtime periods.",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      },
      "post": {
        "tags": [
          "OvertimePeriod"
        ],
        "summary": "Creates a new overtime period.",
        "requestBody": {
          "description": "The DTO containing creation details.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/OvertimePeriodCreationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/OvertimePeriodCreationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/OvertimePeriodCreationDTO"
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
    "/api/v1/OvertimePeriod/{id}": {
      "get": {
        "tags": [
          "OvertimePeriod"
        ],
        "summary": "Retrieves an overtime period by its ID.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The ID of the overtime period.",
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
      },
      "put": {
        "tags": [
          "OvertimePeriod"
        ],
        "summary": "Updates an existing overtime period.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The ID of the overtime period to update.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          }
        ],
        "requestBody": {
          "description": "The DTO containing updated details.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/OvertimePeriodUpdateDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/OvertimePeriodUpdateDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/OvertimePeriodUpdateDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      },
      "delete": {
        "tags": [
          "OvertimePeriod"
        ],
        "summary": "Deletes an overtime period by its ID.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The ID of the overtime period to delete.",
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
    "/api/v1/OvertimePeriod/ByStartDate": {
      "get": {
        "tags": [
          "OvertimePeriod"
        ],
        "summary": "Retrieves overtime periods starting from a specified date or later.",
        "parameters": [
          {
            "name": "startDate",
            "in": "query",
            "description": "The start date for filtering overtime periods.",
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
    "/api/v1/OvertimePeriod/CurrentlyActive": {
      "get": {
        "tags": [
          "OvertimePeriod"
        ],
        "summary": "Retrieves currently active overtime periods.",
        "parameters": [
          {
            "name": "currentDate",
            "in": "query",
            "description": "The current date for filtering overtime periods.",
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
    "/api/v1/Permission": {
      "get": {
        "tags": [
          "Permission"
        ],
        "summary": "Gets all permissions.",
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Permission"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Permission"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Permission"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "Permission"
        ],
        "summary": "Creates a new permission.",
        "requestBody": {
          "description": "The permission creation DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PermissionCreationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/PermissionCreationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/PermissionCreationDTO"
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
    "/api/v1/Permission/{id}": {
      "get": {
        "tags": [
          "Permission"
        ],
        "summary": "Gets a permission by ID.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The permission ID.",
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
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/Permission"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Permission"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/Permission"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "Permission"
        ],
        "summary": "Updates an existing permission.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The permission ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          }
        ],
        "requestBody": {
          "description": "The permission update DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PermissionUpdateDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/PermissionUpdateDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/PermissionUpdateDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      },
      "delete": {
        "tags": [
          "Permission"
        ],
        "summary": "Deletes a permission by ID.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The permission ID.",
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
    "/api/v1/ProductionOrder/RunJobScheduler": {
      "get": {
        "tags": [
          "ProductionOrder"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/ProductionOrder/AllUnfinishedProductionOrderRoutingLine({workcenterNo})": {
      "get": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "workcenterNo",
            "in": "path",
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
    "/api/v1/ProductionOrder/InScheduleProductionOrderRoutingLine({workcenterNo})": {
      "get": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "workcenterNo",
            "in": "path",
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
    "/api/v1/ProductionOrder/LoadEverything": {
      "get": {
        "tags": [
          "ProductionOrder"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/ProductionOrder/SpecificGuidProductionOrderRoutingLine({systemId})": {
      "get": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "systemId",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string",
              "format": "uuid"
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
    "/api/v1/ProductionOrder/SpecificProductionOrderRoutingLine({prodOrderNo})": {
      "get": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "prodOrderNo",
            "in": "path",
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
    "/api/v1/ProductionOrder/SpecificProductionOrderRoutingLine({prodOrderNo})/comments": {
      "get": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "prodOrderNo",
            "in": "path",
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
    "/api/v1/ProductionOrder/ProductionOrderWorkCenterStatistics({workcenter})": {
      "get": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "workcenter",
            "in": "path",
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
    "/api/v1/ProductionOrder/PlannedWorkCenterCalendar({workcenter})": {
      "get": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "workcenter",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
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
    "/api/v1/ProductionOrder/ProductionOrderComponents({prodOrderNo},{lineNo})": {
      "get": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "prodOrderNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "lineNo",
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
    "/api/v1/ProductionOrder/ProductionOrderHeader({prodOrderNo},{lineNo})": {
      "get": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "prodOrderNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "lineNo",
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
    "/api/v1/ProductionOrder/UpdateTaskRush/{systemId}": {
      "post": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "systemId",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string",
              "format": "uuid"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdateRushDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdateRushDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdateRushDTO"
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
    "/api/v1/ProductionOrder/UpdateTaskPriority/{systemId}": {
      "post": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "systemId",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string",
              "format": "uuid"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdatePriorityDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdatePriorityDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdatePriorityDTO"
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
    "/api/v1/ProductionOrder/UpdateTaskStatus/{systemId}": {
      "post": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "systemId",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string",
              "format": "uuid"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdateStatusDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdateStatusDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdateStatusDTO"
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
    "/api/v1/ProductionOrder/AskForHelp/{systemId}": {
      "post": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "systemId",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string",
              "format": "uuid"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionOrderAskForHelpDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionOrderAskForHelpDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionOrderAskForHelpDTO"
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
    "/api/v1/ProductionOrder/UpdateTaskReservation/{systemId}": {
      "post": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "systemId",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string",
              "format": "uuid"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdateReservationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdateReservationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdateReservationDTO"
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
    "/api/v1/ProductionOrder/Completion/{systemId}": {
      "post": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "systemId",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string",
              "format": "uuid"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdateCompletionDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdateCompletionDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingTaskUpdateCompletionDTO"
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
    "/api/v1/ProductionOrder/AddComment/{systemId}": {
      "post": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "systemId",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string",
              "format": "uuid"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CommentsCreationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/CommentsCreationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/CommentsCreationDTO"
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
    "/api/v1/ProductionOrder/RemoveComment/{systemId}": {
      "post": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "systemId",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string",
              "format": "uuid"
            }
          },
          {
            "name": "commentId",
            "in": "query",
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
    "/api/v1/ProductionOrder/ManualRefresh/Workcenter": {
      "post": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "workcenterId",
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
    "/api/v1/ProductionOrder/ManualRefresh/ProdOrderNo": {
      "post": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "prodOrderNo",
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
    "/api/v1/ProductionOrder/ForceFullRefresh/Workcenter": {
      "post": {
        "tags": [
          "ProductionOrder"
        ],
        "parameters": [
          {
            "name": "workcenterId",
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
    "/api/v1/ProductionRoutingStatus": {
      "get": {
        "tags": [
          "ProductionRoutingStatus"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      },
      "post": {
        "tags": [
          "ProductionRoutingStatus"
        ],
        "summary": "DO NOT USE - Create a new Routing Status",
        "requestBody": {
          "description": "The Status creation DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingStatusCreationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingStatusCreationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingStatusCreationDTO"
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
    "/api/v1/ProductionRoutingStatus/{id}": {
      "get": {
        "tags": [
          "ProductionRoutingStatus"
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
      },
      "put": {
        "tags": [
          "ProductionRoutingStatus"
        ],
        "summary": "DO NOT USE - Update a Routing Status",
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
          "description": "The Status update DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingStatusUpdateDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingStatusUpdateDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/ProductionRoutingStatusUpdateDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      },
      "delete": {
        "tags": [
          "ProductionRoutingStatus"
        ],
        "summary": "DO NOT USE - Delete a Status by ID.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "id of the selected Status.",
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
    "/api/v1/ProductionStatistics/current/{workcenterId}": {
      "get": {
        "tags": [
          "ProductionStatistics"
        ],
        "summary": "Gets the current workcenter utilization.",
        "parameters": [
          {
            "name": "workcenterId",
            "in": "path",
            "description": "The workcenter ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "slotDurationMinute",
            "in": "query",
            "description": "The timeslot duration in minute.",
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
    "/api/v1/ProductionStatistics/planned/{workcenterId}": {
      "get": {
        "tags": [
          "ProductionStatistics"
        ],
        "summary": "Gets the planned workcenter utilization.",
        "parameters": [
          {
            "name": "workcenterId",
            "in": "path",
            "description": "The workcenter ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "slotDurationMinute",
            "in": "query",
            "description": "The timeslot duration in minute.",
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
    "/api/v1/Robotize/DailyTaskStatistics": {
      "get": {
        "tags": [
          "Robotize"
        ],
        "summary": "Retrieves daily task statistics within a specified date range.",
        "description": "Uses the Gilbert_BackEnd.API.Validator.ValidateDateRangeFilter to validate the date range.",
        "parameters": [
          {
            "name": "beginDate",
            "in": "query",
            "description": "The start date for the task statistics retrieval.",
            "style": "form",
            "schema": {
              "type": "string",
              "format": "date-time"
            }
          },
          {
            "name": "endDate",
            "in": "query",
            "description": "The end date for the task statistics retrieval. If not specified, defaults to the current date.",
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
    "/api/v1/Role": {
      "get": {
        "tags": [
          "Role"
        ],
        "summary": "Gets all roles.",
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Role"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Role"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Role"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "Role"
        ],
        "summary": "Creates a new role.",
        "requestBody": {
          "description": "The role creation DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/RoleCreationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/RoleCreationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/RoleCreationDTO"
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
    "/api/v1/Role/{id}": {
      "get": {
        "tags": [
          "Role"
        ],
        "summary": "Gets a role by ID.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The role ID.",
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
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/Role"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Role"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/Role"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "Role"
        ],
        "summary": "Updates an existing role.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The role ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          }
        ],
        "requestBody": {
          "description": "The role update DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/RoleUpdateDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/RoleUpdateDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/RoleUpdateDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      },
      "delete": {
        "tags": [
          "Role"
        ],
        "summary": "Deletes a role by ID.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The role ID.",
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
    "/api/v1/Role/{id}/permissions": {
      "get": {
        "tags": [
          "Role"
        ],
        "summary": "Gets the permissions for a role by ID.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The role ID.",
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
      },
      "post": {
        "tags": [
          "Role"
        ],
        "summary": "Adds a permission to a role.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The role ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          }
        ],
        "requestBody": {
          "description": "The role permission DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/RolePermissionDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/RolePermissionDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/RolePermissionDTO"
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
    "/api/v1/Role/{roleId}/permissions/{permissionId}": {
      "delete": {
        "tags": [
          "Role"
        ],
        "summary": "Removes a permission from a role.",
        "parameters": [
          {
            "name": "roleId",
            "in": "path",
            "description": "The role ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          },
          {
            "name": "permissionId",
            "in": "path",
            "description": "The permission ID.",
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
    "/api/v1/Role/{id}/permissionsSync": {
      "post": {
        "tags": [
          "Role"
        ],
        "summary": "Synchronize a permission list to a role.",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "description": "The role ID.",
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
            "application/json": {
              "schema": {
                "type": "array",
                "items": {
                  "$ref": "#/components/schemas/RolePermissionDTO"
                }
              }
            },
            "text/json": {
              "schema": {
                "type": "array",
                "items": {
                  "$ref": "#/components/schemas/RolePermissionDTO"
                }
              }
            },
            "application/*+json": {
              "schema": {
                "type": "array",
                "items": {
                  "$ref": "#/components/schemas/RolePermissionDTO"
                }
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
    "/api/v1/RoutingBom/line": {
      "get": {
        "tags": [
          "RoutingBom"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/RoutingBom"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/RoutingBom"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/RoutingBom"
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/RoutingBom/line/{routingNo}": {
      "get": {
        "tags": [
          "RoutingBom"
        ],
        "parameters": [
          {
            "name": "routingNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/RoutingBom"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/RoutingBom"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/RoutingBom"
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/RoutingBom/line/update": {
      "put": {
        "tags": [
          "RoutingBom"
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/RoutingBomUpdateDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/RoutingBomUpdateDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/RoutingBomUpdateDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "boolean"
                }
              },
              "application/json": {
                "schema": {
                  "type": "boolean"
                }
              },
              "text/json": {
                "schema": {
                  "type": "boolean"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/RoutingBom/header": {
      "get": {
        "tags": [
          "RoutingBom"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/RoutingBomHeader"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/RoutingBomHeader"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/RoutingBomHeader"
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/RoutingBom/header/{routingNo}": {
      "get": {
        "tags": [
          "RoutingBom"
        ],
        "parameters": [
          {
            "name": "routingNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/RoutingBomHeader"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/RoutingBomHeader"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/RoutingBomHeader"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/RoutingBom/header/status": {
      "put": {
        "tags": [
          "RoutingBom"
        ],
        "summary": "Updates the status of a Routing BOM header.",
        "requestBody": {
          "description": "The RoutingBomHeaderUpdateDTO containing the update information.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/RoutingBomHeaderUpdateDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/RoutingBomHeaderUpdateDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/RoutingBomHeaderUpdateDTO"
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
    "/api/v1/RoutingBom/updateRoutingFromData/{workcenter}": {
      "put": {
        "tags": [
          "RoutingBom"
        ],
        "parameters": [
          {
            "name": "workcenter",
            "in": "path",
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
    "/api/v1/RoutingTaskWebHook/handler": {
      "post": {
        "tags": [
          "RoutingTaskWebHook"
        ],
        "summary": "Endpoint to receive notifications.",
        "parameters": [
          {
            "name": "validationToken",
            "in": "query",
            "description": "The validation token.",
            "style": "form",
            "schema": {
              "type": "string",
              "default": ""
            }
          }
        ],
        "requestBody": {
          "description": "The JSON object received in the notification.",
          "content": {
            "application/json": {
              "schema": { }
            },
            "text/json": {
              "schema": { }
            },
            "application/*+json": {
              "schema": { }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      },
      "get": {
        "tags": [
          "RoutingTaskWebHook"
        ],
        "summary": "Endpoint for Handshake.",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/RoutingTaskWebHook": {
      "get": {
        "tags": [
          "RoutingTaskWebHook"
        ],
        "summary": "Endpoint for Handshake.",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/RoutingTaskWebHook/GetOrCreateSubscription": {
      "get": {
        "tags": [
          "RoutingTaskWebHook"
        ],
        "summary": "Endpoint for Handshake.",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/SeedData/SeedDepartments": {
      "post": {
        "tags": [
          "SeedData"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/SeedData/SeedProductionRoutingTask": {
      "post": {
        "tags": [
          "SeedData"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/SeedData/SeedProductionRoutingTaskStartedStatus": {
      "post": {
        "tags": [
          "SeedData"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/SeedData/SeedUsers": {
      "post": {
        "tags": [
          "SeedData"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/SeedData/SeedSkills": {
      "post": {
        "tags": [
          "SeedData"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/SeedData/SeedMissingItems": {
      "post": {
        "tags": [
          "SeedData"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/SeedData/SeedFastem2EventPrograms": {
      "post": {
        "tags": [
          "SeedData"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/SeedData/SeedFastem2EventPrograms_QtyMadeCorrection": {
      "post": {
        "tags": [
          "SeedData"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/SeedData/SeedSigmaNestPrograms": {
      "post": {
        "tags": [
          "SeedData"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/SeedData/SeedSigmaNestPrograms_QtyMadeCorrection": {
      "post": {
        "tags": [
          "SeedData"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/SeedData/SeedFixture": {
      "post": {
        "tags": [
          "SeedData"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/SeedData/SeedOperatorRoleToAll": {
      "post": {
        "tags": [
          "SeedData"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/SeedData/SeedMissingMachineWorkCenter": {
      "post": {
        "tags": [
          "SeedData"
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/SignalRStats/clients": {
      "get": {
        "tags": [
          "SignalRStats"
        ],
        "parameters": [
          {
            "name": "RemoveServerSide",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "boolean"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/SignalRClientInfo"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/SignalRClientInfo"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/SignalRClientInfo"
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/SkillLevel": {
      "get": {
        "tags": [
          "SkillLevel"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/SkillLevel"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/SkillLevel"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/SkillLevel"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "SkillLevel"
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/SkillLevelModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/SkillLevelModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/SkillLevelModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/SkillLevel"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/SkillLevel"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/SkillLevel"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/SkillLevel/{id}": {
      "get": {
        "tags": [
          "SkillLevel"
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
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/SkillLevel"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/SkillLevel"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/SkillLevel"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "SkillLevel"
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
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/SkillLevelModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/SkillLevelModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/SkillLevelModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/SkillLevel"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/SkillLevel"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/SkillLevel"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "SkillLevel"
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
    "/api/v1/Skills": {
      "get": {
        "tags": [
          "Skills"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Skills"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Skills"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Skills"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "Skills"
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/SkillsModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/SkillsModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/SkillsModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/Skills"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Skills"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/Skills"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/Skills/{id}": {
      "get": {
        "tags": [
          "Skills"
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
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/Skills"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Skills"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/Skills"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "Skills"
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
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/SkillsModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/SkillsModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/SkillsModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/Skills"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Skills"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/Skills"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "Skills"
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
    "/api/v1/Subscription": {
      "get": {
        "tags": [
          "Subscription"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Subscription"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Subscription"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Subscription"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "Subscription"
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/SubscriptionCreationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/SubscriptionCreationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/SubscriptionCreationDTO"
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Created",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/Subscription"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Subscription"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/Subscription"
                }
              }
            }
          },
          "400": {
            "description": "Bad Request",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/ProblemDetails"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ProblemDetails"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/ProblemDetails"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/Subscription/{id}": {
      "put": {
        "tags": [
          "Subscription"
        ],
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "eTag",
            "in": "query",
            "style": "form",
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/SubscriptionCreationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/SubscriptionCreationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/SubscriptionCreationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/Subscription"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Subscription"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/Subscription"
                }
              }
            }
          },
          "404": {
            "description": "Not Found",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/ProblemDetails"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ProblemDetails"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/ProblemDetails"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "Subscription"
        ],
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "204": {
            "description": "No Content"
          },
          "404": {
            "description": "Not Found",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/ProblemDetails"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ProblemDetails"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/ProblemDetails"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/TaskItem": {
      "post": {
        "tags": [
          "TaskItem"
        ],
        "summary": "Creates a new task.",
        "requestBody": {
          "description": "The task object to create.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/TaskItemCreationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/TaskItemCreationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/TaskItemCreationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      },
      "get": {
        "tags": [
          "TaskItem"
        ],
        "summary": "Retrieves all tasks.",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    },
    "/api/v1/TaskItem/{taskId}": {
      "get": {
        "tags": [
          "TaskItem"
        ],
        "summary": "Retrieves a task by its ID.",
        "parameters": [
          {
            "name": "taskId",
            "in": "path",
            "description": "The unique identifier of the task.",
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
      },
      "put": {
        "tags": [
          "TaskItem"
        ],
        "summary": "Updates an existing task.",
        "parameters": [
          {
            "name": "taskId",
            "in": "path",
            "description": "The ID of the task to update.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          }
        ],
        "requestBody": {
          "description": "The task object containing updated information.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/TaskItemUpdateDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/TaskItemUpdateDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/TaskItemUpdateDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      },
      "delete": {
        "tags": [
          "TaskItem"
        ],
        "summary": "Deletes a task by its ID.",
        "parameters": [
          {
            "name": "taskId",
            "in": "path",
            "description": "The unique identifier of the task to delete.",
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
    "/api/v1/TaskItem/{taskId}/watchers/{watcherId}": {
      "post": {
        "tags": [
          "TaskItem"
        ],
        "summary": "Adds a watcher to a task.",
        "parameters": [
          {
            "name": "taskId",
            "in": "path",
            "description": "The task ID to add a watcher to.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          },
          {
            "name": "watcherId",
            "in": "path",
            "description": "The ID of the user to add as a watcher.",
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
      },
      "delete": {
        "tags": [
          "TaskItem"
        ],
        "summary": "Removes a watcher from a task.",
        "parameters": [
          {
            "name": "taskId",
            "in": "path",
            "description": "The task ID to remove a watcher from.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          },
          {
            "name": "watcherId",
            "in": "path",
            "description": "The ID of the user to remove as a watcher.",
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
    "/api/v1/TaskItem/{taskId}/status/{newStatusId}": {
      "put": {
        "tags": [
          "TaskItem"
        ],
        "summary": "Updates the status of a task.",
        "parameters": [
          {
            "name": "taskId",
            "in": "path",
            "description": "The task ID to update.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          },
          {
            "name": "newStatusId",
            "in": "path",
            "description": "The ID of the new status.",
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
    "/api/v1/TaskItem/{taskId}/completion/{newCompletionPercentage}": {
      "put": {
        "tags": [
          "TaskItem"
        ],
        "summary": "Updates the completion percentage of a task.",
        "parameters": [
          {
            "name": "taskId",
            "in": "path",
            "description": "The task ID to update.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          },
          {
            "name": "newCompletionPercentage",
            "in": "path",
            "description": "The new completion percentage.",
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
    "/api/v1/TaskItem/{taskId}/comments": {
      "post": {
        "tags": [
          "TaskItem"
        ],
        "summary": "Adds a comment to a task.",
        "parameters": [
          {
            "name": "taskId",
            "in": "path",
            "description": "The ID of the task to add the comment to.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          }
        ],
        "requestBody": {
          "description": "The comment object containing the message.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CommentsCreationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/CommentsCreationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/CommentsCreationDTO"
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
    "/api/v1/TaskStatus": {
      "get": {
        "tags": [
          "TaskStatus"
        ],
        "summary": "Retrieves all task statuses.",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      },
      "post": {
        "tags": [
          "TaskStatus"
        ],
        "summary": "Creates a new task status.",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/TaskStatusCreationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/TaskStatusCreationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/TaskStatusCreationDTO"
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
    "/api/v1/TaskStatus/{id}": {
      "get": {
        "tags": [
          "TaskStatus"
        ],
        "summary": "Retrieves a task status by its ID.",
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
      },
      "put": {
        "tags": [
          "TaskStatus"
        ],
        "summary": "Updates an existing task status.",
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
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/TaskStatusUpdateDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/TaskStatusUpdateDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/TaskStatusUpdateDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      },
      "delete": {
        "tags": [
          "TaskStatus"
        ],
        "summary": "Deletes a task status.",
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
    "/api/v1/UserActionLog/{userId}": {
      "get": {
        "tags": [
          "UserActionLog"
        ],
        "summary": "Retrieves user action logs for a specified user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "User ID to retrieve logs for.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "since",
            "in": "query",
            "description": "Date to filter logs generated since.",
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
    "/api/v1/Users/{userId}": {
      "get": {
        "tags": [
          "Users"
        ],
        "summary": "Gets a user by their ID.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/User"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/User"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/User"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "Users"
        ],
        "summary": "Updates an existing user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "description": "The user update DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/UserCreationModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/UserCreationModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/UserCreationModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/UserDTO"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/UserDTO"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/UserDTO"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "Users"
        ],
        "summary": "Deletes a user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
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
    "/api/v1/Users": {
      "get": {
        "tags": [
          "Users"
        ],
        "summary": "Gets all users.",
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/User"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/User"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/User"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "Users"
        ],
        "summary": "Creates a new user.",
        "requestBody": {
          "description": "The user creation DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/UserCreationModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/UserCreationModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/UserCreationModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/User"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/User"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/User"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/Users/{userId}/roles": {
      "get": {
        "tags": [
          "Users"
        ],
        "summary": "Gets roles for a specific user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
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
      },
      "post": {
        "tags": [
          "Users"
        ],
        "summary": "Adds a role to a user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "description": "The user role DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/UserRoleDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/UserRoleDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/UserRoleDTO"
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
    "/api/v1/Users/{userId}/roles/{roleId}": {
      "delete": {
        "tags": [
          "Users"
        ],
        "summary": "Removes a role from a user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "roleId",
            "in": "path",
            "description": "The role ID.",
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
    "/api/v1/Users/{userId}/departments": {
      "get": {
        "tags": [
          "Users"
        ],
        "summary": "Gets departments for a specific user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
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
      },
      "post": {
        "tags": [
          "Users"
        ],
        "summary": "Adds a department to a user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "description": "The user department DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/UserDepartmentDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/UserDepartmentDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/UserDepartmentDTO"
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
    "/api/v1/Users/{userId}/departments/{departmentId}": {
      "delete": {
        "tags": [
          "Users"
        ],
        "summary": "Removes a department from a user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "departmentId",
            "in": "path",
            "description": "The department ID.",
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
    "/api/v1/Users/{userId}/departments/sync": {
      "put": {
        "tags": [
          "Users"
        ],
        "summary": "Synchronizes departments for a user (replaces all existing departments with the provided list).",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "description": "List of department IDs to set. Pass empty list to remove all departments.",
          "content": {
            "application/json": {
              "schema": {
                "type": "array",
                "items": {
                  "type": "integer",
                  "format": "int32"
                }
              }
            },
            "text/json": {
              "schema": {
                "type": "array",
                "items": {
                  "type": "integer",
                  "format": "int32"
                }
              }
            },
            "application/*+json": {
              "schema": {
                "type": "array",
                "items": {
                  "type": "integer",
                  "format": "int32"
                }
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
    "/api/v1/Users/{userId}/roles/sync": {
      "put": {
        "tags": [
          "Users"
        ],
        "summary": "Synchronizes roles for a user (replaces all existing roles with the provided list).",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "description": "List of role IDs to set. Pass empty list to remove all roles.",
          "content": {
            "application/json": {
              "schema": {
                "type": "array",
                "items": {
                  "type": "integer",
                  "format": "int32"
                }
              }
            },
            "text/json": {
              "schema": {
                "type": "array",
                "items": {
                  "type": "integer",
                  "format": "int32"
                }
              }
            },
            "application/*+json": {
              "schema": {
                "type": "array",
                "items": {
                  "type": "integer",
                  "format": "int32"
                }
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
    "/api/v1/Users/{userId}/skills": {
      "get": {
        "tags": [
          "Users"
        ],
        "summary": "Gets skillset for a specific user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
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
      },
      "post": {
        "tags": [
          "Users"
        ],
        "summary": "Adds a Skill to a user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "description": "The user Skill DTO.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/UserSkillsModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/UserSkillsModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/UserSkillsModificationDTO"
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
    "/api/v1/Users/{userId}/skills/{skillId}": {
      "delete": {
        "tags": [
          "Users"
        ],
        "summary": "Removes a Skill from a user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "skillId",
            "in": "path",
            "description": "The Skill's ID.",
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
    "/api/v1/Users/{userId}/skills/sync": {
      "put": {
        "tags": [
          "Users"
        ],
        "summary": "Synchronize a Skill list to a user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "array",
                "items": {
                  "$ref": "#/components/schemas/UserSkillsModificationDTO"
                }
              }
            },
            "text/json": {
              "schema": {
                "type": "array",
                "items": {
                  "$ref": "#/components/schemas/UserSkillsModificationDTO"
                }
              }
            },
            "application/*+json": {
              "schema": {
                "type": "array",
                "items": {
                  "$ref": "#/components/schemas/UserSkillsModificationDTO"
                }
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
    "/api/v1/Users/{userId}/effectivePermissions": {
      "get": {
        "tags": [
          "Users"
        ],
        "summary": "Retrieve the Effective Permission Lists for a specific user.",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "description": "The user's ID.",
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
    "/api/v1/VolatileLogger/logs": {
      "get": {
        "tags": [
          "VolatileLogger"
        ],
        "summary": "Gets all logs without filtering",
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/LogItem"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/LogItem"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/LogItem"
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/VolatileLogger/logs/filter": {
      "get": {
        "tags": [
          "VolatileLogger"
        ],
        "summary": "Gets logs filtered by origin (contains match, case-insensitive)",
        "parameters": [
          {
            "name": "originFilter",
            "in": "query",
            "description": "The origin filter string to search for",
            "style": "form",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/LogItem"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/LogItem"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/LogItem"
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/WorkActivity/search": {
      "post": {
        "tags": [
          "WorkActivity"
        ],
        "summary": "Gets activities based on filter criteria.",
        "requestBody": {
          "description": "The filter criteria.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/WorkActivityFilterDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/WorkActivityFilterDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/WorkActivityFilterDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/WorkActivityDTO"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/WorkActivityDTO"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/WorkActivityDTO"
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/WorkCenter/Usine": {
      "get": {
        "tags": [
          "WorkCenter"
        ],
        "summary": "Retrieves Factory work centers.",
        "responses": {
          "200": {
            "description": "Success"
          },
          "500": {
            "description": "An error occurred while fetching work centers."
          }
        }
      }
    },
    "/api/v1/WorkCenter/Traitement": {
      "get": {
        "tags": [
          "WorkCenter"
        ],
        "summary": "Retrieves Traitement work centers.",
        "responses": {
          "200": {
            "description": "Success"
          },
          "500": {
            "description": "An error occurred while fetching work centers."
          }
        }
      }
    },
    "/api/v1/WorkCenter/Autre": {
      "get": {
        "tags": [
          "WorkCenter"
        ],
        "summary": "Retrieves Other work centers.",
        "responses": {
          "200": {
            "description": "Success"
          },
          "500": {
            "description": "An error occurred while fetching work centers."
          }
        }
      }
    },
    "/api/v1/WorkCenter": {
      "get": {
        "tags": [
          "WorkCenter"
        ],
        "summary": "Retrieves all the work centers.",
        "responses": {
          "200": {
            "description": "Success"
          },
          "500": {
            "description": "An error occurred while fetching work centers."
          }
        }
      }
    },
    "/api/v1/WorkCenter/Specific": {
      "get": {
        "tags": [
          "WorkCenter"
        ],
        "summary": "Retrieves a specific work center.",
        "parameters": [
          {
            "name": "workcenterNo",
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
          },
          "500": {
            "description": "An error occurred while fetching work centers."
          }
        }
      }
    },
    "/api/v1/WorkCenter/AssociatedDepartments": {
      "get": {
        "tags": [
          "WorkCenter"
        ],
        "summary": "Retrieves all departments associated with a workcenter.",
        "responses": {
          "200": {
            "description": "Success"
          },
          "500": {
            "description": "An error occurred while fetching associated departments."
          }
        }
      }
    },
    "/api/v1/WorkCenter/{departmentId}": {
      "get": {
        "tags": [
          "WorkCenter"
        ],
        "summary": "Retrieves Other work centers.",
        "parameters": [
          {
            "name": "departmentId",
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
          },
          "500": {
            "description": "An error occurred while fetching work centers."
          }
        }
      }
    },
    "/api/v1/WorkCenter/{workcenterNo}/departments/{departmentId}": {
      "delete": {
        "tags": [
          "WorkCenter"
        ],
        "summary": "Removes a workcenter from a department.",
        "parameters": [
          {
            "name": "departmentId",
            "in": "path",
            "description": "The department ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          },
          {
            "name": "workcenterNo",
            "in": "path",
            "description": "The workcenter number.",
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
          },
          "500": {
            "description": "An error occurred while removing the work center from the department."
          }
        }
      },
      "post": {
        "tags": [
          "WorkCenter"
        ],
        "summary": "Adds a workcenter to a department.",
        "parameters": [
          {
            "name": "departmentId",
            "in": "path",
            "description": "The department ID.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          },
          {
            "name": "workcenterNo",
            "in": "path",
            "description": "The workcenter number.",
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
          },
          "500": {
            "description": "An error occurred while adding the work center to the department."
          }
        }
      }
    },
    "/api/v1/WorkCenter/{workcenterNo}/departments": {
      "get": {
        "tags": [
          "WorkCenter"
        ],
        "summary": "Retrieves departments associated with a specific workcenter.",
        "parameters": [
          {
            "name": "workcenterNo",
            "in": "path",
            "description": "The workcenter number.",
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
          },
          "500": {
            "description": "An error occurred while fetching associated departments."
          }
        }
      }
    },
    "/api/v1/WorkCenter/{workcenterNo}/machines": {
      "get": {
        "tags": [
          "WorkCenter"
        ],
        "parameters": [
          {
            "name": "workcenterNo",
            "in": "path",
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
    "/api/v1/WorkCenter/Unassociated": {
      "get": {
        "tags": [
          "WorkCenter"
        ],
        "summary": "Retrieves unassociated Workcenter between Business Central ERP and SQL Server",
        "responses": {
          "200": {
            "description": "Success"
          },
          "500": {
            "description": "An error occurred while fetching associated departments."
          }
        }
      }
    },
    "/api/v1/WorkCenter/{workcenterNo}/calendarEntries": {
      "get": {
        "tags": [
          "WorkCenter"
        ],
        "summary": "Retrieves all the calendar entries related to a particular WorkCenter from a starting Date to an End Date",
        "parameters": [
          {
            "name": "workcenterNo",
            "in": "path",
            "description": "The workcenter number.",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "startingDate",
            "in": "query",
            "description": "The starting date for the entry list",
            "style": "form",
            "schema": {
              "type": "string",
              "format": "date-time"
            }
          },
          {
            "name": "endDate",
            "in": "query",
            "description": "The end date for the entry list",
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
          },
          "500": {
            "description": "An error occurred while fetching associated calendar entries."
          }
        }
      }
    },
    "/api/v1/WorkCenter/{workcenterNo}/SetupSheetPath": {
      "post": {
        "tags": [
          "WorkCenter"
        ],
        "parameters": [
          {
            "name": "workcenterNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/WorkCenterSDPModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/WorkCenterSDPModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/WorkCenterSDPModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "WorkCenter"
        ],
        "parameters": [
          {
            "name": "workcenterNo",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/WorkCenterSDPModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/WorkCenterSDPModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/WorkCenterSDPModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/WorkCenterSDP": {
      "get": {
        "tags": [
          "WorkCenterSDP"
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/WorkCenterSDP"
                  }
                }
              },
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/WorkCenterSDP"
                  }
                }
              },
              "text/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/WorkCenterSDP"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "WorkCenterSDP"
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/WorkCenterSDPModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/WorkCenterSDPModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/WorkCenterSDPModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/WorkCenterSDP/{id}": {
      "get": {
        "tags": [
          "WorkCenterSDP"
        ],
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "WorkCenterSDP"
        ],
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "style": "simple",
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/WorkCenterSDPModificationDTO"
              }
            },
            "text/json": {
              "schema": {
                "$ref": "#/components/schemas/WorkCenterSDPModificationDTO"
              }
            },
            "application/*+json": {
              "schema": {
                "$ref": "#/components/schemas/WorkCenterSDPModificationDTO"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "text/plain": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              },
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              },
              "text/json": {
                "schema": {
                  "$ref": "#/components/schemas/WorkCenterSDP"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "WorkCenterSDP"
        ],
        "parameters": [
          {
            "name": "id",
            "in": "path",
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
    }
  },
  "components": {
    "schemas": {
      "Certification": {
        "type": "object",
        "properties": {
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "itemNo": {
            "type": "string",
            "nullable": true
          },
          "programNo": {
            "type": "string",
            "nullable": true
          },
          "workcenterNo": {
            "type": "string",
            "nullable": true
          },
          "revision": {
            "type": "string",
            "nullable": true
          },
          "comment": {
            "type": "string",
            "nullable": true
          },
          "creationDate": {
            "type": "string",
            "format": "date-time"
          },
          "modificationDate": {
            "type": "string",
            "format": "date-time",
            "nullable": true
          },
          "createdByUserId": {
            "type": "string",
            "nullable": true
          },
          "modifiedByUserId": {
            "type": "string",
            "nullable": true
          },
          "createdBy": {
            "$ref": "#/components/schemas/User"
          },
          "modifiedBy": {
            "$ref": "#/components/schemas/User"
          },
          "certificationCriteria": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/CertificationCertificationCriteria"
            },
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "CertificationCertificationCriteria": {
        "type": "object",
        "properties": {
          "certificationId": {
            "type": "integer",
            "format": "int32"
          },
          "criteriaId": {
            "type": "integer",
            "format": "int32"
          },
          "currentValue": {
            "type": "boolean"
          },
          "associatedUserUserId": {
            "type": "string",
            "nullable": true
          },
          "certification": {
            "$ref": "#/components/schemas/Certification"
          },
          "criteria": {
            "$ref": "#/components/schemas/CertificationCriteria"
          },
          "associatedUser": {
            "$ref": "#/components/schemas/User"
          }
        },
        "additionalProperties": false
      },
      "CertificationCertificationCriteriaDTO": {
        "type": "object",
        "properties": {
          "criteriaId": {
            "type": "integer",
            "format": "int32"
          },
          "currentValue": {
            "type": "boolean"
          },
          "name": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "associatedUser": {
            "$ref": "#/components/schemas/UserDTO"
          }
        },
        "additionalProperties": false
      },
      "CertificationCertificationCriteriaUpdateDTO": {
        "type": "object",
        "properties": {
          "currentValue": {
            "type": "boolean"
          },
          "associatedUserUserId": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "CertificationCriteria": {
        "type": "object",
        "properties": {
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "name": {
            "type": "string",
            "nullable": true
          },
          "certificationPenality": {
            "type": "number",
            "format": "double"
          },
          "maximumCertificationLevel": {
            "type": "integer",
            "format": "int32"
          },
          "applicableOnlyToWorkCenterNo": {
            "type": "string",
            "nullable": true
          },
          "certificationCertifications": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/CertificationCertificationCriteria"
            },
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "CertificationCriteriaCreationDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          },
          "applicableOnlyToWorkCenterNo": {
            "type": "string",
            "nullable": true
          },
          "certificationPenality": {
            "type": "number",
            "format": "double"
          },
          "maximumCertificationLevel": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "CertificationCriteriaUpdateDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          },
          "applicableOnlyToWorkCenterNo": {
            "type": "string",
            "nullable": true
          },
          "certificationPenality": {
            "type": "number",
            "format": "double"
          },
          "maximumCertificationLevel": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "CertificationDTO": {
        "type": "object",
        "properties": {
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "itemNo": {
            "type": "string",
            "nullable": true
          },
          "programNo": {
            "type": "string",
            "nullable": true
          },
          "workcenterNo": {
            "type": "string",
            "nullable": true
          },
          "revision": {
            "type": "string",
            "nullable": true
          },
          "comment": {
            "type": "string",
            "nullable": true
          },
          "creationDate": {
            "type": "string",
            "format": "date-time"
          },
          "modificationDate": {
            "type": "string",
            "format": "date-time",
            "nullable": true
          },
          "maximumCertificationLevel": {
            "type": "integer",
            "format": "int32",
            "readOnly": true
          },
          "totalPenality": {
            "type": "number",
            "format": "double",
            "readOnly": true
          },
          "currentCertificationLevel": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "createdBy": {
            "$ref": "#/components/schemas/UserDTO"
          },
          "modifiedBy": {
            "$ref": "#/components/schemas/UserDTO"
          },
          "certificationCriteria": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/CertificationCertificationCriteriaDTO"
            },
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "CertificationsCreationDTO": {
        "type": "object",
        "properties": {
          "itemNo": {
            "type": "string",
            "nullable": true
          },
          "programNo": {
            "type": "string",
            "nullable": true
          },
          "workcenterNo": {
            "type": "string",
            "nullable": true
          },
          "revision": {
            "type": "string",
            "nullable": true
          },
          "comment": {
            "type": "string",
            "nullable": true
          },
          "associatedUserId": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "CertificationsUpdateDTO": {
        "type": "object",
        "properties": {
          "itemNo": {
            "type": "string",
            "nullable": true
          },
          "programNo": {
            "type": "string",
            "nullable": true
          },
          "workcenterNo": {
            "type": "string",
            "nullable": true
          },
          "revision": {
            "type": "string",
            "nullable": true
          },
          "comment": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "CncProgram": {
        "type": "object",
        "properties": {
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "name": {
            "type": "string",
            "nullable": true
          },
          "itemNo": {
            "type": "string",
            "nullable": true
          },
          "revision": {
            "type": "string",
            "nullable": true
          },
          "workCenterNo": {
            "type": "string",
            "nullable": true
          },
          "operation": {
            "type": "string",
            "nullable": true
          },
          "simulatedCncTimeId": {
            "type": "integer",
            "format": "int32",
            "nullable": true
          },
          "fixtureNo": {
            "type": "string",
            "nullable": true
          },
          "simulatedProgramTime": {
            "$ref": "#/components/schemas/CncTime"
          },
          "averageCncProgramTime": {
            "$ref": "#/components/schemas/CncTimeAverageDTO"
          },
          "fixture": {
            "$ref": "#/components/schemas/Fixture"
          }
        },
        "additionalProperties": false
      },
      "CncProgramDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          },
          "workCenterNo": {
            "type": "string",
            "nullable": true
          },
          "operation": {
            "type": "string",
            "nullable": true
          },
          "simulatedProgramTime": {
            "$ref": "#/components/schemas/CncTime"
          },
          "averageCncProgramTime": {
            "$ref": "#/components/schemas/CncTimeAverageDTO"
          },
          "fixture": {
            "$ref": "#/components/schemas/FixtureDTO"
          },
          "programTimeCount": {
            "type": "integer",
            "format": "int32",
            "readOnly": true
          }
        },
        "additionalProperties": false
      },
      "CncProgramTimeDTO": {
        "type": "object",
        "properties": {
          "timestamp": {
            "type": "string",
            "format": "date-time"
          },
          "cncTime": {
            "$ref": "#/components/schemas/CncTime"
          }
        },
        "additionalProperties": false
      },
      "CncProgramToLogDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          },
          "workCenterNo": {
            "type": "string",
            "nullable": true
          },
          "operation": {
            "type": "string",
            "nullable": true
          },
          "timeStamp": {
            "type": "string",
            "format": "date-time"
          },
          "timeConsumption": {
            "$ref": "#/components/schemas/CncTimeModificationDTO"
          }
        },
        "additionalProperties": false
      },
      "CncProgramWithTimesDTO": {
        "type": "object",
        "properties": {
          "cncProgramId": {
            "type": "integer",
            "format": "int32"
          },
          "name": {
            "type": "string",
            "nullable": true
          },
          "workCenterNo": {
            "type": "string",
            "nullable": true
          },
          "operation": {
            "type": "string",
            "nullable": true
          },
          "simulatedProgramTime": {
            "$ref": "#/components/schemas/CncTime"
          },
          "averageCncProgramTime": {
            "$ref": "#/components/schemas/CncTimeAverageDTO"
          },
          "fixture": {
            "$ref": "#/components/schemas/FixtureDTO"
          },
          "programTimeCount": {
            "type": "integer",
            "format": "int32",
            "readOnly": true
          },
          "cncProgramTimes": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/CncProgramTimeDTO"
            },
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "CncTime": {
        "type": "object",
        "properties": {
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "setupTime": {
            "type": "integer",
            "format": "int32"
          },
          "runTime": {
            "type": "integer",
            "format": "int32"
          },
          "activeTime": {
            "type": "integer",
            "format": "int32"
          },
          "qtyMade": {
            "type": "integer",
            "format": "int32"
          },
          "programSuccessful": {
            "type": "boolean"
          }
        },
        "additionalProperties": false
      },
      "CncTimeAverageDTO": {
        "type": "object",
        "properties": {
          "SetupTime": {
            "type": "integer",
            "format": "int32"
          },
          "RunTimePerItem": {
            "type": "integer",
            "format": "int32"
          },
          "ActiveTimePerItem": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "CncTimeModificationDTO": {
        "type": "object",
        "properties": {
          "setupTime": {
            "type": "integer",
            "format": "int32"
          },
          "runTime": {
            "type": "integer",
            "format": "int32"
          },
          "activeTime": {
            "type": "integer",
            "format": "int32"
          },
          "qtyMade": {
            "type": "integer",
            "format": "int32"
          },
          "programSuccessful": {
            "type": "boolean"
          }
        },
        "additionalProperties": false
      },
      "CommentsCreationDTO": {
        "type": "object",
        "properties": {
          "comment": {
            "type": "string",
            "nullable": true
          },
          "critical": {
            "type": "boolean"
          }
        },
        "additionalProperties": false
      },
      "Department": {
        "type": "object",
        "properties": {
          "typeName": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "parentId": {
            "type": "integer",
            "format": "int32",
            "nullable": true
          },
          "children": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/Department"
            },
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "DepartmentCreationDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "parentId": {
            "type": "integer",
            "format": "int32",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "DepartmentUpdateDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "parentId": {
            "type": "integer",
            "format": "int32",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "Fixture": {
        "type": "object",
        "properties": {
          "typeName": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "fixtureNo": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "receiverId": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "FixtureDTO": {
        "type": "object",
        "properties": {
          "fixtureNo": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "receiverId": {
            "type": "integer",
            "format": "int32"
          },
          "fixtureLocations": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/FixtureLocationDTO"
            },
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "FixtureLocationDTO": {
        "type": "object",
        "properties": {
          "fixtureNo": {
            "type": "string",
            "nullable": true
          },
          "quantity": {
            "type": "number",
            "format": "double"
          },
          "lastModified": {
            "type": "string",
            "format": "date-time"
          },
          "location": {
            "$ref": "#/components/schemas/LocationDTO"
          }
        },
        "additionalProperties": false
      },
      "FixtureModificationDTO": {
        "type": "object",
        "properties": {
          "fixtureNo": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "receiverId": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "FixtureReceiver": {
        "type": "object",
        "properties": {
          "typeName": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "quantity": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "FixtureReceiverModificationDTO": {
        "type": "object",
        "properties": {
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "quantity": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "Item": {
        "type": "object",
        "properties": {
          "typeName": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "itemNo": {
            "type": "string",
            "nullable": true
          },
          "revision": {
            "type": "string",
            "nullable": true
          },
          "itemCncPrograms": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/ItemCncProgram"
            },
            "nullable": true
          },
          "itemLocations": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/ItemLocation"
            },
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "ItemCncProgram": {
        "type": "object",
        "properties": {
          "itemNo": {
            "type": "string",
            "nullable": true
          },
          "revision": {
            "type": "string",
            "nullable": true
          },
          "cncProgramId": {
            "type": "integer",
            "format": "int32"
          },
          "cncProgram": {
            "$ref": "#/components/schemas/CncProgram"
          }
        },
        "additionalProperties": false
      },
      "ItemCncProgramDTO": {
        "type": "object",
        "properties": {
          "itemNo": {
            "type": "string",
            "nullable": true
          },
          "revision": {
            "type": "string",
            "nullable": true
          },
          "cncProgramId": {
            "type": "integer",
            "format": "int32"
          },
          "cncProgram": {
            "$ref": "#/components/schemas/CncProgramDTO"
          }
        },
        "additionalProperties": false
      },
      "ItemDTO": {
        "type": "object",
        "properties": {
          "mainKey": {
            "nullable": true
          },
          "typeName": {
            "type": "string",
            "nullable": true
          },
          "itemNo": {
            "type": "string",
            "nullable": true
          },
          "revision": {
            "type": "string",
            "nullable": true
          },
          "cncPrograms": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/CncProgramDTO"
            },
            "nullable": true,
            "readOnly": true
          },
          "itemLocations": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/ItemLocationDTO"
            },
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "ItemLocation": {
        "type": "object",
        "properties": {
          "locationID": {
            "type": "integer",
            "format": "int32"
          },
          "itemNo": {
            "type": "string",
            "nullable": true
          },
          "revision": {
            "type": "string",
            "nullable": true
          },
          "quantity": {
            "type": "number",
            "format": "double"
          },
          "lastModified": {
            "type": "string",
            "format": "date-time"
          },
          "location": {
            "$ref": "#/components/schemas/Location"
          }
        },
        "additionalProperties": false
      },
      "ItemLocationDTO": {
        "type": "object",
        "properties": {
          "locationID": {
            "type": "integer",
            "format": "int32"
          },
          "itemNo": {
            "type": "string",
            "nullable": true
          },
          "revision": {
            "type": "string",
            "nullable": true
          },
          "quantity": {
            "type": "number",
            "format": "double"
          },
          "lastModified": {
            "type": "string",
            "format": "date-time"
          },
          "location": {
            "$ref": "#/components/schemas/LocationDTO"
          }
        },
        "additionalProperties": false
      },
      "ItemModificationDTO": {
        "type": "object",
        "properties": {
          "itemNo": {
            "type": "string",
            "nullable": true
          },
          "revision": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "Location": {
        "type": "object",
        "properties": {
          "typeName": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "name": {
            "type": "string",
            "nullable": true
          },
          "locationTypeId": {
            "type": "integer",
            "format": "int32"
          },
          "parentLocationId": {
            "type": "integer",
            "format": "int32",
            "nullable": true
          },
          "locationType": {
            "$ref": "#/components/schemas/LocationType"
          },
          "parentLocation": {
            "$ref": "#/components/schemas/Location"
          }
        },
        "additionalProperties": false
      },
      "LocationDTO": {
        "type": "object",
        "properties": {
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "name": {
            "type": "string",
            "nullable": true
          },
          "locationType": {
            "$ref": "#/components/schemas/LocationTypeShortDTO"
          },
          "parentLocation": {
            "$ref": "#/components/schemas/LocationDTO"
          }
        },
        "additionalProperties": false
      },
      "LocationModificationDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          },
          "locationTypeId": {
            "type": "integer",
            "format": "int32"
          },
          "parentLocationId": {
            "type": "integer",
            "format": "int32",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "LocationType": {
        "type": "object",
        "properties": {
          "typeName": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "LocationTypeModificationDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "LocationTypeShortDTO": {
        "type": "object",
        "properties": {
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "LogItem": {
        "type": "object",
        "properties": {
          "timeStamp": {
            "type": "string",
            "format": "date-time",
            "readOnly": true
          },
          "origin": {
            "type": "string",
            "nullable": true
          },
          "message": {
            "type": "string",
            "nullable": true
          },
          "exceptionMessage": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          }
        },
        "additionalProperties": false
      },
      "MachineCenterWorkCenter": {
        "type": "object",
        "properties": {
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "workCentorNo": {
            "type": "string",
            "nullable": true
          },
          "machineNumber": {
            "type": "integer",
            "format": "int32"
          },
          "description": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "MachineCenterWorkCenterModificationDTO": {
        "type": "object",
        "properties": {
          "workCentorNo": {
            "type": "string",
            "nullable": true
          },
          "machineNumber": {
            "type": "integer",
            "format": "int32"
          },
          "description": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "NotificationCreationDTO": {
        "type": "object",
        "properties": {
          "senderId": {
            "type": "string",
            "nullable": true
          },
          "title": {
            "type": "string",
            "nullable": true
          },
          "message": {
            "type": "string",
            "nullable": true
          },
          "critical": {
            "type": "boolean"
          },
          "notificationTypeId": {
            "type": "integer",
            "format": "int32"
          },
          "notificationTargetId": {
            "type": "integer",
            "format": "int32"
          },
          "actionUrl": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "NotificationCreationRequest": {
        "type": "object",
        "properties": {
          "notification": {
            "$ref": "#/components/schemas/NotificationCreationDTO"
          },
          "recipientIds": {
            "type": "array",
            "items": {
              "type": "string"
            },
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "NotificationSubscription": {
        "type": "object",
        "properties": {
          "typeName": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "subscriptionId": {
            "type": "integer",
            "format": "int32"
          },
          "mainKey": {
            "nullable": true,
            "readOnly": true
          },
          "userID": {
            "type": "string",
            "nullable": true
          },
          "entityType": {
            "type": "string",
            "nullable": true
          },
          "entityMainKey": {
            "type": "string",
            "nullable": true
          },
          "entityMainKeyValue": {
            "type": "string",
            "nullable": true
          },
          "active": {
            "type": "boolean"
          },
          "dateSubscribed": {
            "type": "string",
            "format": "date-time"
          }
        },
        "additionalProperties": false
      },
      "NotificationSubscriptionModificationDTO": {
        "type": "object",
        "properties": {
          "userID": {
            "type": "string",
            "nullable": true
          },
          "entityType": {
            "type": "string",
            "nullable": true
          },
          "entityMainKey": {
            "type": "string",
            "nullable": true
          },
          "entityMainKeyValue": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "NotificationTypes": {
        "type": "object",
        "properties": {
          "typeName": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "code": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "NotificationTypesCreationDTO": {
        "type": "object",
        "properties": {
          "code": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "NotificationTypesUpdateDTO": {
        "type": "object",
        "properties": {
          "code": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "OvertimePeriodCreationDTO": {
        "type": "object",
        "properties": {
          "workCenterId": {
            "type": "string",
            "nullable": true
          },
          "rate": {
            "type": "number",
            "format": "double"
          },
          "startTime": {
            "type": "string",
            "format": "date-time"
          },
          "endDateTime": {
            "type": "string",
            "format": "date-time"
          },
          "createdBy": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "OvertimePeriodUpdateDTO": {
        "type": "object",
        "properties": {
          "workCenterId": {
            "type": "string",
            "nullable": true
          },
          "rate": {
            "type": "number",
            "format": "double"
          },
          "startTime": {
            "type": "string",
            "format": "date-time"
          },
          "endDateTime": {
            "type": "string",
            "format": "date-time"
          }
        },
        "additionalProperties": false
      },
      "Permission": {
        "type": "object",
        "properties": {
          "typeName": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "PermissionCreationDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "PermissionUpdateDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "ProblemDetails": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string",
            "nullable": true
          },
          "title": {
            "type": "string",
            "nullable": true
          },
          "status": {
            "type": "integer",
            "format": "int32",
            "nullable": true
          },
          "detail": {
            "type": "string",
            "nullable": true
          },
          "instance": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": { }
      },
      "ProductionOrderAskForHelpDTO": {
        "type": "object",
        "properties": {
          "assignedUserId": {
            "type": "string",
            "nullable": true
          },
          "message": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "ProductionRoutingStatusCreationDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "ProductionRoutingStatusUpdateDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "ProductionRoutingTaskUpdateCompletionDTO": {
        "type": "object",
        "properties": {
          "completionQTY": {
            "type": "number",
            "format": "double"
          }
        },
        "additionalProperties": false
      },
      "ProductionRoutingTaskUpdatePriorityDTO": {
        "type": "object",
        "properties": {
          "priority": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "ProductionRoutingTaskUpdateReservationDTO": {
        "type": "object",
        "properties": {
          "isReserved": {
            "type": "boolean"
          },
          "machineCenterId": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "ProductionRoutingTaskUpdateRushDTO": {
        "type": "object",
        "properties": {
          "isRush": {
            "type": "boolean"
          }
        },
        "additionalProperties": false
      },
      "ProductionRoutingTaskUpdateStatusDTO": {
        "type": "object",
        "properties": {
          "statusId": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "Role": {
        "type": "object",
        "properties": {
          "typeName": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "roleID": {
            "type": "integer",
            "format": "int32"
          },
          "roleName": {
            "type": "string",
            "nullable": true
          },
          "roleDescription": {
            "type": "string",
            "nullable": true
          },
          "permissions": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/Permission"
            },
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "RoleCreationDTO": {
        "type": "object",
        "properties": {
          "roleName": {
            "type": "string",
            "nullable": true
          },
          "roleDescription": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "RolePermissionDTO": {
        "type": "object",
        "properties": {
          "permissionId": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "RoleUpdateDTO": {
        "type": "object",
        "properties": {
          "roleName": {
            "type": "string",
            "nullable": true
          },
          "roleDescription": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "RoutingBom": {
        "type": "object",
        "properties": {
          "etag": {
            "type": "string",
            "nullable": true
          },
          "id": {
            "type": "string",
            "format": "uuid"
          },
          "routingNo": {
            "type": "string",
            "nullable": true
          },
          "operationNo": {
            "type": "string",
            "nullable": true
          },
          "workCenterNo": {
            "type": "string",
            "nullable": true
          },
          "setupTime": {
            "type": "number",
            "format": "double"
          },
          "runTime": {
            "type": "number",
            "format": "double"
          },
          "unitCostPer": {
            "type": "number",
            "format": "double"
          },
          "sequenceNoForward": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "RoutingBomHeader": {
        "type": "object",
        "properties": {
          "@odata.etag": {
            "type": "string",
            "nullable": true
          },
          "id": {
            "type": "string",
            "format": "uuid"
          },
          "no": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "type": {
            "type": "string",
            "nullable": true
          },
          "status": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "RoutingBomHeaderUpdateDTO": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string",
            "format": "uuid"
          },
          "no": {
            "type": "string",
            "nullable": true
          },
          "status": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "RoutingBomUpdateDTO": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string",
            "format": "uuid"
          },
          "routingNo": {
            "type": "string",
            "nullable": true
          },
          "workCenterNo": {
            "type": "string",
            "nullable": true
          },
          "setupTime": {
            "type": "number",
            "format": "double"
          },
          "runTime": {
            "type": "number",
            "format": "double"
          },
          "unitCostPer": {
            "type": "number",
            "format": "double"
          }
        },
        "additionalProperties": false
      },
      "SignalRClientInfo": {
        "type": "object",
        "properties": {
          "connectionId": {
            "type": "string",
            "nullable": true
          },
          "identifier": {
            "type": "string",
            "nullable": true
          },
          "hubName": {
            "type": "string",
            "nullable": true
          },
          "ipAddress": {
            "type": "string",
            "nullable": true
          },
          "connectedAt": {
            "type": "string",
            "format": "date-time"
          }
        },
        "additionalProperties": false
      },
      "SkillLevel": {
        "type": "object",
        "properties": {
          "typeName": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "name": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "SkillLevelModificationDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "Skills": {
        "type": "object",
        "properties": {
          "typeName": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "workCenterNo": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "SkillsModificationDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "workCenterNo": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "Subscription": {
        "type": "object",
        "properties": {
          "typeName": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "oDataETag": {
            "type": "string",
            "nullable": true
          },
          "subscriptionId": {
            "type": "string",
            "nullable": true
          },
          "notificationUrl": {
            "type": "string",
            "nullable": true
          },
          "resource": {
            "type": "string",
            "nullable": true
          },
          "userId": {
            "type": "string",
            "nullable": true
          },
          "lastModifiedDateTime": {
            "type": "string",
            "format": "date-time"
          },
          "clientState": {
            "type": "string",
            "nullable": true
          },
          "expirationDateTime": {
            "type": "string",
            "format": "date-time"
          },
          "systemCreatedAt": {
            "type": "string",
            "format": "date-time"
          },
          "systemCreatedBy": {
            "type": "string",
            "nullable": true
          },
          "systemModifiedAt": {
            "type": "string",
            "format": "date-time"
          },
          "systemModifiedBy": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "SubscriptionCreationDTO": {
        "type": "object",
        "properties": {
          "notificationUrl": {
            "type": "string",
            "nullable": true
          },
          "resource": {
            "type": "string",
            "nullable": true
          },
          "clientState": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "TaskItemCreationDTO": {
        "type": "object",
        "properties": {
          "title": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "completionPercentage": {
            "type": "integer",
            "format": "int32"
          },
          "assigneeId": {
            "type": "string",
            "nullable": true
          },
          "statusId": {
            "type": "integer",
            "format": "int32"
          },
          "priority": {
            "type": "integer",
            "format": "int32"
          },
          "dueDate": {
            "type": "string",
            "format": "date-time",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "TaskItemUpdateDTO": {
        "type": "object",
        "properties": {
          "taskId": {
            "type": "integer",
            "format": "int32"
          },
          "title": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "completionPercentage": {
            "type": "integer",
            "format": "int32"
          },
          "assigneeId": {
            "type": "string",
            "nullable": true
          },
          "statusId": {
            "type": "integer",
            "format": "int32"
          },
          "priority": {
            "type": "integer",
            "format": "int32"
          },
          "dueDate": {
            "type": "string",
            "format": "date-time",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "TaskStatusCreationDTO": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "isActive": {
            "type": "boolean"
          }
        },
        "additionalProperties": false
      },
      "TaskStatusUpdateDTO": {
        "type": "object",
        "properties": {
          "statusId": {
            "type": "integer",
            "format": "int32"
          },
          "name": {
            "type": "string",
            "nullable": true
          },
          "description": {
            "type": "string",
            "nullable": true
          },
          "isActive": {
            "type": "boolean"
          }
        },
        "additionalProperties": false
      },
      "TimeSpan": {
        "type": "object",
        "properties": {
          "ticks": {
            "type": "integer",
            "format": "int64"
          },
          "days": {
            "type": "integer",
            "format": "int32",
            "readOnly": true
          },
          "hours": {
            "type": "integer",
            "format": "int32",
            "readOnly": true
          },
          "milliseconds": {
            "type": "integer",
            "format": "int32",
            "readOnly": true
          },
          "microseconds": {
            "type": "integer",
            "format": "int32",
            "readOnly": true
          },
          "nanoseconds": {
            "type": "integer",
            "format": "int32",
            "readOnly": true
          },
          "minutes": {
            "type": "integer",
            "format": "int32",
            "readOnly": true
          },
          "seconds": {
            "type": "integer",
            "format": "int32",
            "readOnly": true
          },
          "totalDays": {
            "type": "number",
            "format": "double",
            "readOnly": true
          },
          "totalHours": {
            "type": "number",
            "format": "double",
            "readOnly": true
          },
          "totalMilliseconds": {
            "type": "number",
            "format": "double",
            "readOnly": true
          },
          "totalMicroseconds": {
            "type": "number",
            "format": "double",
            "readOnly": true
          },
          "totalNanoseconds": {
            "type": "number",
            "format": "double",
            "readOnly": true
          },
          "totalMinutes": {
            "type": "number",
            "format": "double",
            "readOnly": true
          },
          "totalSeconds": {
            "type": "number",
            "format": "double",
            "readOnly": true
          }
        },
        "additionalProperties": false
      },
      "User": {
        "type": "object",
        "properties": {
          "typeName": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          },
          "userId": {
            "type": "string",
            "nullable": true
          },
          "firstName": {
            "type": "string",
            "nullable": true
          },
          "lastName": {
            "type": "string",
            "nullable": true
          },
          "rfid": {
            "type": "string",
            "nullable": true
          },
          "isActive": {
            "type": "boolean"
          },
          "roles": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/Role"
            },
            "nullable": true
          },
          "departments": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/Department"
            },
            "nullable": true
          },
          "effectivePermission": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/Permission"
            },
            "nullable": true,
            "readOnly": true
          },
          "userSkills": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/UserSkills"
            },
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "UserCreationModificationDTO": {
        "type": "object",
        "properties": {
          "userId": {
            "type": "string",
            "nullable": true
          },
          "firstName": {
            "type": "string",
            "nullable": true
          },
          "lastName": {
            "type": "string",
            "nullable": true
          },
          "rfid": {
            "type": "string",
            "nullable": true
          },
          "isActive": {
            "type": "boolean"
          },
          "roleIds": {
            "type": "array",
            "items": {
              "type": "integer",
              "format": "int32"
            },
            "nullable": true
          },
          "departmentIds": {
            "type": "array",
            "items": {
              "type": "integer",
              "format": "int32"
            },
            "nullable": true
          },
          "skills": {
            "type": "array",
            "items": {
              "$ref": "#/components/schemas/UserSkillsModificationDTO"
            },
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "UserDTO": {
        "type": "object",
        "properties": {
          "mainKey": {
            "nullable": true
          },
          "typeName": {
            "type": "string",
            "nullable": true
          },
          "userId": {
            "type": "string",
            "nullable": true
          },
          "firstName": {
            "type": "string",
            "nullable": true
          },
          "lastName": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "UserDepartmentDTO": {
        "type": "object",
        "properties": {
          "departmentId": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "UserRoleDTO": {
        "type": "object",
        "properties": {
          "roleId": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "UserSkills": {
        "type": "object",
        "properties": {
          "skill": {
            "$ref": "#/components/schemas/Skills"
          },
          "skillLevel": {
            "$ref": "#/components/schemas/SkillLevel"
          }
        },
        "additionalProperties": false
      },
      "UserSkillsModificationDTO": {
        "type": "object",
        "properties": {
          "skillId": {
            "type": "integer",
            "format": "int32"
          },
          "skillLevelId": {
            "type": "integer",
            "format": "int32"
          }
        },
        "additionalProperties": false
      },
      "WorkActivityDTO": {
        "type": "object",
        "properties": {
          "id": {
            "type": "integer",
            "format": "int32"
          },
          "userId": {
            "type": "string",
            "nullable": true
          },
          "startDate": {
            "type": "string",
            "format": "date-time"
          },
          "endDate": {
            "type": "string",
            "format": "date-time"
          },
          "status": {
            "type": "integer",
            "format": "int32"
          },
          "user": {
            "$ref": "#/components/schemas/UserDTO"
          },
          "duration": {
            "$ref": "#/components/schemas/TimeSpan"
          },
          "isActive": {
            "type": "boolean",
            "readOnly": true
          },
          "statusText": {
            "type": "string",
            "nullable": true,
            "readOnly": true
          }
        },
        "additionalProperties": false
      },
      "WorkActivityFilterDTO": {
        "type": "object",
        "properties": {
          "userId": {
            "type": "string",
            "nullable": true
          },
          "startDate": {
            "type": "string",
            "format": "date-time",
            "nullable": true
          },
          "endDate": {
            "type": "string",
            "format": "date-time",
            "nullable": true
          },
          "status": {
            "type": "integer",
            "format": "int32",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "WorkCenterSDP": {
        "type": "object",
        "properties": {
          "workCentorNo": {
            "type": "string",
            "nullable": true
          },
          "setupSheetPath": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      },
      "WorkCenterSDPModificationDTO": {
        "type": "object",
        "properties": {
          "setupSheetPath": {
            "type": "string",
            "nullable": true
          }
        },
        "additionalProperties": false
      }
    },
    "securitySchemes": {
      "RequesterUserID": {
        "type": "apiKey",
        "description": "RequesterUserID required for identifying the user",
        "name": "RequesterUserID",
        "in": "header"
      }
    }
  },
  "security": [
    {
      "RequesterUserID": [ ]
    }
  ],
  "tags": [
    {
      "name": "CacheMonitoring",
      "description": "Controller used to get Statistics data from caching mecanism"
    },
    {
      "name": "Department",
      "description": "Controller for managing departments."
    },
    {
      "name": "FileShare",
      "description": "Controller for managing Notifications"
    },
    {
      "name": "HealthMonitoring",
      "description": "Controller for managing permissions."
    },
    {
      "name": "Notification",
      "description": "Controller for managing Notifications"
    },
    {
      "name": "NotificationTypes",
      "description": "Controller for managing notification types."
    },
    {
      "name": "OvertimePeriod",
      "description": "Controller for managing OvertimePeriod operations."
    },
    {
      "name": "Permission",
      "description": "Controller for managing permissions."
    },
    {
      "name": "ProductionOrder",
      "description": "Controller for managing Work Center operations."
    },
    {
      "name": "ProductionStatistics",
      "description": "Controller for managing production statistics."
    },
    {
      "name": "Role",
      "description": "Controller for managing roles."
    },
    {
      "name": "RoutingBom",
      "description": "Controller for managing Work Center operations."
    },
    {
      "name": "RoutingTaskWebHook",
      "description": "Controller for handling notifications from external APIs."
    },
    {
      "name": "Users",
      "description": "Controller for managing user-related operations."
    },
    {
      "name": "WorkActivity",
      "description": "Controller for managing work activity operations."
    },
    {
      "name": "WorkCenter",
      "description": "Controller for managing Work Center operations."
    }
  ]
}