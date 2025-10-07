import json, os, boto3

EVENT_BUS = os.environ.get("CORE_BUS", "postnl-core-bus")
SUBS_TABLE = os.environ.get("SUBS_TABLE", "postnl-eb-subscriptions")

events = boto3.client("events")
ddb = boto3.resource("dynamodb")
subs_tbl = ddb.Table(SUBS_TABLE)
sns = boto3.client("sns")

def handler(event, context):
    body = event.get("body", {})
    if isinstance(body, str):
        body = json.loads(body)

    required = ["team", "source", "detailType", "schemaVersion"]
    for k in required:
        if k not in body:
            return {"statusCode": 400, "body": json.dumps({"error": f"missing '{k}'"})}

    team = body["team"]
    source = body["source"]
    detail_type = body["detailType"]
    schema_version = str(body["schemaVersion"])

    # Create SNS topic for this subscription
    topic_name = f"postnl-{team}-{detail_type.replace('.', '-')}".lower()
    topic_arn = sns.create_topic(Name=topic_name)["TopicArn"]

    # Create EventBridge rule on Core bus
    rule_name = f"{team}-{detail_type.replace('.', '-')}-v{schema_version}".lower()
    event_pattern = json.dumps({
        "source": [source],
        "detail-type": [detail_type],
        "detail": {"schemaVersion": [schema_version]}
    })
    rule_arn = events.put_rule(
        Name=rule_name,
        EventBusName=EVENT_BUS,
        EventPattern=event_pattern,
        State="ENABLED"
    )["RuleArn"]

    # Add SNS target
    events.put_targets(
        Rule=rule_name,
        EventBusName=EVENT_BUS,
        Targets=[{"Id": "snsTarget", "Arn": topic_arn}]
    )

    # Persist subscription
    subs_tbl.put_item(Item={
        "pk": f"TEAM#{team}",
        "sk": f"SRC#{source}#DT#{detail_type}#V#{schema_version}",
        "protocol": "SNS",
        "topicArn": topic_arn,
        "ruleArn": rule_arn
    })

    return {"statusCode": 200, "body": json.dumps({
        "status": "created",
        "topicArn": topic_arn,
        "ruleArn": rule_arn
    })}
