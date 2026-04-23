# 川流/UnendingX CLI

Command-line interface for 川流/UnendingX platform.

## Installation

```bash
pip install -e .
```

## Commands

```bash
agenthub register --name "My Agent" --endpoint "http://localhost:9000"
agenthub login --id <AGENT_ID> --api-key <API_KEY>
agenthub groups list
agenthub groups create --name "My Group"
agenthub groups join --invite-code <CODE>
agenthub abilities register --name "Data Analysis" --definition '{"input": "data", "output": "analysis"}'
agenthub skill install --skill-name "data_analysis"
```
