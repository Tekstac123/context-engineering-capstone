# Context Engineering Capstone — Starter App (Flavour C: AWS)

You have been handed a running HR & IT support assistant, deployed as an
AWS Lambda function behind API Gateway. It answers employee questions
using an internal policy knowledge base (S3 Vectors), employee/ticket
records, conversation history (DynamoDB), and two tools (`lookup_ticket`,
`lookup_employee`). It is deliberately imperfect.

## What's already provisioned for you

- **Lambda function** (`lambda_app/`) — deployed and running. Edit it directly
  in the Lambda console's inline code editor, or update via the AWS CLI.
- **API Gateway** — the `/chat`, `/reset`, `/health` endpoint contract is
  already wired up and correct. You will not need to change this.
- **S3 Vectors** — the policy documents are already embedded and loaded into
  the vector index, with metadata (`status`, `effective_date`, `source`) on
  every vector.
- **DynamoDB** — the session table is already created.

## Endpoint contract

```
POST /chat    {"session_id": "<string>", "query": "<string>"}
              -> {"answer", "retrieved_doc_ids", "retrieved_scores",
                   "tool_calls", "history_turns", "prompt_chars"}
POST /reset   {"session_id": "<string>"}  -> {"status": "reset"}
GET  /health  -> {"status": "ok"}
```

Scoring reaches your system only at this endpoint. You may change any
internal module's implementation (Lambda code) as long as the contract
above still holds.

## Project layout

```
lambda_app/
  lambda_function.py   entry point — routes API Gateway events
  retrieval.py          S3 Vectors query (embeds query via Bedrock Titan)
  memory.py              DynamoDB session history
  tools.py                lookup_ticket / lookup_employee (bundled data)
  assembly.py              builds the final prompt
  bedrock_llm.py            Bedrock Converse call (Amazon Nova Lite)
  agent.py                  orchestrates a single turn
  subject_records.json      bundled ticket/employee records
tests/
  public_cases.json         runnable public test cases
  run_public_cases.py        plays public_cases.json against your endpoint
```

## What to do

Record a baseline of the current system's behaviour on the public cases in
your own environment before making any change. Then, per the assessment
instructions: diagnose, name the failure class for each fault you
address, redesign the affected part(s) of the context pipeline, rebuild,
and evidence the improvement against your recorded baseline.

Run the public cases at any time with:

```bash
export APP_BASE_URL=<your API Gateway invoke URL>
python tests/run_public_cases.py
```

This script prints raw responses and a manual checklist per case — it is
not an auto-grader. A larger, withheld set is run at scoring time.
