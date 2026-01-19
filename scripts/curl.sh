curl localhost:8080/status
curl localhost:8080/api/webhooks/github
curl localhost:8080/rate-limit-status | jq
curl localhost:8080/test
curl localhost:8080/fanout -X POST -H "Content-Type: application/json" -d '{"action": "test"}'

curl localhost:8090/status
