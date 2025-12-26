# WorkClass Agent Management System
## Comprehensive Implementation Proposal

**Project:** ifinsure Insurance Management System  
**Module:** WorkClass & Agent Performance Management  
**Inspired by:** Finacle Core Banking Work Distribution Model  
**Date:** December 25, 2024  

---

## 1. Executive Summary

This proposal outlines the implementation of a WorkClass-based agent management system that enables:
- **Tiered Work Distribution**: Agents receive tasks based on their assigned work class (skill level, authorization)
- **Self-Assignment**: Staff can pick tickets within their workclass capabilities
- **Performance Monitoring**: Track sales, resolution times, and conversion rates
- **Workflow Automation**: Automatic routing, escalation, and SLA management

---

## 2. Core Concepts (Finacle-Inspired)

### 2.1 WorkClass Definition
A WorkClass defines the scope of operations an agent can perform. Each workclass has:
- **Code**: Unique identifier (e.g., `L1_SUPPORT`, `CLAIMS_SENIOR`)
- **Level**: Numeric tier (1-5) indicating authority
- **Permissions**: Specific actions allowed (approve claims up to X, issue policies, etc.)
- **Limits**: Transaction/monetary limits

### 2.2 WorkClass Hierarchy
```
Level 5: ADMIN / SUPERVISOR
   ├── Full system access, approve all
   ├── Assign work to any agent
   └── Override any decision

Level 4: SENIOR_AGENT
   ├── Handle complex cases
   ├── Approve claims up to 500,000
   └── Escalation point for L3

Level 3: AGENT
   ├── Standard policy issuance
   ├── Approve claims up to 100,000
   └── Handle renewals

Level 2: JUNIOR_AGENT
   ├── Policy applications
   ├── Claims intake (no approval)
   └── Customer inquiries

Level 1: TRAINEE
   ├── View only
   ├── Assist with documentation
   └── Learning mode
```

---

## 3. Data Model Design

### 3.1 Core Models

```
┌─────────────────────────────────────────────────────────────────┐
│                         WorkClass                                │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ code (str, unique) - e.g., "CLAIMS_SENIOR"                      │
│ name (str) - "Senior Claims Agent"                              │
│ level (int, 1-5)                                                │
│ department (FK) - claims, policies, billing                     │
│ description                                                      │
│ monetary_limit (decimal) - max amount for approvals             │
│ permissions (JSON) - detailed permissions                        │
│ is_active                                                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      AgentProfile                                │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ user (OneToOne FK)                                              │
│ workclasses (M2M) - can have multiple                           │
│ primary_workclass (FK)                                          │
│ employee_id                                                      │
│ department                                                       │
│ supervisor (FK to self)                                         │
│ daily_capacity (int) - max tickets/day                          │
│ current_load (int) - active tickets                             │
│ is_available                                                     │
│ shift_start, shift_end                                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         Ticket                                   │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ reference (str) - TKT-YYYYMMDD-XXXX                             │
│ ticket_type (enum) - claim, policy, billing, inquiry            │
│ priority (enum) - low, medium, high, urgent                     │
│ status (enum) - open, assigned, in_progress, resolved, closed   │
│                                                                  │
│ # Related Entity                                                 │
│ content_type (FK) - generic relation                            │
│ object_id - links to Claim, Policy, etc.                        │
│                                                                  │
│ # Assignment                                                     │
│ required_workclass_level (int) - minimum level needed           │
│ required_department                                              │
│ assigned_to (FK Agent)                                          │
│ assigned_by (FK User)                                           │
│ assigned_at                                                      │
│                                                                  │
│ # Customer                                                       │
│ customer (FK User)                                              │
│ subject                                                          │
│ description                                                      │
│                                                                  │
│ # SLA                                                            │
│ sla_due_at                                                       │
│ first_response_at                                                │
│ resolved_at                                                      │
│                                                                  │
│ # Metadata                                                       │
│ created_at                                                       │
│ updated_at                                                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    TicketActivity                                │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ ticket (FK)                                                      │
│ activity_type (enum) - created, assigned, note, status_change   │
│ performed_by (FK User)                                          │
│ details (JSON)                                                   │
│ created_at                                                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   AgentPerformance                               │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ agent (FK)                                                       │
│ period_start, period_end                                        │
│                                                                  │
│ # Metrics                                                        │
│ tickets_assigned                                                │
│ tickets_resolved                                                │
│ tickets_escalated                                               │
│ avg_resolution_time (minutes)                                   │
│ first_response_time (minutes)                                   │
│ customer_satisfaction_score                                      │
│                                                                  │
│ # Sales Metrics                                                  │
│ policies_sold                                                    │
│ total_premium_value                                             │
│ conversion_rate                                                  │
│ leads_handled                                                    │
│ leads_converted                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Permission Matrix

| Action                        | L1 | L2 | L3 | L4 | L5 |
|-------------------------------|----|----|----|----|-----|
| View tickets                  | ✓  | ✓  | ✓  | ✓  | ✓   |
| Pick tickets (self-assign)    | ✗  | ✓  | ✓  | ✓  | ✓   |
| Create tickets                | ✗  | ✓  | ✓  | ✓  | ✓   |
| Add notes                     | ✓  | ✓  | ✓  | ✓  | ✓   |
| Resolve tickets               | ✗  | ✗  | ✓  | ✓  | ✓   |
| Approve claims (< 50K)        | ✗  | ✗  | ✓  | ✓  | ✓   |
| Approve claims (< 500K)       | ✗  | ✗  | ✗  | ✓  | ✓   |
| Approve claims (any)          | ✗  | ✗  | ✗  | ✗  | ✓   |
| Issue policies                | ✗  | ✓  | ✓  | ✓  | ✓   |
| Cancel policies               | ✗  | ✗  | ✓  | ✓  | ✓   |
| Assign to others              | ✗  | ✗  | ✗  | ✓  | ✓   |
| View performance reports      | ✗  | ✗  | ✗  | ✓  | ✓   |
| Manage workclasses            | ✗  | ✗  | ✗  | ✗  | ✓   |

---

## 5. Workflow Scenarios

### 5.1 Claims Ticket Flow
```
1. Customer submits claim
   └─► System creates Ticket (type=claim, status=open)
       └─► Auto-assign based on:
           - Claim amount → determines required_level
           - Department → CLAIMS
           - Agent availability

