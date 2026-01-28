/**
 * TODO: Fix flaky WebSocket tests (https://github.com/OpenHands/OpenHands/issues/11944)
 *
 * Several tests in this file are skipped because they fail intermittently in CI
 * but pass locally. The SUSPECTED root cause is that `wsLink.broadcast()` sends messages
 * to ALL connected clients across all tests, causing cross-test contamination
 * when tests run in parallel with Vitest v4.
 */
import { renderHook, waitFor } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  beforeAll,
  afterAll,
  afterEach,
  vi,
} from "vitest";
import { useWebSocket } from "#/hooks/use-websocket";

describe("useWebSocket", () => {
  class MockWebSocket {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSING = 2;
    static CLOSED = 3;

    static instances: MockWebSocket[] = [];

    url: string;
    readyState = MockWebSocket.CONNECTING;
    onopen: ((event: Event) => void) | null = null;
    onmessage: ((event: MessageEvent) => void) | null = null;
    onclose: ((event: CloseEvent) => void) | null = null;
    onerror: ((event: Event) => void) | null = null;

    private listeners = new Map<string, Set<(event: Event) => void>>();

    constructor(url: string) {
      this.url = url;
      MockWebSocket.instances.push(this);

      queueMicrotask(() => {
        this.readyState = MockWebSocket.OPEN;
        this.dispatch("open", new Event("open"));

        if (this.url.includes("error-test.com/ws")) {
          this.close(1006, "Connection failed");
          return;
        }

        this.dispatch(
          "message",
          new MessageEvent("message", { data: "Welcome to the WebSocket!" }),
        );
      });
    }

    addEventListener(type: string, listener: (event: Event) => void) {
      if (!this.listeners.has(type)) {
        this.listeners.set(type, new Set());
      }
      this.listeners.get(type)?.add(listener);
    }

    removeEventListener(type: string, listener: (event: Event) => void) {
      this.listeners.get(type)?.delete(listener);
    }

    send() {
      // no-op for tests
    }

    dispatchEvent(event: Event) {
      this.dispatch(event.type, event);
      return true;
    }

    close(code = 1000, reason = "") {
      if (
        this.readyState === MockWebSocket.CLOSING ||
        this.readyState === MockWebSocket.CLOSED
      ) {
        return;
      }

      this.readyState = MockWebSocket.CLOSING;

      queueMicrotask(() => {
        this.readyState = MockWebSocket.CLOSED;
        this.dispatch(
          "close",
          new CloseEvent("close", { code, reason, wasClean: code === 1000 }),
        );
      });
    }

    private dispatch(type: string, event: Event) {
      this.listeners.get(type)?.forEach((listener) => listener(event));
      const handler = this[`on${type}` as keyof MockWebSocket];
      if (typeof handler === "function") {
        (handler as (event: Event) => void)(event);
      }
    }
  }

  beforeAll(() => {
    vi.stubGlobal("WebSocket", MockWebSocket);
  });

  afterEach(() => {
    MockWebSocket.instances.length = 0;
  });

  afterAll(() => {
    vi.unstubAllGlobals();
  });

  it("should establish a WebSocket connection", async () => {
    const { result } = renderHook(() => useWebSocket("ws://acme.com/ws"));

    // Initially should not be connected
    expect(result.current.isConnected).toBe(false);
    expect(result.current.lastMessage).toBe(null);

    // Wait for connection to be established
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Should receive the welcome message from our mock
    await waitFor(() => {
      expect(result.current.lastMessage).toBe("Welcome to the WebSocket!");
    });

    // Confirm that the WebSocket connection is established when the hook is used
    expect(result.current.socket).toBeTruthy();
  });

  it.skip("should handle incoming messages correctly", async () => {
    const { result } = renderHook(() => useWebSocket("ws://acme.com/ws"));

    // Wait for connection to be established
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Should receive the welcome message from our mock
    await waitFor(() => {
      expect(result.current.lastMessage).toBe("Welcome to the WebSocket!");
    });

    // Send another message from the mock server
    result.current.socket?.dispatchEvent(
      new MessageEvent("message", { data: "Hello from server!" }),
    );

    await waitFor(() => {
      expect(result.current.lastMessage).toBe("Hello from server!");
    });

    // Should have a messages array with all received messages
    expect(result.current.messages).toEqual([
      "Welcome to the WebSocket!",
      "Hello from server!",
    ]);
  });

  it("should handle connection errors gracefully", async () => {
    const { result } = renderHook(() => useWebSocket("ws://error-test.com/ws"));

    // Initially should not be connected and no error
    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).toBe(null);

    // Wait for the connection to fail
    await waitFor(() => {
      expect(result.current.isConnected).toBe(false);
    });

    // Should have error information (the close event should trigger error state)
    await waitFor(() => {
      expect(result.current.error).not.toBe(null);
    });

    expect(result.current.error).toBeInstanceOf(Error);
    // Should have meaningful error message (could be from onerror or onclose)
    expect(
      result.current.error?.message.includes("WebSocket closed with code 1006"),
    ).toBe(true);

    // Should not crash the application
    expect(result.current.socket).toBeTruthy();
  });

  it.skip("should close the WebSocket connection on unmount", async () => {
    const { result, unmount } = renderHook(() =>
      useWebSocket("ws://acme.com/ws"),
    );

    // Wait for connection to be established
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Verify connection is active
    expect(result.current.isConnected).toBe(true);
    expect(result.current.socket).toBeTruthy();

    const closeSpy = vi.spyOn(result.current.socket!, "close");

    // Unmount the component (this should trigger the useEffect cleanup)
    unmount();

    // Verify that WebSocket close was called during cleanup
    expect(closeSpy).toHaveBeenCalledOnce();
  });

  it("should support query parameters in WebSocket URL", async () => {
    const baseUrl = "ws://acme.com/ws";
    const queryParams = {
      token: "abc123",
      userId: "user456",
      version: "v1",
    };

    const { result } = renderHook(() => useWebSocket(baseUrl, { queryParams }));

    // Wait for connection to be established
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Verify that the WebSocket was created with query parameters
    expect(result.current.socket).toBeTruthy();
    expect(result.current.socket!.url).toBe(
      "ws://acme.com/ws?token=abc123&userId=user456&version=v1",
    );
  });

  it("should call onOpen handler when WebSocket connection opens", async () => {
    const onOpenSpy = vi.fn();
    const options = { onOpen: onOpenSpy };

    const { result } = renderHook(() =>
      useWebSocket("ws://acme.com/ws", options),
    );

    // Initially should not be connected
    expect(result.current.isConnected).toBe(false);
    expect(onOpenSpy).not.toHaveBeenCalled();

    // Wait for connection to be established
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // onOpen handler should have been called
    expect(onOpenSpy).toHaveBeenCalledOnce();
  });

  it("should call onClose handler when WebSocket connection closes", async () => {
    const onCloseSpy = vi.fn();
    const options = { onClose: onCloseSpy };

    const { result, unmount } = renderHook(() =>
      useWebSocket("ws://acme.com/ws", options),
    );

    // Wait for connection to be established
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    expect(onCloseSpy).not.toHaveBeenCalled();

    // Unmount to trigger close
    unmount();

    // Wait for onClose handler to be called
    await waitFor(() => {
      expect(onCloseSpy).toHaveBeenCalledOnce();
    });
  });

  it.skip("should call onMessage handler when WebSocket receives a message", async () => {
    const onMessageSpy = vi.fn();
    const options = { onMessage: onMessageSpy };

    const { result } = renderHook(() =>
      useWebSocket("ws://acme.com/ws", options),
    );

    // Wait for connection to be established
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Should receive the welcome message from our mock
    await waitFor(() => {
      expect(result.current.lastMessage).toBe("Welcome to the WebSocket!");
    });

    // onMessage handler should have been called for the welcome message
    expect(onMessageSpy).toHaveBeenCalledOnce();

    // Send another message from the mock server
    result.current.socket?.dispatchEvent(
      new MessageEvent("message", { data: "Hello from server!" }),
    );

    await waitFor(() => {
      expect(result.current.lastMessage).toBe("Hello from server!");
    });

    // onMessage handler should have been called twice now
    expect(onMessageSpy).toHaveBeenCalledTimes(2);
  });

  it("should call onError handler when WebSocket encounters an error", async () => {
    const onErrorSpy = vi.fn();
    const options = { onError: onErrorSpy };

    const { result } = renderHook(() =>
      useWebSocket("ws://error-test.com/ws", options),
    );

    // Initially should not be connected and no error
    expect(result.current.isConnected).toBe(false);
    expect(onErrorSpy).not.toHaveBeenCalled();

    // Wait for the connection to fail
    await waitFor(() => {
      expect(result.current.isConnected).toBe(false);
    });

    // Should have error information
    await waitFor(() => {
      expect(result.current.error).not.toBe(null);
    });

    // onError handler should have been called
    expect(onErrorSpy).toHaveBeenCalled();
  });

  it.skip("should provide sendMessage function to send messages to WebSocket", async () => {
    const { result } = renderHook(() => useWebSocket("ws://acme.com/ws"));

    // Wait for connection to be established
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Should have a sendMessage function
    expect(result.current.sendMessage).toBeDefined();
    expect(typeof result.current.sendMessage).toBe("function");

    // Mock the WebSocket send method
    const sendSpy = vi.spyOn(result.current.socket!, "send");

    // Send a message
    result.current.sendMessage("Hello WebSocket!");

    // Verify that WebSocket.send was called with the correct message
    expect(sendSpy).toHaveBeenCalledOnce();
    expect(sendSpy).toHaveBeenCalledWith("Hello WebSocket!");
  });

  it("should not send message when WebSocket is not connected", () => {
    const { result } = renderHook(() => useWebSocket("ws://acme.com/ws"));

    // Initially should not be connected
    expect(result.current.isConnected).toBe(false);
    expect(result.current.sendMessage).toBeDefined();

    // Mock the WebSocket send method (even though socket might be null)
    const sendSpy = vi.fn();
    if (result.current.socket) {
      vi.spyOn(result.current.socket, "send").mockImplementation(sendSpy);
    }

    // Try to send a message when not connected
    result.current.sendMessage("Hello WebSocket!");

    // Verify that WebSocket.send was not called
    expect(sendSpy).not.toHaveBeenCalled();
  });
});
