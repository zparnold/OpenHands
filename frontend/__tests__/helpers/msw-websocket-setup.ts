import { ws } from "msw";

/**
 * Creates a WebSocket link for MSW testing
 * @param url - WebSocket URL to mock (default: "ws://localhost/events/socket")
 * @returns MSW WebSocket link
 */
export const createWebSocketLink = (url = "ws://localhost/events/socket") =>
  ws.link(url);

/**
 * Standard WebSocket link for conversation WebSocket handler tests.
 * Use with the global server: server.use(wsLink.addEventListener(...))
 * Updated to use the V1 WebSocket URL pattern: /sockets/events/{conversationId}
 */
export const conversationWebSocketLink = createWebSocketLink(
  "ws://localhost:3000/sockets/events/*",
);
