#!/bin/bash

COMMAND=$(echo "$JSON_INPUT" | jq -r '.tool_input.command // empty')

cd ../..
echo "$(pwd)"
case "$COMMAND" in
    *"frontend"*)
        docker compose up -d --build frontend
        ;;
    *"backend"*)
        docker compose restart backend
        ;;
    *"worker"*)
        docker compose up -d --build worker
        ;;
    *)
        echo "No matching service found for: $COMMAND"
        exit 1
        ;;
esac

exit 0