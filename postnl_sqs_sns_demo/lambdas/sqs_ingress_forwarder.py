import json, os, boto3

INGRESS_BUS = os.environ.get("INGRESS_BUS", "postnl-ingress-bus")
events = boto3.client("events")

def _to_entries(payload):
    # Ensure EventBridge "detail-type", "source", and "detail" shape
    if isinstance(payload, str):
        payload = json.loads(payload)
    if "detail" not in payload:
        raise ValueError("payload must contain 'detail'")
    return [{
        "EventBusName": INGRESS_BUS,
        "Source": payload.get("source", "demo.producer"),
        "DetailType": payload.get("detail-type", "demo.event"),
        "Detail": json.dumps(payload["detail"])
    }]

def handler(event, context):
    entries = []
    # Accept either SQS-like Records or a simple { "body": json-string }
    if "Records" in event:
        for r in event["Records"]:
            entries += _to_entries(r.get("body", "{}"))
    elif "body" in event:
        entries += _to_entries(event["body"])
    else:
        entries += _to_entries(json.dumps(event))

    resp = events.put_events(Entries=entries)
    forwarded = resp.get("Entries", [])
    return {"statusCode": 200, "body": json.dumps({"forwarded": len(forwarded), "ingressBus": INGRESS_BUS})}
