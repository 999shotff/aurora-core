/**
 * M27 WebSocket Stream Client.
 *
 * Manages a single WebSocket connection to the Aurora Core backend.
 * Provides subscribe/unsubscribe, automatic reconnection with
 * exponential backoff, heartbeat, and REST fallback integration.
 *
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

import type { OHLCBar } from '../types';
import { WS_BASE } from './config';

// ============================================================
// Types
// ============================================================

export type ConnectionState = 'connecting' | 'live' | 'reconnecting' | 'fallback' | 'offline';

export type ServerMessageType = 'connected' | 'subscribed' | 'unsubscribed' | 'market_update' | 'initial_data' | 'pong' | 'error' | 'ping';
export type ClientMessageType = 'subscribe' | 'unsubscribe' | 'ping' | 'pong';

export interface ServerMessage {
  type: ServerMessageType;
  protocol_version?: number;
  [key: string]: unknown;
}

export interface ConnectedMessage extends ServerMessage {
  type: 'connected';
  server_id: string;
  version: string;
  client_id: string;
  heartbeat_interval: number;
}

export interface SubscribedMessage extends ServerMessage {
  type: 'subscribed';
  asset: string;
  timeframe: string;
  request_id: string;
}

export interface MarketUpdateMessage extends ServerMessage {
  type: 'market_update';
  asset: string;
  timeframe: string;
  bar: OHLCBar;
  provider: string;
  is_demo: boolean;
}

export interface InitialDataMessage extends ServerMessage {
  type: 'initial_data';
  asset: string;
  timeframe: string;
  bars: OHLCBar[];
  count: number;
  provider: string;
  is_demo: boolean;
}

export interface PongMessage extends ServerMessage {
  type: 'pong';
  timestamp: number;
  server_timestamp: string;
}

export interface ErrorMessage extends ServerMessage {
  type: 'error';
  code: string;
  message: string;
  request_id: string;
}

export interface PingMessage extends ServerMessage {
  type: 'ping';
  server_initiated?: boolean;
}

export interface StreamCallbacks {
  onConnectionChange: (state: ConnectionState) => void;
  onInitialData: (bars: OHLCBar[], asset: string, timeframe: string, provider: string, isDemo: boolean) => void;
  onUpdate: (bar: OHLCBar, asset: string, timeframe: string) => void;
  onError: (code: string, message: string) => void;
}

// ============================================================
// Stream Client
// ============================================================

const MAX_RECONNECT_DELAY = 30_000;
const INITIAL_RECONNECT_DELAY = 1_000;
const HEARTBEAT_TIMEOUT = 90_000;

export class MarketStreamService {
  private ws: WebSocket | null = null;
  private url: string;
  private callbacks: StreamCallbacks;
  private state: ConnectionState = 'offline';
  private reconnectDelay = INITIAL_RECONNECT_DELAY;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private lastPong = 0;
  private pendingSubscribe: { asset: string; timeframe: string } | null = null;
  private disposed = false;
  private manualClose = false;

  constructor(callbacks: StreamCallbacks) {
    this.url = WS_BASE + '/ws/stream';
    this.callbacks = callbacks;
  }

  connect() {
    if (this.disposed) return;
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.manualClose = false;
    this._setState('connecting');

    try {
      this.ws = new WebSocket(this.url);
      this.ws.onopen = () => {
        this.reconnectDelay = INITIAL_RECONNECT_DELAY;
      };
      this.ws.onmessage = (event) => this._handleMessage(event.data);
      this.ws.onclose = () => {
        if (!this.manualClose && !this.disposed) {
          this._setState('reconnecting');
          this._scheduleReconnect();
        } else if (this.disposed) {
          this._setState('offline');
        }
      };
      this.ws.onerror = () => {
        this._setState('fallback');
      };
    } catch {
      this._setState('fallback');
      this._scheduleReconnect();
    }
  }

  disconnect() {
    this.manualClose = true;
    this._clearTimers();
    if (this.ws) {
      try { this.ws.close(); } catch { /* ignore */ }
      this.ws = null;
    }
    this._setState('offline');
  }

  subscribe(asset: string, timeframe: string) {
    if (this.state === 'live' && this.ws?.readyState === WebSocket.OPEN) {
      if (this.pendingSubscribe) {
        this._send({ type: 'unsubscribe', asset: this.pendingSubscribe.asset, timeframe: this.pendingSubscribe.timeframe, request_id: crypto.randomUUID() });
      }
      this._send({
        type: 'subscribe',
        asset,
        timeframe,
        request_id: crypto.randomUUID(),
      });
    } else {
      this.pendingSubscribe = { asset, timeframe };
      if (this.state !== 'connecting') {
        this.connect();
      }
    }
  }

  unsubscribe(asset: string, timeframe: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this._send({
        type: 'unsubscribe',
        asset,
        timeframe,
        request_id: crypto.randomUUID(),
      });
    }
  }

  getState(): ConnectionState {
    return this.state;
  }

  destroy() {
    this.disposed = true;
    this.disconnect();
  }

  private _send(msg: object) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  private _handleMessage(raw: string) {
    let msg: ServerMessage;
    try {
      msg = JSON.parse(raw);
    } catch {
      return;
    }

    switch (msg.type) {
      case 'connected':
        this._setState('live');
        this._startHeartbeat((msg as ConnectedMessage).heartbeat_interval || 30);
        if (this.pendingSubscribe) {
          this._send({
            type: 'subscribe',
            asset: this.pendingSubscribe.asset,
            timeframe: this.pendingSubscribe.timeframe,
            request_id: crypto.randomUUID(),
          });
        }
        break;

      case 'initial_data': {
        const init = msg as InitialDataMessage;
        this.callbacks.onInitialData(init.bars, init.asset, init.timeframe, init.provider, init.is_demo);
        this.pendingSubscribe = null;
        break;
      }

      case 'market_update': {
        const upd = msg as MarketUpdateMessage;
        this.callbacks.onUpdate(upd.bar, upd.asset, upd.timeframe);
        break;
      }

      case 'subscribed':
        break;

      case 'unsubscribed':
        break;

      case 'pong':
        this.lastPong = Date.now();
        break;

      case 'ping':
        this._send({ type: 'pong', timestamp: Date.now() });
        break;

      case 'error': {
        const err = msg as ErrorMessage;
        this.callbacks.onError(err.code, err.message);
        break;
      }
    }
  }

  private _setState(state: ConnectionState) {
    if (this.state !== state) {
      this.state = state;
      this.callbacks.onConnectionChange(state);
    }
  }

  private _scheduleReconnect() {
    if (this.disposed || this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      if (!this.disposed && this.state !== 'live') {
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, MAX_RECONNECT_DELAY);
        this.connect();
      }
    }, this.reconnectDelay);
  }

  private _startHeartbeat(interval: number) {
    this._clearHeartbeat();
    this.lastPong = Date.now();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState !== WebSocket.OPEN) return;
      if (Date.now() - this.lastPong > HEARTBEAT_TIMEOUT) {
        try { this.ws.close(); } catch { /* ignore */ }
        this._setState('reconnecting');
        this._scheduleReconnect();
        return;
      }
      this._send({ type: 'ping', timestamp: Date.now() });
    }, interval * 1000);
  }

  private _clearHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private _clearTimers() {
    this._clearHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}