2. Agent Dashboard shows available tickets
   └─► Agent "picks" ticket (if within workclass)
       └─► Status → assigned

3. Agent reviews, investigates
   └─► Logs activities, adds notes
   └─► If amount > limit → escalate to higher level

4. Agent approves/rejects
   └─► If within monetary limit → direct approval
   └─► Status → resolved

5. Ticket closed
   └─► Performance metrics updated
```

### 5.2 Policy Application Flow
```
1. Customer applies for policy
   └─► Ticket created (type=policy, status=open)

2. Agent reviews application
   └─► Verifies documents
   └─► Risk assessment

3. Agent issues policy
   └─► Policy generated
   └─► Status → resolved
   └─► Sales metrics updated
```

---

## 6. Dashboard & Monitoring

### 6.1 Agent Dashboard
- **My Queue**: Assigned tickets, sorted by SLA
- **Available Tickets**: Tickets I can pick
- **Recent Activity**: My actions today
- **Performance Summary**: Resolution rate, avg time

### 6.2 Supervisor Dashboard
- **Team Overview**: All agents, their load
- **Unassigned Tickets**: Items needing attention
- **SLA Breaches**: Overdue items
- **Performance Leaderboard**: Top performers

### 6.3 Management Reports
- **Daily/Weekly/Monthly metrics**
- **Conversion funnel**: Leads → Applications → Policies
- **Claims ratio**: Filed vs Approved vs Rejected
- **Revenue by agent**
- **Customer satisfaction trends**

---

## 7. Implementation Plan

### Phase 1: Core Models ✅ COMPLETE
- [x] Create `workflow` app
- [x] WorkClass model
- [x] AgentProfile model
- [x] Ticket model with generic relations
- [x] TicketActivity model
- [x] Migrations

### Phase 2: Assignment System ✅ COMPLETE
- [x] Ticket creation service
- [x] Auto-assignment algorithm
- [x] Self-pickup functionality
- [x] Escalation rules

### Phase 3: Agent Views ✅ COMPLETE
- [x] Agent dashboard
- [x] Ticket queue views
- [x] Ticket detail with actions
- [x] Activity timeline

### Phase 4: Performance Tracking ✅ COMPLETE
- [x] AgentPerformance model
- [x] Metrics calculation service
- [x] Supervisor dashboard (basic)
- [ ] Reports and exports (TODO)

### Phase 5: Integration (TODO)
- [ ] Connect Claims app signals
- [ ] Connect Policies app signals
- [ ] Connect Billing app
- [ ] Signals for auto-ticket creation

---

## 8. API Endpoints

```
/api/workflow/
├── tickets/                    # List/Create tickets
├── tickets/{id}/               # Ticket detail
├── tickets/{id}/pick/          # Self-assign
├── tickets/{id}/assign/        # Assign to agent
├── tickets/{id}/escalate/      # Escalate to higher level
├── tickets/{id}/resolve/       # Mark resolved
├── tickets/{id}/activities/    # Activity log
│
├── workclasses/               # List workclasses
├── agents/                    # List agents
├── agents/{id}/performance/   # Agent metrics
│
├── dashboard/my-queue/        # Agent's tickets
├── dashboard/available/       # Pickable tickets
├── dashboard/stats/           # Performance summary
└── dashboard/team/            # Supervisor view
```

---

## 9. Success Metrics

| Metric                     | Target         |
|----------------------------|----------------|
| Avg First Response Time    | < 30 minutes   |
| Ticket Resolution Rate     | > 85%          |
| SLA Compliance             | > 95%          |
| Customer Satisfaction      | > 4.0/5        |
| Policy Conversion Rate     | > 15%          |
| Agent Utilization          | 70-85%         |

---

## 10. Next Steps

1. **Review & Approve** this proposal
2. **Create workflow app** with core models
3. **Implement ticket system** with assignment
4. **Build agent dashboards** with queues
5. **Add performance tracking**
6. **Integrate with existing apps**

---

*Prepared for ifinsure by Antigravity AI*
