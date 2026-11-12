export type Language = 'en' | 'ru';

export type SwitchState = 'ACTIVE' | 'GRACE_PERIOD' | 'TRIGGERED' | 'NOT_CONFIGURED';

export interface SwitchStatus {
  setup_completed: boolean;
  status: SwitchState;
  remaining_seconds: number;
  interval_seconds?: number;
  grace_seconds?: number;
  last_checkin_timestamp?: number;
  last_checkin_str?: string;
  next_deadline_str?: string;
  grace_deadline_str?: string;
  interval_str?: string;
  grace_str?: string;
  unlocked_session?: boolean;
  telegram_connected?: boolean;
  telegram_username?: string | null;
}

export interface WindowsSecurityContext {
  is_admin: boolean;
  task_scheduler: {
    registered: boolean;
    status: string;
    task_name?: string;
    details?: string;
  };
  platform: string;
}

export interface TelegramInfo {
  connected: boolean;
  username: string | null;
}

export interface SystemStatusResponse {
  switch: SwitchStatus;
  windows: WindowsSecurityContext;
  telegram: TelegramInfo;
  language: Language;
}

export interface AuditLog {
  id: number;
  timestamp: number;
  event_type: string;
  details: string;
  severity: 'INFO' | 'WARNING' | 'DANGER';
}

export type VaultCategory = 'note' | 'credential' | 'file' | 'target_path';
export type VaultPolicy = 'transfer_and_wipe' | 'wipe_only';

export interface VaultItem {
  id: string;
  title: string;
  category: VaultCategory;
  policy: VaultPolicy;
  target_path: string | null;
  attachment_filename: string | null;
  has_attachment: boolean;
  contact_ids: string[];
  content?: string | null;
  created_at: number;
  updated_at: number;
}

export interface TrustedContact {
  id: string;
  name: string;
  email: string | null;
  telegram_chat_id: string | null;
  recovery_token_hash: string | null;
  public_instructions: string | null;
  created_at: number;
  assigned_items_count: number;
}

export interface SettingsData {
  language: Language;
  checkin_interval_sec: number;
  grace_period_sec: number;
  telegram_bot_token_masked: string;
  has_telegram_token: boolean;
  telegram_owner_chat_id: string;
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_from: string;
  smtp_use_tls: boolean;
}
