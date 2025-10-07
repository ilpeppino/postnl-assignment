import json, os, boto3

SCHEMA_TABLE = os.environ.get("SCHEMA_TABLE", "postnl-eb-schemas")
CATALOG_TABLE = os.environ.get("CATALOG_TABLE", "postnl-eb-catalog")

ddb = boto3.resource("dynamodb")
schemas = ddb.Table(SCHEMA_TABLE)
catalog = ddb.Table(CATALOG_TABLE)

def handler(event, context):
    body = event.get("body", {})
    if isinstance(body, str):
        body = json.loads(body)

    required = ["producer", "eventType", "version", "schemaJson", "ingressType"]
    for k in required:
        if k not in body:
            return {"statusCode": 400, "body": json.dumps({"error": f"missing '{k}'"})}

    producer = body["producer"]
    event_type = body["eventType"]
    version = str(body["version"])
    ingress = body["ingressType"]
    schema_json = body["schemaJson"]

    # Store schema row
    schemas.put_item(Item={
        "producer_event": f"{producer}:{event_type}",
        "version": version,
        "schemaJson": json.dumps(schema_json, separators=(",", ":"))
    })

    # Store catalog row (simple PK/SK for demo)
    catalog.put_item(Item={
        "pk": f"PRODUCER#{producer}",
        "sk": f"EVENT#{event_type}",
        "ingressType": ingress,
        "version": version
    })

    # Return a fake endpoint hint for demo
    endpoint = {
        "SQS": "https://sqs.REGION.amazonaws.com/ACCOUNT_ID/postnl-ingress-queue",
        "HTTPS": "https://api.example/ingress",
        "SNS": "arn:aws:sns:REGION:ACCOUNT_ID:postnl-ingress",
        "EventBridge": "arn:aws:events:REGION:ACCOUNT_ID:event-bus/postnl-ingress-bus"
    }.get(ingress, "n/a")

    # IMPORTANT NOTE:
    # We should create the actual SQS/DLQ queue, SNS topic, or EventBridge bus here but skipping for demo

    return {"statusCode": 200, "body": json.dumps({
        "status": "registered",
        "producer": producer,
        "eventType": event_type,
        "version": version,
        "ingressType": ingress,
        "endpoint": endpoint
    })}
