import json, os, boto3

SCHEMA_TABLE = os.environ.get("SCHEMA_TABLE", "postnl-eb-schemas")
CORE_BUS = os.environ.get("CORE_BUS", "postnl-core-bus")
DLQ_URL = os.environ.get("DLQ_URL")

ddb = boto3.resource("dynamodb")
schemas = ddb.Table(SCHEMA_TABLE)
events = boto3.client("events")
sqs = boto3.client("sqs")

def _get_schema(producer, detail_type, version):
    key = {"producer_event": f"{producer}:{detail_type}", "version": str(version)}
    res = schemas.get_item(Key=key)
    item = res.get("Item")
    if not item:
        raise KeyError(f"schema not found for {key}")
    return json.loads(item["schemaJson"])

def _validate_instance(schema, detail):
    # Very small subset: check required keys and primitive types
    required = schema.get("required", [])
    props = schema.get("properties", {})
    for k in required:
        if k not in detail:
            return False, f"missing required field '{k}'"
    for k, v in detail.items():
        if k in props:
            t = props[k].get("type")
            if t == "string" and not isinstance(v, str): return False, f"field '{k}' type must be string"
            if t == "number" and not isinstance(v, (int, float)): return False, f"field '{k}' type must be number"
            if t == "boolean" and not isinstance(v, bool): return False, f"field '{k}' type must be boolean"
    return True, "ok"

def handler(event, context):
    # Expect a single EventBridge event (already normalized by sqs_ingress_forwarder)
    source = event.get("source")
    detail_type = event.get("detail-type")
    detail = event.get("detail", {})
    version = detail.get("schemaVersion", "1")

    try:
        schema = _get_schema(source, detail_type, version)
        ok, reason = _validate_instance(schema, detail)
        if ok:
            # Forward to Core bus
            events.put_events(Entries=[{
                "EventBusName": CORE_BUS,
                "Source": source,
                "DetailType": detail_type,
                "Detail": json.dumps(detail)
            }])
            result = {"status": "accepted", "eventType": detail_type}
        else:
            raise ValueError(reason)
    except Exception as e:
        # Send to DLQ with reason if configured
        if DLQ_URL:
            sqs.send_message(QueueUrl=DLQ_URL, MessageBody=json.dumps({
                "error": str(e), "event": event
            }))
        result = {"status": "rejected", "reason": str(e)}

    return {"statusCode": 200, "body": json.dumps([result])}
