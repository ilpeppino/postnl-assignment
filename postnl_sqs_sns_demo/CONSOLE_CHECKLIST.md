# 🧭 PostNL Event Broker – Console Checklist

### 🎯 Goal
Demonstrate an end-to-end event flow:
SQS Producer → EventBridge Ingress Bus → Validator Lambda → EventBridge Core Bus → SNS Consumer

---

## 🧱 1️⃣ One-Time Setup (Console)
| Step | AWS Service | Action |
|------|--------------|--------|
| 1 | **DynamoDB** | Create tables:<br>• `postnl-eb-schemas` → PK=`producer_event`, SK=`version`<br>• `postnl-eb-catalog` → PK=`pk`, SK=`sk`<br>• `postnl-eb-subscriptions` → PK=`pk`, SK=`sk` |
| 2 | **EventBridge** | Create event buses:<br>• `postnl-ingress-bus`<br>• `postnl-core-bus` |
| 3 | **SQS** | Create DLQ: `postnl-runtime-dlq` |
| 4 | **IAM** | Attach inline policies from `/iam/policies/` to each Lambda |
| 5 | **Environment Variables** | Configure values listed in README.md |
| 6 | **Rule** | Create rule `ingress-validate` on `postnl-ingress-bus` → Target `runtime_event_validator` |

---

## 🚀 2️⃣ Run Lambdas in Order
| # | Lambda | Description | Input | Expected Output |
|---|--------| ----------- |------ | ---------------|
| 1 | **event_schema_validator** | Validates the **JSON Schema** submitted by a producer before registration. Ensures the schema is syntactically correct and follows PostNL rules. | `broker_admin_sunny.json` (schema block only) | `tests/broker_admin_sunny.json` (schema only) | ✅ 200 + `"schema_valid"` → DynamoDB entry |
| 2 | **broker_admin** | Handles **producer registration**: validates schema, stores producer metadata, creates catalog entry, and sets default permissions. | `tests/broker_admin_sunny.json` | ✅ 200 + `"registered"` → `schemas` & `catalog` tables updated |
| 3 | **consumer_admin** | Handles **consumer registration**: records subscriptions, creates EventBridge rules and SNS topics, enabling consumers to receive chosen events. | `tests/consumer_admin_sunny_sns.json` | ✅ 200 + `"created"` → SNS topic + EventBridge rule |
| 4 | **sqs_ingress_forwarder** | Acts as a **producer ingress point** for SQS producers. Consumes SQS messages and forwards them to the EventBridge Ingress Bus. | `sqs_ingress_forwarder_sunny.json` | `tests/sqs_ingress_forwarder_sunny.json` | ✅ 200 + `"forwarded":1` → Event in `postnl-ingress-bus` |
| 5 | **runtime_event_validator** | Core **event validation and routing** component. Validates incoming events against the registered schema, sends valid events to the Core Bus, and rejects invalid ones to the DLQ. | `tests/runtime_event_validator_valid.json` | ✅ 200 + `"accepted"` → Event → Core Bus → SNS → email received |

---

## 🧪 Testing (AWS Console)

All tests are run directly from the **AWS Lambda Console** using the provided payloads in `/tests/`.

1. **event_schema_validator** → validate schema only.  
2. **broker_admin** → register producer with schema.  
3. **consumer_admin** → register consumer with chosen event type and delivery method.  
4. **sqs_ingress_forwarder** → simulate producer event via SQS.  
5. **runtime_event_validator** → validate and forward event to consumer.

### Sunny-Day Scenarios
✅ Schema valid → Producer registered → Consumer created → Event forwarded → SNS email received.

### Rainy-Day Scenarios
❌ Schema invalid → 400 error  
❌ Invalid payload → message sent to DLQ (`postnl-runtime-dlq`)

---

## 🌧️ 3️⃣ Rainy-Day Validation
| Scenario | Lambda | Test | Expected Result |
|-----------|---------|------|-----------------|
| Missing eventType | broker_admin | `broker_admin_rainy_missing_eventType.json` | ❌ 400 Bad Request |
| Missing field | consumer_admin | `consumer_admin_rainy_missing_field.json` | ❌ 400 Bad Request |
| Invalid type | runtime_event_validator | `runtime_event_validator_invalid.json` | ✅ 200 + `"rejected"` → message in DLQ |

---

## 🔎 4️⃣ Verification After Demo
| Service | Check |
|----------|--------|
| **DynamoDB** | Rows in `schemas`, `catalog`, `subscriptions` |
| **EventBridge** | 2 buses exist + rules active |
| **SNS** | Topic + email subscription active |
| **SQS (DLQ)** | Contains rejected events |
| **CloudWatch Logs** | Show `"accepted"` / `"rejected"` for each Lambda |

---

## 🧠 5️⃣ Key Talking Points
- **Serverless-first**: Lambda + EventBridge + DynamoDB + SNS/SQS
- **Schema enforcement**: Validation via runtime validator
- **Protocol flexibility**: SQS/SNS/HTTPS/EventBridge
- **Reliability**: DLQ + at-least-once delivery
- **Observability**: CloudWatch + optional S3 insights
