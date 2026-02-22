
# k8-s-Auditing-Security-Agent
A comprehensive Auditing &amp; Security Agentic AI of cloud agnostic Kubernetes cluster 
=======

 k8s-security-agent 🚨🔍

Kubernetes Security Audit Agent using the Claude Agent SDK and AWS Bedrock.

This project runs an autonomous auditor that inspects Kubernetes manifests and/or a live cluster to produce a security audit report (for example, `k8s_audit_report.md`). The core agent is implemented as an asynchronous Python script that uses the `claude_agent_sdk` and may invoke `kubectl` as part of its workflow.

 ✨ Highlights

- Autonomous Kubernetes security auditing (privileged containers, RBAC, network policies).
- Produces human- and machine-readable audit reports (`k8s_audit_report.md`).
- Designed to be extended with a FastAPI web UI and container/k8s deployment.

 📁 Repository layout

- `main.py` — CLI entrypoint that runs the Kubernetes security audit loop using Claude Agent SDK.
- `k8s_audit_report.md` — example or output report produced by the agent.
- `pyproject.toml` — project metadata and Python dependencies.
- `README.md` — this file (you're reading it!).

🚀 Quickstart — run the audit locally (CLI)

1. Create and activate a Python 3.10+ virtual environment.

2. Install dependencies listed in `pyproject.toml` (examples: `anthropic[bedrock]`, `claude-agent-sdk`, `boto3`, `python-dotenv`, `loguru`).

Example using pip:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  # create this file or pip install from pyproject
   ```

3. Add runtime environment variables (use a `.env`):

   - `AWS_REGION` (e.g. `us-east-1`)
   - `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (or use IAM role-based auth)
   - Bedrock/Claude variables: `CLAUDE_CODE_USE_BEDROCK`, `ANTHROPIC_MODEL`, etc. (see `main.py`).

4. Run the agent:

   ```bash
   python main.py
   ```

   The agent will run and write an audit file such as `k8s_audit_report.md`.

🔔 Notes
- `main.py` may execute `kubectl` during audits. Ensure `kubectl` is available and kubeconfig/service-account permissions are set if you want to audit live clusters.
- `pyproject.toml` currently declares a script `audit-k8s`, but you can also run `python main.py` directly.

 🌐 Web UI & API (planned)

Planned components to expose the audit via web:

- `app.py` — FastAPI app exposing endpoints to trigger audits, check status, and fetch reports.
- `static/index.html` — minimal JS UI for triggering audits and showing results.
- Background worker (PoC: FastAPI BackgroundTasks; production: Redis + RQ/Celery).
- `Dockerfile` — containerize the app for easy deployment.
- `k8s/` — deployment manifests (Deployment, Service, Ingress) with RBAC guidance.

If you'd like, I can implement the FastAPI UI and Dockerfile now and wire it to the existing audit function.

 🔐 Security & operational notes

- Never expose Bedrock or AWS credentials to the browser or client-side code.
- For live cluster audits, prefer running the container in-cluster with a scoped service account and restrictive RBAC.
- Add authentication (OAuth2/JWT) before allowing public access to audit triggers.
- For long-running audits, persist job state (DB or Redis) so status survives restarts.

🛠️ Deployment options (brief)

- Local development: run via `uvicorn` (after adding FastAPI) or run CLI directly.
- Container: build a `Dockerfile` and deploy to Cloud Run, Render, Fly, or any container host.
- Kubernetes: deploy the container into a cluster with a locked-down service account and namespace.
- Serverless: avoid direct `kubectl` in serverless functions due to timeouts; instead analyze uploaded manifests.

{"type":"excalidraw/clipboard","workspaceId":"WnyEDpvAaXK1Y5JUeWQI","elements":[{"id":"a33b0839bbc838a42c4cf205a7b6c67d","strokeColor":"#2866c4","backgroundColor":"rgba(247,249,253, 1)","fillStyle":"solid","strokeWidth":0.75,"strokeStyle":"solid","strokeSharpness":"round","roughness":0,"opacity":100,"elementStyle":1,"colorMode":0,"diagramId":"7VsWq40MsxTVeRIm8JRcO","diagramEntityId":"Kubernetes Cluster","type":"rectangle","isContainer":true,"sizingMode":"auto","compound":{"type":"parent","containerType":"group","settings":{"color":"blue","colorMode":"pastel","styleMode":"shadow","typeface":"rough"},"children":{"label":"KUBERNETES CLUSTER","icon":{"name":"k8s-cluster"}}},"x":15,"y":15,"width":226.90625,"height":430,"angle":0,"groupIds":[],"lockedGroupId":null,"seed":257941833,"version":2,"isDeleted":false,"modifiedAt":1771798235454,"zIndex":1},{"id":"7fa9535561e06081145277b10d397081","strokeColor":"#2866c4","backgroundColor":"rgba(247,249,253, 1)","fillStyle":"solid","strokeWidth":0.75,"strokeStyle":"solid","strokeSharpness":"round","roughness":0,"opacity":100,"elementStyle":1,"colorMode":0,"diagramId":"7VsWq40MsxTVeRIm8JRcO","diagramEntityId":"Security & Auditing Agent","type":"rectangle","isContainer":true,"containerId":"a33b0839bbc838a42c4cf205a7b6c67d","sizingMode":"auto","compound":{"type":"parent","containerType":"group","settings":{"colorMode":"pastel","styleMode":"shadow","typeface":"rough"},"children":{"label":"SECURITY & AUDITING AGENT","icon":{"name":"shield"}}},"x":35,"y":85,"width":176.90625,"height":340,"angle":0,"groupIds":[],"lockedGroupId":null,"seed":1647108873,"version":2,"isDeleted":false,"modifiedAt":1771798235454,"zIndex":2},{"id":"765abb84b776ff776f749b1196aa78a2","containerId":"7fa9535561e06081145277b10d397081","diagramId":"7VsWq40MsxTVeRIm8JRcO","diagramEntityId":"Claude Agent SDK","x":98.453125,"y":155,"compound":{"type":"parent","containerType":"cad-node","settings":{"colorMode":"pastel","styleMode":"shadow","typeface":"rough"},"children":{"label":"Claude Agent SDK","icon":{"name":"code"}}},"strokeColor":"#242424","backgroundColor":"transparent","fillStyle":"solid","strokeWidth":1,"strokeStyle":"solid","strokeSharpness":"sharp","roughness":0,"opacity":100,"name":"code","customStyle":false,"type":"icon","width":50,"height":50,"angle":0,"groupIds":[],"lockedGroupId":null,"seed":1289963593,"version":3,"isDeleted":false,"modifiedAt":1771798235454,"zIndex":3},{"id":"ed782ec6f171aa3e4275bb92a7b095c9","containerId":"7fa9535561e06081145277b10d397081","diagramId":"7VsWq40MsxTVeRIm8JRcO","diagramEntityId":"Compliance Monitor Module","x":98.453125,"y":290,"compound":{"type":"parent","containerType":"cad-node","settings":{"colorMode":"pastel","styleMode":"shadow","typeface":"rough"},"children":{"label":"CIS Compliance Monitor","icon":{"name":"check-circle"}}},"strokeColor":"#242424","backgroundColor":"transparent","fillStyle":"solid","strokeWidth":1,"strokeStyle":"solid","strokeSharpness":"sharp","roughness":0,"opacity":100,"name":"check-circle","customStyle":false,"type":"icon","width":50,"height":50,"angle":0,"groupIds":[],"lockedGroupId":null,"seed":2076530473,"version":3,"isDeleted":false,"modifiedAt":1771798235454,"zIndex":4}],"diagramMetadata":{"settings":{"colorMode":"pastel","styleMode":"shadow","typeface":"rough","direction":"right"},"diagramType":"cloud-architecture-diagram","diagramId":"7VsWq40MsxTVeRIm8JRcO","entitySettings":{"Kubernetes Cluster":{"colorMode":"pastel","styleMode":"shadow","typeface":"rough","color":"blue","icon":"k8s-cluster"},"Security & Auditing Agent":{"colorMode":"pastel","styleMode":"shadow","typeface":"rough","icon":"shield"},"Claude Agent SDK":{"colorMode":"pastel","styleMode":"shadow","typeface":"rough","icon":"code"},"Compliance Monitor Module":{"colorMode":"pastel","styleMode":"shadow","typeface":"rough","label":"CIS Compliance Monitor","icon":"check-circle"}}}}

