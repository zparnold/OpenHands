# Desired Features & Roadmap

This document outlines the desired feature set and architectural requirements for extending the OpenHands platform. These features aim to robustly support multi-user environments, complex integrations, and scalable operations.

## 1. Authentication & Identity System

The platform requires a robust identity management system that moves beyond simple token-based access.

*   **OAuth2/OIDC Integration**: Support for standard OAuth2 and OpenID Connect flows (e.g., Microsoft Entra integration).
*   **User Identity**: Distinct user profiles with associated metadata (email, display name).
*   **Token Management**:
    *   Support for JWT validation.

## 2. Persistent Storage & Relational Database

To support complex persistent state, we need to transition from file-based storage to a relational database architecture.

*   **Database**: PostgreSQL integration via an ORM (e.g., SQLAlchemy).
*   **Core Entities**:
    *   **Users**: Secure storage of user identities.
    *   **Organizations**: Grouping users into tenants.
    *   **Sessions**: Persistent session state linked to users/orgs.
*   **Secrets Management**: Secure, encrypted storage for third-party API keys (Azure DevOps, Jira, etc.) at the user or organization level.

## 3. Advanced Integration System

We need a flexible "Manager" pattern to handle complex, bidirectional integrations with external tools, moving beyond simple Git operations.

### Core Architecture
*   **Integration Manager Interface**: A standardized interface for:
    *   Receiving incoming webhooks/messages.
    *   Sending outgoing messages/notifications.
    *   Starting agent jobs from external triggers.
*   **Source Management**: handling of diverse event sources (Azure DevOps, Microsoft Teams, Jira,...).

### Specific Integration Requirements
*   **Jira**:
    *   Parse complex webhook payloads.
    *   Authenticate users against Jira instances.
    *   Trigger conversation jobs from ticket creation or updates.
*   **Microsoft Teams**:
    *   Bot-based interaction (listen for @mentions).
    *   Context inference (identifying repos from chat messages).
    *   Interactive UI elements (Adaptive Cards) within Teams.
*   **Azure DevOps (Advanced)**:
    *   Dynamic OAuth token management (refreshing Entra ID tokens automatically).
    *   Background synchronization of repository metadata.
    *   Handling of advanced events (PR comments, checks).

## 4. Multi-Tenancy & Organization Management

The system must support multiple tenants (Organizations) sharing the same infrastructure.

*   **Organization Model**: Users belong to Organizations.
*   **Scoped Resources**: Settings, Secrets, and related data must be scoped to the Organization.
*   **Member Management**:
    *   Role-based access (Admin vs Member).
    *   Email invitation system for onboarding users.

## 6. Server Architecture & Advanced Features

### 6.1 Sharing & Collaboration
*   **Read-Only Views**: Ability to generate public or shared links for specific conversations.
*   **Shared Events**: API support for retrieving event streams for shared sessions.

### 6.2 Extended MCP (Model Context Protocol) Support
*   **Stateless Transport**: Implementation of HTTP-based MCP transport to support load-balanced, stateless server environments (replacing stateful SSE where necessary).
*   **Dynamic Server Mounting**: Capability to dynamically mount external MCP servers (e.g., Search tools) based on configuration or user entitlement.

### 6.3 Async Event Processing
*   **Event Webhooks**: A batch-processing system for high-volume event streams, supporting background processing to minimize latency.
*   **Conversation Callbacks**: A trigger system to send asynchronous notifications (e.g., to Microsoft Teams or Azure DevOps) when agent state changes (e.g., "Pausing for User Input", "Task Completed").

### 6.4 Maintenance & Operations
*   **Background Tasks**: A system for running short-lived maintenance jobs (e.g., schema migrations, data cleanup) without requiring full system downtime.
*   **Infrastructure**: Redis integration for distributed caching, rate limiting, and task queues.
