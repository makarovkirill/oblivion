import { SystemStatusResponse, AuditLog, VaultItem, TrustedContact, SettingsData } from '../types';

const API_BASE = '';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Accept': 'application/json',
      ...(options?.headers || {}),
    },
  });

  const isJson = res.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await res.json() : null;

  if (!res.ok) {
    const errorMsg = data?.detail || `Request failed with status ${res.status}`;
    throw new Error(errorMsg);
  }

  return data as T;
}

export const api = {
  getSetupStatus: () => request<{ setup_completed: boolean; language: string }>('/api/setup/status'),

  testTelegram: (token: string, chat_id: string) =>
    request<{ success: boolean; message: string }>('/api/setup/test-telegram', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, chat_id }),
    }),

  testEmail: (data: any) =>
    request<{ success: boolean; message: string }>('/api/setup/test-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  initializeSystem: (payload: any) =>
    request<{ success: boolean; message: string }>('/api/setup/initialize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  getStatus: () => request<SystemStatusResponse>('/api/status'),

  getLogs: (limit: number = 50) => request<{ logs: AuditLog[] }>(`/api/status/logs?limit=${limit}`),

  unlockVault: (password: string) =>
    request<{ success: boolean; message: string }>('/api/auth/unlock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    }),

  lockVault: () =>
    request<{ success: boolean; message: string }>('/api/auth/lock', {
      method: 'POST',
    }),

  checkIn: (passphrase: string) =>
    request<{ success: boolean; message: string }>('/api/checkin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ passphrase }),
    }),

  getVaultItems: () => request<{ items: VaultItem[] }>('/api/vault/items'),

  createVaultItem: (formData: FormData) =>
    request<{ success: boolean; item_id: string }>('/api/vault/items', {
      method: 'POST',
      body: formData,
    }),

  deleteVaultItem: (id: string) =>
    request<{ success: boolean; message: string }>(`/api/vault/items/${id}`, {
      method: 'DELETE',
    }),

  getContacts: () => request<{ contacts: TrustedContact[] }>('/api/contacts'),

  createContact: (data: any) =>
    request<{ success: boolean; contact_id: string; recovery_token: string }>('/api/contacts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  updateContact: (id: string, data: any) =>
    request<{ success: boolean }>(`/api/contacts/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  deleteContact: (id: string) =>
    request<{ success: boolean }>(`/api/contacts/${id}`, {
      method: 'DELETE',
    }),

  getSettings: () => request<SettingsData>('/api/settings'),

  updateSettings: (data: any) =>
    request<{ success: boolean; message: string }>('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  simulateTrigger: () =>
    request<{ success: boolean; plan: any }>('/api/settings/simulate', {
      method: 'POST',
    }),

  panicWipe: (passphrase: string) =>
    request<{ success: boolean; result: any }>('/api/settings/panic-wipe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ passphrase }),
    }),
};
