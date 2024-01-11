#!/bin/sh

set -eu

curl -XPOST https://monitoring.antoinealb.net/api/annotations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  --data @- << EOF
  {
    "text": "$CI_COMMIT_MESSAGE\n\n
      <a href=\"$CI_JOB_URL\">Gitlab CI</a>",
    "tags": [
      "deployment",
      "infra"
    ]
  }
EOF
