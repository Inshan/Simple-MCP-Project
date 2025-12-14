# import requests

# payload = {
#     "jsonrpc": "2.0",
#     "method": "call",
#     "params": {
#         "tool": "insert_query",
#         "title": "Mrs. Wifey",
#         "body": "Mordor's Gang",
#     },
#     "id": 1,
# }

# res = requests.post("http://127.0.0.1:8000/mcp", json=payload)
# print(res.json())


# {
#   "jsonrpc": "2.0",
#   "method": "tools/call",
#   "params": {"tool": "list_tables"},
#   "id": 3
# }

# import requests

# payload = {
#     "jsonrpc": "2.0",
#     "method": "call",
#     "params": {
#         "tool": "insert_query",
#         "title": "Here I am!",
#         "body": "Who am I?",
#     },
#     "id": 11,
# }

# res = requests.post("http://127.0.0.1:8000/mcp", json=payload)
# print(res)

# import requests

# payload = {
#     "jsonrpc": "2.0",
#     "method": "call",
#     "params": {
#         "tool": "insert_query",
#         "title": "Rohini",
#         "body": "Got money?",
#     },
#     "id": 11,
# }

# res = requests.post("http://127.0.0.1:8000/mcp", json=payload)
# print(res.json())

import requests
import os

SECRET_KEY = os.getenv("MCP_SECRET_KEY", "1234")

payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {"tool": "query", "table": "query", "limit": 5},
    "id": 11,
}

headers = {
    "Authorization": f"Bearer {SECRET_KEY}",
    "Content-Type": "application/json",
}

res = requests.post("http://127.0.0.1:8000/mcp", json=payload, headers=headers)
print(res.json())
