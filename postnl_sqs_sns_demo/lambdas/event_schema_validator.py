import json, os, boto3

SCHEMA_TABLE = os.environ.get("SCHEMA_TABLE", "postnl-eb-schemas")
WRITE_TO_DDB = os.environ.get("WRITE_TO_DDB", "true").lower() == "true"

dynamodb = boto3.resource("dynamodb")
schemas_tbl = dynamodb.Table(SCHEMA_TABLE)

def _validate_schema_shape(schema):
    if not isinstance(schema, dict):
        raise ValueError("schemaJson must be an object")
    if schema.get("type") != "object":
        raise ValueError("schemaJson.type must be 'object'")
    if "properties" not in schema or not isinstance(schema["properties"], dict):
        raise ValueError("schemaJson.properties must be an object")
    req = schema.get("required", [])
    if not isinstance(req, list):
        raise ValueError("schemaJson.required must be an array")
    return True

def handler(event, context):
    body = event.get("body", {})
    if isinstance(body, str):
        body = json.loads(body)
    try:
        producer = body["producer"]
        event_type = body["eventType"]
        version = str(body.get("version", "1"))
        schema_json = body["schemaJson"]
        _validate_schema_shape(schema_json)
    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}

    written = False
    if WRITE_TO_DDB:
        item = {
            "producer_event": f"{producer}:{event_type}",
            "version": version,
            "schemaJson": json.dumps(schema_json, separators=(",", ":"))
        }
        schemas_tbl.put_item(Item=item)
        written = True

    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "schema_valid",
            "producer": producer,
            "eventType": event_type,
            "version": version,
            "written": written
        })
    }
