name: Send Authenticated Request

on:
  push:
    branches:
      - main

jobs:
  send_request:
    runs-on: ubuntu-latest
    steps:
      - name: Send request with password header
        run: |
          curl -X POST "http://your-server-ip:8080/archive/https%3A%2F%2Fexample.com" \
            -H "X-Password: ${{ secrets.ARCHIVE_PASSWORD }}" \
            -H "Content-Type: application/json"
