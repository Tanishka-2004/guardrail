#!/usr/bin/env bash
set -e

BOOTSTRAP_SERVER=${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}

echo "Waiting for Kafka broker at $BOOTSTRAP_SERVER..."
cub kafka-ready 1 30 -b "$BOOTSTRAP_SERVER" 2>/dev/null || sleep 5

TOPICS=(
  "fraud.alerts:3:1"
  "fraud.alerts.retry:3:1"
  "fraud.alerts.dlq:3:1"
  "fraud.alerts.events:3:1"
)

for t in "${TOPICS[@]}"; do
  IFS=":" read -r name partitions replication <<< "$t"
  echo "Creating topic: $name (partitions: $partitions, replication: $replication)"
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP_SERVER" \
    --create --if-not-exists \
    --topic "$name" \
    --partitions "$partitions" \
    --replication-factor "$replication" || true
done

echo "Kafka topics created successfully."
