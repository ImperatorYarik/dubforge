#!/bin/bash

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

case "$FILE_PATH" in
    *"frontend"*)
        docker compose up -d --build frontend
        ;;
    *"api"*)
        docker compose up -d --build api
        ;;
    *"worker"*)
        docker compose up -d --build worker
        ;;
    *)
        echo "No matching service found for: $FILE_PATH"
        exit 0
        ;;
esac

exit 0