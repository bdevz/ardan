import '@testing-library/jest-dom';

// Mock ResizeObserver for recharts
global.ResizeObserver = class ResizeObserver {
  constructor(_callback: ResizeObserverCallback) {
    // Mock implementation
  }
  
  observe() {}
  unobserve() {}
  disconnect() {}
} as any;

// Mock WebSocket for tests
global.WebSocket = class WebSocket {
  constructor(_url: string) {
    // Mock implementation
  }
  
  close() {}
  send() {}
  
  onopen = null;
  onclose = null;
  onmessage = null;
  onerror = null;
  readyState = 1;
} as any;

// Mock localStorage
Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
  },
  writable: true,
});

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});