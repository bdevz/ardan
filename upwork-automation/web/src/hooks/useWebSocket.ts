import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

export interface WebSocketOptions {
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  clientId?: string;
}

export type ConnectionStatus = 'Connecting' | 'Connected' | 'Disconnected' | 'Reconnecting' | 'Error';

export const useWebSocket = (url: string, options: WebSocketOptions = {}) => {
  const {
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    heartbeatInterval = 30000,
    clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  } = options;

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('Connecting');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const heartbeatTimer = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
  const isManualClose = useRef(false);

  const connect = useCallback(() => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = process.env.NODE_ENV === 'development' ? 'localhost:8000' : window.location.host;
      const wsUrl = `${protocol}//${host}${url}?client_id=${clientId}`;
      
      setConnectionStatus('Connecting');
      setError(null);
      
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setConnectionStatus('Connected');
        reconnectAttempts.current = 0;
        setError(null);
        
        // Start heartbeat
        if (heartbeatTimer.current) {
          clearInterval(heartbeatTimer.current);
        }
        heartbeatTimer.current = setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ type: 'ping', timestamp: new Date().toISOString() }));
          }
        }, heartbeatInterval);
      };

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          // Handle pong responses
          if (message.type === 'pong') {
            return;
          }
          
          setLastMessage({
            type: message.type,
            data: message.data,
            timestamp: message.timestamp || new Date().toISOString(),
          });
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
          setError('Failed to parse message');
        }
      };

      ws.current.onclose = (event) => {
        if (heartbeatTimer.current) {
          clearInterval(heartbeatTimer.current);
          heartbeatTimer.current = null;
        }
        
        if (!isManualClose.current && reconnectAttempts.current < maxReconnectAttempts) {
          setConnectionStatus('Reconnecting');
          reconnectAttempts.current++;
          
          reconnectTimer.current = setTimeout(() => {
            connect();
          }, reconnectInterval * Math.pow(1.5, reconnectAttempts.current - 1)); // Exponential backoff
        } else {
          setConnectionStatus('Disconnected');
          if (reconnectAttempts.current >= maxReconnectAttempts) {
            setError('Max reconnection attempts reached');
          }
        }
      };

      ws.current.onerror = (event) => {
        console.error('WebSocket error:', event);
        setConnectionStatus('Error');
        setError('Connection error occurred');
      };

    } catch (err) {
      console.error('Error creating WebSocket connection:', err);
      setConnectionStatus('Error');
      setError('Failed to create connection');
    }
  }, [url, clientId, reconnectInterval, maxReconnectAttempts, heartbeatInterval]);

  const disconnect = useCallback(() => {
    isManualClose.current = true;
    
    if (heartbeatTimer.current) {
      clearInterval(heartbeatTimer.current);
      heartbeatTimer.current = null;
    }
    
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
    
    setConnectionStatus('Disconnected');
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      try {
        const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
        ws.current.send(messageStr);
        return true;
      } catch (err) {
        console.error('Error sending WebSocket message:', err);
        setError('Failed to send message');
        return false;
      }
    }
    return false;
  }, []);

  const reconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    reconnectAttempts.current = 0;
    isManualClose.current = false;
    connect();
  }, [connect]);

  useEffect(() => {
    isManualClose.current = false;
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    connectionStatus,
    lastMessage,
    error,
    sendMessage,
    reconnect,
    disconnect,
    isConnected: connectionStatus === 'Connected',
    reconnectAttempts: reconnectAttempts.current,
  };
};