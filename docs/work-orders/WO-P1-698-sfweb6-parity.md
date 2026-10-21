# WO-P1-698 — SF-WEB-6: Web/Tk parity

Issue: #698
Status: P1 IMPLEMENTATION (Worker CRUD + Connector create)
Risk: R3 (mutation authority extension)
Topology: CONTROL_PLANE_ONLY

## Parity Matrix Summary
- At parity: 5 features (status, start/stop, assign, live monitor)
- P1 gaps (this slice): Worker create/delete, Connector create
- P2 gaps (future): Rename/delete connector, CPU/RAM metrics
- Tk retirement: NOT ready until P1 closes

## P1 Server Endpoints (this slice)
- POST /api/v1/workers — create worker slot
- DELETE /api/v1/workers/{worker_id} — delete stopped worker
- POST /api/v1/connectors — create connector with project + tunnel_id

## P1 Client Components (next slice)
- WorkerCreateButton + dialog
- WorkerDeleteButton + confirmation
- ConnectorCreateWizard (simplified)

## Tests
- tests/test_web_api_p1_gaps.py — server endpoint tests
