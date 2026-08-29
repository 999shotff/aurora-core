/**
 * Shared configuration for Aurora Core frontend.
 * Single source of truth for API URLs.
 */

export const API_BASE = (import.meta.env.VITE_API_URL || 'https://aurora-core-1-txvl.onrender.com').replace(/\/$/, '');

export const WS_BASE = API_BASE.replace(/^http/, 'ws');
